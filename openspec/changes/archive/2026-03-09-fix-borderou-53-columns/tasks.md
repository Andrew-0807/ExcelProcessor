## 1. Fix `to_csv.py` module-level side effects

- [x] 1.1 Remove or guard lines 14-30 in `to_csv.py` that execute file I/O at import time (wrap in `if __name__ == "__main__":` block)

## 2. Fix `borderou_to_import_transformer.py` values

- [x] 2.1 Change `Cont banca` from `51131` to `5125` in the single-file loop (lines ~396, ~607)
- [x] 2.2 Change `Numerar` from `-total_valoare_fata_netaxablil` to `+total_valoare_fata_netaxablil` in the single-file loop and `process_pos_group()`
- [x] 2.3 Change `Cont tichete` from `53281` to `5328` in both loops
- [x] 2.4 Update `read_borderou_data()` to also accept a pre-parsed DataFrame (pass-through mode) so `main.py` can call without a file path

## 3. Rewrite `main.py` pipeline

- [x] 3.1 Add `parse_borderou_excel(excel_file_path)` function that uses `openpyxl` to read from row 5 onward, detecting AUTOS vs standard column layout from filename, and returns a clean DataFrame with standard column names (`Nr_Doc_Z`, `Data`, `Total_Valoare`, `Netaxabil_Baza_Impozitare`, `Taxabile_21_Baza_Impozitare`, `Taxabile_21_Val_TVA`, `Taxabile_11_Baza_Impozitare`, `Taxabile_11_Val_TVA`)
- [x] 3.2 Add `get_output_filename(input_filename)` function that maps input filename to output name pattern `borderou - Borderou_de_Vanzare_(XX).xlsx`
- [x] 3.3 Update `BorderouPipeline.process_file()` to: (a) call `parse_borderou_excel()`, (b) skip DEPOZIT files, (c) pass DataFrame to transformer, (d) save output to `models/out/` with correct filename
- [x] 3.4 Fix undefined variable references in `process_file()`: replace `result` with `import_files`, replace `input_file` with `excel_file_path`
- [x] 3.5 Update `run_pipeline()` to use `models/in` as default input dir and `models/out` as default output dir

## 4. Verify all 5 input files produce correct output

- [x] 4.1 Run the pipeline manually: `python -m app.modules.borderou.main` from `e:\Programming\Trae - MomAutomations`
- [x] 4.2 Verify FF1 output: open `models/out/borderou - Borderou_de_Vanzare_(FF1).xlsx` and confirm 53 columns and correct data values (Cont banca=5125, Cont tichete=5328, Numerar positive)
- [x] 4.3 Verify FF2 output: open `models/out/borderou - Borderou_de_Vanzare_(FF2).xlsx` and confirm 53 columns
- [x] 4.4 Verify AUTOS output: open `models/out/borderou - Borderou_de_Vanzare_(AUTOS).xlsx` and confirm 53 columns with correct AUTOS column parsing
- [x] 4.5 Verify REST output: open `models/out/borderou - Borderou_de_Vanzare_(REST).xlsx` and confirm 53 columns
- [x] 4.6 Confirm DEPOZIT is skipped gracefully (no crash, no output file, warning logged)
