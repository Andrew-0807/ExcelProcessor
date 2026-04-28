import pandas as pd
from pathlib import Path
from loguru import logger


class ExcelProcessor:
    """Base class for Excel file processing with common functionality."""

    def __init__(self, input_folder="in", output_folder="out"):
        self.input_folder = input_folder
        self.output_folder = output_folder

    def create_folders(self):
        Path(self.output_folder).mkdir(parents=True, exist_ok=True)

    def load_excel(self, file_path):
        try:
            df = pd.read_excel(file_path)
            return df
        except Exception as e:
            try:
                df = pd.read_excel(file_path, engine="openpyxl")
                return df
            except Exception as e:
                logger.error(f"Error loading Excel file {file_path}: {str(e)}")
                return None

    def save_to_excel(self, df: pd.DataFrame, output_path: str):
        try:
            with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name="Sheet1")
                workbook = writer.book
                worksheet = writer.sheets["Sheet1"]
                for i, col in enumerate(df.columns):
                    column_width = max(df[col].astype(str).map(len).max(), len(col))
                    worksheet.set_column(i, i, column_width + 2)
            logger.success(f"Successfully saved Excel file to {output_path}")
        except Exception as e:
            logger.error(f"Error saving Excel file to {output_path}: {str(e)}")
            raise