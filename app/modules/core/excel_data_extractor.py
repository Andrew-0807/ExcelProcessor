import re
import pandas as pd
import logging
from app.log import info as print  # debug chatter; silent unless MOM_VERBOSE=1
logger = logging.getLogger(__name__)


class ExcelDataExtractor:
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
        "Centre de cost",
    ]

    def __init__(self):
        self.extracted_data = self._initialize_data_structure()

    def _initialize_data_structure(self):
        return {col: [] for col in self.columns}

    def _determine_document_type(self, file_name: str) -> str:
        patterns = {
            "M1": r"(?:^|[\s_\-\.\(\)])M1(?:[\s_\-\.\(\)]|$)",
            "M2": r"(?:^|[\s_\-\.\(\)])M2(?:[\s_\-\.\(\)]|$)",
            "M3": r"(?:^|[\s_\-\.\(\)])M3(?:[\s_\-\.\(\)]|$)",
            "M4": r"(?:^|[\s_\-\.\(\)])M4(?:[\s_\-\.\(\)]|$)",
            "M5": r"(?:^|[\s_\-\.\(\)])M5(?:[\s_\-\.\(\)]|$)",
            "FF1": r"(?:^|[\s_\-\.\(\)])FF1(?:[\s_\-\.\(\)]|$)",
            "FF2": r"(?:^|[\s_\-\.\(\)])FF2(?:[\s_\-\.\(\)]|$)",
            "AMTA": r"(?:^|[\s_\-\.\(\)])AUTOSERVIRE(?:[\s_\-\.\(\)]|$)",
            "AMTR": r"(?:^|[\s_\-\.\(\)])RESTAURANT(?:[\s_\-\.\(\)]|$)",
            "AMTD": r"(?:^|[\s_\-\.\(\)])DEPOZIT(?:[\s_\-\.\(\)]|$)",
            "FF": r"(?:^|[\s_\-\.\(\)])FAST(?:[\s_\-\.\(\)]|$)",
        }
        file_name_upper = file_name.upper()
        for doc_type, pattern in patterns.items():
            if re.search(pattern, file_name_upper):
                return doc_type
        return "UNKNOWN"

    def extract_data(self, df: pd.DataFrame, doc_type: str):
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
            "UNKNOWN": "",
        }
        tipMarfa = type_mapping.get(doc_type, "marfa") if doc_type != "UNKNOWN" else "marfa"
        print(doc_type)
        try:
            for idx, row in df.iterrows():
                self._process_row(row, tipMarfa, idx + 1)
            self._normalize_data_lengths(self.extracted_data)
            return self.extracted_data
        except Exception as e:
            logger.error(f"Error in extract_data: {e}")
            return self._initialize_data_structure()

    def _process_row(self, row: pd.Series, tipMarfa: str, idx: int) -> None:
        success = False
        errors = []
        for process_func, style_name in [
            (self._process_row_style1, "Style 1"),
            (self._process_row_style2, "Style 2"),
            (self._process_row_style3, "Style 3"),
        ]:
            try:
                process_func(row, tipMarfa)
                self.extracted_data["NR.linie"].append(str(idx))
                success = True
                break
            except Exception as e:
                errors.append(f"{style_name}: {str(e)}")
                continue

        if not success:
            self._add_default_row(tipMarfa, idx)
            logger.warning(f"Using default values for row {idx}. Errors: {'; '.join(errors)}")

    def _add_default_row(self, tipMarfa: str, idx: int) -> None:
        self.extracted_data["NR.linie"].append(str(idx))
        self.extracted_data["Denumire articol"].append(f"{tipMarfa} 0%")
        self.extracted_data["Optiune TVA"].append("TAXABILE")
        for col in self.columns:
            if col not in ["NR.linie", "Denumire articol", "Optiune TVA"]:
                if col not in self.extracted_data:
                    self.extracted_data[col] = []
                if len(self.extracted_data[col]) < len(self.extracted_data["NR.linie"]):
                    self.extracted_data[col].append(self._get_default_value(col))

    def _process_row_style1(self, row: pd.Series, tipMarfa: str) -> None:
        self._fill_basic_data(
            row.get("Numar Factura", ""),
            str(row.get("Data Document", "")),
            row.get("Valoare Achizitie", 0),
            row.get("Nume", ""),
            str(row.get("CUI/CNP", "")),
            row,
            tipMarfa,
            "TVA Achizitie",
        )

    def _process_row_style2(self, row: pd.Series, tipMarfa: str) -> None:
        self._fill_basic_data(
            row.get("Numar Factura", ""),
            str(row.get("Data Factura", "")),
            row.get("ValoareAchizitie Fara TVA", 0),
            row.get("Partener", ""),
            str(row.get("Cod Fiscal Partener", "")),
            row,
            tipMarfa,
            "Cota TVA B",
        )

    def _process_row_style3(self, row: pd.Series, tipMarfa: str) -> None:
        self._fill_basic_data(
            row.get("NIR", ""),
            str(row.get("Data NIR", "")),
            row.get("Valoare", 0),
            row.get("Furnizor", ""),
            str(row.get("CUI", "")),
            row,
            tipMarfa,
            "% TVA Ach",
        )

    def _fill_basic_data(
        self, doc_num, date, price, partner, code, row, tipMarfa, tva_field
    ) -> None:
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
            "Cantitate": "1",
        }
        for key, value in base_data.items():
            if key not in self.extracted_data:
                self.extracted_data[key] = []
            self.extracted_data[key].append(value)
        self._process_tva_logic(code, row, tipMarfa, tva_field)

    def _convert_date(self, date_value) -> str:
        if date_value is None:
            return ""
        return pd.to_datetime(date_value).strftime("%Y%m%d")

    def _process_tva_logic(self, code, row, tipMarfa, tva_field) -> None:
        try:
            tva_value = int(str(row.get(tva_field, "0")).replace(",", ".") or "0")
            if tva_value == 0:
                article = "SGR"
                tva_option = "SCUTITE"
            else:
                if "AMT" in self.filename:
                    article = f"{tipMarfa.strip()}"
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

    def _get_default_value(self, column_name):
        defaults = {
            "Cantitate": "1",
            "Pret de lista": "0",
            "Cota TVA": "0",
            "Moneda": "RON",
            "Optiune TVA": "TAXABILE",
            "Serie": "",
            "Observatie": "",
            "Centre de cost": "",
        }
        return defaults.get(column_name, "")

    def _normalize_data_lengths(self, data) -> None:
        if not data:
            return
        for col in self.columns:
            if col not in data:
                data[col] = []
        max_length = max((len(v) for v in data.values()), default=0)
        for key in data:
            if len(data[key]) < max_length:
                data[key].extend([self._get_default_value(key)] * (max_length - len(data[key])))

    def process_dataframe(self, df):
        print("Processing DataFrame with ExcelDataExtractor")
        self.filename = getattr(df, "name", "UNKNOWN")
        doc_type = self._determine_document_type(self.filename)
        data = self.extract_data(df, doc_type)
        self._normalize_data_lengths(data)
        output_df = pd.DataFrame(data, columns=self.columns)
        print("Extraction finished")
        return output_df