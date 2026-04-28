import pandas as pd


class ValoareMinus:
    def process_dataframe(self, df):
        """Negate the Valoare column and format dates to YYYYMMDD."""
        print("Available columns:", df.columns)

        date_column = "Data Ultimei Incasari"
        if date_column in df.columns:
            df[date_column] = pd.to_datetime(df[date_column], errors='coerce').dt.strftime('%Y%m%d')
            print(f"Formatted date column: {date_column}")
        else:
            print(f"Error: '{date_column}' does not exist in the DataFrame.")
            raise KeyError(f"'{date_column}' not found in DataFrame columns.")

        tva_column = "Valoare"
        if tva_column in df.columns:
            df[tva_column] = df[tva_column].apply(lambda x: -x)
        else:
            print(f"Error: '{tva_column}' does not exist in the DataFrame.")
            raise KeyError(f"'{tva_column}' not found in DataFrame columns.")

        return df