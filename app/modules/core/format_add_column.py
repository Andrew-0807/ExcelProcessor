import pandas as pd
import numpy as np
from app.log import info as print  # debug chatter; silent unless MOM_VERBOSE=1


class FormatAddColumn:
    def format_data(self, df):
        if df is None:
            print("Warning: DataFrame is None in format_data")
            return None

        try:
            date_columns = ["Data NIR", "Data"]
            for col in date_columns:
                if col in df.columns:
                    original_values = df[col].copy()
                    parsed_dates = pd.to_datetime(df[col], errors="coerce")
                    coerced_mask = (
                        parsed_dates.isna()
                        & original_values.notna()
                        & (original_values.astype(str).str.strip() != "")
                    )
                    coerced_count = coerced_mask.sum()
                    if coerced_count > 0:
                        bad_rows = df.index[coerced_mask].tolist()[:5]
                        bad_vals = original_values[coerced_mask].head(5).tolist()
                        print(
                            f"[WARN] {coerced_count} unparseable dates in column '{col}' were lost. "
                            f"Rows (first 5): {bad_rows}, Values: {bad_vals}"
                        )
                    df[col] = parsed_dates.dt.strftime("%d/%m/%Y")

            numeric_columns = [
                "Valoare Achizitie",
                "TVVAaloare Diferenta",
                "Adaos",
                "Valoare TVA.1",
            ]
            for col in numeric_columns:
                if col in df.columns:
                    original_values = df[col].copy()
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                    coerced_mask = (
                        df[col].isna()
                        & original_values.notna()
                        & (original_values.astype(str).str.strip() != "")
                    )
                    coerced_count = coerced_mask.sum()
                    if coerced_count > 0:
                        bad_rows = df.index[coerced_mask].tolist()[:5]
                        bad_vals = original_values[coerced_mask].head(5).tolist()
                        print(
                            f"[WARN] {coerced_count} non-numeric values in column '{col}' were converted to 0. "
                            f"Rows (first 5): {bad_rows}, Values: {bad_vals}"
                        )
                    df[col] = df[col].fillna(0).round(2)

            currency_columns = ["Valoare Achizitie", "TVVAaloare Diferenta"]
            for col in currency_columns:
                if col in df.columns:
                    df[col] = df[col].apply(
                        lambda x: "{:,.2f}".format(float(x))
                        if pd.notnull(x) and not isinstance(x, str)
                        else x
                    )
            return df
        except Exception as e:
            print(f"Error formatting data: {e}")
            return None

    def fix_column(self, df):
        if df is None:
            print("Warning: DataFrame is None in fix_column")
            return None

        try:
            if "TVVAaloare Diferenta" not in df.columns:
                print("  [fix_column] 'TVVAaloare Diferenta' not found — skipping fix_column")
                return df

            df["TVVAaloare Diferenta"] = df["TVVAaloare Diferenta"].replace(
                r"^\s*$", np.nan, regex=True
            )

            if "Unnamed: 10" in df.columns:
                mask = df["TVVAaloare Diferenta"].isna()
                df.loc[mask, "TVVAaloare Diferenta"] = df.loc[mask, "Unnamed: 10"]
                df.drop(columns=["Unnamed: 10"], inplace=True)
            else:
                print("  [fix_column] 'Unnamed: 10' not found — skipping fallback fill")

            return df
        except Exception as e:
            print(f"Error in fix_column: {e}")
            return None

    @staticmethod
    def correct_format(value):
        try:
            num = pd.to_numeric(str(value).replace("%", ""), errors="coerce")
            if pd.notna(num) and num < 1:
                num = int(num * 100)
            return f"%{int(num)}" if pd.notna(num) else None
        except:
            return None

    def drop_columns(self, df):
        if df is None:
            print("Warning: DataFrame is None in drop_columns")
            return None

        dropcol = [
            "NIR",
            "Data NIR",
            "Adaos Proc",
            "Procent TVA",
            "Numar Aviz",
            "Data Aviz",
            "TVA Achizitie",
            "% TVA Ach",
            "TVAACH",
        ]
        try:
            for col in dropcol:
                if col in df.columns:
                    df.drop(columns=[col], inplace=True)
            return df
        except Exception as e:
            print(f"Error dropping columns: {e}")
            return None

    def split_by_tva_vanzare(self, df):
        if df is None or not isinstance(df, pd.DataFrame):
            print("Warning: Invalid DataFrame in split_by_tva_vanzare")
            return None

        try:
            if "% TVA VANZARE" not in df.columns:
                print(
                    f"Error: Column '% TVA VANZARE' not found. "
                    f"Available columns: {list(df.columns)}"
                )
                return None

            df = df.copy()
            df["% TVA VANZARE"] = df["% TVA VANZARE"].apply(self.correct_format)
            df = df.dropna(subset=["% TVA VANZARE"])

            df.loc[:, "Numeric_TVA"] = (
                df["% TVA VANZARE"].str.extract(r"(\d+)")[0].astype(float)
            )
            df = df.sort_values(by="Numeric_TVA", ascending=True).drop(
                columns=["Numeric_TVA"]
            )

            unique_values = df["% TVA VANZARE"].unique()
            split_dfs = {
                value: df[df["% TVA VANZARE"] == value].reset_index(drop=True)
                for value in unique_values
            }
            return split_dfs
        except Exception as e:
            print(f"Error in split_by_tva_vanzare: {e}")
            return None

    def merge_splits_with_clean_summary(self, split_dfs):
        if not split_dfs:
            print("Warning: No data to merge")
            return None

        try:
            merged_df = pd.concat(split_dfs.values(), ignore_index=True)
            if merged_df.empty:
                print("Warning: Merged DataFrame is empty")
                return None

            summary_data = []
            for key, split_df in split_dfs.items():
                try:
                    if key == "%19":
                        achf19 = (
                            split_df["Valoare Achizitie"]
                            .str.replace(",", "")
                            .astype(float)
                            .sum()
                        )
                        summary_data.append([
                            key, achf19, achf19 * 0.19,
                            split_df["Valoare TVA.1"].astype(float).sum() / 0.19,
                            split_df["Valoare TVA.1"].astype(float).sum(),
                            split_df["Adaos"].astype(float).sum()
                        ])
                    elif key == "%9":
                        achf9 = (
                            split_df["Valoare Achizitie"]
                            .str.replace(",", "")
                            .astype(float)
                            .sum()
                        )
                        summary_data.append([
                            key, achf9, achf9 * 0.09,
                            split_df["Valoare TVA.1"].astype(float).sum() / 0.09,
                            split_df["Valoare TVA.1"].astype(float).sum(),
                            split_df["Adaos"].astype(float).sum()
                        ])
                    elif key == "%21":
                        achf21 = (
                            split_df["Valoare Achizitie"]
                            .str.replace(",", "")
                            .astype(float)
                            .sum()
                        )
                        summary_data.append([
                            key, achf21, achf21 * 0.21,
                            split_df["Valoare TVA.1"].astype(float).sum() / 0.21,
                            split_df["Valoare TVA.1"].astype(float).sum(),
                            split_df["Adaos"].astype(float).sum()
                        ])
                    elif key == "%11":
                        achf11 = (
                            split_df["Valoare Achizitie"]
                            .str.replace(",", "")
                            .astype(float)
                            .sum()
                        )
                        summary_data.append([
                            key, achf11, achf11 * 0.11,
                            split_df["Valoare TVA.1"].astype(float).sum() / 0.11,
                            split_df["Valoare TVA.1"].astype(float).sum(),
                            split_df["Adaos"].astype(float).sum()
                        ])
                except Exception as e:
                    print(f"Error processing summary for {key}: {e}")
                    continue

            if not summary_data:
                print("Warning: No summary data generated")
                return merged_df

            summary_df = pd.DataFrame(
                summary_data,
                columns=[
                    "% TVA VANZARE",
                    "Total Valoare Achizitie",
                    "Total Valoare Achizitie TVA",
                    "Total Valoare Vanzare",
                    "Total Valoare Vanzare TVA",
                    "Total Adaos",
                ],
            )

            empty_rows = pd.DataFrame(
                [[""] * len(merged_df.columns)] * 3, columns=merged_df.columns
            )

            summary_headers = [""] * len(merged_df.columns)
            summary_headers[:6] = [
                "% TVA VANZARE",
                "Total Valoare Achizitie",
                "Total Valoare Achizitie TVA",
                "Total Valoare Vanzare",
                "Total Valoare Vanzare TVA",
                "Total Adaos",
            ]

            summary_headers_df = pd.DataFrame(
                [summary_headers], columns=merged_df.columns
            )

            summary_with_padding = pd.DataFrame(columns=merged_df.columns)
            for i, (_, row) in enumerate(summary_df.iterrows()):
                new_row = [""] * len(merged_df.columns)
                for j, value in enumerate(row.values):
                    if j < len(new_row):
                        new_row[j] = value
                summary_with_padding.loc[i] = new_row

            final_df = pd.concat(
                [merged_df, empty_rows, summary_headers_df, summary_with_padding],
                ignore_index=True,
            )

            print(
                f"[OK] DataFrame created with {len(merged_df)} data rows and {len(summary_with_padding)} summary rows"
            )
            return final_df

        except Exception as e:
            print(f"Error in merge_splits_with_clean_summary: {e}")
            return None

    def _normalize_columns(self, df):
        rename_map = {}

        merged_col = None
        for col in df.columns:
            if (
                "TVVAaloare Diferenta" in str(col)
                and str(col) != "TVVAaloare Diferenta"
            ):
                merged_col = col
                break

        if merged_col is not None and "TVVAaloare Diferenta" not in df.columns:
            merged_idx = df.columns.get_loc(merged_col)
            rename_map[merged_col] = "Valoare Achizitie Cu TVA"
            if merged_idx + 1 < len(df.columns):
                next_col = df.columns[merged_idx + 1]
                if str(next_col).startswith("Unnamed:"):
                    rename_map[next_col] = "TVVAaloare Diferenta"
                    print(
                        f"  [normalize] Split merged header: '{merged_col}' -> 'Valoare Achizitie Cu TVA' + '{next_col}' -> 'TVVAaloare Diferenta'"
                    )

        if "Data Document" in df.columns and "Data" not in df.columns:
            rename_map["Data Document"] = "Data"
            print(f"  [normalize] Renamed 'Data Document' -> 'Data'")

        if (
            "Unnamed: 10" not in df.columns
            and "Unnamed: 9" in df.columns
            and "Unnamed: 9" not in rename_map
        ):
            rename_map["Unnamed: 9"] = "Unnamed: 10"
            print(f"  [normalize] Renamed 'Unnamed: 9' -> 'Unnamed: 10'")

        if rename_map:
            df = df.rename(columns=rename_map)
            print(f"  [normalize] Applied {len(rename_map)} column renames")

        return df

    def process_dataframe(self, df):
        if df is None:
            print("Warning: DataFrame is None in process_dataframe")
            return None

        try:
            df = self._normalize_columns(df)
            print(f"  [debug] Columns after normalization: {list(df.columns)}")

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