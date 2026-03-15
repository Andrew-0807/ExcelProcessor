## Context

The `app/modules/borderou/` module converts Excel "Borderou de Vanzare (Incasare)" files into a 53-column import format for accounting software. The current implementation spans 6 files (~1500 lines) with duplicated lookup tables, position-based parsing that breaks when column layouts differ (AUTOS vs standard), and a complex multi-step pipeline (Excel→CSV→clean→transform→CSV→XLSX).

The input files share a common template: 4-row merged header, data rows starting at row 5, and a footer with totals. Some files (FF1) have a repeated header mid-file. AUTOS has "Total Valoare" at column index 5 instead of 6.

## Goals / Non-Goals

**Goals:**
- Single `main.py` file that correctly processes all 5 input types (FF1, FF2, AUTOS, REST, DEPOZIT)
- Convert Excel to CSV first using openpyxl for reliable data extraction
- Standardize all variants into one intermediate format before transformation
- Produce output matching the reference file exactly (53 columns, TVA row ordering)
- Preserve the `BorderouPipeline` class interface and `__init__.py` exports

**Non-Goals:**
- M1/M2/M3 splitting logic (not in current input files, can be added later)
- Accounting format transformation (separate concern, `accounting_format_transformer.py` output format is different)
- Web UI changes
- Changing input/output directory paths

## Decisions

### 1. Single-file architecture
**Decision**: Replace 6 files with 1 `main.py` (~250 lines) + `__init__.py`
**Rationale**: The current code has duplicated lookup tables across `main.py`, `borderou_to_import_transformer.py`, and `extract_file_patterns()`. A single file eliminates all duplication. The total complexity is low enough for one file.
**Alternative**: Keep separate parser/transformer modules → rejected because the coupling between them creates bugs.

### 2. CSV-first parsing via openpyxl
**Decision**: Convert Excel to CSV using openpyxl row iteration, then parse CSV with standard logic.
**Rationale**: Excel files have merged cells, multi-row headers, and formatting quirks. Converting to CSV first normalizes everything. openpyxl with `data_only=True` gives us computed values.
**Alternative**: Parse Excel directly with pandas `read_excel` → rejected because it struggles with merged headers and multi-row column names.

### 3. Dynamic header detection instead of fixed row offsets
**Decision**: Scan rows for the first data row (where column 0 is a valid integer) instead of hardcoding `DATA_START_ROW = 5`.
**Rationale**: FF1 has a repeated header at rows 24-26, and different files may have varying header sizes. Dynamic detection handles all cases.

### 4. Column detection by proximity, not fixed index
**Decision**: After finding data rows in CSV, detect columns by looking at header row content (matching keywords like "Total Valoare", "Baza Impozitare", "Val. TVA") instead of hardcoded column indices.
**Rationale**: AUTOS has "Total Valoare" at index 5 while standard files have it at index 6. Keyword-based detection handles both.

### 5. All temporary files in `tmp/` directory
**Decision**: Any intermediate CSV files created during processing go to the `tmp/` folder and are deleted after use. 
**Rationale**: User rule requires temp files in `tmp/` and deletion after use.

## Risks / Trade-offs

- **Risk**: New column layout in future input files → **Mitigation**: Keyword-based header detection adapts automatically; only new file-type mappings need adding.
- **Risk**: Floating point precision in TVA calculations → **Mitigation**: Use Python's `round()` to 2 decimal places to match reference output behavior.
- **Trade-off**: Losing M1/M2/M3 splitting logic → acceptable since those types are not in the current input set. Logic can be re-added later if needed.
