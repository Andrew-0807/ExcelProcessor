import pandas as pd
from pathlib import Path
from typing import Dict, Tuple, Optional
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Allowed payment types for filtering (lowercase).
ALLOWED_PAYMENT_TYPES = {'card', 'cec', 'sgr', 'tichet'}

# Mapping of explicatie to cont_credit
EXPLICATIE_TO_ACCOUNT = {
    'CARD': '51131',
    'Cec': '51132',
    'CASH': '5311',
    # Add more mappings as needed
}

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

class POSProcessor:
    """Process POS files and convert them to the required import format."""
    
    def __init__(self, input_file: str, output_file: str, pos_type: str, filename: str = None):
        """
        Initialize POSProcessor.
        
        Args:
            input_file: Path to the input POS file
            output_file: Path to save the output file
            pos_type: Type of POS (must be a key in POS_CONFIGS)
            filename: Original filename for M1/M2/M3 detection
        """
        self.input_file = Path(input_file)
        self.output_file = Path(output_file)
        self.pos_type = pos_type
        self.filename = filename or input_file
        
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

    def _read_input_file(self) -> pd.DataFrame:
        """Read the input POS file and return a DataFrame."""
        logger.info(f"Reading input file: {self.input_file}")
        try:
            # Read the file based on extension
            if self.input_file.suffix.lower() == '.xlsx':
                df = pd.read_excel(self.input_file)
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
            else:
                df = pd.read_csv(self.input_file, encoding='latin1')

            # Clean column names: strip whitespace and normalize Romanian diacritics
            # so that e.g. 'Data Ultimei Încasări' matches 'Data Ultimei Incasari'
            df.columns = [self._normalize_col(c) for c in df.columns]
            logger.info(f"Columns after normalization: {list(df.columns)}")
            
            # Filter by payment type (card or cec only)
            tip_col = 'Tip Incasare' if 'Tip Incasare' in df.columns else 'Explicatie'
            if tip_col in df.columns:
                df = df[df[tip_col].astype(str).str.strip().str.lower().isin(ALLOWED_PAYMENT_TYPES)]
                logger.info(f"Filtered by payment type: {len(df)} rows remaining")
            
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
        if date_col is None:
            logger.error(
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
            
            # Get the correct debit account based on filename
            filename = self.config.get('filename', '')
            if 'M1' in filename.upper():
                debit_account = '53111'
            elif 'M2' in filename.upper():
                debit_account = '53112'
            elif 'M3' in filename.upper():
                debit_account = '53113'
            else:
                debit_account = '5311'  # Default for AMT COMPLEX
            
            # Determine cont_credit and output Explicatie based on Tip Incasare
            tip_inc = str(row.get('Tip Incasare', '')).upper()
            explicatie_in = str(row.get('Explicatie', '')).upper()

            if tip_inc == 'CARD' or 'CARD' in explicatie_in:
                cont_credit  = '51131'
                explicatie_out = 'CARD'
            elif tip_inc == 'CEC' or 'CEC' in explicatie_in:
                cont_credit  = '51132'
                explicatie_out = 'Cec'
            elif tip_inc == 'TICHET':
                cont_credit  = '53281'
                explicatie_out = 'TICHET'
            else:
                # SGR and any other cash type
                cont_credit  = '5311'
                explicatie_out = tip_inc if tip_inc else 'SGR'

            # Negate value: these are credit entries (money leaving the cash register)
            raw_val = row.get('Valoare', 0)
            try:
                valoare = -abs(float(raw_val))
            except (TypeError, ValueError):
                valoare = raw_val

            # First row gets the account title; subsequent rows leave it blank
            debit_titlu = 'Casa in lei' if row_idx == 0 else ''

            # Create a new row in the output format
            new_row = {
                'Nr. inreg.': '',
                'Tip inregistrare': 'Casa',
                'Jurnal': 'RC',
                'Data': formatted_date,
                'Data scadenta': formatted_date,
                'Numar document': str(row.get('Nr. Z', '')),
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
    
    def process(self) -> None:
        """Process the input file and save the output."""
        try:
            # Read the input file
            input_df = self._read_input_file()
            
            # Transform the data
            output_df = self._transform_data(input_df)
            
            # Save the output file
            if self.output_file.suffix.lower() in ('.xlsx', '.xls'):
                output_df.to_excel(self.output_file, index=False)
            else:
                output_df.to_csv(self.output_file, index=False, encoding='utf-8-sig')
            logger.info(f"Successfully saved output to {self.output_file}")
            
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
    elif 'm1' in filename_lower:
        return 'M1'
    elif 'm2' in filename_lower:
        return 'M2'
    elif 'm3' in filename_lower:
        return 'M3'
    elif 'autoservire' in filename_lower or 'amt complex' in filename_lower:
        return 'Autoservire'

    return None

def process_pos_file(input_path: str, output_path: str = None, pos_type: str = None, original_filename: str = None) -> None:
    """
    Process a POS file and convert it to the required import format.
    
    Args:
        input_path: Path to the input POS file
        output_path: Path to save the output file (default: same as input with 'IMPORT CARD' prefix)
        pos_type: Type of POS (if None, will try to detect from filename)
        original_filename: The original filename to use for POS type detection and M1/M2 routing
    """
    input_path = Path(input_path)
    
    if output_path is None:
        # Default output path
        output_filename = f"IMPORT CARD {input_path.name}"
        if input_path.suffix.lower() == '.pdf':
            output_filename = output_filename.replace('.pdf', '.csv').replace('.PDF', '.csv')
        output_path = input_path.parent / output_filename
    
    filename_to_check = original_filename or input_path.name
    
    if pos_type is None:
        pos_type = detect_pos_type(filename_to_check)
        if pos_type is None:
            logger.warning(f"Could not explicitly detect POS type from filename: {filename_to_check}. Defaulting to 'Autoservire'")
            pos_type = 'Autoservire'  # Fallback
            
    # Process the file
    processor = POSProcessor(str(input_path), str(output_path), pos_type, filename=filename_to_check)
    processor.process()

if __name__ == "__main__":
    import argparse
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Process POS files into import format.')
    parser.add_argument('input_file', help='Path to the input POS file')
    parser.add_argument('-o', '--output', help='Output file path (default: same as input with IMPORT CARD prefix)')
    parser.add_argument('-t', '--pos-type', 
                        choices=['Fast Food 1', 'Fast Food 2', 'Autoservire', 'M1', 'M2', 'M3'],
                        help='Type of POS (if not provided, will try to detect from filename)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    
    # Process the file
    process_pos_file(args.input_file, args.output, args.pos_type)
