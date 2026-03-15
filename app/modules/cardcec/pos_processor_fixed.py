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
        'export_info': '20250101-20251231-CielStd_1057',
        # Add other business-specific configurations here
    },
    # Add other business configurations as needed
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
        
    def _read_input_file(self) -> pd.DataFrame:
        """Read the input POS file and return a DataFrame."""
        logger.info(f"Reading input file: {self.input_file}")
        try:
            # Read the file based on extension
            if self.input_file.suffix.lower() == '.xlsx':
                df = pd.read_excel(self.input_file)
            else:
                df = pd.read_csv(self.input_file, encoding='latin1')
            
            # Clean column names (strip whitespace and remove special characters)
            df.columns = df.columns.str.strip()
            
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
        
        # Create a new DataFrame with the required columns
        output_data = []
        
        for _, row in df.iterrows():
            # Extract and format date from 'Data Ultimei Incasari' column
            try:
                # Get the date string and split by space to separate date and time
                date_str = str(row['Data Ultimei Incasari']).split()[0]
                # Parse the date parts (format DD-MMM-YY)
                day, month_str, year = date_str.split('-')
                
                # Map month abbreviations to numbers
                month_map = {
                    'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
                    'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
                    'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
                }
                
                # Get the month number from abbreviation
                month_num = month_map.get(month_str, '01')
                
                # Format as YYYYMMDD (assuming 20xx for 2-digit years)
                formatted_date = f"20{year}{month_num}{day.zfill(2)}"
            except (KeyError, ValueError, AttributeError, IndexError) as e:
                logger.warning(f"Could not parse date from: {row.get('Data Ultimei Incasari', 'N/A')}. Error: {e}")
                formatted_date = ''
            
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
            
            # Get cont_credit based on explicatie
            explicatie = str(row.get('Explicatie', '')).upper()
            if 'CARD' in explicatie:
                cont_credit = '51131'
            elif 'CEC' in explicatie:
                cont_credit = '51132'
            else:
                cont_credit = '5311'
            
            # Create a new row in the output format
            new_row = {
                'Nr. inreg.': '',  # Empty as per requirements
                'Tip inregistrare': 'CASA',
                'Jurnal': 'RC',
                'Data': formatted_date,
                'Data scadenta': formatted_date,  # Same as Data
                'Numar document': str(row.get('Nr. Z', '')),  # Convert to string to ensure consistent format
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
                'Explicatie': f"{self.config['explicatie']} {BUSINESS_CONFIG[self.config['business']]['tag']}",
                'Valoare': row.get('Valoare', ''),
                'Informatii export': BUSINESS_CONFIG[self.config['business']]['export_info'],
                'Punct de lucru': self.config['punct_lucru'],
                # Add other required fields with default values
                'Optiune TVA': '',
                'TVA la incasare': 0,
                'Deductibilitate': 0,
                'Reevaluare': 0,
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
    elif 'autoservire' in filename_lower or 'amt' in filename_lower:
        return 'Autoservire'
    elif 'm1' in filename_lower:
        return 'M1'
    elif 'm2' in filename_lower:
        return 'M2'
    elif 'm3' in filename_lower:
        return 'M3'
    
    return None

def process_pos_file(input_path: str, output_path: str = None, pos_type: str = None) -> None:
    """
    Process a POS file and convert it to the required import format.
    
    Args:
        input_path: Path to the input POS file
        output_path: Path to save the output file (default: same as input with 'IMPORT CARD' prefix)
        pos_type: Type of POS (if None, will try to detect from filename)
    """
    input_path = Path(input_path)
    
    # Set default output path if not provided
    if output_path is None:
        output_path = input_path.parent / f"IMPORT CARD {input_path.stem}.csv"
    
    # Detect POS type if not provided
    if pos_type is None:
        pos_type = detect_pos_type(input_path.name)
        if pos_type is None:
            raise ValueError(
                "Could not detect POS type from filename. "
                "Please specify the POS type using --pos-type parameter."
            )
    
    # Process the file
    processor = POSProcessor(input_path, output_path, pos_type, input_path.name)
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
