import os
import pandas as pd
from pathlib import Path

def convert_xlsx_to_csv():
    # Define paths
    xlsx_dir = Path('xlsx')
    csv_dir = Path('csv')
    
    # Create csv directory if it doesn't exist
    csv_dir.mkdir(exist_ok=True)
    
    # Check if xlsx directory exists
    if not xlsx_dir.exists() or not xlsx_dir.is_dir():
        print(f"Error: '{xlsx_dir}' directory not found.")
        return
    
    # Get all xlsx files
    xlsx_files = list(xlsx_dir.glob('*.xls*'))
    
    if not xlsx_files:
        print(f"No XLSX files found in '{xlsx_dir}' directory.")
        return
    
    # Convert each xlsx to csv
    for xlsx_file in xlsx_files:
        try:
            # Read the Excel file
            df = pd.read_excel(xlsx_file)
            
            # Create output path
            csv_file = csv_dir / f"{xlsx_file.stem}.csv"
            
            # Save as CSV
            df.to_csv(csv_file, index=False, encoding='utf-8')
            print(f"Converted: {xlsx_file.name} -> {csv_file}")
            
        except Exception as e:
            print(f"Error converting {xlsx_file.name}: {str(e)}")

if __name__ == "__main__":
    convert_xlsx_to_csv()
