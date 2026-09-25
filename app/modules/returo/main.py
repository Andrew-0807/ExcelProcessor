"""RetuRO module — standalone.

Converts a raw "RetuRO-SGR > Garantii SGR Platite cu Numerar" voucher export
(multi-sheet xlsx or the printed PDF of the same report, rows tagged
"Plata Voucher RetuRO") into the 53-column
"Note Contabile" accounting-import sheet.

Processing is derived purely from the input<->output model in models/returo/:
- one output row per unique 'Nr. Document' (first-seen order; pages overlap)
- 'Valoare' is negated (payout -> credit)
- dates -> YYYYMMDD
- account codes / export string vary by sub-firm (see _accounts)

The only thing shared with other modules is the UI 'Nr. inreg.' start field
(server passes start_nr); none of the processing comes from the SGR module.
"""
import os
import re
import pandas as pd
import openpyxl
from datetime import datetime

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

_MARKER = "Plata Voucher RetuRO"
_PERIOD_RE = re.compile(r"In perioada:\s*\d+\.\d+\.(\d{4})")
# AMT subtypes first so e.g. "M2" in a path doesn't shadow a real AMT marker.
_PUNCT_TOKENS = ("FF1", "FF2", "AUTOSERVIRE", "RESTAURANT", "AMT", "M1", "M2", "M3")


def _detect_punct(filename: str) -> str:
    up = filename.upper()
    for tok in _PUNCT_TOKENS:
        if tok in up:
            return tok
    return ""


def _accounts(punct: str) -> tuple[str, str]:
    """(cont_debit_simbol, cielstd_code) for a sub-firm.

    M-magazines: 5311 + shop digit, CielStd_1001.
    AMT (Restaurant/FF1/FF2/Autoservire) and unknown: 5311, CielStd_1057.
    """
    debit = {"M1": "53111", "M2": "53112", "M3": "53113"}.get(punct, "5311")
    cielstd = "1001" if punct in ("M1", "M2", "M3") else "1057"
    return debit, cielstd


def _fmt_date(cell) -> str:
    if isinstance(cell, datetime):
        return cell.strftime("%Y%m%d")
    s = str(cell).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y%m%d")
        except ValueError:
            continue
    return pd.to_datetime(s).strftime("%Y%m%d")


def _parse_pdf(file_path: str) -> tuple[list[dict], str | None]:
    """Voucher rows from the PDF export (same report, printed instead of xlsx).

    The PDF has no "In perioada" banner, so the year is returned as None and
    the caller derives it from the document dates.
    """
    try:
        from app.modules.core.pdf_extractor import extract_returo_rows_from_pdf
    except ImportError:  # server also puts modules/core directly on sys.path
        from pdf_extractor import extract_returo_rows_from_pdf

    df = extract_returo_rows_from_pdf(file_path)
    parsed: list[dict] = []
    seen: set = set()
    for nr_doc, data_cell, valoare in df.itertuples(index=False, name=None):
        if nr_doc in seen:  # report pages can overlap; keep first occurrence
            continue
        seen.add(nr_doc)
        parsed.append({
            "nr_doc": nr_doc,
            "data": _fmt_date(data_cell),
            "valoare": float(valoare),
        })
    return parsed, None


def _parse_xlsx(file_path: str) -> tuple[list[dict], str]:
    """Voucher rows + reporting year from the raw multi-sheet xlsx export."""
    wb = openpyxl.load_workbook(file_path, data_only=True)
    try:
        year = str(datetime.today().year)
        parsed: list[dict] = []
        seen: set = set()
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                if not row:
                    continue
                # Year comes from the "In perioada: 01.05.2026 - ..." banner.
                if row[0] and isinstance(row[0], str):
                    m = _PERIOD_RE.search(row[0])
                    if m:
                        year = m.group(1)
                if row[0] != _MARKER:  # skips headers, banners, TOTAL GENERAL
                    continue
                nr_doc, data_cell, valoare = row[1], row[2], row[4]
                if nr_doc in seen:  # report pages overlap; keep first occurrence
                    continue
                seen.add(nr_doc)
                parsed.append({
                    "nr_doc": nr_doc,
                    "data": _fmt_date(data_cell),
                    "valoare": float(valoare),
                })
    finally:
        wb.close()
    return parsed, year


def process_returo(
    file_path: str,
    start_nr: int | None = None,
    punct_de_lucru: str | None = None,
) -> pd.DataFrame | None:
    """Parse a raw RetuRO voucher xlsx/PDF -> 53-column DataFrame, or None if empty.

    *start_nr* fills 'Nr. inreg.' starting at that value (+1 per row); None -> blank.
    *punct_de_lucru* overrides filename detection (used for testing).
    """
    filename = os.path.basename(file_path)
    punct = punct_de_lucru or _detect_punct(filename)
    cont_debit, cielstd = _accounts(punct)

    if filename.lower().endswith(".pdf"):
        parsed, year = _parse_pdf(file_path)
    else:
        parsed, year = _parse_xlsx(file_path)

    if not parsed:
        return None
    if year is None:  # no banner (PDF): use the year the documents belong to
        year = parsed[0]["data"][:4]

    informatii_export = f"{year}0101-{year}1231-CielStd_{cielstd}"
    rows = []
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
        row["Explicatie"] = "Returnare garantie SGR"
        row["Valoare"] = -r["valoare"]
        row["TVA la incasare"] = 0
        row["Informatii export"] = informatii_export
        row["Punct de lucru"] = punct
        row["Factura simplificata"] = 0
        row["Borderou de achizitie"] = 0
        row["Carnet prod. Agricole"] = 0
        row["Contract"] = 0
        row["Document stornat"] = 0
        rows.append(row)

    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


if __name__ == "__main__":
    # Self-check against the model input/output in models/returo/.
    here = os.path.dirname(__file__)
    model = os.path.join(here, "..", "..", "..", "models", "returo")
    inp = os.path.join(model, "initial RetuRO-SGR__Garantii_SGR_Platite_cu_Numerar.xlsx")
    df = process_returo(inp, start_nr=13267, punct_de_lucru="M2")
    assert df is not None and len(df) == 300, len(df) if df is not None else None
    assert list(df.columns) == OUTPUT_COLUMNS
    assert df["Nr. inreg."].iloc[0] == 13267 and df["Nr. inreg."].iloc[-1] == 13566
    assert df["Valoare"].sum() == -12081.5, df["Valoare"].sum()
    assert (df["Explicatie"] == "Returnare garantie SGR").all()
    assert df["Cont debit simbol"].iloc[0] == "53112"
    assert df["Informatii export"].iloc[0] == "20260101-20261231-CielStd_1001"
    assert df["Cont debit titlu"].iloc[0] == "Casa in lei" and df["Cont debit titlu"].iloc[1] == ""
    print("returo self-check OK:", len(df), "rows, sum", df["Valoare"].sum())
