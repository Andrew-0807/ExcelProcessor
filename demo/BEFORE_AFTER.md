# ExcelProcessor — Before & After Summary

## What the tool replaces

Every workflow below was done **entirely by hand** before this tool existed. Each module covers one specific accounting document type that arrives in a different format every time — different date formats, different column names, different file types (PDF vs Excel), Romanian diacritics, merged cells, text-embedded values.

| # | Workflow | Before (manual process) | After (tool) | Time saved |
|---|----------|------------------------|--------------|------------|
| 1 | **Borderou de Vanzare** | Open PDF/Excel of daily Z-reports. Copy 50+ rows into a blank template. Split each row into two (21% TVA and 11% TVA). Look up account codes per branch (76211/76212/76213). Extract POS terminal numbers from free-text Explicatii field. Type SAF-T series codes manually. | Drag file → 53-column SAGA import file with TVA split, correct accounts, POS-extracted series. | **~45 min → 5 sec** |
| 2 | **Plati POS (Card/CEC/Tichet)** | Export from POS terminal. Sort rows by payment type. Look up correct account: 51131 for Card, 51132 for Cec, 53281 for Tichet. Manually negate all values (credit entries). Fix date format (DD-Mon-YY → YYYYMMDD). Remove diacritics from column names. | Drag file → 53-column journal with accounts assigned, values negated, dates formatted, diacritics normalized. | **~30 min → 5 sec** |
| 3 | **Garantii SGR RetuRO** | Open RetuRO PDF — but it's just text, no table. Read voucher numbers, dates, and amounts line by line. Type each into accounting template. Detect fiscal year from header text. Assign accounts (53111 / 4621). | Drag PDF → 53-column file with all vouchers extracted, year auto-detected, accounts populated. | **~20 min → 5 sec** |
| 4 | **Avize (iesiri/intrari)** | Open Excel export. For each row: determine direction from context, look up partner account number from name suffix, calculate TVA from the amount, assign debit/credit accounts per rate and branch. | Drag file → 53-column file with accounts auto-assigned per partner number and branch, TVA split, direction detected from filename. | **~25 min → 5 sec** |
| 5 | **Centralizator Receptii** | Open PDF/Excel of supplier receptions. Clean CUI formatting (remove "RO", remove spaces). Determine TVA option per row (TAXABILE vs SCUTITE). Build Denumire articol from branch + rate. Map to 43-column Ciel format. | Drag file → 43-column Ciel import file with clean CUI, TVA logic applied, article names built automatically. | **~35 min → 5 sec** |
| 6 | **Adaos Comercial** | Open messy Excel — merged cells, typo header ("TVVAaloare Diferenta"), percentages as text ("%19"). Split rows by TVA rate. Calculate totals per rate manually. Build summary section. | Drag file → Clean data + auto-appended summary with per-rate totals (Achizitie, Vanzare, Adaos). | **~40 min → 5 sec** |
| 7 | **Sales Transform** | Export sales data from ERP. Filter out non-sale rows (CLIENT MARFA, CLIENT I.T.P). Reorder columns. Format dates. Map to 43-column Ciel schema. | Drag file → 43-column Ciel import file, non-sale rows filtered, columns mapped. | **~15 min → 5 sec** |
| 8 | **Valoare Minus** | Open Excel. Select Valoare column. Multiply by -1. Reformat date column cell by cell. | Drag file → Values negated, dates YYYYMMDD. | **~5 min → 3 sec** |

---

## Daily time savings (estimated)

| Task | Frequency | Manual time | Tool time | Daily saving |
|------|-----------|-------------|-----------|-------------|
| Borderou de Vanzare | Daily | 45 min | 5 sec | 45 min |
| Plati POS | Daily | 30 min | 5 sec | 30 min |
| SGR | Weekly | 20 min | 5 sec | ~3 min/day |
| Avize | 3x/week | 25 min | 5 sec | ~10 min/day |
| Receptii | 3x/week | 35 min | 5 sec | ~15 min/day |
| Adaos | Weekly | 40 min | 5 sec | ~6 min/day |
| Sales Transform | Weekly | 15 min | 5 sec | ~2 min/day |
| Minus | Daily | 5 min | 3 sec | 5 min |
| **TOTAL** | | **~3.5 hours/day** | **~38 seconds** | **~3.5 hours/day** |

---

## Processing capabilities

| Capability | Modules |
|-----------|---------|
| **PDF text extraction** (no tables, just lines of text) | SGR, Borderou, Receptii (PDF variant) |
| **PDF table extraction** (merged cells, scattered columns) | CardCec, Borderou |
| **Excel with merged cells & typos** | Adaos Comercial |
| **Date format normalization** (DD-Mon-YY, DD/MM/YYYY, YYYY-MM-DD → YYYYMMDD) | All |
| **Romanian number parsing** (1.234,56 → 1234.56) | SGR, PDF layer |
| **Romanian diacritics normalization** (Incasari vs Incasari) | CardCec, all PDF |
| **TVA rate splitting** (one row → multiple rows per rate) | Borderou, Avize, Adaos |
| **Account auto-assignment** (by branch, partner number, payment type) | Borderou, CardCec, Avize |
| **CUI/CNP cleaning** (RO prefix, spaces) | Receptii, Sales Transform |
| **Filename-based routing** (auto-detect module from name) | Borderou, CardCec, Avize, Receptii |
| **Error file preservation** (failed files saved with full traceback) | All (via server.py) |
| **Double entry accounting** (always debit + credit per row) | SGR, Avize |
