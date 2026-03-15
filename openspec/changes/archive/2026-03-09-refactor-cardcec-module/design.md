## Context

The POS file ingestion process for the `cardcec` module currently receives simple input Excel files (e.g., matching columns like 'Grup incasare', 'Data', 'Suma'). However, the required downstream output (as shown by example files in `models/out`) demands a strict 53-column Ciel template format containing both empty columns and complex accounting mappings (e.g., setting 'Cont debit', 'Cont credit', 'Tip inregistrare').

## Goals / Non-Goals

**Goals:**

- Read `.xlsx` files from the `cardcec`/`models` `in` folder.
- Parse the simple 3-column data structure.
- Transform the parsed data into a robust 53-column Ciel format.
- Ensure all 53 columns are consistently generated in the output header, preserving empty columns identically.
- Output the fully transformed `.xls` or `.xlsx` files to the `out` folder.

**Non-Goals:**

- Changing the processing for other modules (e.g., `borderou`) which handle different types of inputs or formats.
- Restructuring the global application folder structure beyond the necessary processor changes.

## Decisions

- **Parser Implementation:** A dedicated script will evaluate files in the `in` directory using `pandas`. It will extract the transactional details ('Data', 'Suma') and apply a static 53-column schema.
- **Column Mapping:** Ensure the output precisely matches the examples (e.g., `Tip inregistrare` mapped to 'CASA', `Cont debit simbol` mapped to '5311', `Cont credit simbol` mapped to '51131', and `Valoare` mapped to negative `Suma`).

## Risks / Trade-offs

- [Risk] Expected input column names change -> Mitigation: Add column validation checks before parsing. If they don't match, log the skipping condition or error and do not produce an output file.
- [Risk] Hardcoded logic mapping breaking on untested files -> Mitigation: Make sure the logic closely aligns with the provided example outputs.
