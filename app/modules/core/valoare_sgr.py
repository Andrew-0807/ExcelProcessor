import pandas as pd
import numpy as np
from openpyxl.utils import get_column_letter, column_index_from_string

class SGRValueProcessor:
    FILE_CONFIGS = {
        'M1': {'subtract_from': 'Unnamed: 5', 'subtract_this': 'Unnamed: 20'},
        'M2': {'subtract_from': 'Unnamed: 5', 'subtract_this': 'Unnamed: 19'},
        'M3': {'subtract_from': 'Unnamed: 5', 'subtract_this': 'Unnamed: 18'},
        'AMT': {'subtract_from':'Unnamed: 5', 'subtract_this': 'Unnamed: 18'}
    }
    
    def get_file_type(self, filename):
        """Determine file type based on filename."""
        for file_type in self.FILE_CONFIGS:
            if file_type in filename:
                return file_type
        return None
    
    def format_date_column_simple(self, df, column_name):
        """Format date column by removing forward slashes."""
        if column_name in df.columns:
            df[column_name] = df[column_name].astype(str).str.replace('/', '', regex=False)
        return df
    
    def process_dataframe(self, df):
        """Process the DataFrame and return the modified DataFrame"""
        print("Processing DataFrame with SGRValueProcessor")
        
        # Get the filename from the DataFrame if it exists
        filename = getattr(df, 'name', '')
        file_type = self.get_file_type(filename)
        
        if not file_type:
            print(f"No matching file type found for {filename}")
            return df
        
        config = self.FILE_CONFIGS[file_type]
        print(f"File type: {file_type}, Config: {config}")
        
        # Check if required columns exist
        if config['subtract_from'] not in df.columns or config['subtract_this'] not in df.columns:
            print(f"Required columns not found. Available columns: {list(df.columns)}")
            return df
        
        # Create a copy of the dataframe to avoid modifying the original
        result_df = df.copy()
        
        # Format date column D if it exists
        if 'D' in result_df.columns:
            result_df = self.format_date_column_simple(result_df, 'D')
        
        # Calculate Fara SGR values
        subtract_from_col = config['subtract_from']
        subtract_this_col = config['subtract_this']
        
        # Ensure numeric values for calculation
        result_df[subtract_from_col] = pd.to_numeric(result_df[subtract_from_col], errors='coerce')
        result_df[subtract_this_col] = pd.to_numeric(result_df[subtract_this_col], errors='coerce')
        
        # Find the position to insert the new column (after subtract_from column)
        cols = list(result_df.columns)
        insert_pos = cols.index(subtract_from_col) + 1
        
        # Calculate Fara SGR = subtract_from - subtract_this
        fara_sgr_values = result_df[subtract_from_col] - result_df[subtract_this_col]
        
        # Insert the new column at the correct position
        cols.insert(insert_pos, 'Fara SGR')
        result_df = result_df.reindex(columns=cols)
        result_df['Fara SGR'] = fara_sgr_values
        
        # Apply formula to column H if it exists
        if 'H' in result_df.columns and 'I' in result_df.columns:
            result_df = self.apply_formula_to_column_H(result_df)
        
        print("SGR processing completed")
        return result_df
    
    def apply_formula_to_column_H(self, df):
        """Apply the formula =(I/11%)+I to column H"""
        if 'I' in df.columns:
            # Ensure column I is numeric
            df['I'] = pd.to_numeric(df['I'], errors='coerce')
            # Apply the formula: (I/0.11) + I
            df['H'] = (df['I'] / 0.11) + df['I']
        return df

def main():
    # This main function is for standalone testing
    processor = SGRValueProcessor()
    # For server usage, this won't be called
    print("SGRValueProcessor initialized for server use")

if __name__ == "__main__":
    main()