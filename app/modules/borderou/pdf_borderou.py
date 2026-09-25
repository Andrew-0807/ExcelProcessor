"""
Borderou-specific PDF extraction.

This is a SELF-CONTAINED extractor that lives inside the borderou module so it
does not modify (or depend on the internals of) the shared
``app.modules.core.pdf_extractor`` module, which is used by other modules.

Why it exists:
    The shared ``extract_borderou_rows_from_pdf`` drops the per-row description
    text (e.g. ``"Z emis la POS nr.14"``). The M-branch (M1/M2) needs that text
    to build the document serie with its POS number (``BFM1 0014``,
    ``BFM2 102`` …). The Excel path already keeps it; this gives the PDF path
    parity by preserving an ``Explicatii`` field on every row.

The numeric parsing mirrors the proven text-line strategy of the shared
extractor: each data line ends with 13 financial values, of which we keep
Total Valoare, the 21%/11% base+TVA pairs, and Netaxabil base.
"""

import re

import pandas as pd
import pdfplumber


# A borderou data line looks like:
#   "1 Z POS 1682 01-Feb-26 Z emis la POS nr.14 3,706.62 0 0 762.7 ... 21.5 0"
# group(1)=Nr. Crt, group(2)=Nr. Doc(Z), group(3)=Data
#
# The date separator depends on the regional settings of the machine that ran the
# SmartCash export, so all three observed variants must be accepted:
#   "01-Feb-26"   (dash + month name)
#   "01/04/2026"  (slash + numeric)
#   "01.Jul.26" / "01.02.2026"  (DOT — AMT_M exports from 2026-08 onwards)
# Accepting only [-/] made every M1 line fail to match, yielding zero rows.
_ROW_PREFIX = re.compile(
    r"^(\d+)\s+Z\s*POS\s+(\d+)\s+(\d{1,2}[-/.][^\s]+[-/.]\d{2,4})\s+"
)

# Matches numbers with an optional comma thousands separator and an optional
# decimal part: "3,706.62", "762.7", "0".
#
# A SPACE is deliberately NOT accepted as a thousands separator here: the line
# text is assembled by ``_all_page_text`` below, which already rejoins numbers
# split by a thousands space. Allowing it as well made the match straddle the
# gap between two fields — e.g. in "... inchiderea 927 10545 ..." it consumed
# "927 105" as one value and left "45" as the next, shifting every column.
_NUM_PAT = re.compile(
    r"[1-9]\d{0,2}(?:,\d{3})+(?:[.,]\d+)?"
    r"|\d+(?:[.,]\d+)?"
)


def _parse_float(s: str) -> float:
    """Parse a Romanian/English formatted number string to float."""
    s = str(s).strip()
    # Drop thousands separators (space or comma followed by exactly 3 digits).
    s = re.sub(r"(?<=\d) (?=\d{3}(?!\d))", "", s)
    s = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", s)
    s = s.replace(",", ".")
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


# ── Space-thousands disambiguation ──────────────────────────────────────────
# The export writes thousands separators as a literal space, so a plain text
# dump renders "3187" + "350.57" as "3 187 350.57" — indistinguishable from the
# single value 3187350.57, which silently shifts the 13-value window and
# corrupts the Baza/TVA amounts.
#
# Geometry resolves it: measured over every data line of the FF1/AUTOS/M2/M3
# exports, the gap for a thousands separator *inside* one number is 1.89pt
# (glyph height 6.9pt), while the smallest padding between two different
# columns is 10.77pt. A cut at 0.6x the glyph height separates the two with a
# wide margin and stays correct if the export font size changes.
_Y_TOL = 3.0  # pdfplumber's default line-grouping tolerance
_GLUE_GAP_RATIO = 0.6
# A thousands continuation is always exactly 3 digits, optionally carrying the
# decimal tail of the whole number ("303.97" in "4 303.97").
_THOUSANDS_GROUP = re.compile(r"\d{3}(?:[.,]\d+)?")


def _line_text(words: list) -> str:
    """Join one line's words, re-gluing space-separated thousands groups."""
    parts: list[str] = []
    for i, w in enumerate(words):
        prev = words[i - 1] if i else None
        if (
            prev is not None
            and prev["text"][-1:].isdigit()
            and _THOUSANDS_GROUP.fullmatch(w["text"])
            and (w["x0"] - prev["x1"])
            < _GLUE_GAP_RATIO * max(prev["height"], w["height"])
        ):
            parts[-1] += w["text"]  # "4" + "303.97" -> "4303.97"
        else:
            parts.append(w["text"])
    return " ".join(parts)


def _all_page_text(pdf_path: str) -> list[str]:
    """Return every text line from every page of the PDF.

    Built from positioned words rather than ``page.extract_text()`` so that
    numbers split by a thousands space can be rejoined (see above).
    """
    lines: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            rows: list[list] = []
            for w in sorted(page.extract_words(), key=lambda w: (w["top"], w["x0"])):
                if rows and abs(w["top"] - rows[-1][0]) <= _Y_TOL:
                    rows[-1][1].append(w)
                else:
                    rows.append([w["top"], [w]])
            for _, ws in rows:
                lines.append(_line_text(sorted(ws, key=lambda w: w["x0"])))
    return lines


def _make_row(nr_doc: int, dt, explicatii: str, vals: list) -> dict:
    """Build a standardized borderou row from the 13 trailing financial values.

    ``explicatii`` is preserved so the M-branch can extract the POS number.
    """
    return {
        "Nr_Doc_Z": nr_doc,
        "Data": dt,
        "Explicatii": explicatii,
        "Total_Valoare": vals[0],
        "Taxabile_21_Baza": vals[3],
        "Taxabile_21_TVA": vals[4],
        "Taxabile_11_Baza": vals[5],
        "Taxabile_11_TVA": vals[6],
        "Netaxabil_Baza": vals[11],
    }


def extract_borderou_rows_from_pdf(pdf_path: str) -> list | None:
    """
    Extract borderou rows (with Explicatii / POS text) from a PDF.

    Each data row's 13 financial values are taken as the LAST 13 numbers on the
    line, which avoids accidentally consuming the Nr. Crt, Nr. Doc, date digits
    and the ``POS nr.N`` number that appear earlier in the line. When a row's
    numbers wrap onto continuation lines, they are accumulated until 13 are seen.

    Returns a list of row dicts, or None if no data rows were found.
    """
    rows: list[dict] = []
    pending: tuple | None = None  # (nr_doc, dt, explicatii, collected_tokens)

    def _flush(p):
        nr_doc, dt, explicatii, tokens = p
        if len(tokens) >= 13:
            vals = [_parse_float(t) for t in tokens[-13:]]
            rows.append(_make_row(nr_doc, dt, explicatii, vals))

    for line in _all_page_text(pdf_path):
        line = line.strip()
        m = _ROW_PREFIX.match(line)
        if m:
            # A new row begins — flush any incomplete previous row first.
            if pending is not None:
                _flush(pending)
                pending = None

            nr_doc_raw = m.group(2)
            date_str = m.group(3)
            try:
                nr_doc = int(nr_doc_raw)
                dt = pd.to_datetime(date_str, dayfirst=True)
            except Exception:
                continue

            # Keep the whole line as Explicatii; the M-branch POS regex
            # (``POS\s+nr\.(\d+)``) finds the terminal number within it.
            num_tokens = _NUM_PAT.findall(line)
            if len(num_tokens) >= 13:
                vals = [_parse_float(t) for t in num_tokens[-13:]]
                rows.append(_make_row(nr_doc, dt, line, vals))
            else:
                pending = (nr_doc, dt, line, num_tokens)

        elif pending is not None:
            # Continuation line — accumulate more numbers for the pending row.
            nr_doc, dt, explicatii, tokens = pending
            tokens = tokens + _NUM_PAT.findall(line)
            if len(tokens) >= 13:
                vals = [_parse_float(t) for t in tokens[-13:]]
                rows.append(_make_row(nr_doc, dt, explicatii, vals))
                pending = None
            else:
                pending = (nr_doc, dt, explicatii, tokens)

    if pending is not None:
        _flush(pending)

    return rows or None
