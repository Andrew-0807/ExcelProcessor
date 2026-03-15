# cardcec-transformation Specification

## Purpose
TBD - created by archiving change refactor-cardcec-module. Update Purpose after archive.
## Requirements
### Requirement: Parse POS Input File

The system SHALL read Excel files from the input directory, extracting fundamental columns like 'Grup incasare', 'Data', and 'Suma'.

#### Scenario: Valid input file processing

- **WHEN** a valid input file with expected columns is provided
- **THEN** the system successfully reads the rows for transformation

### Requirement: Generate 53-Column Ciel Output

The system SHALL map the parsed input to exactly a 53-column template format, preserving all specific column headers seamlessly.

#### Scenario: Output completeness

- **WHEN** transformation logic finishes executing
- **THEN** the ultimate output file contains exactly 53 columns in its header, matching template specification

### Requirement: Apply Static Accounting Logic

The system SHALL enforce explicit accounting mappings based on context (e.g., generating negative values for 'Valoare' from input value, specific GL account assignments such as Debit: 5311 and Credit: 51131). The `TVA la incasare` output column (AN, index 39) SHALL be set to `0`. The `Optiune TVA` output column (AE, index 30) SHALL be empty (`''`). The `Punct de lucru` for the Autoservire POS type SHALL be `'Autoservire'`.

#### Scenario: Value and GL Mapping

- **WHEN** a transaction is evaluated
- **THEN** `Valoare` equals the negative of the input value, and `Cont debit`/`Cont credit` are assigned their proper static values

#### Scenario: TVA la incasare is zero

- **WHEN** any row is transformed
- **THEN** the `TVA la incasare` column (AN) in the output contains `0`

#### Scenario: Optiune TVA is empty

- **WHEN** any row is transformed
- **THEN** the `Optiune TVA` column (AE) in the output is empty (`''`)

#### Scenario: Autoservire Punct de lucru

- **WHEN** a file is processed as Autoservire POS type
- **THEN** the `Punct de lucru` column contains `'Autoservire'` (not `'Autoservire AMT COMPLEX'`)

### Requirement: Filter Input Rows by Payment Type

The system SHALL drop any input row whose payment type column (`Tip Incasare` or `Explicatie`) does not match `card` or `cec` (case-insensitive). Only rows with an allowed payment type SHALL appear in the output file.

#### Scenario: Numerar rows are excluded

- **WHEN** an input file contains rows with `Tip Incasare` = `numerar`
- **THEN** those rows do not appear in the output file

#### Scenario: Card and Cec rows are included

- **WHEN** an input file contains rows with `Tip Incasare` = `card` or `cec` (any case)
- **THEN** all those rows appear in the output file

#### Scenario: Missing payment type column skips filter safely

- **WHEN** the input file has neither a `Tip Incasare` nor an `Explicatie` column
- **THEN** the processor does not crash and processes all rows as before

