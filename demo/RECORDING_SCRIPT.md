# ExcelProcessor — Demo Recording Script

## Preparation (one-time)

1. Open browser to `http://127.0.0.1:5000`
2. Have `demo/inputs/` folder open in File Explorer next to the browser
3. Screen recording software ready (OBS / ScreenToGif / Loom)
4. Each module demo takes ~20 seconds — aim for 30 sec max per clip

---

## Module 1: Borderou de Vanzare (M1 branch)

**Input file:** `Borderou_de_Vanzare_M1_demo.xlsx`
**What it looks like:** An Excel sheet with merged title header, 2 header rows, and 6 data rows of daily Z-report summaries. Columns: NrCrt, NrDoc, Data, Explicatii (with POS numbers hidden in text), TVA 21% Baza/TVA, TVA 11% Baza/TVA, Netaxabil Baza.

**Record these steps:**
1. Show the input file briefly (2 sec) — point out the messy header rows and raw Z-report data
2. Drag `Borderou_de_Vanzare_M1_demo.xlsx` into the browser upload area
3. Select process type "Borderou" from the dropdown
4. Click Process
5. Wait ~2 seconds for download
6. Open the downloaded file — show the 53 columns, point out `Serie document: BFM1 0014` (POS extracted from Explicatii), and the split into 21% and 11% TVA rows (6 input → 12 output)

**Key visual moments:**
- Row 1 Explicatii field: "Z emis la POS nr.14..." → output Serie document reads "BFM1 0014"
- 21% and 11% rows stacked, same document numbers

**Duration target:** 25 seconds

---

## Module 2: Plati POS — Card/CEC/Tichet

**Input file:** `Incasari_POS_Autoservire_demo.xlsx`
**What it looks like:** A POS terminal export with 8 rows. Columns: Nr POS, Nr. Z, Data Ultimei Incasari (DD-Mon-YY format), Tip Incasare (CARD/CEC/TICHET), Valoare, Rest. Mixed payment types on the same export.

**Record these steps:**
1. Show the input — point out the mixed CARD/CEC/TICHET rows and the DD-Mon-YY date format
2. Drag into browser, select "CardCec", click Process
3. Open output — show the 53-column journal format
4. Point out: CARD → Cont 51131, CEC → Cont 51132, TICHET → Cont 53281, all values negated (credit entries)
5. Dates now formatted as YYYYMMDD

**Key visual moments:**
- Row with "CARD" → Cont credit simbol column reads "51131"
- Row with "CEC" → Cont credit simbol column reads "51132"
- All Valoare values negative

**Duration target:** 20 seconds

---

## Module 3: SGR — Garantii RetuRO

**Input file:** `Garantii_SGR_M1_demo.pdf`
**What it looks like:** A text-based PDF from RetuRO-SGR — no tables! Just lines of text: "Plata Numerar 847 01/02/2026 Returnare garantie SGR 76.50" and "Plata Voucher RetuRO 1735 02/02/2026 Returnare garantie SGR 6.00". The year is hidden in a header line: "In perioada: 01.02.2026".

**Record these steps:**
1. Show the PDF — scroll through to demonstrate it's pure text, no table structure
2. Drag into browser, select "SGR", click Process
3. Open output — show the 53-column file
4. Point out: 6 rows extracted, Cont debit 53111, Cont credit 4621, Explicatie "SGR", In perioada year auto-detected → 20260101-20261231

**Key visual moments:**
- PDF is just text lines — viewer sees "there's nothing to extract"
- Output has all 6 rows, perfectly structured
- Year automatically detected from header text

**Duration target:** 25 seconds

---

## Module 4: Avize — Iesiri/Intrari

**Input file:** `Iesiri avize M1 demo.xlsx`
**What it looks like:** An Excel export with dispatch notes. Columns: Nr. Doc. Intern, Data Doc. Intern, Partener (name ends with a number), Val. TVA Achizitie A (21%), Val. TVA Achizitie B (11%).

**Record these steps:**
1. Show the input — note the partner name ending in a number (e.g. "SC Demo Construct SRL 1")
2. Drag, select "Avize", Process
3. Open output — show debit/credit accounts using 371.xx scheme
4. Point out: partner number extracted from name → account suffix, TVA split per row (21%/11%), iesiri direction detected from filename

**Key visual moments:**
- Partner "SC Beta Logistic SRL 4" → Cont debit "371.19.4"
- 6 input rows → 9 output rows (some have both 21% and 11% non-zero)
- Filename "Iesiri avize M1 demo.xlsx" → direction=iesiri, punct_lucru=M1

**Duration target:** 20 seconds

---

## Module 5: Furnizori — Centralizator Receptii

**Input file:** `Centralizator_Receptii_M1_demo.xlsx`
**What it looks like:** A receptions centralizer with supplier invoices. Columns: Numar Factura, Data Document, Valoare Achizitie, Nume, CUI/CNP (mix of RO-prefixed and plain), TVA Achizitie, Procent TVA.

**Record these steps:**
1. Show the input — point out the mixed CUI formats: "RO12345678" vs "87654321"
2. Drag, select "Furnizori", Process
3. Open output — show the 43-column Ciel format
4. Point out: CUI cleaned (RO prefix removed), Denumire articol shows "marfa m1 19%", TVA logic applied (SCUTITE for 0% + non-RO, TAXABILE for >0%)

**Key visual moments:**
- CUI "RO12345678" → "12345678" in output
- Row with TVA Achizitie=0 → Optiune TVA "SCUTITE"
- Row with TVA Achizitie=21 → Optiune TVA "TAXABILE"

**Duration target:** 20 seconds

---

## Module 6: Adaos Comercial

**Input file:** `Adaos_comercial_februarie_demo.xlsx`
**What it looks like:** A messy markup calculation sheet. Has a typo in the column header ("TVVAaloare Diferenta" — double V), merged cell spanning column G-H, percentages as text ("%19", "%9"), and mixed TVA rates on the same sheet.

**Record these steps:**
1. Show the input — zoom in on the typo "TVVAaloare Diferenta" and the merged header cell
2. Drag, select "Adaos", Process
3. Open output — show that the data is clean and a summary section is appended at the bottom
4. Point out the summary rows: per-TVA-rate totals for Valoare Achizitie, Valoare Vanzare, Adaos

**Key visual moments:**
- Header reads "TVVAaloare Diferenta" (typo) — but it still works
- Output has summary rows appended: "%19 → Total Achizitie: 8561,30", "%9 → ...", etc.
- 7 data rows + 4 summary rows = 15 total output rows

**Duration target:** 25 seconds

---

## Module 7: Sales Transform

**Input file:** `Vanzari_gestiune_demo.xlsx`
**What it looks like:** A sales export from inventory management. Columns: data, nr_iesire, den_tip (product type), denumire, den_gest, cantitate, pret, valoare, tert (client name), cod_fiscal, tva_art, tva. Includes a "CLIENT MARFA" row that should be filtered out.

**Record these steps:**
1. Show the input — point out the "CLIENT MARFA" row (row 6) that will be filtered
2. Drag, select "Sales Transform", Process
3. Open output — show the 43-column Ciel format
4. Count rows: 7 input → 6 output (CLIENT MARFA removed)
5. Point out Serie = "FV", Moneda = "RON", Optiune TVA = "TAXABILE"

**Key visual moments:**
- Scroll to row 6 in input "CLIENT MARFA" → absent from output
- Output shows 6 clean rows, all with real clients only

**Duration target:** 18 seconds

---

## Module 8: Minus (Valoare)

**Input file:** `Minus_simple_demo.xlsx`
**What it looks like:** Simple file with 4 columns: Nr. Z, Data Ultimei Incasari, Tip Incasare, Valoare. All values positive — they need to be negated for accounting import.

**Record these steps:**
1. Show the input — note positive values and DD-Mon-YY dates
2. Drag, select "Minus", Process
3. Open output — show negated values and YYYYMMDD dates
4. Quick before/after: 1250.50 → -1250.50, "18-Mar-26" → "20260318"

**Key visual moments:**
- Side-by-side: input Valoare=1250.50 → output Valoare=-1250.50
- Date transformation visible

**Duration target:** 12 seconds

---

## Recording tips

- Keep browser window at ~1280x720 for consistent framing
- Don't narrate — just show the screen. Add text overlays in post-production
- For each module: show input (4 sec) → drag-and-drop + processing (4 sec) → open output, highlight key columns (10-15 sec)
- If an output file looks empty or wrong in Excel due to formatting: open it again, Excel sometimes hides columns on first open
- Total combined runtime across all 8 clips: ~2.5 to 3 minutes
