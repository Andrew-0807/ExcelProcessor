## 1. Cleanup and Preparation

- [x] 1.1 Delete the following files from `app/modules/borderou/`: `borderou_to_import_transformer.py`, `csv_cleaner.py`, `csv_to_xlsx_converter.py`, `accounting_format_transformer.py`, `to_csv.py`
- [x] 1.2 Delete `app/modules/borderou/__pycache__/` directory

## 2. Core Implementation

- [x] 2.1 Rewrite `app/modules/borderou/main.py` with the new CSV-first pipeline: Excel→CSV→parse→standardize→transform→XLSX. Include file type detection config (FF1, FF2, AUTOS, REST, DEPOZIT), dynamic header detection, and 53-column output generation
- [x] 2.2 Update `app/modules/borderou/__init__.py` to match the new module exports (keep `BorderouPipeline` export)

## 3. Verification

- [x] 3.1 Run the pipeline against all 5 input files in `app/models/Borderou/In/` and verify DEPOZIT is skipped
- [x] 3.2 Compare the generated FF1 output against the reference file `app/models/Borderou/Out/borderou - Borderou_de_Vanzare_(FF1).xlsx` — verify headers match exactly (53 columns), row count matches (2×N), and numeric values match
- [x] 3.3 Verify all 4 output files are created correctly: FF1, FF2, AUTOS, REST
- [x] 3.4 Clean up all temporary files from `tmp/` directory
