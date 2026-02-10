import pandas as pd
import numpy as np
from rich import print
import os
import sys

from classes.excel_processor import ExcelProcessor

class FormatAddColumn(ExcelProcessor):
    def __init__(self):
        super().__init__(input_folder="C:/in/format", output_folder="C:/out/format")

    def format_data(self, df):
        """Formats dates and numerical values in the DataFrame"""
        if df is None:
            print("Warning: DataFrame is None in format_data")
            return None

        try:
            # Format date columns
            date_columns = ['Data NIR', 'Data']
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%d/%m/%Y')

            # Format numeric columns
            numeric_columns = ['Valoare Achizitie', 'TVVAaloare Diferenta', 'Adaos', 'Valoare TVA.1']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    df[col] = df[col].fillna(0).round(2)

            # Format currency columns
            currency_columns = ['Valoare Achizitie', 'TVVAaloare Diferenta']
            for col in currency_columns:
                if col in df.columns:
                    df[col] = df[col].apply(
                        lambda x: '{:,.2f}'.format(float(x)) if pd.notnull(x) and not isinstance(x, str) else x
                    )
            return df
        except Exception as e:
            print(f"Error formatting data: {e}")
            return None

    def fix_column(self, df):
        """Fills empty spaces in column J with values from column K"""
        if df is None:
            print("Warning: DataFrame is None in fix_column")
            return None

        try:
            df['TVVAaloare Diferenta'] = df['TVVAaloare Diferenta'].replace(r'^\s*$', np.nan, regex=True)
            mask = df['TVVAaloare Diferenta'].isna()
            df.loc[mask, 'TVVAaloare Diferenta'] = df.loc[mask, 'Unnamed: 10']
            df.drop(columns=['Unnamed: 10'], inplace=True)
            return df
        except Exception as e:
            print(f"Error in fix_column: {e}")
            return None

    @staticmethod
    def correct_format(value):
        """Fix formatting (e.g., %0.09 → %9)"""
        try:
            num = pd.to_numeric(str(value).replace("%", ""), errors='coerce')
            if pd.notna(num) and num < 1:
                num = int(num * 100)
            return f"%{int(num)}" if pd.notna(num) else None
        except:
            return None

    def drop_columns(self, df):
        """Drops unused columns from the DataFrame"""
        if df is None:
            print("Warning: DataFrame is None in drop_columns")
            return None

        dropcol = ["NIR","Data NIR", "Adaos Proc", "Procent TVA", "Numar Aviz", "Data Aviz",
                  "TVA Achizitie", "% TVA Ach", "TVAACH"]
        try:
            for col in dropcol:
                if col in df.columns:
                    df.drop(columns=[col], inplace=True)
            return df
        except Exception as e:
            print(f"Error dropping columns: {e}")
            return None

    def split_by_tva_vanzare(self, df):
        """Splits DataFrame based on '% TVA VANZARE' values"""
        if df is None or not isinstance(df, pd.DataFrame):
            print("Warning: Invalid DataFrame in split_by_tva_vanzare")
            return None

        try:
            if '% TVA VANZARE' not in df.columns:
                print("Error: Column '% TVA VANZARE' not found")
                return None

            df = df.copy()
            df['% TVA VANZARE'] = df['% TVA VANZARE'].apply(self.correct_format)
            df = df.dropna(subset=['% TVA VANZARE'])

            df.loc[:, 'Numeric_TVA'] = df['% TVA VANZARE'].str.extract(r'(\d+)')[0].astype(float)
            df = df.sort_values(by='Numeric_TVA', ascending=True).drop(columns=['Numeric_TVA'])

            unique_values = df['% TVA VANZARE'].unique()
            split_dfs = {value: df[df['% TVA VANZARE'] == value].reset_index(drop=True)
                        for value in unique_values}
            return split_dfs
        except Exception as e:
            print(f"Error in split_by_tva_vanzare: {e}")
            return None

    def merge_splits_with_clean_summary(self, split_dfs):
        """Merges split DataFrames and adds summary table with headers - returns complete DataFrame"""
        if not split_dfs:
            print("Warning: No data to merge")
            return None

        try:
            # Merge all DataFrames in split_dfs
            merged_df = pd.concat(split_dfs.values(), ignore_index=True)
            if merged_df.empty:
                print("Warning: Merged DataFrame is empty")
                return None

            # Calculate summary data exactly like the original
            summary_data = []
            for key, split_df in split_dfs.items():
                try:
                    if key == "%19":
                        achf19 = split_df['Valoare Achizitie'].str.replace(',', '').astype(float).sum()
                        achtva19 = achf19 * 0.19
                        vzf19 = split_df['Valoare TVA.1'].astype(float).sum() / 0.19
                        vztva19 = split_df['Valoare TVA.1'].astype(float).sum()
                        adaos19 = split_df['Adaos'].astype(float).sum()
                        summary_data.append([key, achf19, achtva19, vzf19, vztva19, adaos19])
                    elif key == "%9":
                        achf9 = split_df['Valoare Achizitie'].str.replace(',', '').astype(float).sum()
                        achtva9 = achf9 * 0.09
                        vzf9 = split_df['Valoare TVA.1'].astype(float).sum() / 0.09
                        vztva9 = split_df['Valoare TVA.1'].astype(float).sum()
                        adaos9 = split_df['Adaos'].astype(float).sum()
                        summary_data.append([key, achf9, achtva9, vzf9, vztva9, adaos9])
                    elif key == "%21":
                        achf21 = split_df['Valoare Achizitie'].str.replace(',', '').astype(float).sum()
                        achtva21 = achf21 * 0.21
                        vzf21 = split_df['Valoare TVA.1'].astype(float).sum() / 0.21
                        vztva21 = split_df['Valoare TVA.1'].astype(float).sum()
                        adaos21 = split_df['Adaos'].astype(float).sum()
                        summary_data.append([key, achf21, achtva21, vzf21, vztva21, adaos21])
                    elif key == "%11":
                        achf11 = split_df['Valoare Achizitie'].str.replace(',', '').astype(float).sum()
                        achtva11 = achf11 * 0.11
                        vzf11 = split_df['Valoare TVA.1'].astype(float).sum() / 0.11
                        vztva11 = split_df['Valoare TVA.1'].astype(float).sum()
                        adaos11 = split_df['Adaos'].astype(float).sum()
                        summary_data.append([key, achf11, achtva11, vzf11, vztva11, adaos11])
                except Exception as e:
                    print(f"Error processing summary for {key}: {e}")
                    continue

            if not summary_data:
                print("Warning: No summary data generated")
                return merged_df

            # Create the summary DataFrame with its own headers
            summary_df = pd.DataFrame(
                summary_data,
                columns=['% TVA VANZARE', 'Total Valoare Achizitie',
                        'Total Valoare Achizitie TVA', 'Total Valoare Vanzare',
                        'Total Valoare Vanzare TVA', 'Total Adaos']
            )

            # Create empty rows for spacing (3 rows like original)
            empty_rows = pd.DataFrame(
                [[""] * len(merged_df.columns)] * 3,
                columns=merged_df.columns
            )

            # Create the summary table headers row
            summary_headers = [""] * len(merged_df.columns)
            summary_headers[0] = "% TVA VANZARE"
            summary_headers[1] = "Total Valoare Achizitie"
            summary_headers[2] = "Total Valoare Achizitie TVA"
            summary_headers[3] = "Total Valoare Vanzare"
            summary_headers[4] = "Total Valoare Vanzare TVA"
            summary_headers[5] = "Total Adaos"
            
            summary_headers_df = pd.DataFrame([summary_headers], columns=merged_df.columns)

            # Convert summary_df to have the same number of columns as merged_df
            summary_with_padding = pd.DataFrame(columns=merged_df.columns)
            
            # Add the summary data to the first few columns
            for i, (_, row) in enumerate(summary_df.iterrows()):
                new_row = [""] * len(merged_df.columns)
                # Fill the first 6 columns with summary data
                for j, value in enumerate(row.values):
                    if j < len(new_row):
                        new_row[j] = value
                summary_with_padding.loc[i] = new_row

            # Combine everything: main data + empty rows + summary headers + summary data
            final_df = pd.concat([
                merged_df,
                empty_rows,
                summary_headers_df,
                summary_with_padding
            ], ignore_index=True)

            print(f"✅ DataFrame created with {len(merged_df)} data rows and {len(summary_with_padding)} summary rows")
            return final_df

        except Exception as e:
            print(f"Error in merge_splits_with_clean_summary: {e}")
            return None

    def process_dataframe(self, df):
        """Process a single DataFrame and return the result with summary"""
        if df is None:
            print("Warning: DataFrame is None in process_dataframe")
            return None

        try:
            df = self.format_data(df)
            if df is None:
                return None

            df = self.fix_column(df)
            if df is None:
                return None

            df = self.drop_columns(df)
            if df is None:
                return None

            df_dict = self.split_by_tva_vanzare(df)
            if df_dict is None:
                return None

            final_df = self.merge_splits_with_clean_summary(df_dict)
            return final_df

        except Exception as e:
            print(f"Error processing DataFrame: {e}")
            return None

    def process_files(self):
        """Main method to process all files and return results"""
        self.create_folders()
        results = {}

        for file in os.listdir(self.input_folder):
            if file.endswith('.xlsx'):
                print(f"Processing file: {file}")
                df = self.load_excel(os.path.join(self.input_folder, file))

                if df is None:
                    print(f"Failed to load file: {file}")
                    continue

                final_df = self.process_dataframe(df)
                if final_df is not None:
                    results[file] = final_df
                    print(f"Successfully processed: {file}")
                else:
                    print(f"Failed to process: {file}")

        return results

if __name__ == "__main__":
    processor = FormatAddColumn()
    results = processor.process_files()
    
    # Example: Access the result DataFrame for a specific file
    for filename, dataframe in results.items():
        print(f"\nFile: {filename}")
        print(f"DataFrame shape: {dataframe.shape}")
        print("Last 10 rows (including summary):")
        print(dataframe.tail(10))