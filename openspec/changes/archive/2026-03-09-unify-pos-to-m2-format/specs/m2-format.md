# Spec: M2 Uniform Transformation

## Context
All POS data (FF1, FF2, M1, M2, Restaurant, etc.) needs to be formatted into the exact 22-column structure of `M2_template.csv`.

## Requirements

### Requirement: Uniform 22-Column Output
All POS transformations must result in a CSV with exactly 22 columns.

- **WHEN** any valid POS file is processed
- **THEN** the output file must contain exactly 22 columns
- **AND** the headers must consist of two rows matching the template exactly.

### Requirement: M2 Dual-Header Structure
The output file must recreate the exact dual-header system found in `M2_template.csv`.

- **WHEN** initializing the output CSV
- **THEN** Row 1 must contain: `Unnamed: 0,Denumire,Nr. Doc(Z),Data,Unnamed: 4,Total Valoare,Scutit cu drept de reducere,Scutit fara drept de reducere,Taxabile,Unnamed: 9,0.21,Taxabile.1,Unnamed: 12,0.11,Nefolosit,Unnamed: 15,Nefolosit.1,Unnamed: 17,Netaxabil,Unnamed: 19,Unnamed: 20,0`
- **AND** Row 2 must contain: `,,,,,,,,Baza Impozitare,,Val. TVA,Baza Impozitare,Val. TVA,,Baza Impozitare,Val. TVA,Baza Impozitare,Val. TVA,Baza Impozitare,Val. TVA,,`

### Requirement: Numeric Calculation and Placement
Gross transaction values must be broken down into Net Value (Baza Impozitare) and TVA (Val. TVA) and placed in specific columns.

- **WHEN** processing a transaction row with a total value
- **THEN** `Baza Impozitare` (Net) is calculated (e.g., Total / 1.19) and placed in Column Index 8 (0-indexed)
- **AND** `Val. TVA` is calculated (Total - Net) and placed in Column Index 9
- **AND** the Total Value is placed in Column Index 5 (`Total Valoare`).

### Requirement: Preserving Empty Columns
The template's empty columns must be preserved exactly as empty strings in the output rows.

- **WHEN** writing a data row
- **THEN** column indices 0, 4, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21 must remain empty unless specifically required by a future business logic update.
