import os
import sys
import xlwings as xw  # Import xlwings directly
import pandas as pd  # Import pandas

# Assuming ExcelProcessor is in a separate file (excel_processor.py)
# If it's in the same file, you don't need this path manipulation
# sys.path.append(os.path.abspath(r'D:\Programming\Python\MomAutomations'))
from classes.excel_processor import ExcelProcessor  # Import the ExcelProcessor class

class ValoareMinus(ExcelProcessor):
    def __init__(self):
        super().__init__()
        self.input_folder = "C:/in/minus"
        self.output_folder = "C:/out/minus"

    @staticmethod
    def col_index_to_letter(index):
        """Convert a column index (1-based) to Excel letter (e.g., 1 -> 'A')"""
        result = ''
        while index:
            index, remainder = divmod(index - 1, 26)
            result = chr(65 + remainder) + result
        return result

    def process_dataframe(self, df):
        """Process the DataFrame and return the modified DataFrame"""
        # Print the columns to verify the available columns
        print("Available columns:", df.columns)

        
        # Format the date column "Data Document"
        
        date_column = "Data Ultimei Incasari"
        if date_column in df.columns:
            df[date_column] = pd.to_datetime(df[date_column], errors='coerce').dt.strftime('%Y%m%d')
            print(f"Formatted date column: {date_column}")
        else:
            print(f"Error: '{date_column}' does not exist in the DataFrame.")
            raise KeyError(f"'{date_column}' not found in DataFrame columns.")

        # Remove the multiplication and rounding for "% TVA VANZARE" column
        tva_column = "Valoare"
        if tva_column in df.columns:
            df[tva_column] = df[tva_column].apply(lambda x: -x)
        else:
            print(f"Error: '{tva_column}' does not exist in the DataFrame.")
            raise KeyError(f"'{tva_column}' not found in DataFrame columns.")

        return df

    def process_files(self):
        """Process all Cu Minus files in the input folder"""
        # Initialize Excel and create folders only once at the beginning
        self.initialize_excel()
        self.create_folders()

        try:
            for file in os.listdir(self.input_folder):
                if file.endswith('.xlsx'):
                    input_path = os.path.join(self.input_folder, file)
                    output_path = os.path.join(self.output_folder, "Minus--" + file)

                    if self.open_workbook(input_path):
                        self.process_single_file()  # Process the file
                        self.save_and_close(output_path)  # Save and close after processing
        except Exception as e:
            print(f"An error occurred: {e}")  # Handle errors during file processing
        finally:
            self.cleanup()  # Ensure cleanup happens even if there's an error

    def find_date_column(self, header_row):
        # Find all columns that contain the word "data" in row 3
        data_columns = []
        columns_name_Date = "Data Ultimei Incasari".lower()
        for col in range(1, self.ws.used_range.columns.count + 1):
            cell = self.ws.cells(header_row, col)
            if isinstance(cell.value, str) and columns_name_Date in cell.value.strip().lower():
                col_letter = self.col_index_to_letter(col)
                data_columns.append(col_letter)
                print("Column date found")
        return data_columns

    def process_single_file(self):
        """Process a single CuMinus file"""
        start_row = 2
        header_row = 1
        data_columns = self.find_date_column(header_row)

        total_valoare_cols = []



        # Format date columns
        for col_letter in data_columns:
            self.format_date_column(col_letter, start_row)
        columns_name = "Valoare".lower()
        # Find all columns that contain "Total Valoare" in row 3
        for col in range(1, self.ws.used_range.columns.count + 1):
            cell_value = self.ws.cells(header_row, col).value
            if cell_value and isinstance(cell_value, str) and columns_name in cell_value.strip().lower():
                total_valoare_cols.append(self.col_index_to_letter(col))
                print("Column Val found")


        # Process each "Total Valoare" column
        for col_letter in total_valoare_cols:
            last_row = self.get_last_row(col_letter, start_row)  # Get last row for current column

            try:
                for row_num in range(start_row, last_row + 1):
                    cell = self.ws.cells(row_num, col_letter)
                    # print(f"Row {row_num} | Original value: {cell.value}")
                    if cell.value is not None and isinstance(cell.value, (int, float)):
                        cell.value = -cell.value
            except Exception as e:
                # print(f"Error at row {row_num}, col {col_letter}: {e}")
                pass


if __name__ == "__main__":
    processor = ValoareMinus()
    processor.process_files()
