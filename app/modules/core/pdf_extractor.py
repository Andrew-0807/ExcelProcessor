"""
PDF extraction utilities for MomAutomations.

Each extractor tries multiple strategies in parallel and returns whichever
produced the most complete result (scored by row count × field completeness).

  extract_borderou_rows_from_pdf(pdf_path)
  extract_pos_dataframe_from_pdf(pdf_path)
  extract_sgr_dataframe_from_pdf(pdf_path)
  extract_returo_rows_from_pdf(pdf_path)
  extract_tichete_dataframe_from_pdf(pdf_path)
"""

import logging
import os
import re
from pathlib import Path

import pandas as pd
import pdfplumber

logger = logging.getLogger(__name__)


# ── Romanian / English number parsing ───────────────────────────────────────

_RO_NUM_PAT = re.compile(
    r"[1-9]\d{0,2}(?:[\s,]\d{3})+(?:[.,]\d+)?"
    r"|\d+(?:[.,]\d+)?"
)


def _parse_ro_float(s: str) -> float:
    s = str(s).strip()
    s = re.sub(r"(?<=\d) (?=\d{3}(?!\d))", "", s)
    s = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", s)
    s = s.replace(",", ".")
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def _all_page_text(pdf_path: str) -> list[str]:
    """Return all lines from all pages via text extraction."""
    lines = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines.extend(text.splitlines())
    return lines


# ── Borderou scoring ─────────────────────────────────────────────────────────

_BORDEROU_FIELDS = (
    "Nr_Doc_Z", "Data", "Total_Valoare",
    "Taxabile_21_Baza", "Taxabile_21_TVA",
    "Taxabile_11_Baza", "Taxabile_11_TVA",
    "Netaxabil_Baza",
)

def _score_borderou(rows: list | None) -> float:
    """Higher is better. Score = rows × avg field completeness."""
    if not rows:
        return 0.0
    complete = sum(
        1 for row in rows
        for f in _BORDEROU_FIELDS
        if row.get(f) not in (None, "", 0, 0.0)
    )
    return len(rows) * (complete / (len(rows) * len(_BORDEROU_FIELDS)))


# ── Borderou strategy A: table extraction (merged first cell) ────────────────

_BORDEROU_ROW_PREFIX = re.compile(
    r"^(\d+)\s+Z\s*POS\s+(\d+)\s+(\d{1,2}[-/][^\s]+[-/]\d{2,4})\s+"
)


def _borderou_strategy_table_merged(pdf_path: str) -> list | None:
    """Original approach: pdfplumber table, all columns merged into cell[0]."""
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for table_row in table:
                    if not table_row or not table_row[0]:
                        continue
                    cell0 = str(table_row[0])
                    m = _BORDEROU_ROW_PREFIX.match(cell0)
                    if not m:
                        continue
                    nr_doc_raw = m.group(2)
                    date_str = m.group(3)
                    try:
                        nr_doc = int(nr_doc_raw)
                        dt = pd.to_datetime(date_str, dayfirst=True)
                    except Exception:
                        continue
                    main_part = cell0.split("\n")[0]
                    num_tokens = _RO_NUM_PAT.findall(main_part)
                    if len(num_tokens) < 13:
                        continue
                    vals = [_parse_ro_float(t) for t in num_tokens[-13:]]
                    rows.append({
                        "Nr_Doc_Z": nr_doc,
                        "Data": dt,
                        "Total_Valoare": vals[0],
                        "Taxabile_21_Baza": vals[3],
                        "Taxabile_21_TVA": vals[4],
                        "Taxabile_11_Baza": vals[5],
                        "Taxabile_11_TVA": vals[6],
                        "Netaxabil_Baza": vals[11],
                    })
    return rows or None


# ── Borderou strategy B: table with "text" vertical strategy ─────────────────

def _borderou_strategy_table_text_strategy(pdf_path: str) -> list | None:
    """pdfplumber with vertical_strategy='text' to split columns differently."""
    rows = []
    settings = {
        "vertical_strategy": "text",
        "horizontal_strategy": "lines",
        "intersection_tolerance": 5,
    }
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables(settings):
                for table_row in table:
                    if not table_row:
                        continue
                    # Join all cells into one string and parse like strategy A
                    cell0 = " ".join(str(c) for c in table_row if c)
                    m = _BORDEROU_ROW_PREFIX.match(cell0)
                    if not m:
                        continue
                    nr_doc_raw = m.group(2)
                    date_str = m.group(3)
                    try:
                        nr_doc = int(nr_doc_raw)
                        dt = pd.to_datetime(date_str, dayfirst=True)
                    except Exception:
                        continue
                    main_part = cell0.split("\n")[0]
                    num_tokens = _RO_NUM_PAT.findall(main_part)
                    if len(num_tokens) < 13:
                        continue
                    vals = [_parse_ro_float(t) for t in num_tokens[-13:]]
                    rows.append({
                        "Nr_Doc_Z": nr_doc,
                        "Data": dt,
                        "Total_Valoare": vals[0],
                        "Taxabile_21_Baza": vals[3],
                        "Taxabile_21_TVA": vals[4],
                        "Taxabile_11_Baza": vals[5],
                        "Taxabile_11_TVA": vals[6],
                        "Netaxabil_Baza": vals[11],
                    })
    return rows or None


# ── Borderou strategy C: pure text extraction, line-by-line regex ────────────

def _borderou_strategy_text_lines(pdf_path: str) -> list | None:
    """
    Extract raw text from each page and match lines with the data prefix.
    Works on PDFs where pdfplumber table detection fails entirely.
    Handles continuation lines: if a row prefix is found but < 13 numbers,
    the next line's numbers are appended.
    """
    rows = []
    pending_prefix: tuple | None = None  # (nr_doc, dt, collected_tokens)

    for line in _all_page_text(pdf_path):
        line = line.strip()
        m = _BORDEROU_ROW_PREFIX.match(line)
        if m:
            # Flush any incomplete pending row first
            if pending_prefix:
                nr_doc, dt, tokens = pending_prefix
                if len(tokens) >= 13:
                    vals = [_parse_ro_float(t) for t in tokens[-13:]]
                    rows.append(_make_borderou_row(nr_doc, dt, vals))
                pending_prefix = None

            nr_doc_raw = m.group(2)
            date_str = m.group(3)
            try:
                nr_doc = int(nr_doc_raw)
                dt = pd.to_datetime(date_str, dayfirst=True)
            except Exception:
                continue

            main_part = line.split("\n")[0]
            num_tokens = _RO_NUM_PAT.findall(main_part)
            if len(num_tokens) >= 13:
                vals = [_parse_ro_float(t) for t in num_tokens[-13:]]
                rows.append(_make_borderou_row(nr_doc, dt, vals))
            else:
                pending_prefix = (nr_doc, dt, num_tokens)

        elif pending_prefix:
            # Continuation line — accumulate more numbers
            nr_doc, dt, tokens = pending_prefix
            extra = _RO_NUM_PAT.findall(line)
            tokens = tokens + extra
            if len(tokens) >= 13:
                vals = [_parse_ro_float(t) for t in tokens[-13:]]
                rows.append(_make_borderou_row(nr_doc, dt, vals))
                pending_prefix = None
            else:
                pending_prefix = (nr_doc, dt, tokens)

    # Flush last pending row
    if pending_prefix:
        nr_doc, dt, tokens = pending_prefix
        if len(tokens) >= 13:
            vals = [_parse_ro_float(t) for t in tokens[-13:]]
            rows.append(_make_borderou_row(nr_doc, dt, vals))

    return rows or None


def _make_borderou_row(nr_doc: int, dt, vals: list) -> dict:
    return {
        "Nr_Doc_Z": nr_doc,
        "Data": dt,
        "Total_Valoare": vals[0],
        "Taxabile_21_Baza": vals[3],
        "Taxabile_21_TVA": vals[4],
        "Taxabile_11_Baza": vals[5],
        "Taxabile_11_TVA": vals[6],
        "Netaxabil_Baza": vals[11],
    }


# ── Borderou strategy D: table with lines-only strategy ──────────────────────

def _borderou_strategy_table_lines_only(pdf_path: str) -> list | None:
    """pdfplumber with lines-only strategies — different PDF renderers."""
    rows = []
    settings = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 3,
        "join_tolerance": 3,
    }
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables(settings):
                for table_row in table:
                    if not table_row:
                        continue
                    cell0 = " ".join(str(c) for c in table_row if c)
                    m = _BORDEROU_ROW_PREFIX.match(cell0)
                    if not m:
                        continue
                    nr_doc_raw = m.group(2)
                    date_str = m.group(3)
                    try:
                        nr_doc = int(nr_doc_raw)
                        dt = pd.to_datetime(date_str, dayfirst=True)
                    except Exception:
                        continue
                    main_part = cell0.split("\n")[0]
                    num_tokens = _RO_NUM_PAT.findall(main_part)
                    if len(num_tokens) < 13:
                        continue
                    vals = [_parse_ro_float(t) for t in num_tokens[-13:]]
                    rows.append(_make_borderou_row(nr_doc, dt, vals))
    return rows or None


# ── Borderou public entry point ───────────────────────────────────────────────

_BORDEROU_STRATEGIES = [
    ("table_merged",       _borderou_strategy_table_merged),
    ("text_lines",         _borderou_strategy_text_lines),
    ("table_text_strat",   _borderou_strategy_table_text_strategy),
    ("table_lines_only",   _borderou_strategy_table_lines_only),
]


def extract_borderou_rows_from_pdf(pdf_path: str) -> list | None:
    """
    Try all Borderou extraction strategies and return the result with the
    highest completeness score (most rows × most non-zero fields).
    Returns None if all strategies fail.
    """
    best_rows = None
    best_score = -1.0
    best_name = None

    for name, strategy in _BORDEROU_STRATEGIES:
        try:
            rows = strategy(pdf_path)
            score = _score_borderou(rows)
            logger.debug("Borderou strategy '%s': %d rows, score=%.3f",
                         name, len(rows) if rows else 0, score)
            if score > best_score:
                best_score = score
                best_rows = rows
                best_name = name
        except Exception as exc:
            logger.warning("Borderou strategy '%s' failed: %s", name, exc)

    if best_rows:
        logger.info(
            "Borderou PDF '%s': best strategy='%s', %d rows (score=%.3f)",
            pdf_path, best_name, len(best_rows), best_score,
        )
    else:
        logger.warning("No data rows extracted from Borderou PDF: %s", pdf_path)

    return best_rows


# ── POS helpers ───────────────────────────────────────────────────────────────

_PAYMENT_TYPES = {"CARD", "CEC", "NUMERAR", "TICHET"}
_CARD_CEC = {"CARD", "CEC", "TICHET"}

_POS_COLS = ["Nr POS", "Nr. Z", "Data Ultimei Incasari", "Tip Incasare", "Valoare"]


def _score_pos(df: pd.DataFrame) -> float:
    if df is None or df.empty:
        return 0.0
    required = ["Nr POS", "Nr. Z", "Data Ultimei Incasari", "Tip Incasare", "Valoare"]
    present = [c for c in required if c in df.columns]
    if not present:
        return 0.0
    complete = df[present].apply(
        lambda col: col.notna() & (col.astype(str).str.strip() != "") & (col != 0)
    ).values.sum()
    return len(df) * (complete / (len(df) * len(required)))


def _detect_has_operator(data_lines: list) -> bool:
    for line in data_lines:
        tokens = line.split()
        if len(tokens) < 6:
            continue
        if tokens[4].upper() in _PAYMENT_TYPES:
            return False
        if len(tokens) > 5 and tokens[5].upper() in _PAYMENT_TYPES:
            return True
    return False


# ── POS strategy A: text lines (original) ────────────────────────────────────

def _pos_strategy_text_lines(pdf_path: str) -> pd.DataFrame:
    all_lines = _all_page_text(pdf_path)
    data_lines = [
        ln.strip()
        for ln in all_lines
        if re.match(r"^\d+\s+\d+\s+\d{1,2}[/\-.]", ln.strip())
    ]
    has_operator = _detect_has_operator(data_lines)
    records = []
    for line in data_lines:
        tokens = line.split()
        if len(tokens) < 6:
            continue
        nr_pos = tokens[0]
        nr_z = tokens[1]
        date_str = tokens[2]
        if has_operator:
            if len(tokens) < 7:
                continue
            tip = tokens[5].upper()
            val_tokens = tokens[6:]
        else:
            tip = tokens[4].upper()
            val_tokens = tokens[5:]
        if tip not in _CARD_CEC:
            continue
        if len(val_tokens) < 2:
            continue
        # Drop the trailing 'Rest Tichet' token; the rest form the Valoare
        # (which may be space-split for thousands, e.g. "1 678.99").
        valoare_str = "".join(val_tokens[:-1])
        try:
            valoare = _parse_ro_float(valoare_str)
        except Exception:
            continue
        records.append({
            "Nr POS": nr_pos,
            "Nr. Z": nr_z,
            "Data Ultimei Incasari": date_str,
            "Tip Incasare": tip,
            "Valoare": valoare,
        })
    return pd.DataFrame(records)


# ── POS strategy B: flexible token scanning ───────────────────────────────────

def _pos_strategy_flexible(pdf_path: str) -> pd.DataFrame:
    """
    Relaxed parser: finds tip keyword anywhere in the token list;
    takes the token immediately before tip as time/operator-agnostic,
    and the token after as valoare start.
    Works on PDFs where column ordering varies.
    """
    all_lines = _all_page_text(pdf_path)
    records = []
    for ln in all_lines:
        line = ln.strip()
        if not re.match(r"^\d+\s+\d+\s+\d{1,2}[/\-.]", line):
            continue
        tokens = line.split()
        # Find the first CARD/CEC token
        tip_idx = next(
            (i for i, t in enumerate(tokens) if t.upper() in _CARD_CEC), None
        )
        if tip_idx is None or tip_idx < 3:
            continue
        nr_pos = tokens[0]
        nr_z = tokens[1]
        date_str = tokens[2]
        tip = tokens[tip_idx].upper()
        val_tokens = tokens[tip_idx + 1:]
        if len(val_tokens) < 2:
            continue
        valoare_str = "".join(val_tokens[:-1])
        try:
            valoare = _parse_ro_float(valoare_str)
        except Exception:
            continue
        records.append({
            "Nr POS": nr_pos,
            "Nr. Z": nr_z,
            "Data Ultimei Incasari": date_str,
            "Tip Incasare": tip,
            "Valoare": valoare,
        })
    return pd.DataFrame(records)


# ── POS strategy C: table extraction ─────────────────────────────────────────

def _pos_strategy_table(pdf_path: str) -> pd.DataFrame:
    """
    Extract via pdfplumber tables. Headers may differ — map by keyword.
    Keeps only CARD/CEC rows.
    """
    all_rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                if not table or len(table) < 2:
                    continue
                headers = [str(h).strip().lower() if h else "" for h in table[0]]
                # Try to find relevant columns by keyword
                col_map = {}
                for i, h in enumerate(headers):
                    if "pos" in h and "nr" in h:
                        col_map["Nr POS"] = i
                    elif "nr" in h and ("z" in h or "inchid" in h):
                        col_map["Nr. Z"] = i
                    elif "data" in h:
                        col_map["Data Ultimei Incasari"] = i
                    elif "tip" in h or "incas" in h:
                        col_map["Tip Incasare"] = i
                    elif "val" in h or "suma" in h:
                        col_map["Valoare"] = i
                if "Tip Incasare" not in col_map or "Valoare" not in col_map:
                    continue
                for row in table[1:]:
                    if not row:
                        continue
                    tip = str(row[col_map["Tip Incasare"]] or "").upper().strip()
                    if tip not in _CARD_CEC:
                        continue
                    try:
                        val = _parse_ro_float(str(row[col_map["Valoare"]] or ""))
                    except Exception:
                        continue
                    all_rows.append({
                        "Nr POS": str(row[col_map.get("Nr POS", 0)] or "").strip(),
                        "Nr. Z": str(row[col_map.get("Nr. Z", 1)] or "").strip(),
                        "Data Ultimei Incasari": str(row[col_map.get("Data Ultimei Incasari", 2)] or "").strip(),
                        "Tip Incasare": tip,
                        "Valoare": val,
                    })
    return pd.DataFrame(all_rows)


# ── POS strategy D: text lines without time column ───────────────────────────

def _pos_strategy_no_time(pdf_path: str) -> pd.DataFrame:
    """
    Some POS PDFs omit the Time column:
    Format: NrPOS NrZ Date TipIncasare Valoare Rest
    """
    all_lines = _all_page_text(pdf_path)
    records = []
    for ln in all_lines:
        line = ln.strip()
        if not re.match(r"^\d+\s+\d+\s+\d{1,2}[/\-.]", line):
            continue
        tokens = line.split()
        if len(tokens) < 5:
            continue
        # Try tip at index 3 (no-time format) or index 4 (with-time format)
        for tip_idx in (3, 4, 5):
            if tip_idx < len(tokens) and tokens[tip_idx].upper() in _CARD_CEC:
                val_tokens = tokens[tip_idx + 1:]
                if len(val_tokens) < 1:
                    continue
                # May or may not have Rest column
                valoare_str = "".join(val_tokens[:-1]) if len(val_tokens) > 1 else val_tokens[0]
                try:
                    valoare = _parse_ro_float(valoare_str)
                except Exception:
                    continue
                records.append({
                    "Nr POS": tokens[0],
                    "Nr. Z": tokens[1],
                    "Data Ultimei Incasari": tokens[2],
                    "Tip Incasare": tokens[tip_idx].upper(),
                    "Valoare": valoare,
                })
                break
    return pd.DataFrame(records)


# ── POS public entry point ────────────────────────────────────────────────────

_POS_STRATEGIES = [
    ("text_lines",  _pos_strategy_text_lines),
    ("flexible",    _pos_strategy_flexible),
    ("no_time",     _pos_strategy_no_time),
    ("table",       _pos_strategy_table),
]


def extract_pos_dataframe_from_pdf(pdf_path: str) -> pd.DataFrame:
    """
    Try all POS extraction strategies and return the most complete result.
    """
    best_df = pd.DataFrame()
    best_score = -1.0
    best_name = None

    for name, strategy in _POS_STRATEGIES:
        try:
            df = strategy(pdf_path)
            score = _score_pos(df)
            logger.debug("POS strategy '%s': %d rows, score=%.3f",
                         name, len(df), score)
            if score > best_score:
                best_score = score
                best_df = df
                best_name = name
        except Exception as exc:
            logger.warning("POS strategy '%s' failed: %s", name, exc)

    logger.info(
        "POS PDF '%s': best strategy='%s', %d rows (score=%.3f)",
        pdf_path, best_name, len(best_df), best_score,
    )
    return best_df


# ── RetuRO-SGR Garantii extractor ────────────────────────────────────────────

_PERIOD_PAT = re.compile(
    r"In\s+(?:intervalul|perioada):\s*"
    r"(\d{2}\.\d{2}\.\d{4})\s*-\s*(\d{2}\.\d{2}\.\d{4})",
    re.IGNORECASE,
)


def _sgr_strategy_voucher_lines(pdf_path: str) -> pd.DataFrame:
    """Original: match 'Plata Voucher RetuRO' lines."""
    records = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.splitlines():
                line = line.strip()
                if not line.startswith("Plata Voucher RetuRO"):
                    continue
                tokens = line.split()
                if len(tokens) < 9:
                    continue
                nr_doc = tokens[3]
                date_str = tokens[4]
                valoare_raw = tokens[-3]
                try:
                    valoare = _parse_ro_float(valoare_raw)
                except Exception:
                    continue
                records.append({
                    "Nr. Z": nr_doc,
                    "Data Ultimei Incasari": date_str,
                    "Tip Incasare": "SGR",
                    "Valoare": valoare,
                })
    return pd.DataFrame(records)


def _sgr_strategy_flexible(pdf_path: str) -> pd.DataFrame:
    """
    Flexible fallback: find any line with 'Voucher' or 'RetuRO' and extract
    a date + numeric value, even if token count differs.
    """
    records = []
    date_pat = re.compile(r"\d{2}[-\.]\w{3}[-\.]\d{2,4}|\d{2}\.\d{2}\.\d{4}")
    for line in _all_page_text(pdf_path):
        line = line.strip()
        if "voucher" not in line.lower() and "returo" not in line.lower():
            continue
        tokens = line.split()
        # Find date token
        date_str = next((t for t in tokens if date_pat.match(t)), None)
        if not date_str:
            continue
        # Find numeric tokens — take last one before potential text suffix
        nums = _RO_NUM_PAT.findall(line)
        if len(nums) < 2:
            continue
        try:
            valoare = _parse_ro_float(nums[-3] if len(nums) >= 3 else nums[-1])
        except Exception:
            continue
        # nr_doc: first token after "RetuRO" keyword
        returo_idx = next(
            (i for i, t in enumerate(tokens) if t.upper() == "RETURO"), None
        )
        nr_doc = tokens[returo_idx + 1] if returo_idx is not None and returo_idx + 1 < len(tokens) else ""
        records.append({
            "Nr. Z": nr_doc,
            "Data Ultimei Incasari": date_str,
            "Tip Incasare": "SGR",
            "Valoare": valoare,
        })
    return pd.DataFrame(records)


def _score_df_rows(df: pd.DataFrame) -> float:
    if df is None or df.empty:
        return 0.0
    return float(len(df))


def extract_sgr_dataframe_from_pdf(pdf_path: str) -> pd.DataFrame:
    """Try all SGR strategies, return the most complete result."""
    strategies = [
        ("voucher_lines", _sgr_strategy_voucher_lines),
        ("flexible",      _sgr_strategy_flexible),
    ]
    best_df = pd.DataFrame()
    best_score = -1.0
    best_name = None

    for name, strategy in strategies:
        try:
            df = strategy(pdf_path)
            score = _score_df_rows(df)
            logger.debug("SGR strategy '%s': %d rows", name, len(df))
            if score > best_score:
                best_score = score
                best_df = df
                best_name = name
        except Exception as exc:
            logger.warning("SGR strategy '%s' failed: %s", name, exc)

    logger.info("SGR PDF '%s': best strategy='%s', %d rows", pdf_path, best_name, len(best_df))
    return best_df


# ── RetuRO voucher extractor (Garantii SGR Platite cu Numerar) ───────────────

_RETURO_LINE_PAT = re.compile(
    r"^Plata\s+Voucher\s+RetuRO\s+(\d+)\s+"
    r"(\d{1,2}[./-]\d{1,2}[./-]\d{4})\s+(.+)$",
    re.IGNORECASE,
)
_RETURO_NUM_TOKEN = re.compile(r"^-?\d{1,3}(?:[\s,]\d{3})*(?:[.,]\d+)?$")


def extract_returo_rows_from_pdf(pdf_path: str) -> pd.DataFrame:
    """Rows of a RetuRO 'Garantii SGR Platite cu Numerar' PDF report.

    Handles both report layouts: the 6-column one
    (Document / Nr. Document / Data Document / Explicatie / Valoare / Operator)
    and the 7-column one that also carries 'Marca Operator'. The value is taken
    as the first numeric token after the document date, so trailing marca /
    operator tokens are ignored in either layout.

    Returns columns Nr. Document (int) / Data Document (str) / Valoare (float),
    in file order and without de-duplication (callers decide how to merge
    overlapping report pages).
    """
    records = []
    for line in _all_page_text(pdf_path):
        m = _RETURO_LINE_PAT.match(line.strip())
        if not m:
            continue
        nr_doc, date_str, rest = m.group(1), m.group(2), m.group(3)
        value_token = next(
            (t for t in rest.split() if _RETURO_NUM_TOKEN.match(t)), None
        )
        if value_token is None:
            continue
        records.append({
            "Nr. Document": int(nr_doc),
            "Data Document": date_str,
            "Valoare": _parse_ro_float(value_token),
        })
    df = pd.DataFrame(records, columns=["Nr. Document", "Data Document", "Valoare"])
    logger.info("RetuRO PDF '%s': %d voucher rows", pdf_path, len(df))
    return df


# ── Tichete Valorice extractor ────────────────────────────────────────────────

_TOTAL_FURNZOR_PAT = re.compile(
    r"^TOTAL\s+FURNZOR\s+([\d,\.\s]+?)\s+([\d,\.\s]+?)\s*$",
    re.IGNORECASE,
)
_FURNIZOR_PAT = re.compile(r"^Furnizor:\s*(.+)$", re.IGNORECASE)


def _tichete_strategy_total_furnzor(pdf_path: str) -> pd.DataFrame:
    """Original: match TOTAL FURNZOR lines."""
    all_lines = _all_page_text(pdf_path)
    period_end_str = ""
    for line in all_lines:
        m = _PERIOD_PAT.search(line)
        if m:
            try:
                period_end_str = pd.to_datetime(m.group(2), format="%d.%m.%Y").strftime("%Y%m%d")
            except Exception:
                period_end_str = m.group(2)
            break

    records = []
    current_furnizor = "TICHET"
    row_index = 1
    for line in all_lines:
        line = line.strip()
        mf = _FURNIZOR_PAT.match(line)
        if mf:
            current_furnizor = mf.group(1).strip()
            continue
        mt = _TOTAL_FURNZOR_PAT.match(line)
        if mt:
            valoare_raw = mt.group(2).strip()
            try:
                valoare = _parse_ro_float(valoare_raw)
            except Exception:
                continue
            records.append({
                "Nr. Z": str(row_index),
                "Data Ultimei Incasari": period_end_str,
                "Tip Incasare": "TICHET",
                "Valoare": valoare,
                "Explicatie": current_furnizor,
            })
            row_index += 1
    return pd.DataFrame(records)


def _tichete_strategy_flexible(pdf_path: str) -> pd.DataFrame:
    """
    Fallback: also match 'TOTAL FURNIZOR' (with I) and lines that look like
    per-provider totals even without the exact keyword.
    """
    # Broaden the pattern to also allow 'FURNIZOR' (correct spelling)
    pat = re.compile(
        r"^TOTAL\s+FURNIZ[AO]R\s+([\d,\.\s]+?)\s+([\d,\.\s]+?)\s*$",
        re.IGNORECASE,
    )
    all_lines = _all_page_text(pdf_path)
    period_end_str = ""
    for line in all_lines:
        m = _PERIOD_PAT.search(line)
        if m:
            try:
                period_end_str = pd.to_datetime(m.group(2), format="%d.%m.%Y").strftime("%Y%m%d")
            except Exception:
                period_end_str = m.group(2)
            break

    records = []
    current_furnizor = "TICHET"
    row_index = 1
    for line in all_lines:
        line = line.strip()
        mf = _FURNIZOR_PAT.match(line)
        if mf:
            current_furnizor = mf.group(1).strip()
            continue
        mt = pat.match(line)
        if mt:
            valoare_raw = mt.group(2).strip()
            try:
                valoare = _parse_ro_float(valoare_raw)
            except Exception:
                continue
            records.append({
                "Nr. Z": str(row_index),
                "Data Ultimei Incasari": period_end_str,
                "Tip Incasare": "TICHET",
                "Valoare": valoare,
                "Explicatie": current_furnizor,
            })
            row_index += 1
    return pd.DataFrame(records)


def extract_tichete_dataframe_from_pdf(pdf_path: str) -> pd.DataFrame:
    """Try all Tichete strategies, return the most complete result."""
    strategies = [
        ("total_furnzor", _tichete_strategy_total_furnzor),
        ("flexible",      _tichete_strategy_flexible),
    ]
    best_df = pd.DataFrame()
    best_score = -1.0
    best_name = None

    for name, strategy in strategies:
        try:
            df = strategy(pdf_path)
            score = _score_df_rows(df)
            logger.debug("Tichete strategy '%s': %d rows", name, len(df))
            if score > best_score:
                best_score = score
                best_df = df
                best_name = name
        except Exception as exc:
            logger.warning("Tichete strategy '%s' failed: %s", name, exc)

    logger.info("Tichete PDF '%s': best strategy='%s', %d rows", pdf_path, best_name, len(best_df))
    return best_df


def extract_tichete_dataframe_from_xlsx(xlsx_path: str) -> pd.DataFrame:
    """Excel counterpart of extract_tichete_dataframe_from_pdf.

    The 'POS > Centralizator Incasari Tichete Valorice' Excel export has a title
    banner, a 'In intervalul: dd.mm.yyyy - dd.mm.yyyy' line, then per-supplier
    sections. We emit one row per furnizor with that supplier's grand total,
    matching the PDF output schema (Nr. Z / Data Ultimei Incasari / Tip Incasare /
    Valoare / Explicatie).

    Per supplier the total is taken from its 'TOTAL FURNZOR' row; when absent
    (single-supplier reports omit it) we fall back to the sum of 'TOTAL BON' rows.
    The supplier name appears either inline ('Furnizor: X'), in the next cell
    ('Furnizor:' | 'X'), or embedded after a newline in a 'TOTAL FURNZOR' cell.
    """
    raw = pd.read_excel(xlsx_path, header=None)

    def _last_num(cells):
        val = None
        for c in cells[1:]:
            if pd.isna(c):
                continue
            try:
                val = _parse_ro_float(str(c))
            except Exception:
                pass
        return val

    period_end = ""
    for _, row in raw.iterrows():
        blob = " ".join(str(c) for c in row if pd.notna(c))
        m = _PERIOD_PAT.search(blob)
        if m:
            try:
                period_end = pd.to_datetime(m.group(2), format="%d.%m.%Y").strftime("%Y%m%d")
            except Exception:
                period_end = m.group(2)
            break

    records = []
    cur_name = None
    furn_total = None   # from 'TOTAL FURNZOR'
    bon_sum = 0.0       # sum of 'TOTAL BON' (fallback)
    have_data = False

    def flush():
        nonlocal furn_total, bon_sum, have_data
        if cur_name and have_data:
            records.append({
                "Nr. Z": str(len(records) + 1),
                "Data Ultimei Incasari": period_end,
                "Tip Incasare": "TICHET",
                "Valoare": furn_total if furn_total is not None else bon_sum,
                "Explicatie": cur_name,
            })
        furn_total, bon_sum, have_data = None, 0.0, False

    for _, row in raw.iterrows():
        cells = list(row)
        col0 = str(cells[0]) if pd.notna(cells[0]) else ""
        last = _last_num(cells)
        for seg in col0.split("\n"):
            seg = seg.strip()
            up = seg.upper()
            if up.startswith("TOTAL FURNZOR") or up.startswith("TOTAL FURNIZOR"):
                if last is not None:
                    furn_total = last
                    have_data = True
            elif up.startswith("TOTAL BON"):
                if last is not None:
                    bon_sum += last
                    have_data = True
            elif up.startswith("TOTAL GENERAL"):
                continue
            elif up.startswith("FURNIZOR:"):
                name = seg.split(":", 1)[1].strip()
                if not name:  # name lives in the adjacent cell
                    name = next((str(c).strip() for c in cells[1:]
                                 if pd.notna(c) and str(c).strip()), "")
                if name and name != cur_name:
                    flush()
                    cur_name = name
    flush()  # emit the final open section

    return pd.DataFrame(records)


# ── Legacy compatibility shims ────────────────────────────────────────────────

def _row_looks_like_data(row: list) -> bool:
    """Return True if most cells look like data values (numeric, dates, codes)."""
    if not row:
        return False
    data_like = 0
    for v in row:
        s = str(v).strip() if v else ""
        if not s:
            continue
        # Numeric (possibly with %, commas, dots)
        if re.match(r"^-?[\d,.\s]+%?$", s):
            data_like += 1
        # Date-like (e.g. 01.Apr.26, 05.04.2026, 01/04/2026)
        elif re.match(r"^\d{1,2}[./\-]\w+[./\-]\d{2,4}$", s):
            data_like += 1
    return data_like >= len(row) * 0.4


def _build_headers_from_words(page, table_obj, num_cols: int) -> list[str] | None:
    """
    Build column headers from page words that sit above the table boundary.
    Uses table cell x-positions to assign multi-word headers to the right column.
    Returns None if no suitable header words are found.
    """
    table_top = table_obj.bbox[1]
    words = page.extract_words()
    header_words = sorted(
        [w for w in words if w["bottom"] <= table_top + 1],
        key=lambda w: w["x0"],
    )
    if not header_words:
        return None

    # Get column x-boundaries from the first row of table cells
    cells = table_obj.cells
    first_top = min(c[1] for c in cells)
    first_row_cells = sorted(
        [c for c in cells if abs(c[1] - first_top) < 2],
        key=lambda c: c[0],
    )
    if len(first_row_cells) != num_cols:
        return None

    # Column start x-positions (use cell x0)
    col_starts = [c[0] for c in first_row_cells]

    # Assign each header word to a column: find the last col_start <= word x0
    col_words: dict[int, list[str]] = {i: [] for i in range(num_cols)}
    for w in header_words:
        x = w["x0"]
        col_idx = 0
        for i, cx in enumerate(col_starts):
            if cx <= x + 2:  # small tolerance
                col_idx = i
        col_words[col_idx].append(w["text"])

    headers = [" ".join(col_words[i]) for i in range(num_cols)]
    # Check we got at least some non-empty headers
    if sum(1 for h in headers if h.strip()) < num_cols * 0.5:
        return None
    return headers


def _extract_overflow_column(page, table_obj, num_data_rows: int) -> tuple[str, list[str]] | None:
    """
    Check for a column of data to the right of the table boundary.
    Returns (header_name, [values...]) or None.
    """
    table_right = table_obj.bbox[2]
    table_top = table_obj.bbox[1]
    table_bottom = table_obj.bbox[3]
    words = page.extract_words()

    # Header words: above table, to the right of table boundary
    hdr_words = sorted(
        [w for w in words if w["bottom"] <= table_top + 1 and w["x0"] >= table_right - 1],
        key=lambda w: w["x0"],
    )
    header_name = " ".join(w["text"] for w in hdr_words).strip()
    if not header_name:
        return None

    # Data words: inside table y-range, to the right of table boundary
    data_words = sorted(
        [w for w in words if w["top"] >= table_top - 1 and w["bottom"] <= table_bottom + 1
         and w["x0"] >= table_right - 1],
        key=lambda w: w["top"],
    )

    # Group data words by y-position (each row)
    if not data_words:
        return header_name, [""] * num_data_rows

    # Get table row y-positions from cells
    cells = table_obj.cells
    col0_cells = sorted(
        [c for c in cells if abs(c[0] - min(cc[0] for cc in cells)) < 2],
        key=lambda c: c[1],
    )
    row_tops = [c[1] for c in col0_cells]

    values = []
    for rt_idx, rt in enumerate(row_tops):
        rb = col0_cells[rt_idx][3]  # row bottom
        row_words = [w for w in data_words if w["top"] >= rt - 2 and w["bottom"] <= rb + 2]
        val = " ".join(w["text"] for w in sorted(row_words, key=lambda w: w["x0"]))
        values.append(val.strip())

    # Pad or trim to match expected row count
    while len(values) < num_data_rows:
        values.append("")
    return header_name, values[:num_data_rows]


def extract_dataframe_from_pdf(pdf_path: str) -> pd.DataFrame:
    """Generic table extractor — largest table wins.

    Handles PDFs where the header row is rendered above the table boundary
    and/or an extra column overflows past the table's right edge.
    """
    best_table_data = None
    best_table_obj = None
    best_row_count = 0
    best_page = None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.find_tables()
            for tbl in tables:
                data = tbl.extract()
                if data and len(data) > best_row_count:
                    best_table_data = data
                    best_table_obj = tbl
                    best_row_count = len(data)
                    best_page = page

        if best_table_data is None or len(best_table_data) < 2:
            raise ValueError("No table found in PDF")

        num_cols = len(best_table_data[0])
        first_row = [str(v).strip() if v else "" for v in best_table_data[0]]

        if _row_looks_like_data(first_row):
            # Headers are outside the table — reconstruct from word positions
            headers = _build_headers_from_words(best_page, best_table_obj, num_cols)
            if not headers:
                headers = [f"Col{i}" for i in range(num_cols)]
            data_rows = best_table_data  # all rows are data

            # Check for an overflow column past the table's right edge
            overflow = _extract_overflow_column(
                best_page, best_table_obj, len(data_rows)
            )
            if overflow:
                extra_header, extra_values = overflow
                headers.append(extra_header)
                for row, val in zip(data_rows, extra_values):
                    row.append(val)
        else:
            headers = [
                str(h).strip() if h is not None else f"Col{i}"
                for i, h in enumerate(best_table_data[0])
            ]
            data_rows = best_table_data[1:]

    rows = [
        [str(cell).strip() if cell is not None else "" for cell in raw_row]
        for raw_row in data_rows
    ]
    # Deduplicate column names (e.g. two "Valoare TVA" → "Valoare TVA", "Valoare TVA.1")
    seen: dict[str, int] = {}
    deduped = []
    for h in headers:
        if h in seen:
            seen[h] += 1
            deduped.append(f"{h}.{seen[h]}")
        else:
            seen[h] = 0
            deduped.append(h)
    return pd.DataFrame(rows, columns=deduped)
