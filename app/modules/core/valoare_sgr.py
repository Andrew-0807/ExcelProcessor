import os
import re
import pandas as pd
import pdfplumber
import openpyxl
from datetime import datetime
from app.log import info as print  # debug chatter; silent unless MOM_VERBOSE=1

OUTPUT_COLUMNS = [
    "Nr. inreg.", "Tip inregistrare", "Jurnal", "Data", "Data scadenta",
    "Numar document", "Cod tip factura", "Cont debit simbol", "Cont debit titlu",
    "Metoda de plata SAF-T", "Mecanism de plata SAF-T", "Tip Taxa SAF-T",
    "Cod Taxa SAF-T", "Cont credit simbol", "Cont credit titlu",
    "Metoda de plata SAF-T    ", "Mecanism de plata SAFT-T", "Tip Taxa SAF_T",
    "Cod TAXA SAF_T", "Explicatie", "Valoare", "Cod Partener", "Partener CIF",
    "Partener Nume", "Partener Rezidenta", "Partener Judet", "Partener Cont",
    "Angajat CNP", "Angajat Nume", "Angajat Cont", "Optiune TVA", "Cota TVA",
    "Cod TVA SAF-T", "Moneda", "Curs", "Valoare deviza",
    "Stornare - Nr. inreg.", "Incasari/plati", "Diferente curs",
    "TVA la incasare", "Colectare/Deducere TVA", "Efect de incasat/platit",
    "Banca efect", "Centre de cost", "Informatii export", "Punct de lucru",
    "Deductibilitate", "Reevaluare", "Factura simplificata",
    "Borderou de achizitie", "Carnet prod. Agricole", "Contract",
    "Document stornat",
]
assert len(OUTPUT_COLUMNS) == 53

# Matches SGR data lines, e.g.:
#   "Plata Voucher RetuRO 1735 01/02/2026 Returnare garantie SGR 6.00 1013 Casier2"
#   "Plata Numerar 831 01/02/2026 Returnare garantie SGR 76.50 ..."
_DATA_LINE_RE = re.compile(
    r"^(Plata\s+\S+(?:\s+\S+)*?)\s+(\d+)\s+(\d{2}[/\-.]\w+[/\-.]\d{2,4})"
    r"\s+Returnare garantie SGR\s+([\d.,]+)",
    re.IGNORECASE,
)
_PERIOD_RE = re.compile(r"In perioada:\s*\d+\.\d+\.(\d{4})")
_INTERVAL_RE = re.compile(r"In intervalul\s+\d{2}\.\d{2}\.(\d{4})")

# Matches Borderou de Vanzare data lines (Z POS or VANZARE RIDICATA rows)
_BORDEROU_LINE_RE = re.compile(
    r"^\d+\s+(?:Z POS|VANZARE RIDICATA \w+)\s+(\d+)\s+"
    r"(\d{2}[-/\.]\w+[-/\.]\d{2,4})"
)


def _parse_date(date_str: str) -> str:
    """Return YYYYMMDD string from PDF date. Handles DD-Mon-YY and DD/MM/YYYY."""
    date_str = date_str.strip()
    for fmt in ("%d-%b-%y", "%d/%m/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y%m%d")
        except ValueError:
            continue
    raise ValueError(f"Cannot parse SGR date: {date_str!r}")


def _extract_punct_de_lucru(filename: str) -> str:
    for ft in ("AMT", "FF1", "FF2", "M1", "M2", "M3"):
        if ft in filename:
            return ft
    return ""


def _cont_debit_simbol(punct_de_lucru: str) -> str:
    """Cash debit account per location. AMT_M magazines get a per-shop suffix
    (M1->53111, M2->53112, M3->53113); everything else (AMT) uses 5311.
    Mirrors the cardcec convention in pos_processor_fixed.py."""
    return {"M1": "53111", "M2": "53112", "M3": "53113"}.get(punct_de_lucru, "5311")


def _coerce_int(cell) -> int | None:
    """Best-effort int from an Excel cell (handles 920, 920.0, '920')."""
    if cell is None or str(cell).strip() == "":
        return None
    try:
        return int(float(str(cell).strip()))
    except (ValueError, TypeError):
        return None


def _coerce_date_cell(cell) -> str | None:
    """Return YYYYMMDD from an Excel date cell (openpyxl gives datetime) or a
    date-like string. Returns None when the cell is not a date."""
    if cell is None or str(cell).strip() == "":
        return None
    if isinstance(cell, datetime):
        return cell.strftime("%Y%m%d")
    s = str(cell).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%b-%y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y%m%d")
        except ValueError:
            continue
    try:
        return pd.to_datetime(s).strftime("%Y%m%d")
    except Exception:
        return None


def _detect_borderou_excel_columns(grid: list[list]) -> dict | None:
    """Locate the Nr.Doc / Data / Netaxabil columns in a raw 'Borderou de
    Vanzare' export by reading the HEADER LABELS, not fixed offsets.

    The Netaxabil column index is not stable across exports (AUTOS pushes the
    21% rate into its own column, shifting everything right), so the borderou
    module's hard-coded offsets read the wrong column for FF1/FF2. We anchor on
    the literal 'Netaxabil' section label instead, which always sits above its
    'Baza Impozitare' sub-column.

    Returns a dict {nr, data, netax, start} (0-based col indices + first data
    row index) or None when the layout is not recognised.
    """
    def find_idx(row, pred):
        for ci, c in enumerate(row):
            if c is not None and pred(str(c)):
                return ci
        return None

    # ── Multi-row-header layout (the common POS export) ──
    for i, row in enumerate(grid):
        if any(c is not None and "Total Valoare" in str(c) for c in row):
            netax = find_idx(row, lambda s: s.strip() == "Netaxabil")
            if netax is None:
                return None
            nr = find_idx(row, lambda s: "Nr. Doc" in s)
            data = find_idx(row, lambda s: s.strip() == "Data")
            return {
                "nr": nr if nr is not None else 2,
                "data": data if data is not None else 3,
                "netax": netax,
                "start": i + 2,  # skip the 'Baza Impozitare' sub-header row
            }

    # ── Flat single-header layout (newer export) ──
    for i, row in enumerate(grid):
        if any(c is not None and "Valoare Totala" in str(c) for c in row):
            netax = find_idx(row, lambda s: "Valoare fara TVA" in s)
            if netax is None:
                return None
            nr = find_idx(row, lambda s: "Nr. Doc" in s)
            data = find_idx(row, lambda s: "Data" in s)
            return {
                "nr": nr if nr is not None else 2,
                "data": data if data is not None else 0,
                "netax": netax,
                "start": i + 1,
            }

    return None


class SGRValueProcessor:
    """Converts a RetuRO-SGR PDF (Garantii SGR Platite cu Numerar) to the
    53-column accounting import format used by all other processors."""

    def process_pdf_file(self, file_path: str, start_nr: int | None = None) -> pd.DataFrame | None:
        """Parse the SGR PDF at *file_path* and return a 53-column DataFrame.

        Supports two PDF types:
        - RetuRO-SGR PDFs (header contains "RetuRO-SGR") — explicit SGR refund lines
        - Borderou de Vanzare PDFs (header contains "Borderou de Vanzare") — extracts
          the "Netaxabil E-0%" column which holds embedded SGR deposit amounts

        *start_nr*, when given, fills 'Nr. inreg.' starting at that value and
        increments by 1 per output row.
        """
        filename = os.path.basename(file_path)
        punct_de_lucru = _extract_punct_de_lucru(filename)

        text_lines: list[str] = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                text_lines.extend(text.splitlines())

        full_text = "\n".join(text_lines)

        if "Borderou de Vanzare" in full_text:
            return self._parse_borderou_pdf(text_lines, filename, punct_de_lucru, start_nr)
        else:
            return self._parse_returo_sgr_pdf(text_lines, filename, punct_de_lucru, start_nr)

    def _parse_returo_sgr_pdf(
        self, text_lines: list[str], filename: str, punct_de_lucru: str,
        start_nr: int | None = None,
    ) -> pd.DataFrame | None:
        """Parse a RetuRO-SGR PDF with explicit 'Returnare garantie SGR' lines."""
        year = str(datetime.today().year)
        for line in text_lines:
            m = _PERIOD_RE.search(line)
            if m:
                year = m.group(1)
                break
        informatii_export = f"{year}0101-{year}1231-CielStd_1001"

        parsed: list[dict] = []
        for line in text_lines:
            m = _DATA_LINE_RE.match(line.strip())
            if not m:
                continue
            _doc_type, nr_doc_str, date_str, val_str = (
                m.group(1), m.group(2), m.group(3), m.group(4),
            )
            try:
                date_fmt = _parse_date(date_str)
                valoare = float(val_str.replace(",", "."))
            except ValueError:
                print(f"SGR: skipping unparseable row: {line.strip()!r}")
                continue
            parsed.append({"nr_doc": int(nr_doc_str), "data": date_fmt, "valoare": valoare})

        if not parsed:
            print(f"SGR: no RetuRO-SGR data rows found in {filename!r}")
            return None

        return self._build_output(parsed, informatii_export, punct_de_lucru, start_nr)

    def _parse_borderou_pdf(
        self, text_lines: list[str], filename: str, punct_de_lucru: str,
        start_nr: int | None = None,
    ) -> pd.DataFrame | None:
        """Parse a Borderou de Vanzare PDF, extracting the Netaxabil E-0% column
        (second-to-last numeric value on each data row) as the SGR amount."""
        year = str(datetime.today().year)
        for line in text_lines:
            m = _INTERVAL_RE.search(line)
            if m:
                year = m.group(1)
                break
            m = _PERIOD_RE.search(line)
            if m:
                year = m.group(1)
                break
        informatii_export = f"{year}0101-{year}1231-CielStd_1001"

        parsed: list[dict] = []
        for line in text_lines:
            line = line.strip()
            m = _BORDEROU_LINE_RE.match(line)
            if not m:
                continue
            nr_doc_str, date_str = m.group(1), m.group(2)
            tokens = line.split()
            try:
                netaxabil = float(tokens[-2].replace(",", ""))
            except (ValueError, IndexError):
                continue
            if netaxabil <= 0:
                continue
            try:
                date_fmt = _parse_date(date_str)
            except ValueError:
                print(f"SGR-Borderou: skipping unparseable date: {date_str!r}")
                continue
            parsed.append({"nr_doc": int(nr_doc_str), "data": date_fmt, "valoare": netaxabil})

        if not parsed:
            print(f"SGR: no Netaxabil data found in Borderou {filename!r}")
            return None

        return self._build_output(parsed, informatii_export, punct_de_lucru, start_nr)

    def process_excel_file(self, file_path: str, start_nr: int | None = None) -> pd.DataFrame | None:
        """Entry point for Excel SGR input. Accepts either:

        - a raw 'Borderou de Vanzare' export (extracts the Netaxabil/SGR
          column, mirroring the Borderou-PDF path), or
        - an already-formatted 53-column SGR import template.

        Returns a 53-column DataFrame, or None when no SGR rows are found.
        Raises ValueError for a Borderou *output* file (53-col borderou schema),
        from which the SGR value can no longer be recovered.

        *start_nr*, when given, fills 'Nr. inreg.' on the extracted rows (the
        raw-borderou path); a pre-formatted SGR template keeps its own values.
        """
        filename = os.path.basename(file_path)
        punct_de_lucru = _extract_punct_de_lucru(filename)

        wb = openpyxl.load_workbook(file_path, data_only=True)
        try:
            grid = [list(r) for r in wb.active.iter_rows(values_only=True)]
        finally:
            wb.close()

        first_row = {str(c).strip() for c in (grid[0] if grid else []) if c is not None}
        if "Serie document" in first_row:
            raise ValueError(
                "Acesta este un fisier Borderou deja procesat (53 coloane) - "
                "valoarea SGR nu mai poate fi extrasa din el. Incarca borderoul "
                "brut (export 'Borderou de Vanzare') in format PDF sau Excel, "
                "sau un Excel deja formatat in schema de 53 de coloane SGR."
            )

        is_borderou = any(
            c is not None
            and any(k in str(c) for k in ("Total Valoare", "Valoare Totala", "Netaxabil"))
            for row in grid[:8]
            for c in row
        )
        if is_borderou:
            return self._parse_borderou_excel(grid, filename, punct_de_lucru, start_nr)

        # Otherwise assume a pre-formatted SGR template.
        df = pd.read_excel(file_path)
        return self.process_dataframe(df)

    def _parse_borderou_excel(
        self, grid: list[list], filename: str, punct_de_lucru: str,
        start_nr: int | None = None,
    ) -> pd.DataFrame | None:
        """Parse a raw 'Borderou de Vanzare' Excel export, extracting the
        Netaxabil column as the SGR amount (mirrors _parse_borderou_pdf)."""
        year = str(datetime.today().year)
        for row in grid[:8]:
            text = " ".join(str(c) for c in row if c is not None)
            m = _INTERVAL_RE.search(text) or _PERIOD_RE.search(text)
            if m:
                year = m.group(1)
                break
        informatii_export = f"{year}0101-{year}1231-CielStd_1001"

        cols = _detect_borderou_excel_columns(grid)
        if cols is None:
            print(f"SGR: could not detect borderou layout in {filename!r}")
            return None

        parsed: list[dict] = []
        for row in grid[cols["start"]:]:
            if cols["netax"] >= len(row) or cols["nr"] >= len(row) or cols["data"] >= len(row):
                continue
            nr_doc = _coerce_int(row[cols["nr"]])
            if nr_doc is None:
                continue
            date_fmt = _coerce_date_cell(row[cols["data"]])
            if date_fmt is None:
                continue
            raw = row[cols["netax"]]
            try:
                netaxabil = float(str(raw).replace(",", "")) if raw not in (None, "") else 0.0
            except (ValueError, TypeError):
                continue
            if netaxabil <= 0:
                continue
            parsed.append({"nr_doc": nr_doc, "data": date_fmt, "valoare": netaxabil})

        if not parsed:
            print(f"SGR: no Netaxabil rows in borderou Excel {filename!r}")
            return None

        return self._build_output(parsed, informatii_export, punct_de_lucru, start_nr)

    def _build_output(
        self, parsed: list[dict], informatii_export: str, punct_de_lucru: str,
        start_nr: int | None = None,
    ) -> pd.DataFrame:
        """Build the 53-column accounting DataFrame from parsed rows."""
        cont_debit = _cont_debit_simbol(punct_de_lucru)
        output_rows = []
        for i, r in enumerate(parsed):
            row = {col: "" for col in OUTPUT_COLUMNS}
            row["Nr. inreg."] = (start_nr + i) if start_nr is not None else ""
            row["Tip inregistrare"] = "Casa"
            row["Jurnal"] = "RC"
            row["Data"] = r["data"]
            row["Data scadenta"] = r["data"]
            row["Numar document"] = r["nr_doc"]
            row["Cont debit simbol"] = cont_debit
            row["Cont debit titlu"] = "Casa in lei" if i == 0 else ""
            row["Cont credit simbol"] = "4621"
            row["Explicatie"] = "SGR"
            row["Valoare"] = r["valoare"]
            row["TVA la incasare"] = 0
            row["Informatii export"] = informatii_export
            row["Punct de lucru"] = punct_de_lucru
            row["Factura simplificata"] = 0
            row["Borderou de achizitie"] = 0
            row["Carnet prod. Agricole"] = 0
            row["Contract"] = 0
            row["Document stornat"] = 0
            output_rows.append(row)

        return pd.DataFrame(output_rows, columns=OUTPUT_COLUMNS)

    def process_dataframe(self, df) -> pd.DataFrame | None:
        """Handle Excel SGR input that is already in the 53-column import format.

        The user sometimes fills the import template manually (e.g. when multiple
        cash-register accounts are needed). This method accepts such a file,
        validates the column schema, and returns a clean 53-column DataFrame.
        """
        if df is None or df.empty:
            print("SGR processor: received empty dataframe.")
            return None

        missing = [c for c in OUTPUT_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(
                f"Fisierul Excel nu este in formatul SGR de import (lipsesc {len(missing)} coloane: "
                f"{missing[:3]}{'...' if len(missing) > 3 else ''}). "
                "Incarca fie un PDF RetuRO-SGR (Garantii SGR Platite cu Numerar), "
                "fie un Excel deja formatat in schema de 53 de coloane SGR."
            )

        result = df[OUTPUT_COLUMNS].copy()
        result = result.fillna("")
        return result
