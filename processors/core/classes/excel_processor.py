import pandas as pd
import re
import xlwings as xw
from datetime import datetime
from pathlib import Path
from rich import print
from loguru import logger


class ExcelProcessor:
    """Base class for Excel file processing with common functionality"""

    def __init__(self, input_folder="in", output_folder="out"):
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.app = None
        self.wb = None
        self.ws = None

    def initialize_excel(self):
        try:
            print("Attempting to launch Excel via COM...")
            import xlwings as xw
            self.app = xw.App(visible=False)
            self.wb = self.app.books.add()
            print("Excel launched and workbook created successfully.")
            self.ws = self.wb.sheets[0]
            return True
        except Exception as e:
            print(f"Excel initialization encountered an error: {e}")
            return False

    def cleanup(self):
        """Clean up Excel application"""
        if self.app:
            self.app.quit()
            print("Excel application closed successfully.")

    def create_folders(self):
        """Create output folder if it doesn't exist"""
        Path(self.output_folder).mkdir(parents=True, exist_ok=True)

    def open_workbook(self, input_path):
        """Open an Excel workbook"""
        try:
            self.wb = self.app.books.open(input_path)
            self.ws = self.wb.sheets[0]
            return True
        except Exception as e:
            print(f"[red]Error opening workbook {input_path}: {str(e)}[/red]")
            return False

    def save_and_close(self, output_path):
        """Save and close the current workbook using xlwings"""
        try:
            if self.wb:
                self.wb.save(output_path)
                self.wb.close()
                print(f"[green]Saved processed file to {output_path}[/green]")
        except Exception as e:
            print(f"[red]Error saving file: {str(e)}[/red]")
            if self.wb:
                self.wb.close()

    def load_excel(self, file_path):
        try:
            df = pd.read_excel(file_path)
            return df
        except Exception as e:
            try:
                df = pd.read_excel(file_path, engine='openpyxl')
                return df
            except Exception as e:
                logger.error(f"Error loading Excel file {file_path}: {str(e)}")
                return None

    def extract_type(self, file_name : str):
        pattern = r"_(AMTA|AMTR|AMTD|FF|M[4-6])_"
        try:
            match = re.search(pattern, file_name.upper())
            if match:
                return match.group(1)
            else:
                logger.warning(f"Could not extract type from filename: {file_name}")
                return "UNKNOWN"
        except Exception as e:
            logger.error(f"Error extracting type from filename {file_name}: {str(e)}")
            return "UNKNOWN"

    def save_to_excel(self, df: pd.DataFrame, output_path: str):
        try:
            # Use pandas to save the DataFrame
            with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Sheet1')
                workbook = writer.book
                worksheet = writer.sheets['Sheet1']

                for i, col in enumerate(df.columns):
                    column_width = max(df[col].astype(str).map(len).max(), len(col))
                    worksheet.set_column(i, i, column_width + 2)

            logger.success(f"Successfully saved Excel file to {output_path}")

        except Exception as e:
            logger.error(f"Error saving Excel file to {output_path}: {str(e)}")
            raise

    def format_date_column(self, column_letter: str, start_row: int):
        """Format dates in specified column to YYYYMMDD"""
        try:
            # Safer way to get last used row in the sheet
            last_row = self.ws.used_range.last_cell.row

            date_range = self.ws.range(f"{column_letter}{start_row}:{column_letter}{last_row}")

            for cell in date_range:
                if cell.value is not None:
                    try:
                        formatted_date = self.format_date(cell.value)
                        cell.clear_contents()
                        cell.number_format = 'General'
                        cell.value = formatted_date
                    except Exception as e:
                        print(f"[red]Failed to format value '{cell.value}' at {cell.address}: {e}[/red]")

            print(f"[green]Date formatting completed for column {column_letter}[/green]")
            return last_row

        except Exception as e:
            print(f"[red]Error formatting dates: {str(e)}[/red]")
            return None



    @staticmethod
    def format_date(date_value):
        """Convert date to YYYYMMDD format"""
        if date_value is None:
            return None

        try:
            if isinstance(date_value, datetime):
                return date_value.strftime('%Y%m%d')

            if isinstance(date_value, str):
                date_value = date_value.strip()
                formats_to_try = [
                    '%d/%m/%Y',    # DD/MM/YYYY
                    '%d-%m-%Y',    # DD-MM-YYYY
                    '%Y-%m-%d',    # YYYY-MM-DD
                    '%d.%m.%Y',    # DD.MM.YYYY
                    '%Y/%m/%d',    # YYYY/MM/DD
                    '%m/%d/%Y',    # MM/DD/YYYY
                    '%d-%b-%Y',    # DD-MMM-YYYY (14-Feb-2024)
                    '%d-%B-%Y',    # DD-MMMM-YYYY
                    '%d %b %Y',    # DD MMM YYYY
                    '%d %B %Y'     # DD MMMM YYYY
                ]

                for date_format in formats_to_try:
                    try:
                        return datetime.strptime(date_value, date_format).strftime('%Y%m%d')
                    except ValueError:
                        continue

            if isinstance(date_value, (int, float)):
                try:
                    return xw.utils.datetime_from_excel_date(date_value).strftime('%Y%m%d')
                except:
                    return date_value

            return date_value

        except Exception as e:
            print(f"[red]Error formatting date {date_value}: {str(e)}[/red]")
            return date_value

    def sort_column(self, column_letter, start_row, has_header=True):
        """Sort column alphabetically"""
        try:
            last_row = self.ws.range(f'{column_letter}{start_row}').end('down').row
            last_col = self.ws.used_range.last_cell.column
            last_col_letter = chr(64 + last_col) if last_col <= 26 else chr(64 + last_col//26) + chr(64 + last_col%26)

            data_range = self.ws.range(f'A{start_row}:{last_col_letter}{last_row}')
            header_type = 1 if has_header else 2

            data_range.api.Sort(
                Key1=self.ws.range(f'{column_letter}{start_row}').api,
                Order1=1,
                Header=header_type,
                OrderCustom=1,
                MatchCase=False,
                Orientation=1
            )
            print(f"[green]Column {column_letter} sorted successfully[/green]")
            return last_row
        except Exception as e:
            print(f"[red]Error sorting column: {str(e)}[/red]")
            return None

    def get_last_row(self, column_letter, start_row, max_rows=10000):
        row = start_row
        while row < start_row + max_rows:
            if self.ws.range(f"{column_letter}{row}").value is None:
                return row - 1
            row += 1
        return row - 1


    def save_all_processed_files(self, processed_files):
        """Save all processed DataFrames to the output folder"""
        for file_name, df in processed_files.items():
            output_path = os.path.join(self.output_folder, f"Processed--{file_name}")
            self.save_to_excel(df, output_path)
            print(f"Saved processed file: {output_path}")

    def process_files(self):
        """Main method to process all files, including old files"""
        self.create_folders()
        processed_files = {}

        for file in os.listdir(self.input_folder):
            if file.endswith('.xlsx'):
                input_path = os.path.join(self.input_folder, file)
                # Check if the file has been processed before
                if not self.is_file_processed(input_path):
                    print(f"Processing file: {file}")
                    df = self.load_excel(input_path)

                    if df is None:
                        print(f"Failed to load file: {file}")
                        continue

                    df = self.process_dataframe(df)
                    if df is not None:
                        processed_files[file] = df

        # Save all processed files
        self.save_all_processed_files(processed_files)

    def is_file_processed(self, file_path):
        """Check if a file has been processed based on its modification date"""
        # Implement logic to check if the file has been processed
        # For example, compare the modification date with a stored date
        return False  # Placeholder logic
