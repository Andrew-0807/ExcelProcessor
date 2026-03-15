import pandas as pd

# Read the output file
try:
    df = pd.read_csv('csv/OUTPUT_IMPORT_CARD.csv', encoding='latin1')
    print("First 5 rows of the output:")
    print(df.head().to_string())
    
    print("\nColumn names and data types:")
    print(df.dtypes)
    
    print("\nSample data (first row):")
    print(df.iloc[0].to_string())
    
except Exception as e:
    print(f"Error reading file: {e}")
