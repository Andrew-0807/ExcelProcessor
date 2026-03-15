## ADDED Requirements

### Requirement: CSV-first Excel parsing
The system SHALL convert each input `.xlsx` file to an intermediate CSV representation using openpyxl (with `data_only=True`) before parsing data rows. The CSV SHALL be written to the `tmp/` directory and deleted after processing.

#### Scenario: Excel file is converted to CSV before parsing
- **WHEN** processing any input `.xlsx` file from `app/models/Borderou/In/`
- **THEN** the system SHALL create a temporary CSV file in the `tmp/` directory, parse it for data rows, and delete the temporary file after processing completes

### Requirement: Dynamic header and data row detection
The system SHALL detect data rows by scanning for rows where the first column is a valid integer (the Nr.Crt field). The system SHALL skip all header rows, repeated header rows mid-file, total/summary rows, and footer rows automatically.

#### Scenario: Standard file with 4-row header
- **WHEN** processing FF1, FF2, or REST input files
- **THEN** the system SHALL skip the first 4 rows (title + sub-headers) and start extracting data from row 5

#### Scenario: File with repeated header mid-file
- **WHEN** processing FF1 which has a repeated header block at rows 24-26
- **THEN** the system SHALL skip those repeated header rows and continue extracting data rows after them

#### Scenario: Total and footer rows are excluded
- **WHEN** the CSV contains rows starting with "TOTAL GENERAL" or "Intocmit"
- **THEN** the system SHALL exclude those rows from the data extraction

### Requirement: Column detection by keyword matching
The system SHALL identify numeric data columns by scanning the header rows for keywords: "Total Valoare", "Baza Impozitare", "Val. TVA", "Nr. Doc(Z)", and "Data". This allows the system to handle column layout variations (e.g., AUTOS having "Total Valoare" at a different index than standard files).

#### Scenario: Standard file column detection
- **WHEN** processing a standard layout file (FF1, FF2, REST)
- **THEN** the system SHALL correctly identify Total_Valoare at column index 6, Taxabile_21 Baza at index 9, Taxabile_21 TVA at index 10, Taxabile_11 Baza at index 11, Taxabile_11 TVA at index 12, Netaxabil Baza at index 18

#### Scenario: AUTOS file column detection
- **WHEN** processing the AUTOS file (Total Valoare at index 5)
- **THEN** the system SHALL correctly identify Total_Valoare at column index 5, Taxabile_21 Baza at index 8, Taxabile_21 TVA at index 10, Taxabile_11 Baza at index 11, Taxabile_11 TVA at index 12, Netaxabil Baza at index 18

### Requirement: Standardized intermediate data format
The system SHALL normalize all parsed input data into a standard intermediate format with fields: `Nr_Doc_Z`, `Data`, `Total_Valoare`, `Taxabile_21_Baza`, `Taxabile_21_TVA`, `Taxabile_11_Baza`, `Taxabile_11_TVA`, `Netaxabil_Baza`, regardless of the original column layout.

#### Scenario: All file types produce the same intermediate format
- **WHEN** any input file (FF1, FF2, AUTOS, REST) is parsed
- **THEN** the resulting intermediate data SHALL have exactly the same field names and structure, with numeric values as floats and dates as datetime objects

### Requirement: Empty files are skipped gracefully
The system SHALL detect input files with no data rows (like DEPOZIT) and skip them without error.

#### Scenario: DEPOZIT file is skipped
- **WHEN** processing DEPOZIT which contains only a title header and no data rows
- **THEN** the system SHALL skip the file, log a message, and produce no output file
