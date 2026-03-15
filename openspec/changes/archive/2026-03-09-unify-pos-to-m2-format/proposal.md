# Unify POS Format to M2 Standard

## Motivation

Currently, the `pos_processor.py` orchestrates the transformation of multiple types of POS input files (Fast Food 1, Fast Food 2, Restaurant, M1, M2, M3, etc.). However, it incorrectly forces all of them into a generic 54-column Ciel import format. 

The business requirement is that **all POS exports must adhere identically to the M2 template format**, which is a strict 22-column structure with dual-row headers and specific empty columns for alignment. Forcing non-M-type POS files into the 54-column format violates the core formatting rule.

## Impact

- `processors/cardcec/CardCec/pos_processor.py`
- `processors/cardcec/CardCec/transform_m2.py` (potentially deprecate or absorb)
- Downstream systems that import these CSVs will now receive a uniform 22-column file regardless of whether the source was Fast Food or M-type.

## Proposed Solution

1. Deprecate the 54-column generic output format entirely within the context of POS processing.
2. Build a rigid 22-column formatter based exactly on `M2_template.csv`.
3. Route all POS variants (FF1, FF2, M1, M2, M3, Restaurant) through this new M2-style formatter, ensuring fields like 'Valoare neta totala' and 'Valoare TVA' are calculated and placed in the precise columns required by the new template.
