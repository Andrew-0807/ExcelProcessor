import re
from datetime import datetime
import pandas as pd
from loguru import logger
import os
from typing import Dict, Any, Optional, List, Tuple
from classes.excel_processor import ExcelProcessor

class ExcelDataExtractor:
    """
    A class for extracting and processing data from Excel files with different formats.

    This class handles various Excel file formats and extracts relevant data into a
    standardized structure, supporting multiple document types and processing styles.

    Attributes:
        excel_processor (ExcelProcessor): Handler for Excel file operations
        extracted_data (Dict): Dictionary containing the extracted and processed data
        columns (List[str]): List defining the order of columns in the output
    """

    # Define columns as a class attribute
    print("started etraction")
    columns = [
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
        "Valoare cu TVa",
        "Optiune TVA",
        "Cota TVA",
        "Cod TVA SAFT",
        "Observatie",
        "Centre de cost"
    ]

    def __init__(self):
        """Initialize the ExcelDataExtractor with necessary components."""
        self.excel_processor = ExcelProcessor()
        self.extracted_data = self._initialize_data_structure()

    def _initialize_data_structure(self) -> Dict[str, list]:
        """
        Initialize the data structure for storing extracted information.

        Returns:
            Dict[str, list]: Empty dictionary with predefined column headers
        """
        return {col: [] for col in self.columns}

    def process_files(self, input_dir: str = "C:/in/extract", output_dir: str = "C:/out/extract") -> None:
        """
        Process all Excel files in the input directory and save results to output directory.

        Args:
            input_dir (str): Path to input directory containing Excel files
            output_dir (str): Path where processed files will be saved
        """
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Processing files from {input_dir}")

        for file_name in os.listdir(input_dir):
            try:
                if not file_name.endswith(('.xlsx', '.xls')):
                    continue

                input_path = os.path.join(input_dir, file_name)
                df = self.excel_processor.load_excel(input_path)

                if df is not None:
                    # Add filename to DataFrame for reference
                    df.name = file_name
                    self.filename = file_name
                    doc_type = self._determine_document_type(file_name)
                    data = self.extract_data(df, doc_type)

                    # Verify and normalize data
                    self._normalize_data_lengths(data)

                    # Create DataFrame with specific column order
                    output_df = pd.DataFrame(data, columns=self.columns)

                    output_file = f"Restructured--{''.join(str(file_name).split('.')[:-1])}.xlsx"
                    output_path = os.path.join(output_dir, output_file)
                    self.excel_processor.save_to_excel(output_df, output_path)
                    logger.success(f"Successfully processed {file_name}")

                self.extracted_data = self._initialize_data_structure()

            except Exception as e:
                logger.error(f"Error processing {file_name}: {str(e)}")
                continue

    def _determine_document_type(self, file_name: str) -> str:
        """
        Determine document type from filename.

        Args:
            file_name (str): Name of the file

        Returns:
            str: Determined document type
        """
        # Improved patterns that handle more edge cases
        patterns = {
            "M1": r"(?:^|[\s_\-\.\(\)])M1(?:[\s_\-\.\(\)]|$)",  # Handles all separators including parentheses
            "M2": r"(?:^|[\s_\-\.\(\)])M2(?:[\s_\-\.\(\)]|$)",
            "M3": r"(?:^|[\s_\-\.\(\)])M3(?:[\s_\-\.\(\)]|$)", 
            "M4": r"(?:^|[\s_\-\.\(\)])M4(?:[\s_\-\.\(\)]|$)",
            "M5": r"(?:^|[\s_\-\.\(\)])M5(?:[\s_\-\.\(\)]|$)",
            "FF1": r"(?:^|[\s_\-\.\(\)])FF1(?:[\s_\-\.\(\)]|$)",
            "FF2": r"(?:^|[\s_\-\.\(\)])FF2(?:[\s_\-\.\(\)]|$)",
            "AMTA": r"(?:^|[\s_\-\.\(\)])AUTOSERVIRE(?:[\s_\-\.\(\)]|$)",  # Simple word matching works fine
            "AMTR": r"(?:^|[\s_\-\.\(\)])RESTAURANT(?:[\s_\-\.\(\)]|$)",
            "AMTD": r"(?:^|[\s_\-\.\(\)])DEPOZIT(?:[\s_\-\.\(\)]|$)",
            "FF": r"(?:^|[\s_\-\.\(\)])FAST(?:[\s_\-\.\(\)]|$)"  # Flexible spacing for FAST FOOD
        }

        file_name_upper = file_name.upper()
        for doc_type, pattern in patterns.items():
            if re.search(pattern, file_name_upper):
                return doc_type

        return "UNKNOWN"

    def extract_data(self, df: pd.DataFrame, type: str) -> Dict[str, list]:
        """
        Extract data from DataFrame based on document type.

        Args:
            df (pd.DataFrame): Input DataFrame containing the data
            type (str): Document type identifier

        Returns:
            Dict[str, list]: Processed data in standardized format
        """
        type_mapping = {
            "AMTA": "marfa autoservire",
            "AMTR": "restaurant",
            "AMTD": "depozit",
            "FF": "fast-food",
            "FF1": "fast-food 1",
            "FF2": "fast-food 2",
            "M1": "Marfa M1",
            "M2": "Marfa M2",
            "M3": "Marfa M3",
            "M4": "Materie prima M4",
            "M5": "Marfa M5",
            "UNKNOWN": ""
        }
        if type == "UNKNOWN":
            tipMarfa = "marfa"
        else:
            tipMarfa = type_mapping.get(type)
        print(type)
        try:
            for idx, row in df.iterrows():
                self._process_row(row, tipMarfa, idx + 1)

            self._normalize_data_lengths(self.extracted_data)
            return self.extracted_data

        except Exception as e:
            logger.error(f"Error in extract_data: {e}")
            return self._initialize_data_structure()

    def _process_row(self, row: pd.Series, tipMarfa: str, idx: int) -> None:
        """
        Process a single row of data using multiple processing styles.

        Args:
            row (pd.Series): Row data to process
            tipMarfa (str): Type of merchandise
            idx (int): Row index
        """
        success = False
        errors = []

        # Try each processing style in sequence
        processing_styles = [
            (self._process_row_style1, "Style 1"),
            (self._process_row_style2, "Style 2"),
            (self._process_row_style3, "Style 3")
        ]

        for process_func, style_name in processing_styles:
            try:
                process_func(row, tipMarfa)
                self.extracted_data["NR.linie"].append(str(idx))
                success = True
                # logger.debug(f"Successfully processed row {idx} using {style_name}")
                break
            except Exception as e:
                errors.append(f"{style_name}: {str(e)}")
                continue

        if not success:
            self._add_default_row(tipMarfa, idx)
            logger.warning(f"Using default values for row {idx}. Errors: {'; '.join(errors)}")

    def _add_default_row(self, tipMarfa: str, idx: int) -> None:
        """
        Add a row with default values when processing fails.

        Args:
            tipMarfa (str): Type of merchandise
            idx (int): Row index
        """
        # Add default values for required fields
        self.extracted_data["NR.linie"].append(str(idx))
        self.extracted_data["Denumire articol"].append(f"{tipMarfa} 0%")
        self.extracted_data["Optiune TVA"].append("TAXABILE")

        # Ensure all columns have a value
        for col in self.columns:
            if col not in ["NR.linie", "Denumire articol", "Optiune TVA"]:
                if col not in self.extracted_data:
                    self.extracted_data[col] = []
                if len(self.extracted_data[col]) < len(self.extracted_data["NR.linie"]):
                    self.extracted_data[col].append(self._get_default_value(col))

    def _process_row_style1(self, row: pd.Series, tipMarfa: str) -> None:
        """
        Process row using the first data style format.

        Args:
            row (pd.Series): Row data
            tipMarfa (str): Type of merchandise
        """
        try:
            self._fill_basic_data(
                row.get("Numar Factura", ""),
                str(row.get('Data Document', "")),
                row.get('Valoare Achizitie', 0),
                row.get('Nume', ""),
                str(row.get('CUI/CNP', "")),
                row,
                tipMarfa,
                'TVA Achizitie'
            )
        except Exception as e:
            logger.error(f"Error in process_row_style1: {str(e)}")
            raise

    def _process_row_style2(self, row: pd.Series, tipMarfa: str) -> None:
        """
        Process row using the second data style format.

        Args:
            row (pd.Series): Row data
            tipMarfa (str): Type of merchandise
        """
        try:
            self._fill_basic_data(
                row.get("Numar Factura", ""),
                str(row.get('Data Factura', "")),
                row.get('ValoareAchizitie Fara TVA', 0),
                row.get('Partener', ""),
                str(row.get('Cod Fiscal Partener', "")),
                row,
                tipMarfa,
                'Cota TVA B'
            )
        except Exception as e:
            logger.error(f"Error in process_row_style2: {str(e)}")
            raise

    def _process_row_style3(self, row: pd.Series, tipMarfa: str) -> None:
        """
        Process row using the NIR data style format.

        Args:
            row (pd.Series): Row data
            tipMarfa (str): Type of merchandise
        """
        try:
            self._fill_basic_data(
                row.get("NIR", ""),
                str(row.get('Data NIR', "")),
                row.get('Valoare', 0),
                row.get('Furnizor', ""),
                str(row.get('CUI', "")),
                row,
                tipMarfa,
                '% TVA Ach'
            )
        except Exception as e:
            logger.error(f"Error in process_row_style3: {str(e)}")
            raise

    def _fill_basic_data(self, doc_num: str, date: str, price: float,
                        partner: str, code: str, row: pd.Series,
                        tipMarfa: str, tva_field: str) -> None:
        """
        Fill basic data fields with provided values.

        Args:
            doc_num (str): Document number
            date (str): Document date
            price (float): Price value
            partner (str): Partner name
            code (str): Fiscal code
            row (pd.Series): Complete row data
            tipMarfa (str): Type of merchandise
            tva_field (str): TVA field identifier
        """
        data = self._convert_date(date)
        code = str(code) if code else ""

        base_data = {
            "Numar document": str(doc_num or ""),
            "Data": str(data or ""),
            "Data scadenta": str(data or ""),
            "Pret de lista": str(price or "0"),
            "Nume partener": str(partner or ""),
            "Cod fiscal": code.replace("RO", "").replace("RO ", ""),
            "Cota TVA": str(row.get(tva_field, "0")),
            "Moneda": "RON",
            "Cantitate": "1"
        }

        for key, value in base_data.items():
            if key not in self.extracted_data:
                self.extracted_data[key] = []
            self.extracted_data[key].append(value)

        self._process_tva_logic(code, row, tipMarfa, tva_field)

    def _convert_date(self, date_value: Any) -> str:
        if date_value is None:
            return ""

        date_value = date_value.split(" ")
        date_value = date_value[0].split("-")

        return "".join(date_value)



    def _process_tva_logic(self, code: str, row: pd.Series,
                          tipMarfa: str, tva_field: str) -> None:
        """
        Process TVA logic and fill related fields.

        Args: 
            code (str): Fiscal code
            row (pd.Series): Row data
            tipMarfa (str): Type of merchandise
            tva_field (str): TVA field identifier
        """
        try:
            tva_value = int(str(row.get(tva_field, "0")).replace(",", ".") or "0")
            if not str(code).startswith("RO") and tva_value == 0:
                procent_tva = int(str(row.get('Procent TVA', row.get('% TVA Ach', "0"))).replace(",", ".") or "0")
                article = f"{tipMarfa.strip()} {procent_tva}%"
                tva_option = "SCUTITE"
            elif tva_value == 0:
                article = "SGR"
                tva_option = "SCUTITE"
            else:
                if "AMT" in self.filename:
                    article = f"{tipMarfa.strip()}"
                    tva_option = "TAXABILE"
                else:
                    article = f"{tipMarfa.strip()} {tva_value}%"
                    tva_option = "TAXABILE"

            if "Denumire articol" not in self.extracted_data:
                self.extracted_data["Denumire articol"] = []
            self.extracted_data["Denumire articol"].append(article)

            if "Optiune TVA" not in self.extracted_data:
                self.extracted_data["Optiune TVA"] = []
            self.extracted_data["Optiune TVA"].append(tva_option)
        except Exception as e:
            logger.error(f"Error in _process_tva_logic: {e}")
            if "Denumire articol" not in self.extracted_data:
                self.extracted_data["Denumire articol"] = []
            self.extracted_data["Denumire articol"].append(f"{tipMarfa.strip()} 0%")

            if "Optiune TVA" not in self.extracted_data:
                self.extracted_data["Optiune TVA"] = []
            self.extracted_data["Optiune TVA"].append("TAXABILE")

    def _get_default_value(self, column_name: str) -> Any:
        """
        Get default value for a specific column.

        Args:
            column_name (str): Name of the column

        Returns:
            Any: Appropriate default value based on column type
        """
        defaults = {
            "Cantitate": "1",
            "Pret de lista": "0",
            "Cota TVA": "0",
            "Moneda": "RON",
            "Optiune TVA": "TAXABILE",
            "Serie": "",
            "Observatie": "",
            "Centre de cost": ""
        }
        return defaults.get(column_name, "")

    def _normalize_data_lengths(self, data: Dict[str, list]) -> None:
        """
        Ensure all data lists have the same length and all columns are present.

        Args:
            data (Dict[str, list]): Data dictionary to normalize
        """
        if not data:
            return

        # Ensure all columns from self.columns are in data
        for col in self.columns:
            if col not in data:
                data[col] = []

        # Find the maximum length of any list in the data
        max_length = max(len(values) for values in data.values()) if data.values() else 0

        # Extend all lists to the maximum length
        for key in data:
            current_length = len(data[key])
            if current_length < max_length:
                default_value = self._get_default_value(key)
                data[key].extend([default_value] * (max_length - current_length))

    def process_dataframe(self, df):
        """Process the DataFrame and return the modified DataFrame"""
        print("Processing DataFrame with ExcelDataExtractor")
        # Set the filename attribute for use in other methods
        self.filename = getattr(df, 'name', 'UNKNOWN')
        # Use the document type detection logic if possible, else default to UNKNOWN
        doc_type = self._determine_document_type(self.filename)
        data = self.extract_data(df, doc_type)
        self._normalize_data_lengths(data)
        # Ensure all columns are present, even if empty
        output_df = pd.DataFrame(data, columns=self.columns)
        print("Extraction finished")
        return output_df

def main():
    """Main function to run the Excel data extraction process."""
    try:
        extractor = ExcelDataExtractor()
        extractor.process_files()
        logger.success("Processing completed successfully")
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")

if __name__ == "__main__":
    main()
