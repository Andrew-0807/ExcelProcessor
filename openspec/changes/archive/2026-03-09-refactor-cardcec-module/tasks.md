## 1. Setup Data Processing

- [x] 1.1 Create or update the processor script (e.g., `app/modules/cardcec/pos_processor.py`) to read `.xlsx` files from `models/in/`.
- [x] 1.2 Implement logic using `pandas` to open the simple Excel files and extract rows containing 'Grup incasare', 'Data', and 'Suma'.

## 2. Implement Transformation Logic

- [x] 2.1 Define the strict 53-column Ciel format template array to ensure all required headers are present.
- [x] 2.2 Map the extracted 'Suma' to a negative 'Valoare'.
- [x] 2.3 Map static accounting values based on the expected format (e.g., 'Tip inregistrare' = 'CASA', 'Jurnal' = 'RC', 'Cont debit simbol' = '5311', 'Cont credit simbol' = '51131', 'Explicatie' = 'CARD').

## 3. Final Output Generation

- [x] 3.1 Construct the final transformed dataframe populated with the mapped data and ensuring all 53 columns remain intact.
- [x] 3.2 Export the constructed dataframe to `.xls` or `.xlsx` files within the `models/out/` directory.
