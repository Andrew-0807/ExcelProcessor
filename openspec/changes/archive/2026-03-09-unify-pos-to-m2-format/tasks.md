# Implementation Tasks

## 1. Core Logic Update
- [x] 1.1 Remove the 54-column Ciel generation logic from `_transform_data` (and sub-methods `_transform_m_type`, `_transform_ff_type`) inside `POSProcessor`.
- [x] 1.2 Define the 22-column constants (`OUTPUT_COLUMNS_M2`, `HEADER_ROW_1`, `HEADER_ROW_2`) in `pos_processor.py` matching exactly to the provided `M2_template.csv`.

## 2. Universal Data Extraction
- [x] 2.1 Refactor the row iteration logic in `POSProcessor` to universally extract `Date`, `Document Number`, `Payment Type`, and `Total Value` from any supported POS input type.
- [x] 2.2 Standardize the extracted Total Value to be strictly numeric.

## 3. Numeric Calculations
- [x] 3.1 Implement TVA calculation logic specifically tracking the 21% and 11% splits observed in the template. If specific input flags are missing to decide between 21% and 11%, route total calculations into the primary tax block (usually the 21% bracket based on `M2_template.csv` having values there). 
    - `Net Value (Baza Impozitare)` = `Total Value / 1.21`
    - `Val. TVA` = `Total Value - Net Value`.

## 4. Output Generation
- [x] 4.1 Create the generic row mapper that places Net Value in column index 8 (under `Taxabile 0.21`), Val TVA in column index 9, and Total Value in column index 5.
- [x] 4.2 Ensure all other columns remain empty strings to respect the exact template spacing.
- [x] 4.3 Replace the pandas column-header writing with a custom CSV writer or specific DataFrame setup to allow the dual-row header system (Row 1: `Denumire`, `Data`, etc., Row 2: `Baza Impozitare`, `Val. TVA`, etc.).
- [x] 4.4 Update `process_pos_file` output name from `IMPORT CARD` to be distinct `UNIFIED M2 <name>.csv` for verification.

## 5. Verification
- [x] 5.1 Run `pos_processor.py` against `M2_initial.csv` and assert the output has 22 columns.
- [x] 5.2 Run `pos_processor.py` against `Initial POS FF2.csv` and assert the output has the exact same 22-column structure and headers as the M2 conversion.
