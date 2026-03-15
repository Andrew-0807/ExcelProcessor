## 1. pos_processor.py — Row Filter

- [x] 1.1 Define `ALLOWED_PAYMENT_TYPES = {'card', 'cec'}` constant at module level (near top of file, after logger)
- [x] 1.2 In `_read_input_file()`, after the existing `Valoare` numeric filter block, add a payment-type filter: determine `tip_col = 'Tip Incasare' if 'Tip Incasare' in df.columns else 'Explicatie'`, then if `tip_col in df.columns` keep only rows where `df[tip_col].astype(str).str.strip().str.lower().isin(ALLOWED_PAYMENT_TYPES)` is True
- [x] 1.3 Add a `logger.info()` line after the filter reporting how many rows remain

## 2. pos_processor.py — Column Zero Fix

- [x] 2.1 In `_transform_data()`, in the `new_row` dict, change `'Optiune TVA': 0` to `'Optiune TVA': ''`
- [x] 2.2 In the same `new_row` dict, change `'TVA la incasare': ''` to `'TVA la incasare': 0`

## 3. pos_processor.py — Autoservire Config Fix

- [x] 3.1 In `POS_CONFIGS`, change the Autoservire entry `'punct_lucru': 'Autoservire AMT COMPLEX'` to `'punct_lucru': 'Autoservire'`

## 4. pos_processor_fixed.py — Same Fixes

- [x] 4.1 Apply task 1.1: add `ALLOWED_PAYMENT_TYPES = {'card', 'cec'}` constant near top of file
- [x] 4.2 Apply task 1.2: add the payment-type row filter in `_read_input_file()` (note: this file reads with `pd.read_excel(self.input_file)` without dynamic header — the column name to check is `'Explicatie'` since `Tip Incasare` may not exist; use the same `tip_col` fallback pattern)
- [x] 4.3 Apply task 2.1: change `'Optiune TVA': 0` to `'Optiune TVA': ''` in `_transform_data()`
- [x] 4.4 Apply task 2.2: change `'TVA la incasare': ''` to `'TVA la incasare': 0` in `_transform_data()` (note: in this file the key may not be explicitly set; if absent, add it explicitly as `'TVA la incasare': 0`)
- [x] 4.5 Apply task 3.1: change Autoservire `'punct_lucru'` from `'Autoservire AMT COMPLEX'` to `'Autoservire'` in `POS_CONFIGS`

## 5. Verification

- [x] 5.1 Run the processor against a sample input file containing card, cec, and numerar rows; confirm only card and cec rows appear in the output
- [x] 5.2 Open the output file and verify column AE (`Optiune TVA`) is empty and column AN (`TVA la incasare`) contains `0`
- [x] 5.3 Run with an Autoservire input file; confirm `Punct de lucru` in the output is `'Autoservire'`
