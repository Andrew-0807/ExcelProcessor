import os
import re
import pandas as pd
import pdfplumber
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

# Matches SGR data lines, e.g.:
#   "Plata Voucher RetuRO 1735 01/02/2026 Returnare garantie SGR 6.00 1013 Casier2"
#   "Plata Numerar 831 01/02/2026 Returnare garantie SGR 76.50 ..."
_DATA_LINE_RE = re.compile(
    r"^(Plata\s+\S+(?:\s+\S+)*?)\s+(\d+)\s+(\d{2}[/\-.]\w+[/\-.]\d{2,4})"
    r"\s+Returnare garantie SGR\s+([\d.,]+)",
    re.IGNORECASE,
)
_PERIOD_RE = re.compile(r"In perioada:\s*\d+\.\d+\.(\d{4})")


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
    for ft in ("AMT", "M1", "M2", "M3"):
        if ft in filename:
            return ft
    return ""


class SGRValueProcessor:
    """Converts a RetuRO-SGR PDF (Garantii SGR Platite cu Numerar) to the
    53-column accounting import format used by all other processors."""

    def process_pdf_file(self, file_path: str) -> pd.DataFrame | None:
        """Parse the SGR PDF at *file_path* and return a 53-column DataFrame."""
        filename = os.path.basename(file_path)
        punct_de_lucru = _extract_punct_de_lucru(filename)

        text_lines: list[str] = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                text_lines.extend(text.splitlines())

        # Extract fiscal year from the period header line
        year = str(datetime.today().year)
        for line in text_lines:
            m = _PERIOD_RE.search(line)
            if m:
                year = m.group(1)
                break
        informatii_export = f"{year}0101-{year}1231-CielStd_1001"

        # Parse every data row
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
            print(f"SGR: no data rows found in {filename!r}")
            return None

        output_rows = []
        for i, r in enumerate(parsed):
            row = {col: "" for col in OUTPUT_COLUMNS}
            row["Tip inregistrare"] = "Casa"
            row["Jurnal"] = "RC"
            row["Data"] = r["data"]
            row["Data scadenta"] = r["data"]
            row["Numar document"] = r["nr_doc"]
            row["Cont debit simbol"] = "53111"
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
