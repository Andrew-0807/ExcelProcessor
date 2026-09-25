"""
Adaos Avize processor.

Takes the SAME "intrari avize" Excel export as the normal Avize module, but
instead of building the 53-column accounting import it recomputes the adaos
(mark-up) breakdown: it splits each aviz into its 21 %/11 % fara-TVA bases on
both the achizitie (purchase) and gestiune (store) side, then derives the
mark-up per rate (gestiune base minus achizitie base).

One input data row -> one output row (no splitting). A totals row is appended.

VAT rates are fixed at 21 % (rate A) and 11 % (rate B) to match the model.
# ponytail: rates hardcoded; if a future month uses other cotas, read them
# from the "Cota TVA A/B" columns instead of the constants below.
"""

import re
import numpy as np
import pandas as pd

RATE_A = 0.21
RATE_B = 0.11

OUTPUT_COLUMNS = [
    "Tip Miscare",                                    # A
    "Nr Aviz",                                        # B
    "Data Aviz",                                      # C
    "ValoareAchizitie Fara TVA",                      # D
    "Val. TVA Achizitie",                             # E
    "Val. Totala initial  Achizitie (col D+col E)",   # F
    "Val. TOTALA Achizitie (COL H+ I+ J +K)",         # G
    "Val. Fara TVA Achizitie A",                      # H
    "Val. TVA Achizitie A",                           # I
    "Val. Fara TVA Achizitie B",                      # J
    "Val. TVA Achizitie B",                           # K
    "DIFERENTA TRANSFORMARE",                         # L
    "Val Gestiune cu TVA",                            # M
    "Val. Tot. TVA Gestiune",                         # N
    "DIFERENTA TRANSFORMARE",                         # O
    "Val. Totala  Gestiune",                          # P
    "Val. faraTVA A Gest.  ",                         # Q
    "Val. TVA A Gest.  ",                             # R
    "Val. Fara TVA B Gest.  ",                        # S
    "Val. TVA B Gest.  ",                             # T
    "ADAOS FARA TVA 21%",                             # U
    "ADAOS FARA 11%",                                 # V
    "Cota TVA A",                                     # W
    "Cota TVA B",                                     # X
    "GESTIUNE FINALA",                                # Y
]
assert len(OUTPUT_COLUMNS) == 25


def _num(v) -> float:
    """NaN/empty -> 0.0, otherwise float."""
    return 0.0 if pd.isna(v) else float(v)


def _nr_aviz(v):
    """Output only the aviz number. intrari holds a plain number (6080); iesiri
    holds prefixed text 'M2 6081' -> 6081. Take the trailing digits either way."""
    if pd.isna(v):
        return v
    try:
        return int(float(v))                       # intrari: 6080.0 -> 6080
    except (ValueError, TypeError):
        pass
    match = re.search(r"(\d+)\s*$", str(v).strip())  # iesiri: 'M2 6081' -> 6081
    if not match:
        raise ValueError(f"Cannot extract aviz number from: '{v}'")
    return int(match.group(1))


def _gestiune_finala(partner_str, nr_aviz_raw) -> str:
    """Final location tag.

    - Inter-location avize: the partner is a sibling store ('Amato Impex SRL 2'),
      so its trailing number wins -> 'M2'.
    - Furnizori returns: the partner is an external supplier with no number
      ('Raitar S.R.L.'), so fall back to the location prefix carried in Nr Aviz
      ('M2 6116' -> 'M2', the source store this export belongs to).
    """
    m = re.search(r"(\d+)\s*$", str(partner_str).strip())
    if m:
        return f"M{int(m.group(1))}"
    m = re.search(r"[Mm]\s*(\d+)", str(nr_aviz_raw))
    if m:
        return f"M{int(m.group(1))}"
    raise ValueError(
        f"Cannot determine GESTIUNE FINALA from partner '{partner_str}' "
        f"or Nr Aviz '{nr_aviz_raw}'"
    )


def process_adaos_avize(df: pd.DataFrame, original_filename: str = "") -> pd.DataFrame:
    """Transform an intrari-avize input DataFrame into the adaos breakdown."""
    # Input headers carry inconsistent trailing spaces (e.g. "Val. TVA A Gest.  ")
    # across exports — strip them so column lookups don't depend on whitespace.
    df = df.rename(columns=lambda c: c.strip() if isinstance(c, str) else c)
    df = df.dropna(subset=["Nr Aviz"]).copy()
    if df.empty:
        raise ValueError("No data rows found after dropping totals row.")

    # This adaos maths only models the 21 %/11 % rates (A/B). If a file ever
    # carries a third/fourth rate (C/D), silently dropping it would corrupt the
    # totals — fail loudly instead so it gets handled explicitly.
    for extra in ("Val. TVA Achizitie C", "Val. TVA Achizitie D",
                  "Val. TVA C Gest.", "Val. TVA D Gest."):
        if extra in df.columns and df[extra].fillna(0).astype(float).abs().sum() > 0:
            raise ValueError(
                f"Column '{extra}' has non-zero values; Adaos Avize only handles "
                "rates A (21%) and B (11%). This file needs manual review."
            )

    # Positional accumulators (header "DIFERENTA TRANSFORMARE" appears twice, so
    # keying by name would collide — build arrays then one DataFrame, CLAUDE #4).
    cols = [[] for _ in range(25)]

    for _, src in df.iterrows():
        # Achizitie (purchase) side
        d = _num(src["ValoareAchizitie Fara TVA"])
        e = _num(src["Val. TVA Achizitie"])
        i = _num(src["Val. TVA Achizitie A"])
        k = _num(src["Val. TVA Achizitie B"])
        h = i / RATE_A
        j = k / RATE_B
        f = d + e
        g = h + i + j + k
        l = f - g

        # Gestiune (store) side — A/B TVA come in blank when the rate is absent,
        # and the model keeps those cells blank; the fara-TVA base is then 0.
        m = _num(src["Val Gestiune cu TVA"])
        n = _num(src["Val. Tot. TVA Gestiune"])
        r_raw = src["Val. TVA A Gest."]
        t_raw = src["Val. TVA B Gest."]
        q = _num(r_raw) / RATE_A
        s = _num(t_raw) / RATE_B
        p = q + _num(r_raw) + s + _num(t_raw)
        o = m - p

        row = [
            src["Tip Miscare"],                                 # A
            _nr_aviz(src["Nr Aviz"]),                           # B
            pd.Timestamp(src["Data Aviz"]).date(),              # C (date only, no time)
            d, e, f, g, h, i, j, k, l,                          # D..L
            m, n, o, p,                                         # M..P
            q,                                                  # Q
            r_raw if not pd.isna(r_raw) else np.nan,            # R
            s,                                                  # S
            t_raw if not pd.isna(t_raw) else np.nan,            # T
            q - h,                                              # U ADAOS 21%
            s - j,                                              # V ADAOS 11%
            src["Cota TVA A"],                                  # W
            src["Cota TVA B"],                                  # X
            _gestiune_finala(src["Partener"], src["Nr Aviz"]),  # Y
        ]
        for idx in range(25):
            cols[idx].append(row[idx])

    result = pd.DataFrame({idx: cols[idx] for idx in range(25)})
    result.columns = OUTPUT_COLUMNS

    # Totals row: sum numeric columns D..V (index 3..21); A,B,C,W,X,Y blank.
    totals = [np.nan] * 25
    for idx in range(3, 22):
        totals[idx] = result.iloc[:, idx].sum(skipna=True)
    result.loc[len(result)] = totals

    # Summary table below the totals: one blank spacer row, a "SUMA" header,
    # then four labelled totals. Label goes in column D (index 3), value in
    # column F (index 5). Values are the column sums already in `totals`.
    def _summary_row(label, value):
        r = [np.nan] * 25
        r[3] = label
        r[5] = value
        return r

    summary = [
        [np.nan] * 25,                              # blank spacer
        _summary_row(np.nan, np.nan),               # SUMA header (value col)
        _summary_row("ADAOS FARA TVA 21%", totals[20]),
        _summary_row("ADAOS FARA TVA 11%", totals[21]),
        _summary_row("valoare tva la valoarea de vanzare 21% aviz", totals[17]),
        _summary_row("valoare tva la valoarea de vanzare 11% aviz", totals[19]),
    ]
    summary[1][5] = "SUMA"
    for r in summary:
        result.loc[len(result)] = r

    return result
