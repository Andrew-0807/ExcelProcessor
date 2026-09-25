# Content Backlog — Workflow Patterns Found in Codebase

Every pattern below is derived from real logic in the code. Each is a potential carousel topic.

---

## Borderou (`modules/borderou/main.py`)

- **M1/M2/M3 account branching** — Same document type, different debit account per location (e.g., [CONT_M1], [CONT_M2], [CONT_M3]); wrong account = wrong balance sheet.
- **TVA double-row split** — One borderou row contains both 21% and 11% TVA; SAGA requires two separate rows with separate serie numbers ([SERIE_M1], [SERIE_M2]).
- **POS number buried in free text** — The POS terminal ID is not in its own column; it's extracted via regex from a free-text Explicații field like "Z emis la POS nr.[NR_POS] la ora [ORA]".
- **PDF with merged cells** — 4 different pdfplumber strategies run in parallel; winner chosen by rows × field completeness score. Same PDF can render entirely differently depending on which software generated it.
- **FF1 vs AUTOS column layout divergence** — "Total Valoare" column appears at a different position in FF1/FF2/REST vs AUTOS files; all offsets shift accordingly.

---

## CardCec / POS (`modules/cardcec/pos_processor_fixed.py`)

- **Romanian diacritic normalization** — Column headers arrive with or without diacritics (Încasări vs Incasari); all normalized before lookup so one missing ș doesn't break the whole import.
- **Date format chaos** — Same POS exports dates as "18-Mar-26" one day, "01/02/2026" another; two-stage parser with hardcoded month map handles both.
- **Payment type → account mapping** — CARD, CEC, TICHET each map to a different credit account ([CONT_CARD], [CONT_CEC], [CONT_TICHET]); rows with unrecognized type are excluded silently.
- **Value negation** — Cash received at POS is a credit entry (money leaving the cash register account); all amounts negated before export.
- **Auto-detect file type from filename** — "fast food 1", "ff1", "m1", "autoservire", "amt complex" in filename → correct debit account selected automatically.

---

## SGR (`modules/core/valoare_sgr.py`)

- **Text-only PDF extraction** — RetuRO PDFs have no table structure; each payment line parsed via regex from raw text: "Plata Voucher [NR] [DATA] Returnare garantie SGR [SUMA]".
- **Romanian number format** — Amounts written as "[X].[XXX],[XX]" (dot=thousands, comma=decimal); must convert before arithmetic.
- **Year hidden in PDF header** — Fiscal year extracted from "In perioada: [ZZ].[LL].[AAAA] - [ZZ].[LL].[AAAA]" line, not from the data rows.
- **Borderou fallback strategy** — If PDF is not a RetuRO document but a Borderou de Vanzare, a second extraction strategy activates that reads SGR deposits from the netaxabil column.

---

## Adaos / Markup (`modules/core/format_add_column.py`)

- **Column name typo in source file** — Column arrives named "TVVAaloare Diferenta" (typo); code detects and handles it without the user knowing.
- **Merged Excel header spanning 2 columns** — One header cell spans two data columns; pandas produces "Unnamed: [N]" for the second; code reconstructs the correct mapping.
- **Percent as string** — TVA rates arrive as text strings like "%19", "%9", "%21", "%11"; parsed to integers for arithmetic.
- **4-bracket TVA split with per-bracket totals** — Data split by TVA rate; per each bracket: total purchase value, expected TVA, total sale value calculated; 3 summary rows appended automatically.

---

## Furnizori / Recepții (`modules/core/receptii_extractor.py`, `excel_data_extractor.py`)

- **CUI format variants** — Same supplier CUI arrives as "RO [CUI]", "RO[CUI]", or just "[CUI]"; all normalized to bare digits before export.
- **3 Excel input schemas tried in sequence** — Supplier may send NIR file, Factură file, or Aviz file — three different column layouts; code tries each in order and uses first that parses.
- **TVA=0 context disambiguation** — Zero TVA could mean: (a) exempt supplier (SCUTITE), (b) SGR guarantee article (SCUTITE + special article name), or (c) data error; detected from CUI origin and article name.
- **PDF text line parsing with 12 trailing financial values** — Centralizator Recepții PDF: each row is one long text line; last 12 tokens are always financial values; preceding tokens reconstructed into NIR, date, invoice number, supplier name, CUI.
- **Exact column name with intentional typo** — Output column named "Valoare  cu TVa" (two spaces, lowercase 'a') to match the exact schema expected by downstream accounting software; one space = silent import failure.

---

## Sales Transform (`modules/sales_transform/sales_transform.py`)

- **Internal transfer exclusion** — Rows where partner name contains "CLIENT MARFA" or "CLIENT I.T.P" filtered out; these are internal stock movements, not real sales; including them inflates revenue figures.
- **Date format normalization** — Input dates in YYYY-MM-DD; output must be YYYYMMDD (no separator); consistent for all downstream systems.

---

## Infrastructure / Error Handling (`app/server.py`)

- **Wrong file → clear Romanian error message** — Uploading a Borderou de Vanzare PDF to the SGR module returns a human-readable Romanian error explaining exactly what went wrong and what to upload instead.
- **Partial batch success** — Processing 5 files: if 3 succeed and 2 fail, the 3 good files are still returned as a ZIP; failures listed separately with traceback saved to errors/ folder.
- **Auto-mode detection from filename** — Filename containing "borderou" → Borderou module pre-selected; "pos" or "incasari" → CardCec pre-selected; reduces wrong-module errors.
- **Error dump for debugging** — Every failed file is saved alongside its full Python traceback to errors/[modul]/[timestamp]_[filename].txt; enables post-mortem diagnosis without re-running.
