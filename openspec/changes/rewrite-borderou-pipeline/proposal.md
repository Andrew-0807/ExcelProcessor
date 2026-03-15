## Why

The current borderou module (`app/modules/borderou/`) is overly complex at ~1500 lines across 6 files, with duplicated lookup tables, fragile position-based column parsing, and broken edge-case handling. The transformation logic for converting Borderou Excel input files into the 53-column import format is unreliable and produces incorrect output. A complete rewrite with a simpler, CSV-first approach will produce correct results flawlessly for all 5 input file types.

## What Changes

- **Replace** the entire `app/modules/borderou/` directory with a single, clean `main.py` (plus `__init__.py`) that:
  1. Converts each input `.xlsx` to CSV (via openpyxl) for reliable parsing
  2. Standardizes all CSV rows into a common intermediate format regardless of column layout differences (AUTOS vs standard)
  3. Transforms standardized rows into the 53-column output format, with all 21% TVA rows first, then all 11% TVA rows
  4. Writes the final output as `.xlsx` files using openpyxl
- **Remove** the following files that are no longer needed:
  - `borderou_to_import_transformer.py` (877 lines of duplicated logic)
  - `csv_cleaner.py` (274 lines, unused intermediate step)
  - `csv_to_xlsx_converter.py` (188 lines, unnecessary wrapper)
  - `accounting_format_transformer.py` (165 lines, separate output format not in scope)
  - `to_csv.py` (31 lines, legacy utility)
- **Preserve** the `BorderouPipeline` class interface for the rest of the application
- **Handle** all 5 input types: FF1, FF2, AUTOS, REST (all produce output), DEPOZIT (skipped - empty)

## Capabilities

### New Capabilities
- `borderou-csv-pipeline`: Robust CSV-first pipeline that converts Excel→CSV→intermediate format→53-column output XLSX. Handles header detection, column layout variations (AUTOS vs standard), repeated headers mid-file, and summary/total row filtering.

### Modified Capabilities
- `borderou-pipeline`: Complete rewrite of the parsing and transformation requirements to use CSV-based intermediate processing instead of fragile position-based Excel parsing. All existing requirements from the spec still apply (53 columns, TVA ordering, filename-based type detection, file naming).

## Impact

- **Code**: Complete replacement of `app/modules/borderou/` (6 files → 2 files)
- **API**: `BorderouPipeline` class interface is preserved; internal methods change
- **Dependencies**: No new dependencies (openpyxl, pandas already in use)
- **Input/Output**: Input files in `app/models/Borderou/In/`, output to `app/models/Borderou/Out/` — paths unchanged
