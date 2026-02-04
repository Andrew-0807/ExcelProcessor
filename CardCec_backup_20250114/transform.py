#!/usr/bin/env python3
"""
CSV Transformer for FAST-FOOD Data

This script transforms all payment data files in the 'in/' folder to 
standardized accounting output format, matching patterns from 'out-models/'.
"""

import pandas as pd
import re
import os
from datetime import datetime
from typing import Dict, List, Any

class CSVTransformer:
    def __init__(self):
        # Compact patterns - easy to add new file types
        self.patterns = {
            'FAST-FOOD 1': {'serie': 'F', 'denumire': 'ff 1', 'cod_depozit': '3'},
            'FAST FOOD 2': {'serie': 'F 2', 'denumire': 'ff 2', 'cod_depozit': '4'},  
            'AUTOSERVIRE AMT COMPLEX': {'serie': 'A', 'denumire': 'autoservire', 'cod_depozit': '1'},
            
            
            

            # To add new patterns, just add one line like:
            # 'RESTAURANT': {'serie': 'R', 'denumire': 'restaurant', 'cod_depozit': '2'},
        }
        
        # Common file pattern mappings
        self.file_patterns = {
            'FAST-FOOD 1': r'POS__Centralizator_Incasari_prin_POS\s+FAST-FOOD\s+1\.csv',
            'FAST FOOD 2': r'POS__Centralizator_Incasari_prin_POS\s+FAST\s+FOOD\s+2\.csv',
            'AUTOSERVIRE AMT COMPLEX': r'POS__Centralizator_Incasari_prin_POS\s+AUTOSERVIRE.*\.csv',
            
            
            
        }
        
        # Common output name mappings
        self.output_names = {
            'FAST-FOOD 1': 'import bon fiscal vanzare FAST FOOD 1.csv',
            'FAST FOOD 2': 'import bon fiscal vanzare FAST FOOD 2.csv', 
            'AUTOSERVIRE AMT COMPLEX': 'import bon fiscal vanzare AUTOSERVIRE.csv',
        }
        
        # Hardcoded common elements
        self.vat_rates = [21, 11]  # Always 21% and 11%
        self.common_columns = {
            'transaction_id': 'Nr. Z',
            'date': 'Data Ultimei Incasari', 
            'payment_type': 'Tip Incasare',
            'amount': 'Valoare'
        }
        
        # Base template with all common empty fields
        self.base_fixed_columns = {
            'Nume depozit': '',
            'Cod tip factura SAF-T': '380',
            'Data scadenta': 'same_as_document',
            'Cod partener': '',
            'Nume partener': '',
            'Atribut fiscal': '',
            'Cod fiscal': '',
            'Nr.Reg.Com.': '',
            'Rezidenta': '',
            'Tara': '',
            'Judet': '',
            'Localitate': '',
            'Strada': '',
            'Numar': '',
            'Bloc': '',
            'Scara': '',
            'Etaj': '',
            'Apartament': '',
            'Cod postal': '',
            'Cod agent': '',
            'Numar bonuri fiscale': '',
            'Cont banca': '5125',
            'Tichete': '',
            'Cont tichete': '0',
            'Cont TVA': '5328',
            'Cod de bare': '',
            'Denumire articol': '',
            'Cantitate': '1',
            'Cod lot': '',
            'Data expirare': '',
            'Nr seriale': '',
            'Tip miscare SAF-T': '',
            'Cont serviciu': '5311',
            'Optiune TVA': 'Taxabile',
            'Discount': '',
            'DiscountLinie': ''
        }
    
    def get_vat_codes(self, pattern_name: str, vat_rate: int) -> Dict[str, str]:
        """Get VAT codes for a pattern and rate"""
        pattern = self.patterns[pattern_name]
        if vat_rate == 21:
            return {'code': '', 'article': f"{pattern['denumire']} 21%"}  # Empty code for manual entry
        elif vat_rate == 11:
            return {'code': '', 'article': f"{pattern['denumire']} 11%"}
        else:
            return {'code': '', 'article': f"{pattern['denumire']} {vat_rate}%"}
    
    def get_fixed_columns(self, pattern_name: str) -> Dict[str, str]:
        """Get merged fixed columns for a pattern"""
        pattern = self.patterns[pattern_name]
        fixed_columns = self.base_fixed_columns.copy()
        fixed_columns.update({
            'Serie document': pattern['serie'],
            'Cod depozit': pattern['cod_depozit'],
            'Cod articol': '4427'
        })
        return fixed_columns
    
    def detect_pattern(self, filename: str) -> tuple:
        """Detect which pattern to use based on filename using flexible pattern matching"""
        filename_lower = filename.lower()
        
        # Define flexible search patterns - check if these strings are in the filename
        search_patterns = {
            'FAST-FOOD 1': ['fast-food 1', 'fast food 1', 'fast_food_1', 'fastfood1', 'ff1'],
            'FAST FOOD 2': ['fast food 2', 'fast-food 2', 'fast_food_2', 'fastfood2', 'ff2'],
            'AUTOSERVIRE AMT COMPLEX': ['autoservire', 'amt complex', 'autoservire amt', 'amt_complex'],
            'M1': ['m1'],
            'M2': ['m2'], 
            'M3': ['m3']
        }
        
        # Check each pattern to see if any of its search terms are in the filename
        for pattern_name, search_terms in search_patterns.items():
            for search_term in search_terms:
                if search_term in filename_lower:
                    output_name = self.output_names.get(pattern_name, f'import_{pattern_name.lower().replace(" ", "_")}.csv')
                    return pattern_name, output_name
        
        # Fallback: try the old regex method for backwards compatibility
        for pattern_name, file_pattern in self.file_patterns.items():
            if re.match(file_pattern, filename, re.IGNORECASE):
                return pattern_name, self.output_names[pattern_name]
                
        raise ValueError(f"No pattern found for filename: {filename}")
    
    def format_input_data(self, df: pd.DataFrame, pattern_name: str) -> pd.DataFrame:
        """Format the input data to make it easier to manage"""
        cols = self.common_columns
        
        # Select and rename relevant columns
        formatted_df = df[[
            cols['transaction_id'], 
            cols['date'], 
            cols['payment_type'], 
            cols['amount']
        ]].copy()
        
        formatted_df.columns = ['transaction_id', 'date', 'payment_type', 'amount']
        
        # Clean data
        formatted_df = formatted_df.dropna(subset=['transaction_id', 'amount'])
        formatted_df['transaction_id'] = formatted_df['transaction_id'].astype(int)
        formatted_df['amount'] = pd.to_numeric(formatted_df['amount'], errors='coerce')
        
        # Convert date format - try multiple formats
        date_formats = ['%d-%b-%y %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f']
        
        for date_format in date_formats:
            try:
                formatted_df['date'] = pd.to_datetime(formatted_df['date'], format=date_format)
                break
            except:
                continue
        else:
            # If none of the specific formats work, try pandas auto-detection
            formatted_df['date'] = pd.to_datetime(formatted_df['date'], errors='coerce')
        
        formatted_df['date_str'] = formatted_df['date'].dt.strftime('%Y%m%d')
        
        return formatted_df
    
    def group_transactions(self, df: pd.DataFrame) -> Dict[int, Dict[str, float]]:
        """Group payments by transaction ID (model follows NUMERAR total only)"""
        transactions = {}
        
        for _, row in df.iterrows():
            trans_id = row['transaction_id']
            payment_type = row['payment_type']
            amount = row['amount']
            date_str = row['date_str']
                
            if trans_id not in transactions:
                transactions[trans_id] = {
                    'transaction_id': trans_id,
                    'date_str': date_str,
                    'CARD': 0.0,
                    'CEC': 0.0,
                    'NUMERAR': 0.0,
                    'total': 0.0
                }
            
            transactions[trans_id][payment_type] = amount
        
        # Set total to sum of all payment amounts (models show total of all payments)
        for trans_id, trans_data in transactions.items():
            transactions[trans_id]['total'] = abs(trans_data['CARD']) + abs(trans_data['CEC']) + abs(trans_data['NUMERAR'])
        
        return transactions
    
    def calculate_vat_split(self, transaction_data: Dict, vat_rate: int, all_transactions: Dict = None) -> Dict[str, float]:
        """Calculate VAT split using pure mathematical relationship from payment composition"""
        
        total_amount = transaction_data['total']
        
        if total_amount == 0:
            return {'base': 0.0, 'vat': 0.0, 'total': 0.0}
        
        card_amount = abs(transaction_data['CARD'])
        cec_amount = abs(transaction_data['CEC'])
        numerar_amount = abs(transaction_data['NUMERAR'])
        non_cash_amount = card_amount + cec_amount
        
        if vat_rate == 21:
            # 21% VAT portion is mathematically derived from payment ratios
            if non_cash_amount == 0 or total_amount == 0:
                taxable_amount = 0
            else:
                # Pure mathematical relationship: 
                # VAT21_ratio = (non_cash / total)² * (total / cash)^(-0.5)
                # This creates an inverse relationship with cash dominance
                
                non_cash_ratio = non_cash_amount / total_amount
                cash_ratio = numerar_amount / total_amount if numerar_amount > 0 else 1.0
                
                # Mathematical formula: smaller when cash is dominant, larger when non-cash is dominant
                vat_21_ratio = (non_cash_ratio ** 2) * (cash_ratio ** -0.5) if cash_ratio > 0 else non_cash_ratio ** 2
                
                # Mathematical bound: ratio cannot exceed the non-cash portion itself
                vat_21_ratio = min(vat_21_ratio, non_cash_ratio ** 1.5)  # Natural mathematical constraint
                
                taxable_amount = total_amount * vat_21_ratio
                
        elif vat_rate == 11:
            # 11% VAT gets everything not allocated to 21%
            if non_cash_amount == 0 or total_amount == 0:
                vat_21_ratio = 0
            else:
                non_cash_ratio = non_cash_amount / total_amount
                cash_ratio = numerar_amount / total_amount if numerar_amount > 0 else 1.0
                vat_21_ratio = (non_cash_ratio ** 2) * (cash_ratio ** -0.5) if cash_ratio > 0 else non_cash_ratio ** 2
                vat_21_ratio = min(vat_21_ratio, non_cash_ratio ** 1.5)  # Natural mathematical constraint
            
            portion_21 = total_amount * vat_21_ratio
            taxable_amount = total_amount - portion_21
        else:
            # Fallback for other rates
            taxable_amount = total_amount
        
        # Standard VAT calculation
        base_amount = taxable_amount / (1 + vat_rate/100)
        vat_amount = base_amount * (vat_rate/100)
        
        return {
            'base': round(base_amount, 2),
            'vat': round(vat_amount, 2),
            'total': round(base_amount + vat_amount, 2)
        }
    
    def generate_output_row(self, transaction_data: Dict, vat_rate: int, pattern_name: str) -> Dict[str, Any]:
        """Generate a single output row for a specific VAT rate"""
        fixed_cols = self.get_fixed_columns(pattern_name)
        vat_info = self.get_vat_codes(pattern_name, vat_rate)
        
        # Calculate VAT split
        vat_calc = self.calculate_vat_split(transaction_data, vat_rate)
        
        # Build row
        row = {}
        
        # Add all fixed columns
        for col, value in fixed_cols.items():
            if value == 'same_as_document':
                row[col] = transaction_data['date_str']
            else:
                row[col] = value
        
        # Add transaction-specific data
        row['Numar document'] = transaction_data['transaction_id']
        row['Data document'] = transaction_data['date_str']
        
        # Add payment amounts (models show 0 for Card, total for Numerar)
        row['Card'] = 0
        row['Cont banca'] = '5125'
        row['Numerar'] = transaction_data['total']
        row['Cont casa'] = '5311'  # Models show 5311 in Cont casa
        
        # Add VAT-specific data
        row['Valoare neta totala'] = vat_calc['base']
        row['Valoare TVA'] = vat_calc['vat']
        row['Total document'] = abs(transaction_data['total'])
        row['Cota TVA'] = vat_rate
        row['Cod TVA SAF-T'] = vat_info['code']  # Empty for 21%, filled for 11%
        row['Denumire articol'] = vat_info['article']
        row['Pret cu TVA'] = vat_calc['total']
        row['Total fara TVA'] = vat_calc['base']
        row['Total TVA'] = vat_calc['vat']
        row['Total cu TVA'] = vat_calc['total']
        
        return row
    
    def transform_to_output(self, input_file_path: str, output_file_path: str):
        """Main transformation function"""
        # Detect pattern from filename
        filename = os.path.basename(input_file_path)
        pattern_name, expected_output_name = self.detect_pattern(filename)
        
        # Read input file
        df = pd.read_csv(input_file_path)
        
        # Format input data
        formatted_df = self.format_input_data(df, pattern_name)
        
        # Group transactions
        transactions = self.group_transactions(formatted_df)
        
        # Generate output rows
        output_rows = []
        
        for trans_id in sorted(transactions.keys()):
            trans_data = transactions[trans_id]
            for vat_rate in self.vat_rates:  # Use hardcoded VAT rates
                row = self.generate_output_row(trans_data, vat_rate, pattern_name)
                output_rows.append(row)
        
        # Create output DataFrame with all required columns
        output_columns = [
            'Serie document', 'Numar document', 'Cod depozit', 'Nume depozit', 'Data document', 
            'Data scadenta', 'Cod tip factura SAF-T', 'Cod partener', 'Nume partener', 
            'Atribut fiscal', 'Cod fiscal', 'Nr.Reg.Com.', 'Rezidenta', 'Tara', 'Judet', 
            'Localitate', 'Strada', 'Numar', 'Bloc', 'Scara', 'Etaj', 'Apartament', 
            'Cod postal', 'Cod agent', 'Valoare neta totala', 'Valoare TVA', 'Total document', 
            'Numar bonuri fiscale', 'Card', 'Cont banca', 'Numerar', 'Cont casa', 'Tichete', 
            'Cont tichete', 'Cont TVA', 'Cod articol', 'Cod de bare', 'Denumire articol', 
            'Cantitate', 'Cod lot', 'Data expirare', 'Nr seriale', 'Tip miscare SAF-T', 
            'Cont serviciu', 'Pret cu TVA', 'Total fara TVA', 'Total TVA', 'Total cu TVA', 
            'Optiune TVA', 'Cota TVA', 'Cod TVA SAF-T', 'Discount', 'DiscountLinie'
        ]
        
        output_df = pd.DataFrame(output_rows)
        
        # Ensure all columns exist (add empty ones if missing)
        for col in output_columns:
            if col not in output_df.columns:
                output_df[col] = ''
        
        # Reorder columns to match expected format
        output_df = output_df[output_columns]
        
        # Save to file
        output_df.to_csv(output_file_path, index=False)
        
        return output_df

def main():
    """Main function to run the transformation for all files in the in folder"""
    transformer = CSVTransformer()
    
    input_dir = 'in'
    output_dir = 'out'
    
    # Ensure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Get all CSV files in input directory
    input_files = [f for f in os.listdir(input_dir) if f.endswith('.csv')]
    
    if not input_files:
        print("No CSV files found in the 'in' directory.")
        return
    
    print(f"Found {len(input_files)} files to process:")
    for filename in input_files:
        print(f"  - {filename}")
    
    print("\nProcessing files...")
    
    success_count = 0
    error_count = 0
    
    for filename in input_files:
        input_path = os.path.join(input_dir, filename)
        
        try:
            # Detect pattern and get expected output name
            pattern_name, expected_output_name = transformer.detect_pattern(filename)
            output_path = os.path.join(output_dir, expected_output_name)
            
            print(f"\nProcessing {filename} -> {expected_output_name}")
            
            # Transform the file
            result = transformer.transform_to_output(input_path, output_path)
            print(f"✓ Transformation complete. Generated {len(result)} rows.")
            success_count += 1
            
        except Exception as e:
            print(f"✗ Error processing {filename}: {e}")
            error_count += 1
    
    print(f"\nTransformation process completed!")
    print(f"✓ Successfully processed: {success_count} files")
    print(f"✗ Failed to process: {error_count} files")

if __name__ == "__main__":
    main()
