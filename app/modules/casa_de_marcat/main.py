"""
Casa de marcat processor — transforms cash register Excel exports into
the 53-column accounting import format.

Input: Excel with columns IdR, CUI, AMEF, Data, IdZ, ..., Card, Numerar, etc.
Output: Two sections concatenated vertically:
  - Section A (Cont credit 707):  one row per input row, Valoare = Total_0
  - Section B (Cont credit 5125): only rows where Card has a value, Valoare = Card
"""

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

def _format_date_int(dt) -> int:
    """Convert a datetime/Timestamp to YYYYMMDD integer."""
    ts = pd.Timestamp(dt)
    return int(ts.strftime("%Y%m%d"))


def _safe_float(value, default=0.0) -> float:
    """Safely convert a value to float, returning default for NaN/None/empty."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        if pd.isna(value):
            return default
        return float(value)
    s = str(value).strip()
    if s == "":
        return default
    try:
        return float(s)
    except (ValueError, TypeError):
        return default


def _build_row(date_int, idz, cont_credit, valoare, is_first_row=False) -> dict:
    """Build a single 53-column output row."""
    row = {col: "" for col in OUTPUT_COLUMNS}
    row["Nr. inreg."] = ""
    row["Tip inregistrare"] = "Casa"
    row["Jurnal"] = "RC"
    row["Data"] = date_int
    row["Data scadenta"] = date_int
    row["Numar document"] = int(idz)
    row["Cont debit simbol"] = 5311
    row["Cont debit titlu"] = "Casa in lei" if is_first_row else ""
    row["Cont credit simbol"] = cont_credit
    row["Valoare"] = valoare
    row["TVA la incasare"] = 0
    row["Informatii export"] = "20260101-20261231-CielStd_1035"
    row["Punct de lucru"] = "SEDIU"
    row["Factura simplificata"] = 0
    row["Borderou de achizitie"] = 0
    row["Carnet prod. Agricole"] = 0
    row["Contract"] = 0
    row["Document stornat"] = 0
    return row


# ── Main processor ─────────────────────────────────────────────────────────

def process_casa_de_marcat(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transform a cash register input DataFrame into the 53-column output format.

    Parameters
    ----------
    df : pd.DataFrame
        The raw input data (read from .xls/.xlsx).

    Returns
    -------
    pd.DataFrame with OUTPUT_COLUMNS
    """
    # Drop the totals row (IdR == "Total" or NaN in AMEF/Data)
    df = df[df["IdR"] != "Total"].copy()
    df = df.dropna(subset=["AMEF", "Data"]).copy()

    if df.empty:
        raise ValueError("No data rows found after dropping totals row.")

    # Sort by AMEF (ascending) then by original order within each AMEF group
    df = df.sort_values(by=["AMEF", "IdZ"], ascending=True).reset_index(drop=True)

    rows = []

    # ── Section A: Cont credit 707, one row per input row ──
    for i, (_, src) in enumerate(df.iterrows()):
        date_int = _format_date_int(src["Data"])
        idz = src["IdZ"]
        total_0 = _safe_float(src.get("Total_0"), default=0.0)

        row = _build_row(
            date_int=date_int,
            idz=idz,
            cont_credit=707,
            valoare=total_0,
            is_first_row=(i == 0),
        )
        rows.append(row)

    # ── Section B: Cont credit 5125, only rows where Card has a value ──
    for _, src in df.iterrows():
        card_val = src.get("Card")
        if pd.isna(card_val):
            continue

        date_int = _format_date_int(src["Data"])
        idz = src["IdZ"]

        row = _build_row(
            date_int=date_int,
            idz=idz,
            cont_credit=5125,
            valoare=-abs(float(card_val)),
        )
        rows.append(row)

    if not rows:
        raise ValueError("No output rows produced.")

    result = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    return result
