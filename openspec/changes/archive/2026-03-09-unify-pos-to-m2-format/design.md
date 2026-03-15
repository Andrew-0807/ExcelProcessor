# Design: Unify POS to M2 Format

## Context

The `pos_processor.py` currently forces all POS input files into a generic 54-column format. The business requirement dictates that ALL POS inputs (whether Fast Food, Restaurant, or M-type) must be transformed into an exact 22-column structure defined by `M2_template.csv`.

This 22-column structure is highly specific, featuring a dual-row header system, empty columns used for specific alignments, and exact field placements (e.g., `Baza Impozitare`, `Val. TVA`).

## Goals / Non-Goals

**Goals**
- Provide a unified transformation function that accepts any defined POS input structure (from `Initial POS FF2.csv` or `M2_initial.csv`) and strictly outputs the 22-column `M2_template` format.
- Ensure all "empty" columns in the template remain structurally empty in the exact designated indices.
- Map the parsed values (Net Value, TVA Value, Total Value) into their correct respective columns.
- Retain the ability to detect POS types (FF 1, FF 2, M1, M2, etc.) for logging and routing, but ensure the final output format is singular.

**Non-Goals**
- We are not changing the core file reading logic or how the web UI handles uploads.

## Proposed Solution

Rewrite `pos_processor.py`:

1.  **Define Strict Output Constants**: 
    - `OUTPUT_HEADERS_ROW_1` and `OUTPUT_HEADERS_ROW_2` to exactly match `M2_template.csv`.
    - `M2_COLUMN_COUNT = 22`.

2.  **Data Extraction Refactoring**:
    - The `_transform_m_type` and `_transform_ff_type` methods in `POSProcessor` will be refactored to extract the core data: `Doc Number`, `Date`, `Total Value`, and `Payment Type` (Card/Tichet/Cec).

3.  **Unified Formatter**:
    - Instead of creating dictionaries mapped to the 54-column Ciel format, the extracted data will be passed to a singular formatter function: `_format_to_m2_template(self, doc_num, date, total_val, pay_type, business_tag)`.
    - This function will:
        - Calculate `Baza Impozitare` (Net Value) = `Total Value / 1.19` (or `1.09` depending on specific business rules, we need to clarify the exact TVA percentage assumed by the system, currently `transform_m2.py` assumes `1.21` but Romania is typically `1.19` or `1.09`. We will default to the calculation logic observed in `transform_m2.py` or clarify).
        - Calculate `Val. TVA` = `Total Value - Net Value`.
        - Place these values strictly in the column indices defined by the template.

4.  **CSV Output**:
    - The Pandas DataFrame will be constructed using the strict 22 columns.
    - We must ensure headers are written exactly.

## Risks / Trade-offs

- **TVA Calculation**: The template breaks down Total into Base and TVA. We need to ensure the hardcoded TVA rate in the code accurately reflects current business operations.
- **Header Parsing by Downstream Systems**: The downstream systems consuming this CSV are expecting this precise dual-header setup. Any extra commas or missed empty columns will likely cause downstream ingest failures.
