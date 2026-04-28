#!/usr/bin/env python3
"""
Borderou Processing Pipeline
=============================

Processes all Excel files in app/models/Borderou/In/ and produces 53-column
XLSX output files in app/models/Borderou/Out/, matching the reference format in:
  app/models/Borderou/Out/borderou - Borderou_de_Vanzare_(FF1).xlsx

Pipeline per file:
  1. Convert Excel to CSV (via openpyxl) into tmp/
  2. Parse CSV: detect data rows dynamically, extract standardized fields
  3. Transform to 53-column import format (21% TVA rows first, then 11%)
  4. Write output as XLSX via openpyxl
  5. Clean up temporary CSV

Usage: python -m app.modules.borderou.main
"""

import csv
import os
import re
from datetime import datetime

import openpyxl
import pandas as pd


# ── Project root & directories ──────────────────────────────────────────────

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
INPUT_DIR = os.path.join(PROJECT_ROOT, "app", "models", "Borderou", "In")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "app", "models", "Borderou", "Out")
TMP_DIR = os.path.join(PROJECT_ROOT, "tmp")


# ── File-type configuration ─────────────────────────────────────────────────
# Each entry: pattern → (serie, cod_depozit, denumire_articol, cont_casa, out_tag)
# Longer patterns are checked first (sorted by length desc at lookup time).

FILE_TYPE_CONFIG = {
    "DEPOZIT": None,  # skip signal
    "FF1": ("F", 3, "ff 1", 5311, "FF1"),
    "FF 2": ("F", 3, "FF 2", 5311, "FF2"),
    "FF2": ("F", 3, "FF 2", 5311, "FF2"),
    "AUTOS": ("A", 1, "autoservire", 5311, "AUTOS"),
    "REST": ("R", 2, "restaurant", 5311, "REST"),
    # ── Branch M ──────────────────────────────────────────
    # serie is a format string; {pos:04d} / {pos} is replaced with the POS number
    # extracted from the Explicatii column (column E) of each row.
    "M1": ("BFM1 {pos:04d}", 1, "marfa m1 ", 53111, "M1"),
    "M2": ("BFM2 {pos}", 2, "marfa m2 ", 53112, "M2"),
    "M3": ("BFM3", 3, "marfa m3 ", 53113, "M3"),
}


def _match_file_type(filename: str):
    """Return the config tuple for the given filename, or 'skip' / None.

    Falls back to AUTOS for any plain 'Borderou' file that has no recognised
    type suffix (e.g. a PDF exported without a branch/type tag in its name).
    """
    upper = filename.upper()
    # Check longer patterns first to avoid partial matches
    for pattern in sorted(FILE_TYPE_CONFIG, key=len, reverse=True):
        if pattern in upper:
            return FILE_TYPE_CONFIG[pattern]
    # Fallback: a plain borderou file with no type tag → treat as AUTOS
    if "BORDEROU" in upper:
        return FILE_TYPE_CONFIG["AUTOS"]
    return None


def _output_filename(tag: str) -> str:
    return f"borderou - Borderou_de_Vanzare_({tag}).xlsx"


# ── 53-column output header ─────────────────────────────────────────────────

OUTPUT_COLUMNS = [
    "Serie document",
    "Numar document",
    "Cod depozit",
    "Nume depozit",
    "Data document",
    "Data scadenta",
    "Cod tip factura SAF-T",
    "Cod partener",
    "Nume partener",
    "Atribut fiscal",
    "Cod fiscal",
    "Nr.Reg.Com.",
    "Rezidenta",
    "Tara",
    "Judet",
    "Localitate",
    "Strada",
    "Numar",
    "Bloc",
    "Scara",
    "Etaj",
    "Apartament",
    "Cod postal",
    "Cod agent",
    "Valoare neta totala",
    "Valoare TVA",
    "Total document",
    "Numar bonuri fiscale",
    "Card",
    "Cont banca",
    "Numerar",
    "Cont casa",
    "Tichete",
    "Cont tichete",
    "Cont TVA",
    "Cod articol",
    "Cod de bare",
    "Denumire articol",
    "Cantitate",
    "Cod lot",
    "Data expirare",
    "Nr seriale",
    "Tip miscare SAF-T",
    "Cont serviciu",
    "Pret cu TVA",
    "Total fara TVA",
    "Total TVA",
    "Total cu TVA",
    "Optiune TVA",
    "Cota TVA",
    "Cod TVA SAF-T",
    "Discount",
    "DiscountLinie",
]
assert len(OUTPUT_COLUMNS) == 53


# ── Step 1: Excel → CSV ─────────────────────────────────────────────────────


def _excel_to_csv(xlsx_path: str, csv_path: str) -> None:
    """Convert an xlsx file to CSV using openpyxl (data_only)."""
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb.active
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in ws.iter_rows(values_only=True):
            writer.writerow(row)
    wb.close()


# ── Step 2: Parse CSV → standardized rows ───────────────────────────────────


def _is_data_row(cells: list) -> bool:
    """Return True if the first cell is a valid integer (Nr. Crt)."""
    v = cells[0]
    if v is None or str(v).strip() == "":
        return False
    try:
        int(float(str(v).strip()))
        return True
    except (ValueError, TypeError):
        return False


def _detect_column_layout(csv_path: str) -> dict:
    """
    Scan the header rows of the CSV to determine column indices.
    Returns a dict mapping standardized field names to 0-based column indices.

    We look for the header row that contains "Total Valoare" and related
    sub-header rows to map column positions.
    """
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = [next(reader, None) for _ in range(6)]  # read first 6 rows

    # Find the row containing "Total Valoare" (typically row index 2 or 3)
    total_val_col = None
    for row in rows:
        if row is None:
            continue
        for ci, cell in enumerate(row):
            if cell and "Total Valoare" in str(cell):
                total_val_col = ci
                break
        if total_val_col is not None:
            break

    if total_val_col is None:
        # Fallback: return None, file is likely empty
        return None

    # Find Nr. Doc(Z) and Data columns. They are at fixed positions 2 and 3
    # in most variants, so use them directly.
    nr_doc_col = 2
    data_col = 3

    # Now map the rest relative to "Total Valoare".
    # Standard layout (FF1, FF2, REST): Total Valoare at col 6
    #   21% Baza = 9,  21% TVA = 10, 11% Baza = 11, 11% TVA = 12, Netax Baza = 18
    # AUTOS layout:                     Total Valoare at col 5
    #   21% Baza = 8,  21% TVA = 10, 11% Baza = 11, 11% TVA = 12, Netax Baza = 18

    # After analysing both variants:
    # Standard: TV=6, gaps, 21B=9 (+3), 21T=10 (+4), 11B=11 (+5), 11T=12 (+6), NB=18 (+12)
    # AUTOS:    TV=5, gaps, 21B=8 (+3), 21T=10 (+5), 11B=11 (+6), 11T=12 (+7), NB=18 (+13)
    # Actually looking at the raw CSV data more carefully:
    #
    # Standard (FF1): columns are
    #   0:NrCrt, 1:Denumire, 2:NrDoc, 3:Data, 4:Explicatii, 5:empty,
    #   6:Total_Valoare, 7:Scutit_drept, 8:Scutit_fara,
    #   9:Tax_21_Baza, 10:Tax_21_TVA, 11:Tax_11_Baza, 12:Tax_11_TVA,
    #   13:empty, 14:Nefolosit_Baza, 15:Nef_TVA, 16:Nef_Baza, 17:Nef_TVA,
    #   18:Netax_Baza, 19:Netax_TVA
    #
    # AUTOS: columns are
    #   0:NrCrt, 1:Denumire, 2:NrDoc, 3:Data, 4:Explicatii,
    #   5:Total_Valoare, 6:Scutit_drept, 7:Scutit_fara,
    #   8:Tax_21_Baza, 9:21_TVA=empty_in_header, 10:Tax_21_TVA_val,
    #   11:Tax_11_Baza, 12:Tax_11_TVA,
    #   13:empty, 14:Nefolosit_Baza, 15:Nef_TVA, 16:Nef_Baza, 17:Nef_TVA,
    #   18:Netax_Baza, 19:Netax_TVA
    #
    # So the offset from Total_Valoare:
    #   Standard: 21B = TV+3, 21T = TV+4, 11B = TV+5, 11T = TV+6, NB = TV+12
    #   AUTOS:    21B = TV+3, 21T = TV+5, 11B = TV+6, 11T = TV+7, NB = TV+13
    #
    # Wait, let me re-check AUTOS data row:
    # 1,Z POS,843,2026-02-02,Z emis...,10545,0,0,445.87,93.63,,9004.05,990.45,,0,0,0,0,11,0,,,
    # col5=10545(TV), col6=0, col7=0, col8=445.87(21B), col9=93.63(21T), col10=empty
    # col11=9004.05(11B), col12=990.45(11T), ...col18=11(NB)
    # So AUTOS: 21B = TV+3, 21T = TV+4, 11B = TV+6, 11T = TV+7, NB = TV+13
    # Hmm, but col10 is empty between 21T and 11B
    #
    # Actually let me count again for AUTOS row:
    # 0:1, 1:Z POS, 2:843, 3:2026-02-02, 4:Z emis..., 5:10545, 6:0, 7:0,
    # 8:445.87, 9:93.63, 10:empty, 11:9004.05, 12:990.45, 13:empty,
    # 14:0, 15:0, 16:0, 17:0, 18:11, 19:0
    #
    # 21B=col8 (TV+3), 21T=col9 (TV+4), 11B=col11 (TV+6), 11T=col12 (TV+7), NB=col18 (TV+13)
    #
    # Standard FF1 row:
    # 0:1, 1:Z POS, 2:361, 3:2026-02-01, 4:Z emis..., 5:empty, 6:3735.35, 7:0, 8:0,
    # 9:17.77, 10:3.73, 11:3345.36, 12:367.99, 13:empty,
    # 14:0, 15:0, 16:0, 17:0, 18:0.5, 19:0
    #
    # 21B=col9 (TV+3), 21T=col10 (TV+4), 11B=col11 (TV+5), 11T=col12 (TV+6), NB=col18 (TV+12)
    #
    # So the pattern varies. Let me use a more robust approach:
    # After Total_Valoare, there are always 2 "scutit" columns, then the tax data.
    # - Standard: TV, scutit1, scutit2, 21B, 21T, 11B, 11T ...
    # - AUTOS:    TV, scutit1, scutit2, 21B, 21T, empty, 11B, 11T ...
    #
    # It's simplest to just use the known offsets based on where TV is.

    if total_val_col == 6:
        # Standard layout
        return {
            "Nr_Doc_Z": nr_doc_col,
            "Data": data_col,
            "Total_Valoare": 6,
            "Taxabile_21_Baza": 9,
            "Taxabile_21_TVA": 10,
            "Taxabile_11_Baza": 11,
            "Taxabile_11_TVA": 12,
            "Netaxabil_Baza": 18,
        }
    elif total_val_col == 5:
        # AUTOS-like layout
        return {
            "Nr_Doc_Z": nr_doc_col,
            "Data": data_col,
            "Total_Valoare": 5,
            "Taxabile_21_Baza": 8,
            "Taxabile_21_TVA": 9,
            "Taxabile_11_Baza": 11,
            "Taxabile_11_TVA": 12,
            "Netaxabil_Baza": 18,
        }
    else:
        # Unknown layout — try standard offsets from detected TV column
        tv = total_val_col
        return {
            "Nr_Doc_Z": nr_doc_col,
            "Data": data_col,
            "Total_Valoare": tv,
            "Taxabile_21_Baza": tv + 3,
            "Taxabile_21_TVA": tv + 4,
            "Taxabile_11_Baza": tv + 5,
            "Taxabile_11_TVA": tv + 6,
            "Netaxabil_Baza": tv + 12,
        }


def _extract_pos(explicatii: str | None) -> int | None:
    """Extract POS terminal number from an Explicatii string like 'Z emis la POS nr.14 ...'."""
    if not explicatii:
        return None
    m = re.search(r'POS\s+nr\.(\d+)', str(explicatii), re.IGNORECASE)
    return int(m.group(1)) if m else None


def _safe_float(value, default=0.0) -> float:
    """Convert a value to float, returning default for None/empty/invalid."""
    if value is None or str(value).strip() == "":
        return default
    try:
        return float(str(value).strip())
    except (ValueError, TypeError):
        return default


def _parse_csv_to_rows(csv_path: str) -> list[dict] | None:
    """
    Parse a CSV file and return a list of standardized row dicts.
    Returns None if no data rows are found.
    """
    col_layout = _detect_column_layout(csv_path)
    if col_layout is None:
        return None

    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for cells in reader:
            if not _is_data_row(cells):
                continue

            def col(name):
                idx = col_layout[name]
                return cells[idx] if idx < len(cells) else None

            # Parse date
            raw_date = col("Data")
            try:
                dt = pd.to_datetime(raw_date)
            except Exception:
                continue  # skip rows with unparseable dates

            # Skip rows where Nr. Doc(Z) is not a plain number (e.g. 'AMT 2539')
            nr_doc_raw = col("Nr_Doc_Z")
            try:
                nr_doc = int(float(str(nr_doc_raw).strip()))
            except (ValueError, TypeError):
                continue

            rows.append(
                {
                    "Nr_Doc_Z": nr_doc,
                    "Data": dt,
                    "Explicatii": cells[4] if len(cells) > 4 else None,
                    "Total_Valoare": _safe_float(col("Total_Valoare")),
                    "Taxabile_21_Baza": _safe_float(col("Taxabile_21_Baza")),
                    "Taxabile_21_TVA": _safe_float(col("Taxabile_21_TVA")),
                    "Taxabile_11_Baza": _safe_float(col("Taxabile_11_Baza")),
                    "Taxabile_11_TVA": _safe_float(col("Taxabile_11_TVA")),
                    "Netaxabil_Baza": _safe_float(col("Netaxabil_Baza")),
                }
            )

    return rows if rows else None


# ── Step 3: Transform rows → 53-column output ──────────────────────────────


def _build_output_row(
    row: dict,
    serie: str,
    cod_depozit: int,
    denumire: str,
    cont_casa: int,
    cota_tva: int,
    cod_tva_saft: int,
) -> dict:
    """Build one 53-column output row for a given TVA rate."""
    date_str = row["Data"].strftime("%Y%m%d")
    total_minus_netax = row["Total_Valoare"] - row["Netaxabil_Baza"]

    if cota_tva == 21:
        baza = row["Taxabile_21_Baza"]
        tva = row["Taxabile_21_TVA"]
    else:
        baza = row["Taxabile_11_Baza"]
        tva = row["Taxabile_11_TVA"]

    return {
        "Serie document": serie,
        "Numar document": row["Nr_Doc_Z"],
        "Cod depozit": cod_depozit,
        "Nume depozit": "",
        "Data document": date_str,
        "Data scadenta": date_str,
        "Cod tip factura SAF-T": 380,
        "Cod partener": "",
        "Nume partener": "",
        "Atribut fiscal": "",
        "Cod fiscal": "",
        "Nr.Reg.Com.": "",
        "Rezidenta": "",
        "Tara": "",
        "Judet": "",
        "Localitate": "",
        "Strada": "",
        "Numar": "",
        "Bloc": "",
        "Scara": "",
        "Etaj": "",
        "Apartament": "",
        "Cod postal": "",
        "Cod agent": "",
        "Valoare neta totala": baza,
        "Valoare TVA": tva,
        "Total document": total_minus_netax,
        "Numar bonuri fiscale": "",
        "Card": 0,
        "Cont banca": 5125,
        "Numerar": total_minus_netax,
        "Cont casa": cont_casa,
        "Tichete": 0,
        "Cont tichete": 5328,
        "Cont TVA": 4427,
        "Cod articol": f"{denumire} {cota_tva}%",
        "Cod de bare": "",
        "Denumire articol": denumire,
        "Cantitate": 1,
        "Cod lot": "",
        "Data expirare": "",
        "Nr seriale": "",
        "Tip miscare SAF-T": "",
        "Cont serviciu": "",
        "Pret cu TVA": baza + tva,
        "Total fara TVA": baza,
        "Total TVA": tva,
        "Total cu TVA": baza + tva,
        "Optiune TVA": "Taxabile",
        "Cota TVA": cota_tva,
        "Cod TVA SAF-T": cod_tva_saft,
        "Discount": "",
        "DiscountLinie": "",
    }


def _build_m_output_row(
    row: dict,
    serie: str,
    cod_depozit: int,
    denumire: str,
    cont_casa: int,
    cota_tva: int,
    cod_tva_saft: int,
) -> dict:
    """Build one 53-column output row for Branch M (M1/M2/M3).

    If `serie` contains a ``{pos}`` placeholder, it is resolved using the POS
    number extracted from the row's Explicatii field.
    """
    # Resolve per-row serie from POS number in Explicatii when the template
    # contains a {pos} placeholder (M1/M2 configs).
    if "{pos" in serie:
        pos_num = _extract_pos(row.get("Explicatii"))
        if pos_num is not None:
            serie = serie.format(pos=pos_num)
        else:
            # No POS found — strip the placeholder so we get a clean fallback.
            serie = re.sub(r'\{pos[^}]*\}', '', serie).strip()

    date_str = row["Data"].strftime("%Y%m%d")
    total_minus_netax = row["Total_Valoare"] - row["Netaxabil_Baza"]

    if cota_tva == 21:
        baza = row["Taxabile_21_Baza"]
        tva = row["Taxabile_21_TVA"]
    else:
        baza = row["Taxabile_11_Baza"]
        tva = row["Taxabile_11_TVA"]

    return {
        "Serie document": serie,
        "Numar document": row["Nr_Doc_Z"],
        "Cod depozit": cod_depozit,
        "Nume depozit": "",
        "Data document": date_str,
        "Data scadenta": date_str,
        "Cod tip factura SAF-T": 380,
        "Cod partener": "",
        "Nume partener": "",
        "Atribut fiscal": "",
        "Cod fiscal": "",
        "Nr.Reg.Com.": "",
        "Rezidenta": "",
        "Tara": "",
        "Judet": "",
        "Localitate": "",
        "Strada": "",
        "Numar": "",
        "Bloc": "",
        "Scara": "",
        "Etaj": "",
        "Apartament": "",
        "Cod postal": "",
        "Cod agent": "",
        "Valoare neta totala": baza,
        "Valoare TVA": tva,
        "Total document": total_minus_netax,
        "Numar bonuri fiscale": "",
        "Card": 0,
        "Cont banca": 5125,
        "Numerar": total_minus_netax,
        "Cont casa": cont_casa,
        "Tichete": 0,
        "Cont tichete": 5328,
        "Cont TVA": 4427,
        "Cod articol": f"{denumire} {cota_tva}%",
        "Cod de bare": "",
        "Denumire articol": denumire,
        "Cantitate": 1,
        "Cod lot": "",
        "Data expirare": "",
        "Nr seriale": "",
        "Tip miscare SAF-T": "",
        "Cont serviciu": "",
        "Pret cu TVA": baza + tva,
        "Total fara TVA": baza,
        "Total TVA": tva,
        "Total cu TVA": baza + tva,
        "Optiune TVA": "Taxabile",
        "Cota TVA": cota_tva,
        "Cod TVA SAF-T": cod_tva_saft,
        "Discount": "",
        "DiscountLinie": "",
    }


def _transform(
    rows: list[dict], serie: str, cod_depozit: int, denumire: str, cont_casa: int,
    is_m_branch: bool = False,
) -> pd.DataFrame:
    """Transform standardized rows into a 53-column DataFrame."""
    out_rows_21 = []
    out_rows_11 = []

    builder = _build_m_output_row if is_m_branch else _build_output_row

    for row in rows:
        out_rows_21.append(
            builder(row, serie, cod_depozit, denumire, cont_casa, 21, 310344)
        )
        out_rows_11.append(
            builder(row, serie, cod_depozit, denumire, cont_casa, 11, 310351)
        )

    all_rows = out_rows_21 + out_rows_11
    return pd.DataFrame(all_rows, columns=OUTPUT_COLUMNS)


# ── Step 4: Write XLSX ──────────────────────────────────────────────────────


def _write_xlsx(df: pd.DataFrame, xlsx_path: str) -> None:
    """Write a DataFrame to XLSX using openpyxl via pandas."""
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")


# ── Pipeline ────────────────────────────────────────────────────────────────


class BorderouPipeline:
    """End-to-end pipeline: In/*.xlsx → Out/*.xlsx (53 columns)."""

    def __init__(self, input_dir: str | None = None, output_dir: str | None = None):
        self.input_dir = input_dir or INPUT_DIR
        self.output_dir = output_dir or OUTPUT_DIR
        self.tmp_dir = TMP_DIR
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.tmp_dir, exist_ok=True)

    def process_file(self, excel_path: str) -> str | None:
        """
        Process one Excel file through the full pipeline.
        Returns output path on success, "skipped" if skipped, None on failure.
        """
        filename = os.path.basename(excel_path)
        print(f"\n>> Processing: {filename}")

        # ── Determine file type ──
        cfg = _match_file_type(filename)
        if cfg is None:
            print(f"   Skipping {filename} (DEPOZIT / unknown type)")
            return "skipped"

        serie, cod_depozit, denumire, cont_casa, out_tag = cfg

        # ── Step 1: File → CSV (temp) ──
        csv_name = f"_borderou_tmp_{os.path.splitext(filename)[0]}.csv"
        csv_path = os.path.join(self.tmp_dir, csv_name)
        
        # ── PDF short-circuit: parse directly, no CSV step needed ──────────
        if excel_path.lower().endswith('.pdf'):
            try:
                from app.modules.core.pdf_extractor import extract_borderou_rows_from_pdf
                print("   [1] Extracting rows from PDF...")
                rows = extract_borderou_rows_from_pdf(excel_path)
                if not rows:
                    print(f"   WARNING: No data rows in PDF {filename}, skipping.")
                    return "skipped"
                print(f"       Found {len(rows)} data rows.")
                print("   [2] Transforming to 53-column format...")
                is_m_branch = out_tag in ("M1", "M2", "M3")
                df = _transform(rows, serie, cod_depozit, denumire, cont_casa, is_m_branch=is_m_branch)
                out_path = os.path.join(self.output_dir, _output_filename(out_tag))
                print(f"   [3] Writing XLSX -> {_output_filename(out_tag)}")
                _write_xlsx(df, out_path)
                print(f"   OK: {_output_filename(out_tag)}")
                return out_path
            except Exception as e:
                print(f"   ERROR processing PDF: {e}")
                import traceback
                traceback.print_exc()
                return None

        # ── Excel path ────────────────────────────────────────────────────────
        try:
            print("   [1] Converting Excel to CSV...")
            _excel_to_csv(excel_path, csv_path)
        except Exception as e:
            print(f"   ERROR converting to CSV: {e}")
            return None

        try:
            # ── Step 2: Parse CSV ──
            print("   [2] Parsing CSV...")
            rows = _parse_csv_to_rows(csv_path)
            if rows is None:
                print(f"   WARNING: No data rows in {filename}, skipping.")
                return "skipped"
            print(f"       Found {len(rows)} data rows.")

            # ── Step 3: Transform ──
            print("   [3] Transforming to 53-column format...")
            is_m_branch = out_tag in ("M1", "M2", "M3")
            df = _transform(rows, serie, cod_depozit, denumire, cont_casa, is_m_branch=is_m_branch)

            # ── Step 4: Write XLSX ──
            out_path = os.path.join(self.output_dir, _output_filename(out_tag))
            print(f"   [4] Writing XLSX -> {_output_filename(out_tag)}")
            _write_xlsx(df, out_path)
            print(f"   OK: {_output_filename(out_tag)}")
            return out_path

        except Exception as e:
            print(f"   ERROR: {e}")
            import traceback
            traceback.print_exc()
            return None

        finally:
            # ── Step 5: Cleanup temp CSV ──
            if os.path.exists(csv_path):
                os.remove(csv_path)

    def run_pipeline(self):
        """Process all Excel files in the input directory."""
        print("Borderou Processing Pipeline")
        print("=" * 60)
        print(f"Input:  {self.input_dir}")
        print(f"Output: {self.output_dir}")

        if not os.path.exists(self.input_dir):
            print(f"WARNING: Input directory not found: {self.input_dir}")
            return

        excel_files = sorted(
            os.path.join(self.input_dir, f)
            for f in os.listdir(self.input_dir)
            if f.lower().endswith((".xlsx", ".xls", ".pdf"))
        )

        if not excel_files:
            print(f"WARNING: No Excel/PDF files found in {self.input_dir}")
            return

        print(f"Found {len(excel_files)} Excel file(s)\n")

        processed, failed, skipped = [], [], []

        for excel_file in excel_files:
            try:
                result = self.process_file(excel_file)
                if result == "skipped":
                    skipped.append(excel_file)
                elif result:
                    processed.append(result)
                else:
                    failed.append(excel_file)
            except Exception as e:
                print(f"ERROR processing {os.path.basename(excel_file)}: {e}")
                import traceback

                traceback.print_exc()
                failed.append(excel_file)

        print("\n" + "=" * 60)
        print("PIPELINE SUMMARY")
        print("=" * 60)
        print(f"Processed: {len(processed)} files")
        print(f"Skipped:   {len(skipped)} files")
        print(f"Failed:    {len(failed)} files")

        if processed:
            print("\nGenerated XLSX files:")
            for p in processed:
                print(f"  - {os.path.basename(p)}")
        if skipped:
            print("\nSkipped (no data):")
            for p in skipped:
                print(f"  - {os.path.basename(p)}")
        if failed:
            print("\nFailed files:")
            for p in failed:
                print(f"  - {os.path.basename(p)}")


def main():
    """Entry point."""
    pipeline = BorderouPipeline()
    pipeline.run_pipeline()


if __name__ == "__main__":
    main()
