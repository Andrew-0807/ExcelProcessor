import pandas as pd
import re
from pathlib import Path
from typing import Dict, Tuple, Optional
import logging
from datetime import datetime

# Logging is configured centrally in app/log.py (quiet unless MOM_VERBOSE=1).
# Importing it here also covers standalone/CLI use of this module.
try:
    import app.log  # noqa: F401  (side effect: configures root logging via rich)
except Exception:
    pass
logger = logging.getLogger(__name__)

# Which payment kinds are kept per sub-firm, and the credit account each maps
# to. The keys of each entry double as the allowed-kinds set for that sub-firm —
# anything not listed (e.g. NUMERAR) is discarded during input filtering.
#   * AMT   (Complex: Fast Food, Restaurant, Autoservire) — Card→51131, Cec→51132,
#                                                            Tichete→51131.
#   * AMT_M (Amato/Magazine: M1, M2, M3)                   — Card/Tichete/Cec all →51131.
# Both families keep Tichete. NUMERAR is never kept (cash is handled elsewhere).
CREDIT_ACCOUNTS = {
    'AMT':   {'CARD': '51131', 'TICHETE': '51131', 'CEC': '51132'},
    'AMT_M': {'CARD': '51131', 'TICHETE': '51131', 'CEC': '51131'},
}

# The payment-type lives under different column names depending on the source
# format. Checked in priority order; the first one present in the file wins.
PAYMENT_TYPE_COLUMNS = ('Tip Incasare', 'Forma Plata', 'Explicatie')

# Diacritic-free, lowercased column names that mark the real header row. Used to
# skip title/banner rows the Excel export puts above the table (e.g. a row whose
# only cell is "POS > Centralizator Incasari Tichete Valorice").
_HEADER_TOKENS = {t.lower() for t in (
    'Nr. Z', 'Data Ultimei Incasari', 'Data', 'Tip Incasare', 'Valoare',
    'Explicatie', 'Forma Plata', 'Data Tranzactie', 'Data Document',
)}


def _payment_kind(*values) -> Optional[str]:
    """Classify a payment row as 'CARD', 'TICHETE' or 'CEC' from any of the
    candidate column values (handles composite strings like 'CARD AUTOSERVIRE').
    Returns None for anything else (e.g. NUMERAR)."""
    for v in values:
        s = str(v).strip().lower()
        if 'card' in s:
            return 'CARD'
        if 'tichet' in s:
            return 'TICHETE'
        if 'cec' in s:
            return 'CEC'
    return None


# Business configuration
BUSINESS_CONFIG = {
    'AMT': {
        'tag': 'AMT',
        'export_info': '20260101-20261231-CielStd_1057',
    },
    'AMT_M': {
        'tag': 'AMT',
        'export_info': '20260101-20261231-CielStd_1001',
    },
}

# POS type configurations
POS_CONFIGS = {
    'Fast Food 1': {
        'business': 'AMT',
        'punct_lucru': 'Fast Food 1',
        'explicatie': 'CARD',
    },
    'Fast Food 2': {
        'business': 'AMT',
        'punct_lucru': 'Fast Food 2',
        'explicatie': 'CARD',
    },
    'Autoservire': {
        'business': 'AMT',
        'punct_lucru': 'Autoservire',
        'explicatie': 'Cec',
    },
    'Restaurant': {
        'business': 'AMT',
        'punct_lucru': 'Restaurant',
        'explicatie': 'CARD',
    },
    'M1': {
        'business': 'AMT_M',
        'punct_lucru': 'M1',
        'explicatie': 'CARD',
    },
    'M2': {
        'business': 'AMT_M',
        'punct_lucru': 'M2',
        'explicatie': 'CARD',
    },
    'M3': {
        'business': 'AMT_M',
        'punct_lucru': 'M3',
        'explicatie': 'CARD',
    },
}

# Output column names (from target file)
OUTPUT_COLUMNS = [
    'Nr. inreg.', 'Tip inregistrare', 'Jurnal', 'Data', 'Data scadenta',
    'Numar document', 'Cod tip factura', 'Cont debit simbol', 'Cont debit titlu',
    'Metoda de plata SAF-T', 'Mecanism de plata SAF-T', 'Tip Taxa SAF-T',
    'Cod Taxa SAF-T', 'Cont credit simbol', 'Cont credit titlu',
    'Metoda de plata SAF-T    ', 'Mecanism de plata SAFT-T', 'Tip Taxa SAF_T',
    'Cod TAXA SAF_T', 'Explicatie', 'Valoare', 'Cod Partener', 'Partener CIF',
    'Partener Nume', 'Partener Rezidenta', 'Partener Judet', 'Partener Cont',
    'Angajat CNP', 'Angajat Nume', 'Angajat Cont', 'Optiune TVA', 'Cota TVA',
    'Cod TVA SAF-T', 'Moneda', 'Curs', 'Valoare deviza', 'Stornare - Nr. inreg.',
    'Incasari/plati', 'Diferente curs', 'TVA la incasare',
    'Colectare/Deducere TVA', 'Efect de incasat/platit', 'Banca efect',
    'Centre de cost', 'Informatii export', 'Punct de lucru', 'Deductibilitate',
    'Reevaluare', 'Factura simplificata', 'Borderou de achizitie',
    'Carnet prod. Agricole', 'Contract', 'Document stornat'
]
assert len(OUTPUT_COLUMNS) == 53


def _doc_number(v):
    """'Numar document' from the input 'Nr. Z'. The model stores it as a NUMBER,
    so plain str() produced text cells (left-aligned, rejected by the import) and
    turned float-typed columns into '890.0' / empty cells into the string 'nan'.
    Numeric-looking values come out as int, anything else stays text, blank stays
    blank."""
    s = str(v).strip()
    if s == '' or s.lower() in ('nan', 'nat', 'none'):
        return ''
    if s.endswith('.0'):          # pandas read the column as float
        s = s[:-2]
    return int(s) if s.isdigit() else s


# ── Alternate POS PDF layout (AMT_M "Forma Plata" export) ────────────────────
# The shared extractor in core/pdf_extractor.py only knows the layout
#     Nr POS | Nr. Z | Data Ultimei Incasari | Operator | Tip Incasare | Valoare | Rest Tichet
# whose data lines start "<int> <int> <date>". Newer AMT_M (M1/M2/M3) exports of
# the same report use a different column order and an extra leading column:
#     Inchidere | Data Ultimei Incasari | Numar POS | Numar Z | Operator | Forma Plata | Valoare | Rest Tichete
#     e.g. "10245 01.Jul.26 22:13:48 12 980 CARD 7395.3 0"
# Those lines start "<int> <date>", so every core strategy skips them and the
# extractor returns a 0x0 DataFrame. This parser handles that layout and emits
# the exact same five columns, so everything downstream stays unchanged.
_ALT_KIND_TOKENS = ('CARD', 'CEC', 'TICHET')

# 01.Jul.26 / 01-Jul-26 / 01/07/2026 / 01.07.2026 (a whole token, no time part)
_ALT_DATE_TOKEN = re.compile(r'^\d{1,2}[./-](?:\d{1,2}|[A-Za-z]{3,})[./-]\d{2,4}$')

_ALT_POS_COLUMNS = ['Nr POS', 'Nr. Z', 'Data Ultimei Incasari', 'Tip Incasare', 'Valoare']


def _alt_float(s: str) -> Optional[float]:
    """Parse a Romanian/English decimal ('17747.42', '10,964.05', '125,5')."""
    s = re.sub(r'[\s,](?=\d{3}(?!\d))', '', str(s).strip())
    s = s.replace(',', '.')
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _extract_pos_alt_layout(pdf_path: str) -> pd.DataFrame:
    """Parse the 'Forma Plata' POS PDF layout described above.

    Returns a DataFrame with the standard POS columns (empty if nothing matched).
    NUMERAR is dropped here, mirroring the core extractor.
    """
    import pdfplumber

    records = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for line in (page.extract_text() or '').splitlines():
                tokens = line.split()
                if len(tokens) < 5:
                    continue
                tip_idx = next((i for i, t in enumerate(tokens)
                                if t.upper() in _ALT_KIND_TOKENS), None)
                if tip_idx is None:
                    continue
                head = tokens[:tip_idx]
                date_idx = next((i for i, t in enumerate(head)
                                 if _ALT_DATE_TOKEN.match(t)), None)
                if date_idx is None:
                    continue  # header line / totals line
                # Between the date (+ its time token) and the payment type sit
                # Numar POS, Numar Z and an often-blank Operator. Read from the
                # left so a populated Operator cannot shift Numar Z.
                ints = [t for t in head[date_idx + 1:] if t.isdigit()]
                if len(ints) < 2:
                    continue
                val_tokens = tokens[tip_idx + 1:]
                if not val_tokens:
                    continue
                # The trailing token is the informational 'Rest Tichete' column;
                # the rest form Valoare (may be space-split for thousands).
                valoare = _alt_float(
                    ''.join(val_tokens[:-1]) if len(val_tokens) > 1 else val_tokens[0]
                )
                if valoare is None:
                    continue
                records.append({
                    'Nr POS': ints[0],
                    'Nr. Z': ints[1],
                    # Normalize separators to '-' so the DD-MMM-YY fast path in
                    # _transform_data recognizes '01.Jul.26'.
                    'Data Ultimei Incasari': re.sub(r'[./]', '-', head[date_idx]),
                    'Tip Incasare': tokens[tip_idx].upper(),
                    'Valoare': valoare,
                })
    return pd.DataFrame(records, columns=_ALT_POS_COLUMNS)


class POSProcessor:
    """Process POS files and convert them to the required import format."""
    
    def __init__(self, input_file: str, output_file: str, pos_type: str, filename: str = None,
                 start_nr: int = None):
        """
        Initialize POSProcessor.

        Args:
            input_file: Path to the input POS file
            output_file: Path to save the output file
            pos_type: Type of POS (must be a key in POS_CONFIGS)
            filename: Original filename for M1/M2/M3 detection
            start_nr: First 'Nr. inreg.' value; each row increments by 1. None → blank.
        """
        self.input_file = Path(input_file)
        self.output_file = Path(output_file) if output_file else None
        self.pos_type = pos_type
        self.filename = filename or input_file
        self.start_nr = start_nr
        
        if pos_type not in POS_CONFIGS:
            raise ValueError(f"Invalid POS type. Must be one of: {', '.join(POS_CONFIGS.keys())}")
        
        self.config = POS_CONFIGS[pos_type].copy()
        self.config['filename'] = self.filename  # Add filename to config
        
    @staticmethod
    def _normalize_col(name: str) -> str:
        """Strip whitespace and replace Romanian diacritics so column lookups work
        regardless of whether the Excel file uses ă/î/ș/ț or their plain equivalents."""
        name = str(name).strip()
        for ro, plain in [('ă', 'a'), ('Ă', 'A'), ('â', 'a'), ('Â', 'A'),
                          ('î', 'i'), ('Î', 'I'), ('ș', 's'), ('Ș', 'S'),
                          ('ț', 't'), ('Ț', 'T')]:
            name = name.replace(ro, plain)
        return name

    @classmethod
    def _read_excel_table(cls, path) -> pd.DataFrame:
        """read_excel, but tolerant of leading title/banner rows. Scans the first
        rows for the one that holds known column names and uses it as the header;
        falls back to row 0 when nothing matches (original behaviour)."""
        raw = pd.read_excel(path, header=None)
        for i in range(min(10, len(raw))):
            cells = {cls._normalize_col(c).lower()
                     for c in raw.iloc[i] if pd.notna(c)}
            if cells & _HEADER_TOKENS:
                return pd.read_excel(path, header=i)
        # No recognizable header row — dump the raw sheet so the real layout is
        # visible in the logs (this xlsx differs from the PDF export).
        logger.warning(
            "No known header row found in %s. Raw first rows:\n%s",
            path, raw.head(8).to_string()
        )
        return pd.read_excel(path, header=0)

    def _read_input_file(self) -> pd.DataFrame:
        """Read the input POS file and return a DataFrame."""
        logger.info(f"Reading input file: {self.input_file}")
        try:
            # Read the file based on extension
            if self.input_file.suffix.lower() == '.xlsx':
                # The 'Tichete Valorice' Excel export is a per-supplier report with
                # no normal header row; route it to the dedicated extractor (same as
                # the PDF path). Other xlsx files use plain header detection.
                if 'tichete' in Path(self.filename).name.lower():
                    from app.modules.core.pdf_extractor import extract_tichete_dataframe_from_xlsx
                    df = extract_tichete_dataframe_from_xlsx(str(self.input_file))
                else:
                    df = self._read_excel_table(self.input_file)
            elif self.input_file.suffix.lower() == '.pdf':
                from app.modules.core.pdf_extractor import (
                    extract_pos_dataframe_from_pdf,
                    extract_sgr_dataframe_from_pdf,
                    extract_tichete_dataframe_from_pdf,
                )
                # Use the original filename (self.filename) for routing, not the
                # temp file path (self.input_file.name) which has no meaningful name.
                name_lower = Path(self.filename).name.lower()
                if 'sgr' in name_lower:
                    df = extract_sgr_dataframe_from_pdf(str(self.input_file))
                elif 'tichete' in name_lower:
                    df = extract_tichete_dataframe_from_pdf(str(self.input_file))
                else:
                    df = extract_pos_dataframe_from_pdf(str(self.input_file))
                    if df is None or df.empty:
                        # Core knows only the "Nr POS | Nr. Z | Data ..." layout;
                        # fall back to the AMT_M "Forma Plata" layout parser.
                        logger.info(
                            "Core POS extractor returned no rows for %s; "
                            "trying the alternate 'Forma Plata' layout.",
                            self.filename,
                        )
                        df = _extract_pos_alt_layout(str(self.input_file))
            else:
                df = pd.read_csv(self.input_file, encoding='latin1')

            # Clean column names: strip whitespace and normalize Romanian diacritics
            # so that e.g. 'Data Ultimei Încasări' matches 'Data Ultimei Incasari'
            df.columns = [self._normalize_col(c) for c in df.columns]
            logger.info(f"Columns after normalization: {list(df.columns)}")
            
            # Filter by payment type — NUMERAR is dropped here. The kinds kept
            # depend on the sub-firm: AMT keeps Card/Cec, AMT_M also keeps
            # Tichete. The type column name varies by source format (Tip Incasare
            # / Forma Plata / Explicatie); use the first one present.
            type_col = next((c for c in PAYMENT_TYPE_COLUMNS if c in df.columns), None)
            if type_col is None:
                # Source format we don't know by name: pick the column whose cells
                # most often classify as a payment kind. Prevents the silent "no
                # filter → NUMERAR leaks through → Explicatie='AMT'" failure mode.
                hits = {c: df[c].map(lambda v: _payment_kind(v) is not None).sum()
                        for c in df.columns}
                type_col = max(hits, key=hits.get) if hits and max(hits.values()) else None

            if type_col:
                allowed = set(CREDIT_ACCOUNTS[self.config['business']])
                # Classify once and carry the result so the transform never has to
                # re-derive it (and never falls back to the 'AMT' placeholder).
                # _payment_kind handles exact values ("Card", "Cec", "Tichet",
                # "Numerar") and composite ones ("CARD AUTOSERVIRE").
                df['_kind'] = df[type_col].map(_payment_kind)
                df = df[df['_kind'].isin(allowed)].copy().reset_index(drop=True)
                logger.info(f"Filtered by {type_col}: {len(df)} rows remaining")
                # Output preserves the input row order (per day: TICHET then CARD,
                # as it comes from the report) — no regrouping by payment kind.
            else:
                # Raise so the file lands in errors/<module>/ for inspection rather
                # than slipping through unfiltered (NUMERAR would leak as garbage).
                raise ValueError(
                    f"No payment-type column found for filtering. Tried {PAYMENT_TYPE_COLUMNS} "
                    f"and value-sniffing. Available columns: {list(df.columns)}"
                )
            
            # Log basic info about loaded data
            logger.info(f"Successfully loaded {len(df)} rows from {self.input_file}")
            logger.debug(f"Columns in input file: {', '.join(df.columns)}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error reading input file: {e}")
            raise
    
    def _transform_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform the input data into the required output format."""
        logger.info("Transforming data...")

        # Detect date column once before the row loop to avoid per-row KeyError spam
        _DATE_COL_CANDIDATES = [
            'Data Ultimei Incasari', 'Data', 'Data Tranzactie', 'Data Document'
        ]
        date_col = next((c for c in _DATE_COL_CANDIDATES if c in df.columns), None)

        # 'Numar document' source column. Hardcoding 'Nr. Z' left the column blank
        # whenever an export named it slightly differently (e.g. 'Nr Z', 'Nr.Z',
        # 'Numar document'). Match the first present candidate by its already-
        # normalized name; None → blank, same as before.
        _DOC_COL_CANDIDATES = [
            'Nr. Z', 'Nr Z', 'Nr.Z', 'NrZ', 'Numar Z', 'NumarZ',
            'Numar document', 'Numar Document', 'Nr. Document', 'Nr Document',
        ]
        doc_col = next((c for c in _DOC_COL_CANDIDATES if c in df.columns), None)
        if date_col is None:
            # Raise (don't just log) so the server routes the file to errors/<module>/
            # with a report, instead of silently writing a garbage CSV.
            raise ValueError(
                f"No date column found in input file. "
                f"Tried: {_DATE_COL_CANDIDATES}. "
                f"Available columns: {list(df.columns)}"
            )

        # Create a new DataFrame with the required columns
        output_data = []

        for row_idx, (_, row) in enumerate(df.iterrows()):
            # Two-stage date parsing: DD-MMM-YY first, pandas fallback second
            formatted_date = ''
            if date_col:
                raw = row.get(date_col, '')
                raw_str = str(raw).strip() if raw is not None else ''
                if raw_str and raw_str.lower() not in ('nat', 'nan', 'none', ''):
                    # Stage 1: DD-MMM-YY (e.g. "18-Mar-26")
                    try:
                        date_part = raw_str.split()[0]
                        day, month_str, year = date_part.split('-')
                        month_map = {
                            'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
                            'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
                            'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12',
                        }
                        month_num = month_map[month_str]  # KeyError → fallback
                        formatted_date = f"20{year}{month_num}{day.zfill(2)}"
                    except (KeyError, ValueError, AttributeError, IndexError):
                        # Stage 2: DD/MM/YYYY or other formats — always dayfirst
                        try:
                            formatted_date = pd.to_datetime(raw, dayfirst=True).strftime('%Y%m%d')
                        except Exception as e:
                            logger.warning(f"Could not parse date '{raw_str}': {e}")
            
            # Debit account is driven by the (already-detected) POS type, not by
            # re-scanning the raw filename — a filename like "...m 2..." (space)
            # would not match a bare "M2" substring and silently fall back to the
            # AMT default. M1/M2/M3 → 5311x; everything else (AMT) → 5311.
            debit_account = {
                'M1': '53111', 'M2': '53112', 'M3': '53113',
            }.get(self.pos_type, '5311')
            
            # Determine cont_credit and output Explicatie from the payment type.
            # The credit account is sub-firm-specific (see CREDIT_ACCOUNTS):
            # AMT splits Card/Cec across 51131/51132, AMT_M maps all kinds to
            # 51131. The type column name varies by source format, so check all.
            business_tag = BUSINESS_CONFIG[self.config['business']]['tag']
            credit_map = CREDIT_ACCOUNTS[self.config['business']]
            # Prefer the kind classified at filter time; only re-derive if absent.
            kind = row.get('_kind')
            if kind not in credit_map:
                kind = _payment_kind(
                    row.get('Tip Incasare', ''),
                    row.get('Forma Plata', ''),
                    row.get('Explicatie', ''),
                )

            if kind in credit_map:
                cont_credit  = credit_map[kind]
                # Output label matches the source vocabulary: tichete rows are
                # written as 'TICHET' (singular), as in the import model.
                explicatie_out = 'TICHET' if kind == 'TICHETE' else kind
            else:
                # Shouldn't occur (disallowed kinds are filtered upstream), but
                # stay safe. Credit fallback is 51131 (the common POS credit
                # account), never the 5311 cash debit account.
                cont_credit  = '51131'
                explicatie_out = business_tag

            # Negate value: these are credit entries (money leaving the cash
            # register). The booked value is the 'Valoare' column as-is — the
            # 'Rest Tichet' column is informational and NOT applied.
            raw_val = row.get('Valoare', 0)
            try:
                valoare = -abs(float(raw_val))
            except (TypeError, ValueError):
                valoare = raw_val

            # First row gets the account title; subsequent rows leave it blank
            debit_titlu = 'Casa in lei' if row_idx == 0 else ''

            # Create a new row in the output format
            new_row = {
                'Nr. inreg.': (self.start_nr + row_idx) if self.start_nr is not None else '',
                'Tip inregistrare': 'Casa',
                'Jurnal': 'RC',
                'Data': formatted_date,
                'Data scadenta': formatted_date,
                'Numar document': _doc_number(row.get(doc_col, '')) if doc_col else '',
                'Cod tip factura': '',
                'Cont debit simbol': debit_account,
                'Cont debit titlu': debit_titlu,
                'Metoda de plata SAF-T': '',
                'Mecanism de plata SAF-T': '',
                'Tip Taxa SAF-T': '',
                'Cod Taxa SAF-T': '',
                'Cont credit simbol': cont_credit,
                'Cont credit titlu': '',
                'Metoda de plata SAF-T    ': '',
                'Mecanism de plata SAFT-T': '',
                'Tip Taxa SAF_T': '',
                'Cod TAXA SAF_T': '',
                'Explicatie': explicatie_out,
                'Valoare': valoare,
                'Cod Partener': '',
                'Partener CIF': '',
                'Partener Nume': '',
                'Partener Rezidenta': '',
                'Partener Judet': '',
                'Partener Cont': '',
                'Angajat CNP': '',
                'Angajat Nume': '',
                'Angajat Cont': '',
                'Optiune TVA': '',
                'Cota TVA': '',
                'Cod TVA SAF-T': '',
                'Moneda': '',
                'Curs': '',
                'Valoare deviza': '',
                'Stornare - Nr. inreg.': '',
                'Incasari/plati': '',
                'Diferente curs': '',
                'TVA la incasare': 0,
                'Colectare/Deducere TVA': '',
                'Efect de incasat/platit': '',
                'Banca efect': '',
                'Centre de cost': '',
                'Informatii export': BUSINESS_CONFIG[self.config['business']]['export_info'],
                'Punct de lucru': self.config['punct_lucru'],
                'Deductibilitate': '',
                'Reevaluare': '',
                'Factura simplificata': 0,
                'Borderou de achizitie': 0,
                'Carnet prod. Agricole': 0,
                'Contract': 0,
                'Document stornat': 0
            }
            
            output_data.append(new_row)
        
        # Create DataFrame from the processed rows
        output_df = pd.DataFrame(output_data, columns=OUTPUT_COLUMNS)
        
        return output_df
    
    def process(self) -> pd.DataFrame:
        """Process the input file, return the output DataFrame, and (if an output
        path was given) write it. Callers that want xlsx straight from the
        DataFrame can ignore the file and use the return value."""
        try:
            input_df = self._read_input_file()
            output_df = self._transform_data(input_df)

            if self.output_file is not None:
                if self.output_file.suffix.lower() in ('.xlsx', '.xls'):
                    output_df.to_excel(self.output_file, index=False)
                else:
                    output_df.to_csv(self.output_file, index=False, encoding='utf-8-sig')
                logger.info(f"Successfully saved output to {self.output_file}")

            return output_df

        except Exception as e:
            logger.error(f"Error processing file: {e}")
            raise

def detect_pos_type(filename: str) -> Optional[str]:
    """Detect the POS type based on the filename."""
    filename_lower = str(filename).lower()
    
    # More flexible pattern matching
    if any(x in filename_lower for x in ['fast food 1', 'fastfood1', 'ff1']):
        return 'Fast Food 1'
    elif any(x in filename_lower for x in ['fast food 2', 'fastfood2', 'ff2']):
        return 'Fast Food 2'

    # Magazine codes: allow a space/dash/underscore between 'm' and the digit so
    # filenames like "m 2", "m-2", "m_2" still resolve (real client files do this).
    # ponytail: coincidental "...m3..." inside another word would false-match;
    # acceptable until a real filename collides — then anchor on a separator.
    m = re.search(r'm[\s_\-]?([123])(?!\d)', filename_lower)
    if m:
        return f'M{m.group(1)}'
    elif 'autoservire' in filename_lower or 'amt complex' in filename_lower:
        return 'Autoservire'
    elif 'restaurant' in filename_lower:
        return 'Restaurant'

    return None

def process_pos_file(input_path: str, output_path: str = None, pos_type: str = None,
                     original_filename: str = None, start_nr: int = None) -> "pd.DataFrame":
    """
    Process a POS file and convert it to the required import format.
    Returns the output DataFrame; writes a file only when output_path is given.

    Args:
        input_path: Path to the input POS file
        output_path: Where to write the output. None → don't write, just return the
            DataFrame (server/CLI use this to go straight to xlsx, no CSV step).
        pos_type: Type of POS (if None, will try to detect from filename)
        original_filename: The original filename to use for POS type detection and M1/M2 routing
        start_nr: First 'Nr. inreg.' value (increments by 1 per row); None leaves it blank.
    """
    input_path = Path(input_path)

    filename_to_check = original_filename or input_path.name

    if pos_type is None:
        pos_type = detect_pos_type(filename_to_check)
        if pos_type is None:
            logger.warning(f"Could not explicitly detect POS type from filename: {filename_to_check}. Defaulting to 'Autoservire'")
            pos_type = 'Autoservire'  # Fallback

    # output_path=None → process in memory and just return the DataFrame (no file).
    processor = POSProcessor(str(input_path), output_path, pos_type,
                             filename=filename_to_check, start_nr=start_nr)
    return processor.process()

if __name__ == "__main__":
    import argparse
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Process POS files into import format.')
    parser.add_argument('input_file', help='Path to the input POS file')
    parser.add_argument('-o', '--output', help='Output file path (default: same as input with IMPORT CARD prefix)')
    parser.add_argument('-t', '--pos-type', 
                        choices=['Fast Food 1', 'Fast Food 2', 'Autoservire', 'Restaurant', 'M1', 'M2', 'M3'],
                        help='Type of POS (if not provided, will try to detect from filename)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    
    # Standalone CLI: default to writing next to the input (xlsx) when -o omitted.
    out = args.output
    if out is None:
        inp = Path(args.input_file)
        out = str(inp.parent / f"IMPORT CARD {inp.stem}.xlsx")
    process_pos_file(args.input_file, out, args.pos_type)
