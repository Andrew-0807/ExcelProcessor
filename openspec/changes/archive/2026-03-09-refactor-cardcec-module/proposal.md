## Why

The `cardcec` module needs to be able to process Excel files (`.xlsx` or `.xls`) containing POS transaction data and map them consistently into a strict 53-column Ciel format output. Currently, there is a discrepancy between the input files (which contain only a few columns like 'Grup incasare', 'Data', 'Suma') and the required output format (which has 53 columns, including empty ones, and specific accounting logic for 'Valoare', 'Cont debit', 'Cont credit' etc.). This change ensures reliable and standardized transformation of all POS files dropping into the `in` folder so they match the required output (`out` folder) structure exactly.

## What Changes

- Create/update a processor script in the `cardcec` module to read `.xlsx` files from the `in` subdirectory.
- Implement data transformation rules to map the simple input format ('Grup incasare', 'Data', 'Suma') into the comprehensive 53-column Ciel output format.
- Ensure all 53 columns are consistently generated in the header, even if they remain empty for the specific transactions.
- Implement logic to handle data parsing, mapping specific values (e.g., negative `Suma` values mapped to `Valoare`, date formatting, setting 'Cont debit/credit simbol', 'Explicatie').
- Generate the final `.xls` or `.xlsx` files in the `out` subdirectory matching the template exactly.

## Capabilities

### New Capabilities

- `cardcec-transformation`: Standardized transformation of simple POS Excel files into a rigorous 53-column Ciel format, ensuring data integrity and correct accounting variable assignments.

### Modified Capabilities

## Impact

- `app/modules/cardcec/`: This module's processing scripts will be either updated or newly created.
- The pipeline handling file ingestion from `models/in` and output generation to `models/out` for card records.
