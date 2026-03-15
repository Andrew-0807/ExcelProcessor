# borderou-pipeline Specification

## Purpose
TBD - created by archiving change fix-borderou-53-columns. Update Purpose after archive.
## Requirements
### Requirement: Parse multi-header Excel input files

The system SHALL read all `.xlsx` files in `models/in/` by opening them with openpyxl, skipping the first 4 rows (merged title + sub-headers), and extracting data rows starting from row 5 onward.

#### Scenario: FF1 file is parsed correctly

- **WHEN** the pipeline processes `Borderou_de_Vanzare_(Incasare)FF1.xlsx`
- **THEN** the system SHALL extract Nr_Doc_Z from column index 2, Data from index 3, Total_Valoare from index 6, Taxabile_21_Baza_Impozitare from index 9, Taxabile_21_Val_TVA from index 10, Taxabile_11_Baza_Impozitare from index 11, Taxabile_11_Val_TVA from index 12, and Netaxabil_Baza_Impozitare from index 18

#### Scenario: AUTOS file is parsed with different column offsets

- **WHEN** the pipeline processes `Borderou_de_Vanzare_(Incasare)AUTOS.xlsx`
- **THEN** the system SHALL extract Total_Valoare from column index 5, Taxabile_21_Baza_Impozitare from index 8, Taxabile_21_Val_TVA from index 10, Taxabile_11_Baza_Impozitare from index 11, Taxabile_11_Val_TVA from index 12, and Netaxabil_Baza_Impozitare from index 18

#### Scenario: DEPOZIT file is skipped when empty

- **WHEN** the pipeline processes `Borderou_de_Vanzare_(Incasare)DEPOZIT.xlsx` and it has no data rows after the 4-row header
- **THEN** the system SHALL skip the file and log a warning with no output produced

### Requirement: Generate correct 53-column XLSX output

The system SHALL produce one XLSX output file per processed input file, containing exactly 53 columns matching the reference header in `models/out/borderou - Borderou_de_Vanzare_(FF1).xlsx`.

#### Scenario: FF1 produces 53-column XLSX

- **WHEN** the pipeline processes the FF1 input file successfully
- **THEN** the output XLSX at `models/out/borderou - Borderou_de_Vanzare_(FF1).xlsx` SHALL have exactly 53 columns with headers matching the reference file

#### Scenario: Output has correct account values

- **WHEN** any input file (FF1, FF2, AUTOS, REST) is processed
- **THEN** each output row SHALL have `Cont banca = 5125`, `Cont tichete = 5328`, and `Numerar` equal to the positive value of `total_valoare_fata_netaxabil`

#### Scenario: TVA rows are ordered correctly

- **WHEN** an input file with N data rows is processed
- **THEN** the output SHALL contain 2N rows: first all N rows with `Cota TVA = 21`, then all N rows with `Cota TVA = 11`

### Requirement: Pattern-based file type detection

The system SHALL determine the correct Serie document, Cod depozit, Denumire articol, and Cont casa values from the input filename using case-insensitive pattern matching (longer patterns take priority).

#### Scenario: FF1 filename maps to correct values

- **WHEN** input filename contains "FF1" (case-insensitive)
- **THEN** `Serie document = "F"`, `Cod depozit = 3`, `Denumire articol = "ff 1"`, `Cont casa = 5311`

#### Scenario: AUTOS filename maps to correct values

- **WHEN** input filename contains "AUTOS" (case-insensitive)
- **THEN** `Serie document = "A"`, `Cod depozit = 1`, `Denumire articol = "autoservire"`, `Cont casa = 5311`

### Requirement: Output file naming convention

The system SHALL name output files as `borderou - Borderou_de_Vanzare_(XX).xlsx` where XX is the type identifier derived from the filename pattern.

#### Scenario: FF1 output filename

- **WHEN** processing an FF1 input file
- **THEN** the output file SHALL be named `borderou - Borderou_de_Vanzare_(FF1).xlsx`

#### Scenario: FF2 output filename

- **WHEN** processing an FF2 input file
- **THEN** the output file SHALL be named `borderou - Borderou_de_Vanzare_(FF2).xlsx`

#### Scenario: AUTOS output filename

- **WHEN** processing an AUTOS input file
- **THEN** the output file SHALL be named `borderou - Borderou_de_Vanzare_(AUTOS).xlsx`

#### Scenario: REST output filename

- **WHEN** processing a REST input file
- **THEN** the output file SHALL be named `borderou - Borderou_de_Vanzare_(REST).xlsx`

### Requirement: Pipeline must not crash on import of to_csv module

The `to_csv.py` module SHALL NOT execute any file system operations at module import time.

#### Scenario: Importing to_csv does not trigger file I/O

- **WHEN** any Python file imports `from app.modules.borderou.to_csv import excel_to_csv`
- **THEN** no file system operations SHALL occur and no errors SHALL be raised

