# CardCec module — spec (source of truth)

Edit this file first, then make `pos_processor_fixed.py` (and the extractor /
server / UI) reflect it. Rules below are verified byte-exact against the model
fixtures unless marked ⚠ASSUMED.

## What it does

Converts a POS "Centralizator Incasari prin POS" report (xlsx or PDF) into the
fixed **53-column** accounting import file. One input row per (day, payment
kind) becomes one output row.

## Two document families

Both look similar; the differences are the account numbers and the export tag.

| Family   | Subtypes                                          | Debit (Cont debit simbol) | Export tag (`Informatii export`) |
|----------|---------------------------------------------------|---------------------------|----------------------------------|
| **AMT_M** (magazine) | `M1`, `M2`, `M3`                        | `53111`, `53112`, `53113` | `20260101-20261231-CielStd_1001` (all M) |
| **AMT** (complex)    | `Fast Food 1`, `Fast Food 2`, `Autoservire`, `Restaurant` | `5311` (all) | `20260101-20261231-CielStd_1057` |

> The M1 fixture shows `...1057` in its export column — that is a **known mistake
> in the model**; all M-types use `...1001`.

## Payment kinds kept + credit account (`Cont credit simbol`)

NUMERAR is always dropped. **Both families process tichete.**

| Family | CARD    | TICHETE          | CEC     |
|--------|---------|------------------|---------|
| AMT_M  | `51131` | `51131`          | `51131` |
| AMT    | `51131` | `51131` ⚠ASSUMED | `51132` |

- ⚠ASSUMED: no complex-tichete fixture exists; AMT tichete credit defaulted to
  `51131` (same as card). Confirm against a real fast-food/restaurant file.
- Output `Explicatie` = the kind, but tichete is written **`TICHET`** (singular).

## Row order

**Preserve input order** — per day (`Nr. Z`): TICHET then CARD, as it comes from
the report. Do NOT regroup by payment kind.

## Value rule

- `Valoare` column is used **as-is**, then negated (`-abs`) — these are credit
  entries. The PDF row trails a `Rest Tichet` number; it is **ignored** (the
  extractor drops it; the processor does not apply it).

## Date rule

- Output `Data` and `Data scadenta` = `YYYYMMDD` string (e.g. `20260501`).
- Parse: stage 1 `DD-MMM-YY` (e.g. `18-Mar-26`); stage 2 pandas `to_datetime(dayfirst=True)` fallback.

## Nr. inreg.

- The user enters a **starting number** per run (UI field, only shown for CardCec).
- Each output row = start + row index (contiguous +1).
- If the user enters nothing → leave the whole column **blank**.

## Numar document

- = the `Nr. Z` column from the input (sequential receipt number). Blank if absent.

## Subtype detection (from filename)

- `fast food 1 / ff1` → Fast Food 1; `fast food 2 / ff2` → Fast Food 2
- `m1/m2/m3` with optional space/dash/underscore (`m 2`, `m-1`) → M1/M2/M3
- `autoservire` / `amt complex` → Autoservire
- `restaurant` → Restaurant
- no match → defaults to Autoservire (logs a warning)

## Invariants (don't break)

- Output always has all **53** headers, even when empty (`OUTPUT_COLUMNS`, asserted == 53).
- Payment kind is classified **once** at filter time (`_kind` column) and reused —
  never re-derive in a way that can fall back to `'AMT'`.
- First output row gets `Cont debit titlu = 'Casa in lei'`; the rest blank.

## Regression fixtures (matched input → expected output, in `models/CardCec/`)

- M1: `POS__Centralizator_Incasari_prin_POS.pdf` → `cardcec - M1 POS__...prin_POS.xlsx` (start_nr 12448; ignore the export-tag column — model mistake)
- M2: `M2 POS__Centralizator_Incasari_prin_POS.pdf` → `cardcec - M2 POS__...prin_POS.xlsx` (start_nr 12636)

Quick check: `python test_detect_pos_type.py` (detection + account mappings).
