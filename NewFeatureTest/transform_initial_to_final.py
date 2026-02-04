import pandas as pd
import sys
from pathlib import Path


def transform_csv(input_file, output_file):
    """
    Transform Initial.csv to Final.csv format.

    Removes rows with 'CLIENT MARFA' or 'CLIENT I.T.P' in the 'tert' column
    and maps columns to the final format.
    """
    # Read the input CSV
    df = pd.read_csv(input_file)

    # Filter out rows with CLIENT MARFA or CLIENT I.T.P in tert column
    df_filtered = df[
        ~df['tert'].str.contains('CLIENT MARFA|CLIENT  I.T.P', na=False, case=False)
    ].copy()

    # Format date from YYYY-MM-DD to YYYYMMDD
    df_filtered['data_formatted'] = pd.to_datetime(df_filtered['data']).dt.strftime('%Y%m%d')

    # Create the final dataframe with all required columns
    final_columns = [
        'NR.linie', 'Serie', 'Numar document', 'Data', 'Data scadenta',
        'Cod tip Factura', 'Nume partener', 'Atribut fiscal', 'Cod fiscal',
        'Nr.Reg.Com.', 'Rezidenta', 'Tara', 'Judet', 'Localitate',
        'Strada', 'Numar', 'Bloc', 'Scara', 'Etaj', 'Apartament',
        'Cod postal', 'Moneda', 'Curs', 'TVA la incasare', 'Taxare inversa',
        'Factura de transport', 'Cod agent', 'Valoare neta totala', 'Valoare TVA',
        'Total document', 'Denumire articol', 'Cantitate', 'Tip miscare stoc',
        'Cont servicii', 'Pret de lista', 'Valoare fara tva', 'Val TVA',
        'Valoare  cu TVa', 'Optiune TVA', 'Cota TVA', 'Cod TVA SAFT',
        'Observatie', 'Centre de cost'
    ]

    # Create empty dataframe with final columns
    df_final = pd.DataFrame(columns=final_columns)

    # Map columns from filtered dataframe to final format
    df_final['NR.linie'] = ''
    df_final['Serie'] = 'FV'
    df_final['Numar document'] = df_filtered['nr_iesire'].astype(str)
    df_final['Data'] = df_filtered['data_formatted']
    df_final['Data scadenta'] = df_filtered['data_formatted']
    df_final['Cod tip Factura'] = ''
    df_final['Nume partener'] = df_filtered['tert']
    df_final['Atribut fiscal'] = ''
    df_final['Cod fiscal'] = df_filtered['cod_fiscal'].astype(str)
    df_final['Nr.Reg.Com.'] = ''
    df_final['Rezidenta'] = ''
    df_final['Tara'] = ''
    df_final['Judet'] = ''
    df_final['Localitate'] = ''
    df_final['Strada'] = ''
    df_final['Numar'] = ''
    df_final['Bloc'] = ''
    df_final['Scara'] = ''
    df_final['Etaj'] = ''
    df_final['Apartament'] = ''
    df_final['Cod postal'] = ''
    df_final['Moneda'] = 'RON'
    df_final['Curs'] = ''
    df_final['TVA la incasare'] = ''
    df_final['Taxare inversa'] = ''
    df_final['Factura de transport'] = ''
    df_final['Cod agent'] = ''
    df_final['Valoare neta totala'] = ''
    df_final['Valoare TVA'] = ''
    df_final['Total document'] = ''
    df_final['Denumire articol'] = df_filtered['den_tip']
    df_final['Cantitate'] = df_filtered['cantitate']
    df_final['Tip miscare stoc'] = ''
    df_final['Cont servicii'] = ''
    df_final['Pret de lista'] = ''
    df_final['Valoare fara tva'] = df_filtered['valoare']
    df_final['Val TVA'] = df_filtered['tva']
    df_final['Valoare  cu TVa'] = ''
    df_final['Optiune TVA'] = 'TAXABILE'
    df_final['Cota TVA'] = df_filtered['tva_art']
    df_final['Cod TVA SAFT'] = ''
    df_final['Observatie'] = ''
    df_final['Centre de cost'] = ''

    # Save to output file
    df_final.to_csv(output_file, index=False)

    print(f"Transformation complete!")
    print(f"Input rows: {len(df)}")
    print(f"Filtered rows: {len(df_filtered)}")
    print(f"Output saved to: {output_file}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python transform_initial_to_final.py <input_file> <output_file>")
        print("Example: python transform_initial_to_final.py Initial.csv 'Final.csv'")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    transform_csv(input_file, output_file)
