## Why

The borderou module pipeline is broken: `main.py` contains critical bugs (undefined variables `result` and `input_file`), and the Excel-to-CSV conversion step destroys the multi-row header format of the input files, causing column misalignment during parsing. As a result, none of the 5 input files in `models/in/` produce correct 53-column output XLSX files.

## What Changes

- **Fix critical bugs in `main.py`**: undefined variable references (`result`, `input_file`) and incorrect function call signatures
- **Rewrite input parsing**: replace the broken CSV-intermediary path with direct Excel reading that correctly skips the 4-row merged-header structure of the input files
- **Support all 5 input file variants**: FF1, FF2, AUTOS, REST, DEPOZIT — each with its correct column offsets and pattern mappings
- **Standardize `to_csv.py`**: ensure it is only called within the pipeline context (remove module-level code that runs on import)
- **Output validation**: each generated XLSX must have exactly 53 columns matching `models/out/borderou - Borderou_de_Vanzare_(FF1).xlsx`
- **Handle empty/skippable inputs**: DEPOZIT has no data rows; the pipeline must skip it gracefully

## Capabilities

### New Capabilities

- `borderou-pipeline`: End-to-end pipeline processing all `models/in/` Excel files into correct 53-column XLSX output files using direct Excel parsing with proper multi-header skipping, pattern-based column mapping, and TVA splitting (21% + 11%)

### Modified Capabilities

- (none – this is a bug fix; no existing passing specs exist)

## Impact

- `app/modules/borderou/main.py` — major rewrite of `process_file()`, `BorderouPipeline`
- `app/modules/borderou/to_csv.py` — remove module-level side-effect imports
- `app/modules/borderou/csv_cleaner.py` — update `transform_borderou_csv` to accept directly-parsed DataFrames or fix column-position mapping for AUTOS variant
- `app/modules/borderou/borderou_to_import_transformer.py` — minor: verify `read_borderou_data` uses correct column names after new parsing; fix `Numerar` sign and `Cont banca` for FF-type files (use 5125 not 51131)
- Input: `models/in/*.xlsx` (5 files)
- Output: `models/out/*.xlsx` (53-column XLSX per input, matching reference format)
