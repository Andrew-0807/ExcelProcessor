## Why

The CardCec module currently outputs rows for all payment types including `numerar` (cash), places a zero in the wrong output column (AE instead of AN), and uses an incorrect `Punct de lucru` value for the Autoservire POS type. These errors produce accounting import files that require manual correction before use.

## What Changes

- **Row filtering**: Only rows where `Tip Incasare` (or `Explicatie`) matches `card` or `cec` are included in the output. Rows with value `numerar` (or any non-card/cec type) are silently dropped during processing.
- **Column zero fix**: The `0` value is moved from column AE (`Optiune TVA`, index 30) to column AN (`TVA la incasare`, index 39). `Optiune TVA` becomes empty (`''`).
- **Autoservire punct_lucru fix**: The `Punct de lucru` for the Autoservire POS type changes from `'Autoservire AMT COMPLEX'` to `'Autoservire'`.

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `cardcec-transformation`: Requirements change to enforce payment-type filtering (card/cec only) and correct column zero placement (AN, not AE).

## Impact

- `app/modules/cardcec/pos_processor.py` — three targeted changes in `_read_input_file()` (row filter) and `_transform_data()` (column values and POS config).
- `app/modules/cardcec/pos_processor_fixed.py` — same three changes applied for consistency.
- No API changes, no dependency changes, no schema changes.
- Output file structure (53 columns) is unchanged; only row content and two cell values are affected.
