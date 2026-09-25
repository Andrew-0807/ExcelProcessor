"""
Avize processor — transforms "iesiri/intrari avize" Excel exports into
the 53-column accounting import format.

Filename determines direction (iesiri/intrari) and punct de lucru (M1/M2/M3).
Partner trailing number (e.g. "Amato Impex SRL 2" → 2) determines one of the
account numbers.  Each input row may produce up to 2 output rows: one per
non-zero TVA rate (21 % column M, 11 % column N).
"""

import os
import re
import pandas as pd

# ── Fixed 53-column output schema ──────────────────────────────────────────
OUTPUT_COLUMNS = [
    "Nr. inreg.",
    "Tip inregistrare",
    "Jurnal",
    "Data",
    "Data scadenta",
    "Numar document",
    "Cod tip factura",
    "Cont debit simbol",
    "Cont debit titlu",
    "Metoda de plata SAF-T",
    "Mecanism de plata SAF-T",
    "Tip Taxa SAF-T",
    "Cod Taxa SAF-T",
    "Cont credit simbol",
    "Cont credit titlu",
    "Metoda de plata SAF-T    ",
    "Mecanism de plata SAFT-T",
    "Tip Taxa SAF_T",
    "Cod TAXA SAF_T",
    "Explicatie",
    "Valoare",
    "Cod Partener",
    "Partener CIF",
    "Partener Nume",
    "Partener Rezidenta",
    "Partener Judet",
    "Partener Cont",
    "Angajat CNP",
    "Angajat Nume",
    "Angajat Cont",
    "Optiune TVA",
    "Cota TVA",
    "Cod TVA SAF-T",
    "Moneda",
    "Curs",
    "Valoare deviza",
    "Stornare - Nr. inreg.",
    "Incasari/plati",
    "Diferente curs",
    "TVA la incasare",
    "Colectare/Deducere TVA",
    "Efect de incasat/platit",
    "Banca efect",
    "Centre de cost",
    "Informatii export",
    "Punct de lucru",
    "Deductibilitate",
    "Reevaluare",
    "Factura simplificata",
    "Borderou de achizitie",
    "Carnet prod. Agricole",
    "Contract",
    "Document stornat",
]
assert len(OUTPUT_COLUMNS) == 53


# ── Helpers ────────────────────────────────────────────────────────────────

def _parse_filename(filename: str):
    """Extract direction ('iesiri'/'intrari') and M-number from filename."""
    lower = filename.lower()

    # Direction
    if "iesiri" in lower or "iesire" in lower:
        direction = "iesiri"
    elif "intrari" in lower or "intrare" in lower:
        direction = "intrari"
    else:
        raise ValueError(
            f"Cannot determine direction (iesiri/intrari) from filename: {filename}"
        )

    # M-number (m1, m2, m3)
    m_match = re.search(r"\bm(\d)\b", lower)
    if not m_match:
        raise ValueError(
            f"Cannot determine punct de lucru (M1/M2/M3) from filename: {filename}"
        )
    m_number = int(m_match.group(1))

    return direction, m_number


def _extract_partner_number(partner_str: str) -> int:
    """Extract trailing number from partner name, e.g. 'Amato Impex SRL 2' → 2."""
    match = re.search(r"(\d+)\s*$", str(partner_str).strip())
    if not match:
        raise ValueError(
            f"Cannot extract trailing number from partner: '{partner_str}'"
        )
    return int(match.group(1))


def _format_date_int(dt) -> int:
    """Convert a datetime/Timestamp to YYYYMMDD integer."""
    ts = pd.Timestamp(dt)
    return int(ts.strftime("%Y%m%d"))


# ── Main processor ─────────────────────────────────────────────────────────

def process_avize(df: pd.DataFrame, original_filename: str) -> pd.DataFrame:
    """
    Transform an avize input DataFrame into the 53-column output format.

    Parameters
    ----------
    df : pd.DataFrame
        The raw input data (read from .xls/.xlsx).
    original_filename : str
        Original upload filename — used to determine direction and M-number.

    Returns
    -------
    pd.DataFrame with OUTPUT_COLUMNS
    """
    direction, m_number = _parse_filename(original_filename)

    # Drop the totals row (last row usually has NaN in key text columns)
    df = df.dropna(subset=["Nr. Doc. Intern"]).copy()

    if df.empty:
        raise ValueError("No data rows found after dropping totals row.")

    rows = []

    for _, src in df.iterrows():
        nr_doc = int(src["Nr. Doc. Intern"])
        date_int = _format_date_int(src["Data Doc. Intern"])

        # Partner number for account
        partner_num = _extract_partner_number(src["Partener"])

        punct = f"M{m_number}"

        # TVA columns
        tva_21 = src.get("Val. TVA Achizitie A", 0) or 0
        tva_11 = src.get("Val. TVA Achizitie B", 0) or 0

        # Convert NaN to 0
        tva_21 = 0 if pd.isna(tva_21) else float(tva_21)
        tva_11 = 0 if pd.isna(tva_11) else float(tva_11)

        # Build output rows — one per non-zero TVA rate
        # Account prefix: 371.19 for 21%, 371.9 for 11%
        for tva_amount, rate, acct_prefix in [
            (tva_21, 0.21, "371.19"),
            (tva_11, 0.11, "371.9"),
        ]:
            if tva_amount == 0:
                continue

            valoare = round(tva_amount / rate, 2)

            # Account assignment depends on direction
            if direction == "iesiri":
                cont_debit = f"{acct_prefix}.{partner_num}"
                cont_credit = f"{acct_prefix}.{m_number}"
            else:  # intrari
                cont_debit = f"{acct_prefix}.{m_number}"
                cont_credit = f"{acct_prefix}.{partner_num}"

            row = {col: "" for col in OUTPUT_COLUMNS}
            row["Nr. inreg."] = nr_doc
            row["Tip inregistrare"] = "DIVERSE"
            row["Jurnal"] = "OD"
            row["Data"] = date_int
            row["Data scadenta"] = date_int
            row["Numar document"] = nr_doc
            row["Cont debit simbol"] = cont_debit
            row["Cont credit simbol"] = cont_credit
            row["Explicatie"] = "AVIZ"
            row["Valoare"] = valoare
            row["TVA la incasare"] = 0
            row["Informatii export"] = "20260101-20261231-CielStd_1001"
            row["Punct de lucru"] = punct
            row["Factura simplificata"] = 0
            row["Borderou de achizitie"] = 0
            row["Carnet prod. Agricole"] = 0
            row["Contract"] = 0
            row["Document stornat"] = 0

            rows.append(row)

    if not rows:
        raise ValueError("No output rows produced — all TVA columns are zero.")

    result = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    return result
