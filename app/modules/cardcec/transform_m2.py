import pandas as pd
from pathlib import Path

def transform_m2_to_fastfood2():
    """Transform M2 initial data to FAST FOOD 2 import format."""
    
    # Read the M2 initial CSV
    input_file = Path('csv/M2_initial_proper.csv')
    output_file = Path('out/M2_final.csv')
    
    df = pd.read_csv(input_file, header=None)
    
    # Create output data based on the FAST FOOD 2 model format
    output_data = []
    
    # Get the document numbers from column 1
    doc_numbers = df[1].tolist()
    
    # Get the dates from column 2 and format them
    dates = []
    for date_str in df[2]:
        try:
            # Parse the datetime string and extract just the date part
            dt = pd.to_datetime(date_str)
            dates.append(dt.strftime('%Y%m%d'))
        except:
            dates.append('')
    
    # Get the values from column 5
    values = df[5].tolist()
    print("First 5 values:", values[:5])
    print("Type of first value:", type(values[0]) if values else "No values")
    
    # Create rows matching the FAST FOOD 2 format
    for i, (doc_num, date, value) in enumerate(zip(doc_numbers, dates, values)):
        # Skip if value is not a valid number
        try:
            total_value = float(value)
        except (ValueError, TypeError):
            continue
            
        # Calculate net value and TVA (assuming 21% TVA rate)
        net_value = round(total_value / 1.21, 2)
        tva_value = round(total_value - net_value, 2)
        
        # Create row in FAST FOOD 2 format
        row = [
            f'F 2',  # Serie document
            doc_num,  # Numar document
            '4',  # Cod depozit
            '',  # Nume depozit
            date,  # Data document
            date,  # Data scadenta
            '380',  # Cod tip factura SAF-T
            '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',  # Empty fields for partner info (17 fields: 7-23)
            net_value,  # Valoare neta totala (24)
            tva_value,  # Valoare TVA (25)
            total_value,  # Total document (26)
            '',  # Numar bonuri fiscale (27)
            '0',  # Card (28)
            '5125',  # Cont banca (29)
            total_value,  # Numerar (30)
            '5311',  # Cont casa (31)
            '0',  # Tichete (32)
            '5328',  # Cont tichete (33)
            '4427',  # Cont TVA (34)
            f'ff 2 21%',  # Cod articol (35)
            '',  # Cod de bare (36)
            '',  # Denumire articol (37)
            '1',  # Cantitate (38)
            '', '', '', '',  # Lot, expirare, seriale (39-42)
            '',  # Tip miscare SAF-T (43)
            '',  # Cont serviciu (44)
            total_value,  # Pret cu TVA (45)
            net_value,  # Total fara TVA (46)
            tva_value,  # Total TVA (47)
            total_value,  # Total cu TVA (48)
            'Taxabile',  # Optiune TVA (49)
            '21',  # Cota TVA (50)
            '310344',  # Cod TVA SAF-T (51)
            '',  # Discount (52)
            ''  # DiscountLinie (53)
        ]
        output_data.append(row)
    
    # Create DataFrame with proper column headers from the model
    columns = [
        'Serie document', 'Numar document', 'Cod depozit', 'Nume depozit', 'Data document', 'Data scadenta',
        'Cod tip factura SAF-T', 'Cod partener', 'Nume partener', 'Atribut fiscal', 'Cod fiscal', 'Nr.Reg.Com.',
        'Rezidenta', 'Tara', 'Judet', 'Localitate', 'Strada', 'Numar', 'Bloc', 'Scara', 'Etaj', 'Apartament',
        'Cod postal', 'Cod agent', 'Valoare neta totala', 'Valoare TVA', 'Total document', 'Numar bonuri fiscale',
        'Card', 'Cont banca', 'Numerar', 'Cont casa', 'Tichete', 'Cont tichete', 'Cont TVA', 'Cod articol',
        'Cod de bare', 'Denumire articol', 'Cantitate', 'Cod lot', 'Data expirare', 'Nr seriale',
        'Tip miscare SAF-T', 'Cont serviciu', 'Pret cu TVA', 'Total fara TVA', 'Total TVA', 'Total cu TVA',
        'Optiune TVA', 'Cota TVA', 'Cod TVA SAF-T', 'Discount', 'DiscountLinie'
    ]
    
    output_df = pd.DataFrame(output_data, columns=columns)
    
    # Save to output file
    output_df.to_csv(output_file, index=False)
    print(f"Successfully transformed {len(output_df)} rows to {output_file}")
    
    return output_df

if __name__ == "__main__":
    transform_m2_to_fastfood2()
