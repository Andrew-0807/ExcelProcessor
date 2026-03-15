import pandas as pd
from pathlib import Path
from typing import Dict, Tuple, Optional
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Allowed payment types for filtering
ALLOWED_PAYMENT_TYPES = {'card', 'cec'}

# Business configuration
BUSINESS_CONFIG = {
    'AMT': {
        'tag': 'AMT',
        'export_info': '20260101-20261231-CielStd_1057',
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
    'Restaurant': {
        'business': 'AMT',
        'punct_lucru': 'Restaurant',
        'explicatie': 'CARD',
    },
    'Autoservire': {
        'business': 'AMT',
        'punct_lucru': 'Autoservire',
        'explicatie': 'Cec',
    },
    'M1': {
        'business': 'AMT',
        'punct_lucru': 'M1',
        'explicatie': 'CARD',
    },
    'M2': {
        'business': 'AMT',
        'punct_lucru': 'M2',
        'explicatie': 'CARD',
    },
    'M3': {
        'business': 'AMT',
        'punct_lucru': 'M3',
        'explicatie': 'CARD',
    },
}

# Output column names (from target file, strictly 53 columns)
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

class POSProcessor:
    """Process POS files and convert them to the required import format."""
    
    def __init__(self, input_file: str, output_file: str, pos_type: str, filename: str = None):
        """
        Initialize POSProcessor.
        
        Args:
            input_file: Path to the input POS file
            output_file: Path to save the output file
            pos_type: Type of POS (must be a key in POS_CONFIGS)
            filename: Original filename
        """
        self.input_file = Path(input_file)
        self.output_file = Path(output_file)
        self.pos_type = pos_type
        self.filename = filename or self.input_file.name
        
        if pos_type not in POS_CONFIGS:
            raise ValueError(f"Invalid POS type. Must be one of: {', '.join(POS_CONFIGS.keys())}")
        
        self.config = POS_CONFIGS[pos_type].copy()
        self.config['filename'] = self.filename
        
    def _read_input_file(self) -> pd.DataFrame:
        """Read the input POS file and return a DataFrame, handling dynamic headers."""
        logger.info(f"Reading input file: {self.input_file}")
        try:
            # Read the file based on extension
            if self.input_file.suffix.lower() == '.xlsx':
                df = pd.read_excel(self.input_file, header=None)
            else:
                df = pd.read_csv(self.input_file, encoding='latin1', header=None)
            
            # Find the header row by looking for 'Valoare' or 'Data Ultimei Incasari'
            header_idx = -1
            for idx, row in df.iterrows():
                row_vals = [str(x).strip().lower() for x in row.values if pd.notna(x)]
                if 'valoare' in row_vals or 'data ultimei incasari' in row_vals:
                    header_idx = idx
                    break
            
            if header_idx != -1:
                df.columns = df.iloc[header_idx]
                df = df.drop(header_idx).reset_index(drop=True)
            else:
                # If no header found, assume it's data from row 0 and columns are known.
                df.columns = ['Nr POS', 'Nr. Z', 'Data Ultimei Incasari', 'Operator Inchidere', 'Tip Incasare', 'Valoare', 'Rest Tichet'][:len(df.columns)]
                
            # Clean column names
            df.columns = [str(col).strip() for col in df.columns]
            
            # Keep only rows where Valoare is a valid number
            if 'Valoare' in df.columns:
                df = df[pd.to_numeric(df['Valoare'].astype(str).str.replace(',', ''), errors='coerce').notna()]
            
            # Filter by payment type (card or cec only)
            tip_col = 'Tip Incasare' if 'Tip Incasare' in df.columns else 'Explicatie'
            if tip_col in df.columns:
                df = df[df[tip_col].astype(str).str.strip().str.lower().isin(ALLOWED_PAYMENT_TYPES)]
                logger.info(f"Filtered by payment type: {len(df)} rows remaining")
            
            logger.info(f"Successfully loaded {len(df)} rows from {self.input_file}")
            return df
            
        except Exception as e:
            logger.error(f"Error reading input file: {e}")
            raise
    
    def _transform_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform the input data into the exact 53-column format."""
        logger.info("Transforming data...")
        
        output_data = []
        
        for _, row in df.iterrows():
            # 1. Extract and format date
            formatted_date = ''
            try:
                date_val = row.get('Data Ultimei Incasari')
                if pd.notna(date_val):
                    if isinstance(date_val, datetime):
                        formatted_date = date_val.strftime("%Y%m%d")
                    else:
                        date_str = str(date_val).split()[0]
                        if '-' in date_str:
                            parts = date_str.split('-')
                            if len(parts) == 3:
                                if len(parts[0]) == 4: # YYYY-MM-DD
                                    formatted_date = date_str.replace('-', '')
                                else: # DD-MMM-YY
                                    day, month_str, year = parts
                                    month_map = {
                                        'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
                                        'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
                                        'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
                                    }
                                    month_num = month_map.get(month_str, '01')
                                    year_full = f"20{year}" if len(year) == 2 else year
                                    formatted_date = f"{year_full}{month_num}{day.zfill(2)}"
                            else:
                                formatted_date = date_str.replace('/', '').replace('-', '')
                        else:
                            formatted_date = date_str
            except Exception as e:
                logger.warning(f"Could not parse date from {row.get('Data Ultimei Incasari', 'N/A')}: {e}")
                
            # 2. Extract Z Number
            nr_z = str(row.get('Nr. Z', ''))
            if nr_z.endswith('.0'):
                nr_z = nr_z[:-2]
                
            # 3. Get proper debit account
            filename_upper = self.config.get('filename', '').upper()
            if 'M1' in filename_upper:
                debit_account = '53111'
            elif 'M2' in filename_upper:
                debit_account = '53112'
            elif 'M3' in filename_upper:
                debit_account = '53113'
            else:
                debit_account = '5311' # Default
                
            # 4. Get cont credit based on explicatie/tip incasare
            explicatie_col = 'Tip Incasare' if 'Tip Incasare' in df.columns else 'Explicatie'
            explicatie_val = str(row.get(explicatie_col, self.config['explicatie'])).upper()
            
            if 'CARD' in explicatie_val:
                cont_credit = '51131'
                final_explicatie = 'CARD'
            elif 'CEC' in explicatie_val:
                cont_credit = '51132'
                final_explicatie = 'Cec'
            else:
                cont_credit = '5311'
                final_explicatie = 'CASH'
                
            # Append business tag to explicatie
            tag = BUSINESS_CONFIG[self.config['business']]['tag']
            final_explicatie = f"{final_explicatie}" if tag not in final_explicatie else final_explicatie
            # The previous version used f"{self.config['explicatie']} {tag}", let's match that to be safe but adapt to actual type
            if tag not in final_explicatie:
                final_explicatie = f"{final_explicatie}"
            
            # 5. Calculate Valoare (negative of input Suma/Valoare)
            try:
                val = str(row.get('Valoare', '0')).replace(',', '')
                valoare = -float(val) if val else ''
            except ValueError:
                valoare = ''
                
            # Create a new row in the 53-col output format
            new_row = {
                'Nr. inreg.': '',
                'Tip inregistrare': 'CASA',
                'Jurnal': 'RC',
                'Data': formatted_date,
                'Data scadenta': formatted_date,
                'Numar document': nr_z,
                'Cod tip factura': '',
                'Cont debit simbol': debit_account,
                'Cont debit titlu': '',
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
                'Explicatie': final_explicatie,
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
        
        output_df = pd.DataFrame(output_data, columns=OUTPUT_COLUMNS)
        return output_df
    
    def process(self) -> None:
        """Process the input file and save the output."""
        try:
            input_df = self._read_input_file()
            output_df = self._transform_data(input_df)
            
            # Save the output file to xls (using excel writer since we might write generic forms)
            if self.output_file.suffix.lower() == '.csv':
                output_df.to_csv(self.output_file, index=False, encoding='utf-8-sig')
            elif self.output_file.suffix.lower() in ['.xls', '.xlsx']:
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
    
    if any(x in filename_lower for x in ['fast food 1', 'fastfood1', 'ff1']):
        return 'Fast Food 1'
    elif any(x in filename_lower for x in ['fast food 2', 'fastfood2', 'ff2']):
        return 'Fast Food 2'
    elif 'restaurant' in filename_lower:
        return 'Restaurant'
    elif 'autoservire' in filename_lower or 'amt' in filename_lower or 'autoserv' in filename_lower:
        return 'Autoservire'
    elif 'm1' in filename_lower:
        return 'M1'
    elif 'm2' in filename_lower:
        return 'M2'
    elif 'm3' in filename_lower:
        return 'M3'
    
    return None

def process_pos_file(input_path: str, output_path: str = None, pos_type: str = None) -> None:
    input_path = Path(input_path)
    if output_path is None:
        output_path = input_path.parent / f"IMPORT CARD {input_path.stem}.xls"
    
    if pos_type is None:
        pos_type = detect_pos_type(input_path.name)
        if pos_type is None:
            raise ValueError(
                f"Could not detect POS type from filename {input_path.name}. "
            )
            
    processor = POSProcessor(input_path, output_path, pos_type, input_path.name)
    processor.process()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Process POS files to 53-column format.')
    parser.add_argument('input_file', help='Path to the input POS file')
    parser.add_argument('-o', '--output', help='Output file path')
    parser.add_argument('-t', '--pos-type', help='Type of POS', choices=list(POS_CONFIGS.keys()))
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    process_pos_file(args.input_file, args.output, args.pos_type)
