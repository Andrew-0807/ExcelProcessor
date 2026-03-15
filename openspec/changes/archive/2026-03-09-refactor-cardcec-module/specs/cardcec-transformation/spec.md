## ADDED Requirements

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

The system SHALL enforce explicit accounting mappings based on context (e.g., generating negative values for 'Valoare' from 'Suma', specific GL account assignments such as Debit: 5311 and Credit: 51131).

#### Scenario: Value and GL Mapping

- **WHEN** a transaction is evaluated
- **THEN** 'Valoare' equals the negative 'Suma', and 'Cont debit'/'Cont credit' are assigned their proper static values
