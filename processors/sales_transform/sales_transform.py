import pandas as pd
import io
from typing import Optional


class SalesTransformProcessor:
    """
    Sales transformation processor that converts raw sales data into accounting import format.
    Filters out unwanted client types and maps to standard 48-column format.
    """

    def __init__(self):
        self.name = "Sales Transform"
        self.description = "Transform sales data to accounting import format"

    def process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform the input dataframe into final accounting import format.

        Args:
            df: Input dataframe with sales data

        Returns:
            Transformed dataframe in standard accounting format
        """
        try:
            # Expected columns in input data
            required_columns = [
                "data",
                "nr_iesire",
                "den_tip",
                "denumire",
                "den_gest",
                "cantitate",
                "pret",
                "valoare",
                "tert",
                "cod_fiscal",
                "tva_art",
                "tva",
            ]

            # Check if required columns exist
            missing_cols = [col for col in required_columns if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")

            # Filter out rows with CLIENT MARFA or CLIENT I.T.P in tert column
            df_filtered = df[
                ~df["tert"].str.contains(
                    "CLIENT MARFA|CLIENT  I.T.P", na=False, case=False
                )
            ].copy()

            # Format date from YYYY-MM-DD to YYYYMMDD
            df_filtered["data_formatted"] = pd.to_datetime(
                df_filtered["data"], errors="coerce"
            ).dt.strftime("%Y%m%d")

            # Create the final dataframe with all required columns
            final_columns = [
                "NR.linie",
                "Serie",
                "Numar document",
                "Data",
                "Data scadenta",
                "Cod tip Factura",
                "Nume partener",
                "Atribut fiscal",
                "Cod fiscal",
                "Nr.Reg.Com.",
                "Rezidenta",
                "Tara",
                "Judet",
                "Localitate",
                "Strada",
                "Numar",
                "Bloc",
                "Scara",
                "Etaj",
                "Apartament",
                "Cod postal",
                "Moneda",
                "Curs",
                "TVA la incasare",
                "Taxare inversa",
                "Factura de transport",
                "Cod agent",
                "Valoare neta totala",
                "Valoare TVA",
                "Total document",
                "Denumire articol",
                "Cantitate",
                "Tip miscare stoc",
                "Cont servicii",
                "Pret de lista",
                "Valoare fara tva",
                "Val TVA",
                "Valoare  cu TVa",
                "Optiune TVA",
                "Cota TVA",
                "Cod TVA SAFT",
                "Observatie",
                "Centre de cost",
            ]

            # Create empty dataframe with final columns
            df_final = pd.DataFrame(columns=final_columns)

            # Map columns from filtered dataframe to final format
            df_final["NR.linie"] = ""
            df_final["Serie"] = "FV"
            df_final["Numar document"] = df_filtered["nr_iesire"].astype(str)
            df_final["Data"] = df_filtered["data_formatted"]
            df_final["Data scadenta"] = df_filtered["data_formatted"]
            df_final["Cod tip Factura"] = ""
            df_final["Nume partener"] = df_filtered["tert"]
            df_final["Atribut fiscal"] = ""
            df_final["Cod fiscal"] = df_filtered["cod_fiscal"].astype(str)
            df_final["Nr.Reg.Com."] = ""
            df_final["Rezidenta"] = ""
            df_final["Tara"] = ""
            df_final["Judet"] = ""
            df_final["Localitate"] = ""
            df_final["Strada"] = ""
            df_final["Numar"] = ""
            df_final["Bloc"] = ""
            df_final["Scara"] = ""
            df_final["Etaj"] = ""
            df_final["Apartament"] = ""
            df_final["Cod postal"] = ""
            df_final["Moneda"] = "RON"
            df_final["Curs"] = ""
            df_final["TVA la incasare"] = ""
            df_final["Taxare inversa"] = ""
            df_final["Factura de transport"] = ""
            df_final["Cod agent"] = ""
            df_final["Valoare neta totala"] = ""
            df_final["Valoare TVA"] = ""
            df_final["Total document"] = ""
            df_final["Denumire articol"] = df_filtered["den_tip"]
            df_final["Cantitate"] = df_filtered["cantitate"]
            df_final["Tip miscare stoc"] = ""
            df_final["Cont servicii"] = ""
            df_final["Pret de lista"] = ""
            df_final["Valoare fara tva"] = df_filtered["valoare"]
            df_final["Val TVA"] = df_filtered["tva"]
            df_final["Valoare  cu TVa"] = ""
            df_final["Optiune TVA"] = "TAXABILE"
            df_final["Cota TVA"] = df_filtered["tva_art"]
            df_final["Cod TVA SAFT"] = ""
            df_final["Observatie"] = ""
            df_final["Centre de cost"] = ""

            print(f"Sales transformation complete!")
            print(f"Input rows: {len(df)}")
            print(f"Filtered rows: {len(df_filtered)}")
            print(f"Output columns: {len(df_final.columns)}")

            return df_final

        except Exception as e:
            raise Exception(f"Error processing sales data: {str(e)}")

    def get_supported_extensions(self) -> list:
        """Return list of supported file extensions."""
        return [".xlsx", ".xls", ".csv"]

    def validate_input(self, df: pd.DataFrame) -> tuple[bool, Optional[str]]:
        """Validate input dataframe format."""
        try:
            # Check for minimum required columns
            min_columns = ["data", "nr_iesire", "tert", "valoare"]
            missing = [col for col in min_columns if col not in df.columns]

            if missing:
                return False, f"Missing required columns: {', '.join(missing)}"

            # Check if dataframe has data
            if df.empty:
                return False, "Input dataframe is empty"

            return True, None

        except Exception as e:
            return False, f"Validation error: {str(e)}"
