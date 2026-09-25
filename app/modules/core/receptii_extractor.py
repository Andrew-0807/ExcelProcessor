"""
Receptii Extractor — processes Centralizatoare_Receptii PDF files.

Input:  PDF from the Centralizatoare Receptii report.
Output: DataFrame with 43 columns matching the Ciel import schema.

Each data line in the PDF has this structure (space-separated):
    {NIR} {Date_NIR} {Numar_Factura...} {Date_Document} {Nume...} {CUI/CNP}
    {ValAch} {ValTVA} {ValAchCuTVA} {ValDif} {ValTVAAdaos} {AdaosProc}
    {Adaos%} {CotaTVA} {TVAACH} {NumAviz} {TVAAch%} {TVAV%}

The trailing 12 tokens are always financial values; the rest is parsed by
locating the two date tokens and the CUI/CNP working inward from the right.
"""

import logging
import os
import re

import pandas as pd
import pdfplumber

logger = logging.getLogger(__name__)

OUTPUT_COLUMNS = [
    "NR.linie",
    "Serie",
    "Numar document",
    "Data",
    "Data scadenta",
    "Cod tip Factura",
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
    "Moneda",
    "Curs",
    "TVA la incasare",
    "Taxare inversa",
    "Factura de transport",
    "Cod agent",
    "Valoare neta totala",
    "Valoare TVA",
    "Total document",
    "Denumire articol",
    "Cantitate",
    "Tip miscare stoc",
    "Cont servicii",
    "Pret de lista",
    "Valoare fara tva",
    "Val TVA",
    "Valoare  cu TVa",   # two spaces + lowercase 'a' — exact accounting-software column name
    "Optiune TVA",
    "Cota TVA",
    "Cod TVA SAFT",
    "Observatie",
    "Centre de cost",
]
assert len(OUTPUT_COLUMNS) == 43

# PDF date token: DD.Mon.YY / DD.Mon.YYYY (e.g. "02.Mar.26")
#                  or DD.MM.YYYY (e.g. "01.04.2026") — used by M2/M3/M4
_DATE_TOK = re.compile(r'^\d{1,2}\.\w{2,4}\.\d{2,4}$')
# Data rows begin: integer  date-token
_DATA_ROW = re.compile(r'^\d+\s+\d{1,2}\.\w{2,4}\.\d{2,4}')
# CUI patterns
_CUI_COMPACT = re.compile(r'^RO\d+$', re.IGNORECASE)   # "RO8119423"
_CUI_DIGITS  = re.compile(r'^\d{6,13}$')               # bare digits (CUI or CNP)


def _parse_float(s: str) -> float:
    s = str(s).strip().rstrip('%')
    s = re.sub(r'(?<=\d) (?=\d{3}(?!\d))', '', s)
    s = re.sub(r'(?<=\d),(?=\d{3}(?!\d))', '', s)
    s = s.replace(',', '.')
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def _extract_period(filename: str) -> str:
    """Return 'M1', 'M2', etc. from filename, or 'REC' if not found."""
    m = re.search(r'(?:^|[^a-zA-Z])M(\d+)', os.path.basename(filename), re.IGNORECASE)
    return f"M{m.group(1)}" if m else "REC"


def _parse_line(line: str) -> dict | None:
    """
    Parse one Receptii data line.  Returns a field dict or None on failure.
    """
    if not _DATA_ROW.match(line):
        return None

    tokens = line.split()
    # Minimum: NIR + date_nir + doc + date_doc + name_word + CUI + 12 financial
    if len(tokens) < 18:
        return None

    # ── 1. Trailing 12 tokens are always financial values ────────────────────
    financial = tokens[-12:]
    rest      = tokens[:-12]

    # ── 2. Identify CUI/CNP (rightmost token before the 12) ─────────────────
    # Two-token form: "RO" + "6543790"
    if (len(rest) >= 2
            and rest[-2].upper() == 'RO'
            and rest[-1].isdigit()):
        cod_fiscal = rest[-1]
        rest = rest[:-2]
    # One-token form: "RO8119423" or bare digits
    elif rest and _CUI_COMPACT.match(rest[-1]):
        cod_fiscal = re.sub(r'^RO', '', rest[-1], flags=re.IGNORECASE)
        rest = rest[:-1]
    elif rest and _CUI_DIGITS.match(rest[-1]):
        cod_fiscal = rest[-1]
        rest = rest[:-1]
    else:
        return None

    # ── 3. rest is now: NIR  Date_NIR  {Numar_Factura...}  Date_Doc  {Nume...}
    if len(rest) < 4:
        return None

    # Find the second date token (Data Document) — index 0 is NIR, index 1 is Date_NIR
    date_doc_idx = None
    for i in range(2, len(rest)):
        if _DATE_TOK.match(rest[i]):
            date_doc_idx = i
            break

    if date_doc_idx is None:
        return None

    numar_factura = ' '.join(rest[2:date_doc_idx])
    date_doc_str  = rest[date_doc_idx]
    nume          = ' '.join(rest[date_doc_idx + 1:])

    if not numar_factura or not nume:
        return None

    # ── 4. Format date as YYYYMMDD ───────────────────────────────────────────
    try:
        date_fmt = pd.to_datetime(date_doc_str, dayfirst=True).strftime('%Y%m%d')
    except Exception:
        return None

    # ── 5. Extract financial fields ──────────────────────────────────────────
    #   financial[0]  = Valoare Achizitie (net acquisition price) → Pret de lista
    #   financial[7]  = numeric TVA rate: 0, 11, or 21            → Cota TVA
    pret_lista = _parse_float(financial[0])
    try:
        cota_tva = int(float(financial[7].rstrip('%')))
    except (ValueError, TypeError):
        cota_tva = 0

    return {
        'numar_factura': numar_factura,
        'date':          date_fmt,
        'nume':          nume,
        'cod_fiscal':    cod_fiscal,
        'pret_lista':    pret_lista,
        'cota_tva':      cota_tva,
    }


class ReceptiiExtractor:
    """
    Reads a Centralizatoare_Receptii PDF and returns a 43-column DataFrame
    ready for import into the accounting software.
    """

    def process(self, pdf_path: str, original_filename: str = "") -> pd.DataFrame:
        period  = _extract_period(original_filename or pdf_path)
        records = []

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                for line in text.splitlines():
                    parsed = _parse_line(line.strip())
                    if parsed is None:
                        continue

                    cota    = parsed['cota_tva']
                    optiune = 'TAXABILE' if cota > 0 else 'SCUTITE'

                    row = {col: "" for col in OUTPUT_COLUMNS}
                    row["Numar document"]   = parsed['numar_factura']
                    row["Data"]             = parsed['date']
                    row["Data scadenta"]    = parsed['date']
                    row["Nume partener"]    = parsed['nume']
                    row["Cod fiscal"]       = parsed['cod_fiscal']
                    row["Moneda"]           = "RON"
                    row["Denumire articol"] = "SGR" if cota == 0 else f"marfa {period} {cota}%"
                    row["Cantitate"]        = "1"
                    row["Pret de lista"]    = parsed['pret_lista']
                    row["Optiune TVA"]      = optiune
                    row["Cota TVA"]         = cota
                    records.append(row)

        df = pd.DataFrame(records, columns=OUTPUT_COLUMNS)
        logger.info(
            "Extracted %d reception rows from %s",
            len(df), os.path.basename(pdf_path),
        )
        return df
