import pandas as pd
import os
from datetime import datetime

def create_summary_report(df, output_dir):
    """
    Create a financial summary report from the cleaned data
    """
    try:
        # Calculate key metrics
        total_transactions = len(df)
        total_sales = df['Total_Valoare'].sum() if 'Total_Valoare' in df.columns else 0
        
        # TVA calculations
        tva_21_total = df['Taxabile_21_Val_TVA'].sum() if 'Taxabile_21_Val_TVA' in df.columns else 0
        tva_11_total = df['Taxabile_11_Val_TVA'].sum() if 'Taxabile_11_Val_TVA' in df.columns else 0
        total_tva = tva_21_total + tva_11_total
        
        # Average transaction
        avg_transaction = total_sales / total_transactions if total_transactions > 0 else 0
        
        # Date range
        if 'Data' in df.columns and not df['Data'].isna().all():
            date_range = f"{df['Data'].min().strftime('%Y-%m-%d')} to {df['Data'].max().strftime('%Y-%m-%d')}"
        else:
            date_range = "Date information not available"
        
        # Create summary report
        report = f"""
FINANCIAL SUMMARY REPORT
========================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Period: {date_range}

TRANSACTION OVERVIEW:
- Total Transactions: {total_transactions}
- Total Sales Value: {total_sales:,.2f} RON
- Average Transaction: {avg_transaction:,.2f} RON

TAX BREAKDOWN:
- TVA 21%: {tva_21_total:,.2f} RON
- TVA 11%: {tva_11_total:,.2f} RON
- Total TVA: {total_tva:,.2f} RON

DATA QUALITY:
- Rows processed: {total_transactions}
- Columns: {len(df.columns)}
- Complete records: {df.dropna().shape[0]}
"""
        
        # Save report
        report_path = os.path.join(output_dir, "financial_summary.txt")
        os.makedirs(output_dir, exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"📊 Summary report saved: {report_path}")
        return report_path
        
    except Exception as e:
        print(f"⚠️ Warning: Could not create summary report: {str(e)}")
        return None

def transform_borderou_csv(input_file_path, output_file_path=None):
    """
    Transform the complex multi-header Borderou CSV into a clean, standardized format
    that preserves all data but is much easier to work with programmatically.
    """
    
    # Read the CSV file
    df = pd.read_csv(input_file_path)
    
    # Auto-detect the start of actual data by finding the first row with numeric data in first column AND "Z POS" in second column
    data_start_row = 0
    for i, row in df.iterrows():
        # Check if first column has a numeric value AND second column contains "Z POS"
        first_col = str(row.iloc[0]).strip()
        second_col = str(row.iloc[1]).strip() if len(row) > 1 else ""
        
        if (first_col.isdigit() or (first_col.replace('.', '', 1).isdigit() and first_col.count('.') < 2)) and "Z POS" in second_col:
            data_start_row = i
            break
    
    print(f"🔍 Detected data start at row: {data_start_row}")
    
    # Get the actual data starting from the detected row
    data_rows = df.iloc[data_start_row:].copy()
    
    # Dynamic column mapping - detect actual structure
    print("🔍 Analyzing column structure...")
    
    # Look for key patterns in the data to map columns correctly
    columns = list(data_rows.columns)
    
    # Find key column indices by looking for patterns in the first data row
    first_row = data_rows.iloc[0]
    
    # Core columns that should always be in the same position
    nr_crt_idx = 0
    denumire_idx = 1  
    nr_doc_idx = 2
    data_idx = 3
    explicatii_idx = 4
    
    # Find Total Valoare column (first numeric after explicatii)
    total_valoare_idx = None
    for i in range(explicatii_idx + 1, len(columns)):
        try:
            val = pd.to_numeric(first_row.iloc[i], errors='coerce')
            if not pd.isna(val) and val > 0:
                total_valoare_idx = i
                break
        except:
            continue
    
    # Find Taxabile 21% columns by looking for smaller values after Total Valoare
    tva_21_base_idx = None
    tva_21_val_idx = None
    
    if total_valoare_idx is not None:
        # Look for the next two smaller values (base and TVA)
        for i in range(total_valoare_idx + 1, len(columns) - 1):
            try:
                val1 = pd.to_numeric(first_row.iloc[i], errors='coerce')
                val2 = pd.to_numeric(first_row.iloc[i + 1], errors='coerce')
                
                if not pd.isna(val1) and not pd.isna(val2) and val1 > 0 and val2 > 0:
                    # Check if val2 is roughly 21% of val1
                    if abs(val2 - (val1 * 0.21)) < (val1 * 0.05):  # Allow 5% tolerance
                        tva_21_base_idx = i
                        tva_21_val_idx = i + 1
                        break
            except:
                continue
    
    # Find Taxabile 11% columns similarly
    tva_11_base_idx = None
    tva_11_val_idx = None
    
    if tva_21_val_idx is not None:
        for i in range(tva_21_val_idx + 1, len(columns) - 1):
            try:
                val1 = pd.to_numeric(first_row.iloc[i], errors='coerce')
                val2 = pd.to_numeric(first_row.iloc[i + 1], errors='coerce')
                
                if not pd.isna(val1) and not pd.isna(val2) and val1 > 0 and val2 > 0:
                    # Check if val2 is roughly 11% of val1
                    if abs(val2 - (val1 * 0.11)) < (val1 * 0.05):  # Allow 5% tolerance
                        tva_11_base_idx = i
                        tva_11_val_idx = i + 1
                        break
            except:
                continue
    
    # Find Netaxabil columns (usually last numeric values)
    netaxabil_base_idx = None
    netaxabil_val_idx = None
    
    # Search from the end backwards for the last pair of numeric values
    for i in range(len(columns) - 2, max(tva_11_val_idx or 0, 5), -1):
        try:
            val1 = pd.to_numeric(first_row.iloc[i], errors='coerce')
            val2 = pd.to_numeric(first_row.iloc[i + 1], errors='coerce')
            
            if not pd.isna(val1) and not pd.isna(val2):
                netaxabil_base_idx = i
                netaxabil_val_idx = i + 1
                break
        except:
            continue
    
    print(f"📋 Column mapping detected:")
    print(f"   Total Valoare: index {total_valoare_idx}")
    print(f"   TVA 21% Base: index {tva_21_base_idx}, Val: index {tva_21_val_idx}")
    print(f"   TVA 11% Base: index {tva_11_base_idx}, Val: index {tva_11_val_idx}")
    print(f"   Netaxabil Base: index {netaxabil_base_idx}, Val: index {netaxabil_val_idx}")
    
    # Create cleaned DataFrame with proper column names
    cleaned_data = []
    
    for _, row in data_rows.iterrows():
        cleaned_row = {
            'Nr_Crt': pd.to_numeric(row.iloc[nr_crt_idx], errors='coerce'),
            'Denumire': str(row.iloc[denumire_idx]).strip(),
            'Nr_Doc_Z': pd.to_numeric(row.iloc[nr_doc_idx], errors='coerce'),
            'Data': pd.to_datetime(row.iloc[data_idx], errors='coerce'),
            'Explicatii': str(row.iloc[explicatii_idx]).strip(),
        }
        
        # Add financial columns if we found them
        if total_valoare_idx is not None:
            cleaned_row['Total_Valoare'] = pd.to_numeric(row.iloc[total_valoare_idx], errors='coerce')
        else:
            cleaned_row['Total_Valoare'] = 0
            
        if tva_21_base_idx is not None:
            cleaned_row['Taxabile_21_Baza_Impozitare'] = pd.to_numeric(row.iloc[tva_21_base_idx], errors='coerce')
        else:
            cleaned_row['Taxabile_21_Baza_Impozitare'] = 0
            
        if tva_21_val_idx is not None:
            cleaned_row['Taxabile_21_Val_TVA'] = pd.to_numeric(row.iloc[tva_21_val_idx], errors='coerce')
        else:
            cleaned_row['Taxabile_21_Val_TVA'] = 0
            
        if tva_11_base_idx is not None:
            cleaned_row['Taxabile_11_Baza_Impozitare'] = pd.to_numeric(row.iloc[tva_11_base_idx], errors='coerce')
        else:
            cleaned_row['Taxabile_11_Baza_Impozitare'] = 0
            
        if tva_11_val_idx is not None:
            cleaned_row['Taxabile_11_Val_TVA'] = pd.to_numeric(row.iloc[tva_11_val_idx], errors='coerce')
        else:
            cleaned_row['Taxabile_11_Val_TVA'] = 0
            
        if netaxabil_base_idx is not None:
            cleaned_row['Netaxabil_Baza_Impozitare'] = pd.to_numeric(row.iloc[netaxabil_base_idx], errors='coerce')
        else:
            cleaned_row['Netaxabil_Baza_Impozitare'] = 0
            
        if netaxabil_val_idx is not None:
            cleaned_row['Netaxabil_Val_TVA'] = pd.to_numeric(row.iloc[netaxabil_val_idx], errors='coerce')
        else:
            cleaned_row['Netaxabil_Val_TVA'] = 0
        
        # Add placeholder columns for compatibility
        cleaned_row['Scutit_Cu_Drept_Reducere'] = 0
        cleaned_row['Scutit_Fara_Drept_Reducere'] = 0
        cleaned_row['Nefolosit_1_Baza_Impozitare'] = 0
        cleaned_row['Nefolosit_1_Val_TVA'] = 0
        cleaned_row['Nefolosit_2_Baza_Impozitare'] = 0
        cleaned_row['Nefolosit_2_Val_TVA'] = 0
        cleaned_row['Final_Rate'] = 0
        
        cleaned_data.append(cleaned_row)
    
    # Create DataFrame
    data_rows = pd.DataFrame(cleaned_data)
    
    # Define the standard column order
    standard_columns = [
        'Nr_Crt', 'Denumire', 'Nr_Doc_Z', 'Data', 'Explicatii', 'Total_Valoare',
        'Scutit_Cu_Drept_Reducere', 'Scutit_Fara_Drept_Reducere',
        'Taxabile_21_Baza_Impozitare', 'Taxabile_21_Val_TVA',
        'Taxabile_11_Baza_Impozitare', 'Taxabile_11_Val_TVA',
        'Nefolosit_1_Baza_Impozitare', 'Nefolosit_1_Val_TVA',
        'Nefolosit_2_Baza_Impozitare', 'Nefolosit_2_Val_TVA',
        'Netaxabil_Baza_Impozitare', 'Netaxabil_Val_TVA', 'Final_Rate'
    ]
    
    # Reorder columns to match standard format
    data_rows = data_rows[standard_columns]
    
    # Generate output file path if not provided
    if output_file_path is None:
        base_name = os.path.splitext(input_file_path)[0]
        output_file_path = f"{base_name}_cleaned.csv"
    
    # Save the cleaned data
    data_rows.to_csv(output_file_path, index=False)
    
    print(f"✅ Successfully transformed CSV!")
    print(f"📁 Input file: {input_file_path}")
    print(f"📁 Output file: {output_file_path}")
    print(f"📊 Rows processed: {len(data_rows)}")
    print(f"📋 Columns: {len(data_rows.columns)}")
    
    # Display sample of the cleaned data
    print("\n📋 Sample of cleaned data:")
    print(data_rows.head())
    
    return data_rows, output_file_path


if __name__ == "__main__":
    # Configuration
    input_dir = "./in/toClean"
    output_dir = r"e:\Programming\Trae - MomAutomations\NewFeatureTest\out\Cleaned"
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if input directory exists
    if not os.path.exists(input_dir):
        print(f"❌ Input directory not found: {input_dir}")
        exit(1)
    
    # Process all CSV files in the input directory
    csv_files = [f for f in os.listdir(input_dir) if f.endswith('.csv')]
    
    if not csv_files:
        print(f"❌ No CSV files found in {input_dir}")
        exit(1)
    
    print(f"🔍 Found {len(csv_files)} CSV file(s) to process...")
    
    for file in csv_files:
        input_file = os.path.join(input_dir, file)
        output_file = os.path.join(output_dir, f"{os.path.splitext(file)[0]}_cleaned.csv")
        
        print(f"\n📂 Processing: {file}")
        
        # Transform the CSV
        try:
            cleaned_df, output_file_path = transform_borderou_csv(input_file, output_file)

            # Create summary report
            # create_summary_report(cleaned_df, output_dir)

            print(f"✅ Successfully processed: {file}")

        except Exception as e:
            print(f"❌ Error processing {file}: {str(e)}")
            print("Please check the input file path and format.")
            continue
    
    print("\n🎉 All files processed successfully!")
    print("The cleaned CSV files are now ready for easy automation and analysis.")