## MODIFIED Requirements

### Requirement: Parse multi-header Excel input files

The system SHALL read all `.xlsx` files in `app/models/Borderou/In/` by first converting them to CSV via openpyxl, then parsing the CSV to dynamically detect data rows (first column is a valid integer). The system SHALL handle column layout variations by detecting column positions from the header row content rather than using fixed indices.

#### Scenario: FF1 file is parsed correctly

- **WHEN** the pipeline processes `Borderou_de_Vanzare_(Incasare)FF1.xlsx`
- **THEN** the system SHALL extract Nr_Doc_Z, Data, Total_Valoare, Taxabile_21_Baza_Impozitare, Taxabile_21_Val_TVA, Taxabile_11_Baza_Impozitare, Taxabile_11_Val_TVA, and Netaxabil_Baza_Impozitare from the appropriate columns detected via header keywords

#### Scenario: AUTOS file is parsed with different column offsets

- **WHEN** the pipeline processes `Borderou_de_Vanzare_(Incasare)AUTOS.xlsx`
- **THEN** the system SHALL correctly detect that Total_Valoare is at column index 5 (not 6) and Taxabile_21_Baza is at index 8 (not 9), and extract all fields accordingly

#### Scenario: DEPOZIT file is skipped when empty

- **WHEN** the pipeline processes `Borderou_de_Vanzare_(Incasare)DEPOZIT.xlsx` and it has no data rows
- **THEN** the system SHALL skip the file and log a message with no output produced

### Requirement: Generate correct 53-column XLSX output

The system SHALL produce one XLSX output file per processed input file, containing exactly 53 columns matching the reference header in `app/models/Borderou/Out/borderou - Borderou_de_Vanzare_(FF1).xlsx`.

#### Scenario: FF1 produces 53-column XLSX

- **WHEN** the pipeline processes the FF1 input file successfully
- **THEN** the output XLSX at `app/models/Borderou/Out/borderou - Borderou_de_Vanzare_(FF1).xlsx` SHALL have exactly 53 columns with headers matching the reference file

#### Scenario: Output has correct account values

- **WHEN** any input file (FF1, FF2, AUTOS, REST) is processed
- **THEN** each output row SHALL have `Cont banca = 5125`, `Cont tichete = 5328`, `Cont TVA = 4427`, `Cont casa = 5311`, and `Numerar` equal to `Total_Valoare - Netaxabil_Baza`

#### Scenario: TVA rows are ordered correctly

- **WHEN** an input file with N data rows is processed
- **THEN** the output SHALL contain 2N rows: first all N rows with `Cota TVA = 21` and `Cod TVA SAF-T = 310344`, then all N rows with `Cota TVA = 11` and `Cod TVA SAF-T = 310351`

### Requirement: Pattern-based file type detection

The system SHALL determine the correct Serie document, Cod depozit, Denumire articol, and Cont casa values from the input filename using case-insensitive pattern matching (longer patterns take priority).

#### Scenario: FF1 filename maps to correct values

- **WHEN** input filename contains "FF1" (case-insensitive)
- **THEN** `Serie document = "F"`, `Cod depozit = 3`, `Denumire articol = "ff 1"`, `Cont casa = 5311`

#### Scenario: FF2 filename maps to correct values

- **WHEN** input filename contains "FF 2" or "FF2" (case-insensitive)
- **THEN** `Serie document = "F"`, `Cod depozit = 3`, `Denumire articol = "FF 2"`, `Cont casa = 5311`

#### Scenario: AUTOS filename maps to correct values

- **WHEN** input filename contains "AUTOS" (case-insensitive)
- **THEN** `Serie document = "A"`, `Cod depozit = 1`, `Denumire articol = "autoservire"`, `Cont casa = 5311`

#### Scenario: REST filename maps to correct values

- **WHEN** input filename contains "REST" (case-insensitive)
- **THEN** `Serie document = "R"`, `Cod depozit = 2`, `Denumire articol = "restaurant"`, `Cont casa = 5311`

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

## REMOVED Requirements

### Requirement: Pipeline must not crash on import of to_csv module
**Reason**: The `to_csv.py` module is being removed entirely as part of this rewrite. CSV conversion is now handled inline within the pipeline.
**Migration**: No migration needed — the functionality is absorbed into `main.py`.
