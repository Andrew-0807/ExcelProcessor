## Context

The CardCec module (`app/modules/cardcec/pos_processor.py` and `pos_processor_fixed.py`) processes POS terminal export files and converts them into a 53-column Ciel accounting import format. The input file contains rows for all payment types: `card`, `cec`, and `numerar` (cash). Currently all rows are passed through to the output, the `Optiune TVA` column (AE, index 30) is set to `0` when it should be empty, the `TVA la incasare` column (AN, index 39) is empty when it should be `0`, and the Autoservire POS type emits `'Autoservire AMT COMPLEX'` as `Punct de lucru` when it should emit just `'Autoservire'`.

Both `pos_processor.py` and `pos_processor_fixed.py` contain the same logic and both need the same fixes applied.

## Goals / Non-Goals

**Goals:**
- Filter input rows so only `card` and `cec` payment types produce output rows; `numerar` rows are silently dropped.
- Move the zero sentinel value from `Optiune TVA` (AE) to `TVA la incasare` (AN); leave `Optiune TVA` as `''`.
- Change the Autoservire `punct_lucru` config value from `'Autoservire AMT COMPLEX'` to `'Autoservire'`.
- Apply all three fixes to both `pos_processor.py` and `pos_processor_fixed.py`.

**Non-Goals:**
- No changes to the 53-column `OUTPUT_COLUMNS` list (structure unchanged).
- No changes to any other POS type configs (Fast Food 1, Fast Food 2, Restaurant, M1, M2, M3).
- No changes to the accounting account mappings (51131 for CARD, 51132 for CEC, 5311 for cash).
- No changes to date parsing, Z-number extraction, or debit account logic.
- No UI or API changes.

## Decisions

### Decision 1: Where to apply the row filter

**Choice:** Apply the filter inside `_read_input_file()` after the DataFrame is loaded, before returning it.

**Rationale:** Filtering at read time is cleaner — `_transform_data()` never sees unwanted rows, so there is no risk of accidentally outputting a CASH row if the filter logic were missed inside the transform loop. It also means the filter is applied once rather than per-row inside the loop.

**Alternative considered:** Filter per-row inside `_transform_data()` with a `continue` statement. Rejected because it mixes filtering concern into the transform concern and is harder to test in isolation.

**Implementation:** After the existing `Valoare` numeric filter in `_read_input_file()`, add:
```python
ALLOWED_PAYMENT_TYPES = {'card', 'cec'}
tip_col = 'Tip Incasare' if 'Tip Incasare' in df.columns else 'Explicatie'
if tip_col in df.columns:
    df = df[df[tip_col].astype(str).str.strip().str.lower().isin(ALLOWED_PAYMENT_TYPES)]
```

### Decision 2: Column zero placement

**Choice:** Directly swap the literal values in the `new_row` dict inside `_transform_data()`.

**Rationale:** These are static output column assignments — the fix is a two-line change with zero ambiguity. No logic needed.

**Change:**
- `'Optiune TVA': 0` → `'Optiune TVA': ''`
- `'TVA la incasare': ''` → `'TVA la incasare': 0`

### Decision 3: Autoservire punct_lucru

**Choice:** Update the `POS_CONFIGS` dict constant directly.

**Rationale:** The value is a single string constant. Changing it in one place (`POS_CONFIGS`) propagates everywhere automatically without touching any logic.

**Change:**
- `'punct_lucru': 'Autoservire AMT COMPLEX'` → `'punct_lucru': 'Autoservire'`

## Risks / Trade-offs

- **[Risk] Rows with mixed-case payment types are dropped incorrectly** → Mitigation: The filter uses `.str.lower()` before comparing, so `'Card'`, `'CARD'`, `'card'` all pass.
- **[Risk] Input files without a `Tip Incasare` or `Explicatie` column skip filtering** → Mitigation: The `if tip_col in df.columns` guard keeps current behaviour (no crash) for unexpected formats; a warning log line can optionally be added.
- **[Risk] `pos_processor_fixed.py` diverges if only one file is updated** → Mitigation: Both files are listed as explicit tasks — they must both be updated in the same commit.
- **[Risk] Existing output consumers depend on non-zero `Optiune TVA`** → Mitigation: The Ciel import spec treats `Optiune TVA` as optional metadata; an empty value is valid.
