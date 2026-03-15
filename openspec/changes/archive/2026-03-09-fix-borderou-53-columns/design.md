## Overview

The borderou module processes 5 Excel "Borderou de Vanzare" files from `models/in/` and produces 53-column XLSX import files matching `models/out/borderou - Borderou_de_Vanzare_(FF1).xlsx`. The current pipeline is broken due to bugs in `main.py` and an incorrect Excel parsing approach. This design fixes the pipeline end-to-end.

## Root Cause Analysis

| Problem | Location | Detail |
|---|---|---|
| Undefined `result` variable | `main.py:178` | `import_files` returned but code checks `result` |
| Undefined `input_file` variable | `main.py:160` | Should be `excel_file_path` |
| Column misalignment | `to_csv.py` + `csv_cleaner.py` | `pd.read_excel()` flattens merged cells; the 4-row header becomes garbage column names |
| AUTOS different layout | `csv_cleaner.py` | AUTOS has `Total_Valoare` in column 6 (index 5), others in column 7 (index 6) |
| `Cont banca` wrong value | `borderou_to_import_transformer.py:396` | Current code uses `51131`, reference xlsx uses `5125` |
| `Numerar` sign | `borderou_to_import_transformer.py:397` | Positive in reference (FF1 row 2: `2379.58`), code sets it negative |

## Architecture

```
models/in/*.xlsx
       │
       ▼
[1] Excel Parser (direct openpyxl)
    - Skip rows 1-4 (merged title + sub-headers)
    - Map columns by fixed position per variant
    - Detect variant from filename (FF1, FF2, AUTOS, REST, DEPOZIT)
       │
       ▼
[2] Dataframe Normalizer
    - Standard column names: Nr_Doc_Z, Data, Total_Valoare,
      Taxabile_21_Baza_Impozitare, Taxabile_21_Val_TVA,
      Taxabile_11_Baza_Impozitare, Taxabile_11_Val_TVA,
      Netaxabil_Baza_Impozitare
       │
       ▼
[3] borderou_to_import_transformer (mostly unchanged)
    - Creates 2 rows per transaction (21% + 11% TVA)
    - Fills all 53 columns
    - Fix: Cont banca = 5125, Numerar = positive, Cont tichete = 5328
       │
       ▼
[4] XLSX Converter
    - Write output using openpyxl
    - Filename: "borderou - Borderou_de_Vanzare_(XX).xlsx"
       │
       ▼
models/out/*.xlsx  (53 columns)
```

## Input File Column Mapping

All input xlsx files have a 4-row header (rows 1-4), with actual data starting at row 5.

### FF1 / FF2 / REST layout (col index 0-based)

| Index | Content |
|---|---|
| 0 | Nr. Crt |
| 1 | Document Denumire |
| 2 | Nr. Doc(Z) |
| 3 | Data |
| 4 | Explicatii |
| 5 | (empty) |
| 6 | Total Valoare |
| 7 | Scutit cu drept |
| 8 | Scutit fara drept |
| 9 | Taxabile 21% Baza Impozitare |
| 10 | Taxabile 21% Val TVA |
| 11 | Taxabile 11% Baza Impozitare |
| 12 | Taxabile 11% Val TVA |
| 13 | (None) |
| 14 | Nefolosit Baza |
| 15 | Nefolosit Val |
| 16 | Nefolosit2 Baza |
| 17 | Nefolosit2 Val |
| 18 | Netaxabil Baza Impozitare |
| 19 | Netaxabil Val TVA |

### AUTOS layout (Total_Valoare is at index 5, 21% Baza at index 8)

| Index | Content |
|---|---|
| 0 | Nr. Crt |
| 1 | Document Denumire |
| 2 | Nr. Doc(Z) |
| 3 | Data |
| 4 | Explicatii |
| 5 | Total Valoare |
| 6 | Scutit cu drept |
| 7 | Scutit fara drept |
| 8 | Taxabile 21% Baza Impozitare |
| 9 | (None/empty merged) |
| 10 | Taxabile 21% Val TVA |
| 11 | Taxabile 11% Baza Impozitare |
| 12 | Taxabile 11% Val TVA |
| 13 | (None) |
| 14 | Nefolosit Baza |
| 15 | Nefolosit Val |
| 16 | Nefolosit2 Baza |
| 17 | Nefolosit2 Val |
| 18 | Netaxabil Baza Impozitare |
| 19 | Netaxabil Val TVA |

## File Type Patterns & Account Mappings

| Filename contains | Serie | Cod depozit | Denumire | Cont casa | Cont banca |
|---|---|---|---|---|---|
| FF1 | F | 3 | ff 1 | 5311 | 5125 |
| FF 2 / FF2 | F | 3 | FF 2 | 5311 | 5125 |
| AUTOS | A | 1 | autoservire | 5311 | 5125 |
| REST | R | 2 | restaurant | 5311 | 5125 |
| DEPOZIT | skip | — | — | — | — |
| M1 | BFM1 | 1 | marfa m1 | 53111 | 5125 |
| M2 | BFM2 | 2 | marfa m2 | 53112 | 5125 |
| M3 | BFM3 | 3 | marfa m3 | 53113 | 5125 |

## 53-Column Output Structure (Reference: FF1 xlsx)

Columns 1-53 as confirmed from reference file:

```
Serie document, Numar document, Cod depozit, Nume depozit, Data document,
Data scadenta, Cod tip factura SAF-T, Cod partener, Nume partener, Atribut fiscal,
Cod fiscal, Nr.Reg.Com., Rezidenta, Tara, Judet, Localitate, Strada, Numar,
Bloc, Scara, Etaj, Apartament, Cod postal, Cod agent, Valoare neta totala,
Valoare TVA, Total document, Numar bonuri fiscale, Card, Cont banca, Numerar,
Cont casa, Tichete, Cont tichete, Cont TVA, Cod articol, Cod de bare,
Denumire articol, Cantitate, Cod lot, Data expirare, Nr seriale, Tip miscare SAF-T,
Cont serviciu, Pret cu TVA, Total fara TVA, Total TVA, Total cu TVA, Optiune TVA,
Cota TVA, Cod TVA SAF-T, Discount, DiscountLinie
```

Key data values per row (from reference):

- `Numerar`: **positive** total_valoare_fata_netaxabil (not negative)
- `Cont banca`: `5125` (not `51131`)
- `Cont tichete`: `5328` (not `53281`)
- `Total document`: total_valoare_fata_netaxabil
- `Pret cu TVA`: base + tva for that rate
- Row structure: All 21% rows first, then all 11% rows

## Implementation Plan

### Phase 1 – Fix `to_csv.py`

Remove the module-level execution code (lines 14-30) that runs on import.
Keep only the `excel_to_csv(excel_file_path, output_folder)` function.

### Phase 2 – Rewrite `main.py`

Replace `BorderouPipeline.process_file()` with direct Excel parsing:

1. Open xlsx with `openpyxl`, detect layout variant from filename
2. Skip rows 1-4, iterate from row 5 onward
3. Extract columns by fixed index (per variant table above)
4. Build a clean DataFrame with standard column names
5. Skip DEPOZIT files (no data rows)
6. Pass DataFrame directly to `transform_borderou_to_import_format()`
7. Convert result to XLSX using `csv_to_xlsx_converter`
8. Save to `models/out/` with pattern: `borderou - Borderou_de_Vanzare_(XX).xlsx`

### Phase 3 – Fix `borderou_to_import_transformer.py`

- Change `Cont banca`: `51131` → `5125`
- Change `Numerar`: remove negative sign (use `+total_valoare_fata_netaxablil`)
- Change `Cont tichete`: `53281` → `5328`
- Update `read_borderou_data()` to accept a DataFrame directly (not just CSV file path)
- Apply to both the main loop and `process_pos_group()`

### Phase 4 – Update `csv_cleaner.py` (optional cleanup)

Since the new pipeline bypasses CSV entirely, this module is no longer called in the main flow. Leave it in place but add a note. Alternatively, keep a simplified version for backward compatibility.

## Output File Naming

| Input file | Output file |
|---|---|
| `Borderou_de_Vanzare_(Incasare)FF1.xlsx` | `borderou - Borderou_de_Vanzare_(FF1).xlsx` |
| `Borderou_de_Vanzare_(Incasare)FF 2.xlsx` | `borderou - Borderou_de_Vanzare_(FF2).xlsx` |
| `Borderou_de_Vanzare_(Incasare)AUTOS.xlsx` | `borderou - Borderou_de_Vanzare_(AUTOS).xlsx` |
| `Borderou_de_Vanzare_(Incasare)REST .xlsx` | `borderou - Borderou_de_Vanzare_(REST).xlsx` |
| `Borderou_de_Vanzare_(Incasare)DEPOZIT.xlsx` | (skipped, no data) |
