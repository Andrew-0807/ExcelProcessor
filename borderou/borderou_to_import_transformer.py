import pandas as pd
import os
from datetime import datetime
import numpy as np
import re

def extract_file_patterns(filename):
    """Extract Serie document and Denumire articol from filename using pattern recognition"""
    
    # Define patterns for different file types
    patterns = {
        'AUTOSERVIRE AMT': {'serie': 'A', 'denumire': 'autoservire', 'cod_depozit': '1'},
        'AUTOSERVIRE': {'serie': 'A', 'denumire': 'autoservire', 'cod_depozit': '1'},
        'AUTOSERV': {'serie': 'A', 'denumire': 'autoservire', 'cod_depozit': '1'},
        'FF1': {'serie': 'F', 'denumire': 'ff 1', 'cod_depozit': '3'},
        'FF2': {'serie': 'F', 'denumire': 'FF 2', 'cod_depozit': '3'},
        'FFAMT': {'serie': 'F', 'denumire': 'FF AMT', 'cod_depozit': '3'},
        'RESTAURANT AMT': {'serie': 'R', 'denumire': 'restaurant', 'cod_depozit': '2'},
        'RESTAURANT': {'serie': 'R', 'denumire': 'restaurant', 'cod_depozit': '2'},
        'CASA 0014': {'serie': 'BFM1 0014', 'denumire': 'marfa m1 ', 'cod_depozit': '1'},
        'CASA 0012': {'serie': 'BFM1 0012', 'denumire': 'marfa m1 ', 'cod_depozit': '1'},
        '102': {'serie': 'BFM2 102', 'denumire': 'marfa m2 ', 'cod_depozit': '2'},
        '103': {'serie': 'BFM2 103', 'denumire': 'marfa m2 ', 'cod_depozit': '2'},
        'M1': {'serie': 'BFM1', 'denumire': 'marfa m1 ', 'cod_depozit': '1'},
        'M2': {'serie': 'BFM2', 'denumire': 'marfa m2 ', 'cod_depozit': '2'},
        'M3': {'serie': 'BFM3', 'denumire': 'marfa m3 ', 'cod_depozit': '3'},
    }
    
    # Convert filename to uppercase for pattern matching
    filename_upper = filename.upper()
    
    # Check each pattern - order matters, check more specific patterns first
    # Sort patterns by length (descending) to check longer patterns first
    sorted_patterns = sorted(patterns.items(), key=lambda x: len(x[0]), reverse=True)
    
    for pattern_key, pattern_info in sorted_patterns:
        if pattern_key in filename_upper:
            # print(f"📋 Matched pattern '{pattern_key}' for file: {filename}")
            return pattern_info['serie'], pattern_info['denumire'], pattern_info['cod_depozit']
    
    # Default fallback if no pattern matches
    print(f"⚠️  No pattern found for {filename}, using default values")
    return 'X', 'general', ''

def read_borderou_data(file_path):
    """Read and clean the Borderou CSV data"""
    # print(f"📊 Processing {os.path.basename(file_path)}...")
    
    # Read the CSV file
    df = pd.read_csv(file_path)
    
    # Remove empty rows and handle NaN values in critical columns
    df = df.dropna(subset=['Data', 'Nr_Doc_Z'], how='any')
    
    # Convert Data column to datetime if it's not already
    if not pd.api.types.is_datetime64_any_dtype(df['Data']):
        df['Data'] = pd.to_datetime(df['Data'])
    
    # print(f"📊 Processing {len(df)} transactions from Borderou...")
    return df

def transform_borderou_to_import_format(input_file, output_file=None):
    """Transform Borderou CSV to import format"""
    
    # Read the cleaned Borderou data
    df = read_borderou_data(input_file)
    
    # Get file patterns for Serie document
    filename = os.path.basename(input_file)
    serie_document, denumire_articol, cod_depozit = extract_file_patterns(filename)
    
    # print(f"📊 Processing {len(df)} transactions from Borderou...")
    # print(f"📋 Using Serie document: '{serie_document}', Denumire articol: '{denumire_articol}'")
    
    # Check if this is an M1 or M2 file that needs splitting
    needs_splitting = any(pattern in filename.upper() for pattern in ['M1', 'M2'])
    
    # Define the expected output columns
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
    
    # Filename to code mapping - easily extensible
    filename_codes = {
        'FF1': {'cod_articol_prefix': 'F', 'cod_depozit_override': 3, 'denumire': 'ff 1'},
        'FF2': {'cod_articol_prefix': 'F 2', 'cod_depozit_override': 4, 'denumire': 'FF 2'},
        'FFAMT': {'cod_articol_prefix': 'F', 'cod_depozit_override': 3, 'denumire': 'FF AMT'},
        'AUTOSERVIRE AMT': {'cod_articol_prefix': 'A', 'cod_depozit_override': 1, 'denumire': 'autoservire'},
        'AUTOSERVIRE': {'cod_articol_prefix': 'A', 'cod_depozit_override': 1, 'denumire': 'autoservire'},
        'AUTOSERV': {'cod_articol_prefix': 'A', 'cod_depozit_override': 1, 'denumire': 'autoservire'},
        'RESTAURANT AMT': {'cod_articol_prefix': 'R', 'cod_depozit_override': 2, 'denumire': 'restaurant'},
        'RESTAURANT': {'cod_articol_prefix': 'R', 'cod_depozit_override': 2, 'denumire': 'restaurant'},
        'CASA 0014': {'cod_articol_prefix': 'M1', 'cod_depozit_override': 1, 'denumire': 'marfa m1 '},
        'CASA 0012': {'cod_articol_prefix': 'M1', 'cod_depozit_override': 1, 'denumire': 'marfa m1 '},
        '102': {'cod_articol_prefix': 'M2', 'cod_depozit_override': 2, 'denumire': 'marfa m2 '},
        '103': {'cod_articol_prefix': 'M2', 'cod_depozit_override': 2, 'denumire': 'marfa m2 '},
        'M1': {'cod_articol_prefix': 'M1', 'cod_depozit_override': 1, 'denumire': 'marfa m1 '},
        'M2': {'cod_articol_prefix': 'M2', 'cod_depozit_override': 2, 'denumire': 'marfa m2 '},
        'M3': {'cod_articol_prefix': 'M3', 'cod_depozit_override': 3, 'denumire': 'marfa m3 '},
        # Add more mappings here as needed
    }
    
    # Get the appropriate code mapping - check longer patterns first
    code_mapping = None
    # Sort by length (descending) to check more specific patterns first
    sorted_filename_codes = sorted(filename_codes.items(), key=lambda x: len(x[0]), reverse=True)
    
    for key, mapping in sorted_filename_codes:
        if key in filename:
            code_mapping = mapping
            cod_depozit = mapping['cod_depozit_override']  # Override with specific code
            denumire_articol = mapping['denumire']
            # print(f"📋 Using filename mapping '{key}' for file: {filename}")
            break
    
    if not code_mapping:
        raise ValueError(f"No code mapping found for filename: {filename}")
    
    # For M1/M2 files, group data by POS terminal ID
    if needs_splitting:
        pos_groups = {}
        
        # Group transactions by POS terminal ID
        for index, row in df.iterrows():
            pos_id = None
            
            # Determine POS ID based on document number patterns and Explicatii field
            if 'M1' in filename.upper():
                doc_num = str(row['Nr_Doc_Z'])
                if doc_num.startswith('15') or 'nr.14' in str(row.get('Explicatii', '')):
                    pos_id = '0014'
                elif doc_num.startswith('6') or 'nr.12' in str(row.get('Explicatii', '')):
                    pos_id = '0012'
                else:
                    pos_id = '0014'  # Default
            elif 'M2' in filename.upper():
                # For M2, use similar logic or extend as needed
                doc_num = str(row['Nr_Doc_Z'])
                if '102' in str(row.get('Explicatii', '')) or doc_num.startswith('102'):
                    pos_id = '102'
                elif '103' in str(row.get('Explicatii', '')) or doc_num.startswith('103'):
                    pos_id = '103'
                else:
                    pos_id = '102'  # Default
            
            if pos_id not in pos_groups:
                pos_groups[pos_id] = []
            pos_groups[pos_id].append(row)
        
        # print(f"📊 Found {len(pos_groups)} POS terminals: {list(pos_groups.keys())}")
        
        # Process each POS group separately
        output_files = []
        for pos_id, group_rows in pos_groups.items():
            group_df = pd.DataFrame(group_rows)
            output_file_for_pos = process_pos_group(group_df, pos_id, filename, serie_document, 
                                                  denumire_articol, cod_depozit, output_columns, 
                                                  filename_codes, output_file)
            output_files.append(output_file_for_pos)
        
        return output_files  # Return list of output files for M1/M2
    
    # For non-M1/M2 files, process normally (single output)
    output_rows_21 = []  # Store all 21% TVA rows first
    output_rows_11 = []  # Store all 11% TVA rows second
    
    # Process each transaction
    for index, row in df.iterrows():
        # Determine the correct Serie document for M1 files based on document number patterns
        current_serie_document = serie_document
        if 'M1' in filename and serie_document in ['BFM1', 'X']:  # Handle both generic M1 and fallback cases
            doc_num = str(row['Nr_Doc_Z'])
            if doc_num.startswith('15') or 'nr.14' in str(row.get('Explicatii', '')):
                current_serie_document = 'BFM1 0014'
            elif doc_num.startswith('6') or 'nr.12' in str(row.get('Explicatii', '')):
                current_serie_document = 'BFM1 0012'
            else:
                # Default to BFM1 0014 if pattern is unclear
                current_serie_document = 'BFM1 0014'
        nr_doc = int(row['Nr_Doc_Z'])
        date_obj = pd.to_datetime(row['Data'])
        date_str = date_obj.strftime('%Y%m%d')
        
        total_valoare = float(row['Total_Valoare'])
        netaxabil_baza = float(row['Netaxabil_Baza_Impozitare'])
        tva_21_base = float(row['Taxabile_21_Baza_Impozitare'])
        tva_21_val = float(row['Taxabile_21_Val_TVA'])
        tva_11_base = float(row['Taxabile_11_Baza_Impozitare'])
        tva_11_val = float(row['Taxabile_11_Val_TVA'])
        
        # Calculate Total_valoare_fata_netaxablil as per manual process
        total_valoare_fata_netaxablil = total_valoare - netaxabil_baza
        # This should equal: tva_21_base + tva_21_val + tva_11_base + tva_11_val
        
        # Create rows for both 21% and 11% TVA regardless of values (to match reference format)
        
        # Always create 21% TVA row
        row_21 = {
            'Serie document': current_serie_document,
            'Numar document': nr_doc,
            'Cod depozit': cod_depozit,
            'Nume depozit': '',
            'Data document': date_str,
            'Data scadenta': date_str,
            'Cod tip factura SAF-T': 380,
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
            'Valoare neta totala': tva_21_base,
            'Valoare TVA': tva_21_val,
            'Total document': total_valoare_fata_netaxablil,  # Use calculated value
            'Numar bonuri fiscale': '',
            'Card': 0,
            'Cont banca': 5125,
            'Numerar': total_valoare_fata_netaxablil,  # Use calculated value
            'Cont casa': 5311,
            'Tichete': 0,
            'Cont tichete': 5328,
            'Cont TVA': 4427,
            'Cod articol': f'{denumire_articol} 21%',
            'Cod de bare': '',
            'Denumire articol': denumire_articol,
            'Cantitate': 1,
            'Cod lot': '',
            'Data expirare': '',
            'Nr seriale': '',
            'Tip miscare SAF-T': '',
            'Cont serviciu': '',
            'Pret cu TVA': tva_21_base + tva_21_val,
            'Total fara TVA': tva_21_base,
            'Total TVA': tva_21_val,
            'Total cu TVA': tva_21_base + tva_21_val,
            'Optiune TVA': 'Taxabile',
            'Cota TVA': 21,
            'Cod TVA SAF-T': 310344,
            'Discount': '',
            'DiscountLinie': ''
        }
        output_rows_21.append(row_21)
        
        # Always create 11% TVA row
        row_11 = {
            'Serie document': current_serie_document,
            'Numar document': nr_doc,
            'Cod depozit': cod_depozit,
            'Nume depozit': '',
            'Data document': date_str,
            'Data scadenta': date_str,
            'Cod tip factura SAF-T': 380,
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
            'Valoare neta totala': tva_11_base,
            'Valoare TVA': tva_11_val,
            'Total document': total_valoare_fata_netaxablil,  # Use calculated value
            'Numar bonuri fiscale': '',
            'Card': 0,
            'Cont banca': 5125,
            'Numerar': total_valoare_fata_netaxablil,  # Use calculated value
            'Cont casa': 5311,
            'Tichete': 0,
            'Cont tichete': 5328,
            'Cont TVA': 4427,
            'Cod articol': f'{denumire_articol} 11%',
            'Cod de bare': '',
            'Denumire articol': denumire_articol,
            'Cantitate': 1,
            'Cod lot': '',
            'Data expirare': '',
            'Nr seriale': '',
            'Tip miscare SAF-T': '',
            'Cont serviciu': '',
            'Pret cu TVA': tva_11_base + tva_11_val,
            'Total fara TVA': tva_11_base,
            'Total TVA': tva_11_val,
            'Total cu TVA': tva_11_base + tva_11_val,
            'Optiune TVA': 'Taxabile',
            'Cota TVA': 11,
            'Cod TVA SAF-T': 310351,
            'Discount': '',
            'DiscountLinie': ''
        }
        output_rows_11.append(row_11)
    
    # Combine rows in correct order: ALL 21% rows first, then ALL 11% rows
    output_rows = output_rows_21 + output_rows_11
    
    # Create DataFrame with exact target structure
    output_df = pd.DataFrame(output_rows, columns=output_columns)
    
    # Generate output file name if not provided
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"import_bon_fiscal_transformed_{timestamp}.csv"
    
    # Save to CSV with exact formatting
    output_df.to_csv(output_file, index=False)
    
    # print(f"✅ Transformation completed successfully!")
    # print(f"📁 Input: {input_file}")
    # print(f"📁 Output: {output_file}")
    # print(f"📊 Generated {len(output_df)} import rows from {len(df)} Borderou transactions")
    # print(f"📋 Structure: {len(output_columns)} columns matching target format exactly")
    
    # Show sample of output
    # print("\n📋 Sample of transformed data:")
    # print(output_df.head(3).to_string(index=False, max_cols=10))
    
    return output_df, output_file


def process_pos_group(group_df, pos_id, filename, serie_document, denumire_articol, cod_depozit, 
                     output_columns, filename_codes, base_output_file):
    """Process a single POS terminal group and generate output file"""
    
    # Get the appropriate code mapping - check longer patterns first
    code_mapping = None
    # Sort by length (descending) to check more specific patterns first
    sorted_filename_codes = sorted(filename_codes.items(), key=lambda x: len(x[0]), reverse=True)
    
    for key, mapping in sorted_filename_codes:
        if key in filename:
            code_mapping = mapping
            cod_depozit = mapping['cod_depozit_override']  # Override with specific code
            denumire_articol = mapping['denumire']
            break
    
    if not code_mapping:
        raise ValueError(f"No code mapping found for filename: {filename}")
    
    output_rows_21 = []  # Store all 21% TVA rows first
    output_rows_11 = []  # Store all 11% TVA rows second
    
    # Process each transaction in this POS group
    for index, row in group_df.iterrows():
        # Determine the correct Serie document for this POS terminal
        current_serie_document = serie_document
        if 'M1' in filename.upper():
            if pos_id == '0014':
                current_serie_document = 'BFM1 0014'
            elif pos_id == '0012':
                current_serie_document = 'BFM1 0012'
        elif 'M2' in filename.upper():
            if pos_id == '102':
                current_serie_document = 'BFM2 102'
            elif pos_id == '103':
                current_serie_document = 'BFM2 103'
        
        nr_doc = int(row['Nr_Doc_Z'])
        date_obj = pd.to_datetime(row['Data'])
        date_str = date_obj.strftime('%Y%m%d')
        
        total_valoare = float(row['Total_Valoare'])
        netaxabil_baza = float(row['Netaxabil_Baza_Impozitare'])
        tva_21_base = float(row['Taxabile_21_Baza_Impozitare'])
        tva_21_val = float(row['Taxabile_21_Val_TVA'])
        tva_11_base = float(row['Taxabile_11_Baza_Impozitare'])
        tva_11_val = float(row['Taxabile_11_Val_TVA'])
        
        # Calculate Total_valoare_fata_netaxablil as per manual process
        total_valoare_fata_netaxablil = total_valoare - netaxabil_baza
        
        # Create rows for both 21% and 11% TVA regardless of values (to match reference format)
        
        # Always create 21% TVA row
        row_21 = {
            'Serie document': current_serie_document,
            'Numar document': nr_doc,
            'Cod depozit': cod_depozit,
            'Nume depozit': '',
            'Data document': date_str,
            'Data scadenta': date_str,
            'Cod tip factura SAF-T': 380,
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
            'Valoare neta totala': tva_21_base,
            'Valoare TVA': tva_21_val,
            'Total document': total_valoare_fata_netaxablil,
            'Numar bonuri fiscale': '',
            'Card': 0,
            'Cont banca': 5125,
            'Numerar': total_valoare_fata_netaxablil,
            'Cont casa': 5311,
            'Tichete': 0,
            'Cont tichete': 5328,
            'Cont TVA': 4427,
            'Cod articol': f'{denumire_articol} 21%',
            'Cod de bare': '',
            'Denumire articol': denumire_articol,
            'Cantitate': 1,
            'Cod lot': '',
            'Data expirare': '',
            'Nr seriale': '',
            'Tip miscare SAF-T': '',
            'Cont serviciu': '',
            'Pret cu TVA': tva_21_base + tva_21_val,
            'Total fara TVA': tva_21_base,
            'Total TVA': tva_21_val,
            'Total cu TVA': tva_21_base + tva_21_val,
            'Optiune TVA': 'Taxabile',
            'Cota TVA': 21,
            'Cod TVA SAF-T': 310344,
            'Discount': '',
            'DiscountLinie': ''
        }
        output_rows_21.append(row_21)
        
        # Always create 11% TVA row
        row_11 = {
            'Serie document': current_serie_document,
            'Numar document': nr_doc,
            'Cod depozit': cod_depozit,
            'Nume depozit': '',
            'Data document': date_str,
            'Data scadenta': date_str,
            'Cod tip factura SAF-T': 380,
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
            'Valoare neta totala': tva_11_base,
            'Valoare TVA': tva_11_val,
            'Total document': total_valoare_fata_netaxablil,
            'Numar bonuri fiscale': '',
            'Card': 0,
            'Cont banca': 5125,
            'Numerar': total_valoare_fata_netaxablil,
            'Cont casa': 5311,
            'Tichete': 0,
            'Cont tichete': 5328,
            'Cont TVA': 4427,
            'Cod articol': f'{denumire_articol} 11%',
            'Cod de bare': '',
            'Denumire articol': denumire_articol,
            'Cantitate': 1,
            'Cod lot': '',
            'Data expirare': '',
            'Nr seriale': '',
            'Tip miscare SAF-T': '',
            'Cont serviciu': '',
            'Pret cu TVA': tva_11_base + tva_11_val,
            'Total fara TVA': tva_11_base,
            'Total TVA': tva_11_val,
            'Total cu TVA': tva_11_base + tva_11_val,
            'Optiune TVA': 'Taxabile',
            'Cota TVA': 11,
            'Cod TVA SAF-T': 310351,
            'Discount': '',
            'DiscountLinie': ''
        }
        output_rows_11.append(row_11)
    
    # Combine rows in correct order: ALL 21% rows first, then ALL 11% rows
    output_rows = output_rows_21 + output_rows_11
    
    # Create DataFrame with exact target structure
    output_df = pd.DataFrame(output_rows, columns=output_columns)
    
    # Generate output file name for this POS terminal
    if base_output_file:
        base_dir = os.path.dirname(base_output_file)
        base_name = os.path.splitext(os.path.basename(base_output_file))[0]
    else:
        base_dir = "./out/import"
        base_name = f"import_bon_fiscal_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Create POS-specific filename
    if 'M1' in filename.upper():
        pos_output_file = os.path.join(base_dir, f"M1 import bon fiscal vanzare CASA {pos_id}.csv")
    elif 'M2' in filename.upper():
        pos_output_file = os.path.join(base_dir, f"M2 import bon fiscal vanzare CASA {pos_id}.csv")
    else:
        pos_output_file = os.path.join(base_dir, f"{base_name}_{pos_id}.csv")
    
    # Save to CSV with exact formatting
    output_df.to_csv(pos_output_file, index=False)
    
    # print(f"✅ POS {pos_id} transformation completed!")
    # print(f"📁 Output: {pos_output_file}")
    # print(f"📊 Generated {len(output_df)} import rows from {len(group_df)} Borderou transactions")
    
    return pos_output_file, output_df

def validate_format_compatibility(output_file, reference_file):
    """
    Validate that the output format matches the reference format exactly
    """
    try:
        output_df = pd.read_csv(output_file)
        reference_df = pd.read_csv(reference_file)
        
        # Check headers match exactly
        output_headers = list(output_df.columns)
        reference_headers = list(reference_df.columns)
        
        headers_match = output_headers == reference_headers
        
        # print(f"\n🔍 FORMAT VALIDATION:")
        # print(f"✅ Headers match: {headers_match}")
        # print(f"📊 Output columns: {len(output_headers)}")
        # print(f"📊 Reference columns: {len(reference_headers)}")
        
        if not headers_match:
            # print("❌ Header differences found:")
            for i, (out_h, ref_h) in enumerate(zip(output_headers, reference_headers)):
                if out_h != ref_h:
                    # print(f"  Column {i}: '{out_h}' vs '{ref_h}'")
                    pass
        
        # Check data types compatibility
        # print(f"✅ Output ready for import: {headers_match}")
        
        return headers_match
        
    except Exception as e:
        # print(f"❌ Validation error: {str(e)}")
        return False

if __name__ == "__main__":
    # Configuration - Updated paths
    input_dir = "./in/toImport"
    output_dir = "./out/import"
    reference_file = r"e:\Programming\Trae - MomAutomations\NewFeatureTest\base-out\import bon fiscal vanzare FAST FOOD 1.csv"
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if input directory exists
    if not os.path.exists(input_dir):
        # print(f"❌ Input directory not found: {input_dir}")
        # print("Please create the directory and place your cleaned Borderou CSV files there.")
        exit(1)
    
    # Find all CSV files in the input directory
    csv_files = [f for f in os.listdir(input_dir) if f.endswith('.csv')]
    
    if not csv_files:
        # print(f"❌ No CSV files found in {input_dir}")
        # print("Please place your cleaned Borderou CSV files in the input directory.")
        exit(1)
    
    # print(f"🔍 Found {len(csv_files)} CSV file(s) to process...")
    
    # Process each CSV file
    for csv_file in csv_files:
        input_file = os.path.join(input_dir, csv_file)
        
        # Generate output filename
        base_name = os.path.splitext(csv_file)[0]
        output_file = os.path.join(output_dir, f"import_bon_fiscal_{base_name}.csv")
        
        # print(f"\n📂 Processing: {csv_file}")
        
        try:
            # Transform the file
            result = transform_borderou_to_import_format(input_file, output_file)
            
            # Handle different return types (single file vs multiple files)
            if isinstance(result, list):
                # Multiple files (M1/M2 case)
                output_files = result
                # print(f"✅ {csv_file} split into {len(output_files)} files successfully!")
                
                # Validate each output file if reference exists
                if os.path.exists(reference_file):
                    for output_path, _ in output_files:
                        is_compatible = validate_format_compatibility(output_path, reference_file)
                        if is_compatible:
                            pass
                            # print(f"✅ {os.path.basename(output_path)} format validated successfully!")
                        else:
                            print(f"⚠️  {os.path.basename(output_path)} format validation failed.")
                else:
                    print("⚠️  Reference file not found - skipping format validation.")
            else:
                # Single file (normal case)
                transformed_df, output_path = result
                
                if os.path.exists(reference_file):
                    is_compatible = validate_format_compatibility(output_path, reference_file)
                    
                    if is_compatible:
                        pass
                        # print(f"✅ {csv_file} transformed successfully and ready for import!")
                    else:
                        print(f"⚠️  {csv_file} transformed but format validation failed.")
                else:
                    # print(f"✅ {csv_file} transformed successfully!")
                    print("⚠️  Reference file not found - skipping format validation.")
                
        except Exception as e:
            # print(f"❌ Error processing {csv_file}: {str(e)}")
            # print("Please check the input file format.")
            continue
    