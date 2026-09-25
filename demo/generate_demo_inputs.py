#!/usr/bin/env python3
"""
Generate fake demo input files for all 8 ExcelProcessor modules.
All data is fictional — no real companies, CUIs, or account holders.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root so we can import modules for testing later
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUT_DIR = Path(__file__).resolve().parent / "inputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _style_header(ws, row, max_col):
    """Apply bold + bottom border to a header row."""
    bold_font = Font(bold=True)
    thin_border = Border(bottom=Side(style="thin"))
    for col in range(1, max_col + 1):
        cell = ws.cell(row=row, column=col)
        cell.font = bold_font
        cell.border = thin_border


# ══════════════════════════════════════════════════════════════════════════
# 1. BORDEROU DE VANZARE — M1 branch
# ══════════════════════════════════════════════════════════════════════════

def generate_borderou_m1():
    """
    Creates an Excel borderou for M1 (standard layout, TV at col 6).
    The pipeline converts to CSV then parses with _detect_column_layout.
    Standard layout:
      col 0: NrCrt   col 1: Denumire     col 2: NrDoc   col 3: Data
      col 4: Explicatii  col 5: empty      col 6: Total Valoare
      col 7,8: Scutite   col 9: 21% Baza   col 10: 21% TVA
      col 11: 11% Baza   col 12: 11% TVA   col 18: Netaxabil Baza
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Borderou"

    # Row 1: title
    ws.merge_cells("A1:T1")
    ws["A1"] = "BORDEROU DE VANZARE M1 — Luna Februarie 2026"
    ws["A1"].font = Font(bold=True, size=14)

    # Row 2: sub-headers
    headers2 = [
        "Nr. Crt", "Denumire Z", "Nr. Doc(Z)", "Data Document",
        "Explicatii", "", "Total Valoare", "Scutit drept",
        "Scutit fara", "Taxabil 21% Baza", "Taxabil 21% TVA",
        "Taxabil 11% Baza", "Taxabil 11% TVA", "",
        "Nefol. Baza", "Nefol. TVA", "Nefol. Baza", "Nefol. TVA",
        "Netaxabil Baza", "Netaxabil TVA",
    ]
    for i, h in enumerate(headers2, 1):
        ws.cell(row=2, column=i, value=h)
    _style_header(ws, 2, 20)

    # Row 3: unit labels (RON)
    unit_labels = ["", "", "", "", "", "", "RON", "RON", "RON",
                   "RON", "RON", "RON", "RON", "", "RON", "RON",
                   "RON", "RON", "RON", "RON"]
    for i, v in enumerate(unit_labels, 1):
        ws.cell(row=3, column=i, value=v)

    # Data rows — 6 rows of fake M1 data
    data = [
        [1, "Z POS", 341, "2026-02-01", "Z emis la POS nr.14 la ora 15:23",
         "", 4520.15, 0, 0, 125.50, 26.36, 3980.20, 437.82,
         "", 0, 0, 0, 0, 50.00, 0],
        [2, "Z POS", 342, "2026-02-02", "Z emis la POS nr.14 la ora 15:31",
         "", 3876.40, 0, 0, 98.30, 20.64, 3450.00, 379.50,
         "", 0, 0, 0, 0, 28.00, 0],
        [3, "Z POS", 343, "2026-02-03", "Z emis la POS nr.14 la ora 14:55",
         "", 5120.80, 0, 0, 210.75, 44.26, 4576.00, 503.36,
         "", 0, 0, 0, 0, 75.50, 0],
        [4, "Z POS", 344, "2026-02-04", "Z emis la POS nr.14 la ora 16:10",
         "", 2890.30, 0, 0, 45.20, 9.49, 2678.90, 294.68,
         "", 0, 0, 0, 0, 31.00, 0],
        [5, "Z POS", 345, "2026-02-05", "Z emis la POS nr.14 la ora 15:02",
         "", 6340.60, 0, 0, 340.10, 71.42, 5678.50, 624.64,
         "", 0, 0, 0, 0, 110.30, 0],
        [6, "Z POS", 346, "2026-02-06", "Z emis la POS nr.14 la ora 15:47",
         "", 4456.90, 0, 0, 178.60, 37.51, 3980.80, 437.89,
         "", 0, 0, 0, 0, 62.40, 0],
    ]

    for i, row_data in enumerate(data, 4):
        for j, val in enumerate(row_data, 1):
            ws.cell(row=i, column=j, value=val)

    # Auto-width
    for col in range(1, 21):
        ws.column_dimensions[get_column_letter(col)].width = 12

    path = OUT_DIR / "Borderou_de_Vanzare_M1_demo.xlsx"
    wb.save(path)
    print(f"  [OK] {path}")


# ══════════════════════════════════════════════════════════════════════════
# 2. CARDCEC — POS incasari Autoservire
# ══════════════════════════════════════════════════════════════════════════

def generate_cardcec_autoservire():
    """
    Simulates a POS export for Autoservire with Card/Cec/Tichet payments.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Incasari"

    headers = [
        "Nr POS", "Nr. Z", "Data Ultimei Incasari",
        "Tip Incasare", "Valoare", "Rest"
    ]
    for i, h in enumerate(headers, 1):
        ws.cell(row=1, column=i, value=h)
    _style_header(ws, 1, 6)

    data = [
        ["POS1", "341", "18-Mar-26", "CARD",    1250.50, "Rest 0.50"],
        ["POS1", "341", "18-Mar-26", "CARD",     340.00, "Rest 0.00"],
        ["POS1", "341", "18-Mar-26", "CEC",      890.75, "Rest 0.25"],
        ["POS1", "342", "19-Mar-26", "CARD",    2100.00, "Rest 0.00"],
        ["POS1", "342", "19-Mar-26", "CARD",     456.30, "Rest 0.70"],
        ["POS1", "342", "19-Mar-26", "CEC",     1350.25, "Rest 0.75"],
        ["POS1", "343", "20-Mar-26", "CARD",     780.40, "Rest 0.60"],
        ["POS1", "343", "20-Mar-26", "TICHET",   430.00, "Rest 0.00"],
    ]

    for i, row_data in enumerate(data, 2):
        for j, val in enumerate(row_data, 1):
            ws.cell(row=i, column=j, value=val)

    for col in range(1, 7):
        ws.column_dimensions[get_column_letter(col)].width = 18

    path = OUT_DIR / "Incasari_POS_Autoservire_demo.xlsx"
    wb.save(path)
    print(f"  [OK] {path}")


# ══════════════════════════════════════════════════════════════════════════
# 3. SGR — RetuRO Garantii PDF
# ══════════════════════════════════════════════════════════════════════════

def generate_sgr_pdf():
    """
    Creates a PDF that mimics the RetuRO-SGR "Garantii SGR Platite cu Numerar"
    text output. The SGRValueProcessor parses these with regex.
    """
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Courier", "", 10)

    lines = [
        "                     RetuRO Sistem Garanție Returnare S.R.L.",
        "",
        "                RAPORT GARANTII SGR PLATITE CU NUMERAR",
        "",
        "In perioada: 01.02.2026 - 28.02.2026",
        "Punct de lucru: M1 — Str. Exemplu nr. 10, Bucuresti",
        "",
        "================================================================",
        "",
        "Plata Numerar    847 01/02/2026  Returnare garantie SGR   76.50",
        "  Casier: Andrei P.                                    1013",
        "",
        "Plata Voucher RetuRO  1735 02/02/2026  Returnare garantie SGR   6.00",
        "  Casier: Maria I.                                    1013",
        "",
        "Plata Numerar    849 03/02/2026  Returnare garantie SGR  112.30",
        "  Casier: Andrei P.                                    1013",
        "",
        "Plata Voucher RetuRO  1741 04/02/2026  Returnare garantie SGR   3.50",
        "  Casier: Maria I.                                    1013",
        "",
        "Plata Numerar    851 05/02/2026  Returnare garantie SGR   45.00",
        "  Casier: Andrei P.                                    1013",
        "",
        "Plata Voucher RetuRO  1752 06/02/2026  Returnare garantie SGR   8.00",
        "  Casier: Elena D.                                    1013",
        "",
        "================================================================",
        "",
        "Total garantii platite in perioada:           251.30 RON",
        "Numar total tranzactii: 6",
        "",
        "Document generat automat. Data: 01.03.2026 08:00:00",
    ]

    for line in lines:
        pdf.cell(0, 5, line, ln=True)

    path = str(OUT_DIR / "Garantii_SGR_M1_demo.pdf")
    pdf.output(path)
    print(f"  [OK] {path}")


# ══════════════════════════════════════════════════════════════════════════
# 4. AVIZE — Iesiri avize M1
# ══════════════════════════════════════════════════════════════════════════

def generate_avize_iesiri_m1():
    """
    Creates an avize Excel file (iesiri, M1 branch) with partner trailing
    numbers and two TVA columns (A = 21%, B = 11%).
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Avize"

    headers = [
        "Nr. Doc. Intern", "Data Doc. Intern", "Partener",
        "Val. TVA Achizitie A", "Val. TVA Achizitie B"
    ]
    for i, h in enumerate(headers, 1):
        ws.cell(row=1, column=i, value=h)
    _style_header(ws, 1, 5)

    # Partner name must end with a number for account routing
    data = [
        [401, "2026-02-10", "SC Demo Construct SRL 1",  2315.25,    0],
        [402, "2026-02-12", "SC Alfa Distributie SRL 2", 1840.00, 315.70],
        [403, "2026-02-15", "SC Beta Impex SRL 3",        520.30, 145.20],
        [404, "2026-02-18", "SC Gamma Trading SRL 4",   3780.50,    0],
        [405, "2026-02-20", "SC Delta Prodcarn SRL 5",    960.75, 210.40],
        [406, "2026-02-22", "SC Epsilon Market SRL 6",   1250.00,   0],
    ]

    for i, row_data in enumerate(data, 2):
        for j, val in enumerate(row_data, 1):
            ws.cell(row=i, column=j, value=val)

    for col in range(1, 6):
        ws.column_dimensions[get_column_letter(col)].width = 22

    path = OUT_DIR / "Iesiri avize M1 demo.xlsx"
    wb.save(path)
    print(f"  [OK] {path}")


# ══════════════════════════════════════════════════════════════════════════
# 5. RECEPTII / FURNIZORI — Centralizator (Style 1)
# ══════════════════════════════════════════════════════════════════════════

def generate_receptii_m1():
    """
    Creates an Excel file in Style 1 format for the furnizori/receptii module.
    Expects: Numar Factura, Data Document, Valoare Achizitie, Nume, CUI/CNP, TVA Achizitie
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Receptii"

    headers = [
        "Numar Factura", "Data Document", "Valoare Achizitie",
        "Nume", "CUI/CNP", "TVA Achizitie", "Procent TVA"
    ]
    for i, h in enumerate(headers, 1):
        ws.cell(row=1, column=i, value=h)
    _style_header(ws, 1, 7)

    # Mix of RO-prefixed CUIs and plain CUIs, domestic and non-RO
    data = [
        ["FV-2026-0312", "2026-02-03", 2850.50, "SC Exemplu Trading SRL", "RO12345678", 19, 19],
        ["FV-2026-0315", "2026-02-05", 1430.00, "SC Demo Construct SRL",   "87654321",  21, 21],
        ["FV-2026-0320", "2026-02-07",  670.25, "SC Alfa Market SRL",      "RO34561278",  9, 9],
        ["FV-2026-0323", "2026-02-10", 5230.00, "SC Beta Logistic SRL",    "RO45678912", 21, 21],
        ["FV-2026-0328", "2026-02-12",  890.90, "SC Gamma Fresh SRL",      "56789123",    0, 0],
        ["FV-2026-0331", "2026-02-14", 3100.75, "SC Omega Distribution SRL", "RO67891234", 11, 11],
    ]

    for i, row_data in enumerate(data, 2):
        for j, val in enumerate(row_data, 1):
            ws.cell(row=i, column=j, value=val)

    for col in range(1, 8):
        ws.column_dimensions[get_column_letter(col)].width = 20

    path = OUT_DIR / "Centralizator_Receptii_M1_demo.xlsx"
    wb.save(path)
    print(f"  [OK] {path}")


# ══════════════════════════════════════════════════════════════════════════
# 6. ADAOS COMERCIAL — messy Excel with typos and merged cells
# ══════════════════════════════════════════════════════════════════════════

def generate_adaos_comercial():
    """
    Creates a messy adaos comercial Excel with:
    - Typo header: "TVVAaloare Diferenta" (double V)
    - Merged cells
    - Text percentages: "%19", "%9", "%21"
    - Unnamed columns
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Adaos"

    # Row 1: merged header for the problematic column
    ws.merge_cells("G1:H1")
    ws["A1"] = "NIR"
    ws["B1"] = "Data NIR"
    ws["C1"] = "Numar Aviz"
    ws["D1"] = "Data Aviz"
    ws["E1"] = "Valoare Achizitie"
    ws["F1"] = "Procent TVA"
    ws["G1"] = "TVVAaloare Diferenta"  # typo — double V
    ws["I1"] = "Adaos"
    ws["J1"] = "% TVA VANZARE"
    ws["K1"] = "TVAACH"
    ws["L1"] = "Valoare TVA.1"
    # Column H is merged into G

    for col in range(1, 13):
        ws.cell(row=1, column=col).font = Font(bold=True)

    data = [
        ["N001", "2026-02-01", "AV001", "2026-01-28", 1250.50, 19, 1488.10, 237.60, 237.60, "%19", "19%", 237.60],
        ["N002", "2026-02-02", "AV002", "2026-01-29", 3450.00,  9, 3760.50, 310.50, 310.50, "%9",  "9%",  310.50],
        ["N003", "2026-02-03", "AV003", "2026-01-30", 2100.75, 21, 2541.91, 441.16, 441.16, "%21", "21%", 441.16],
        ["N004", "2026-02-04", "AV004", "2026-02-01",  890.00, 11,  987.90,  97.90,  97.90, "%11", "11%",  97.90],
        ["N005", "2026-02-05", "AV005", "2026-02-02", 4560.30, 19, 5426.76, 866.46, 866.46, "%19", "19%", 866.46],
        ["N006", "2026-02-06", "AV006", "2026-02-03",  670.40,  9,  730.74,  60.34,  60.34, "%9",  "9%",   60.34],
        ["N007", "2026-02-07", "AV007", "2026-02-04", 1890.50, 21, 2287.51, 397.01, 397.01, "%21", "21%", 397.01],
    ]

    for r, row_data in enumerate(data, 2):
        for c, val in enumerate(row_data, 1):
            ws.cell(row=r, column=c, value=val)

    # H column is merged — leave it empty for the merged area
    for col in range(1, 13):
        ws.column_dimensions[get_column_letter(col)].width = 16

    path = OUT_DIR / "Adaos_comercial_februarie_demo.xlsx"
    wb.save(path)
    print(f"  [OK] {path}")


# ══════════════════════════════════════════════════════════════════════════
# 7. SALES TRANSFORM — date vanzari din gestiune
# ══════════════════════════════════════════════════════════════════════════

def generate_sales_transform():
    """
    Creates a sales export with the columns expected by SalesTransformProcessor.
    Includes one CLIENT MARFA row that should be filtered out.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Vanzari"

    headers = [
        "data", "nr_iesire", "den_tip", "denumire",
        "den_gest", "cantitate", "pret", "valoare",
        "tert", "cod_fiscal", "tva_art", "tva"
    ]
    for i, h in enumerate(headers, 1):
        ws.cell(row=1, column=i, value=h)
    _style_header(ws, 1, 12)

    data = [
        ["2026-02-01", "IE001", "Ciment Portland 40kg",    "Materiale", "Depozit 1", 50,  25.50, 1275.00, "SC Exemplu Trading SRL", "12345678", 19, 242.25],
        ["2026-02-01", "IE002", "Faina tip 650 25kg",      "Produse",   "Depozit 1", 30,  45.00, 1350.00, "SC Demo Construct SRL",   "87654321",  9, 121.50],
        ["2026-02-02", "IE003", "Ulei floarea soarelui 1L", "Produse",  "Depozit 2", 100, 8.50,   850.00, "SC Alfa Market SRL",     "34561278",  9,  76.50],
        ["2026-02-02", "IE004", "Otel beton 12mm",         "Materiale", "Depozit 1", 200, 12.75, 2550.00, "SC Beta Logistic SRL",    "45678912", 19, 484.50],
        ["2026-02-03", "IE005", "Zahar tos 1kg",           "Produse",   "Depozit 2", 60,   5.20,  312.00, "SC Gamma Fresh SRL",       "56789123",  9,  28.08],
        # This row should be filtered out (CLIENT MARFA)
        ["2026-02-03", "IE006", "Diverse marfa",           "Marfa",     "Depozit 1", 1,    0.00,    0.00, "CLIENT MARFA",             "",          0,   0.00],
        ["2026-02-04", "IE007", "Placa OSB 12mm",          "Materiale", "Depozit 1", 40,  35.00, 1400.00, "SC Omega Distribution SRL", "67891234", 19, 266.00],
    ]

    for i, row_data in enumerate(data, 2):
        for j, val in enumerate(row_data, 1):
            ws.cell(row=i, column=j, value=val)

    for col in range(1, 13):
        ws.column_dimensions[get_column_letter(col)].width = 18

    path = OUT_DIR / "Vanzari_gestiune_demo.xlsx"
    wb.save(path)
    print(f"  [OK] {path}")


# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Generating demo input files...\n")
    generate_borderou_m1()
    generate_cardcec_autoservire()
    generate_sgr_pdf()
    generate_avize_iesiri_m1()
    generate_receptii_m1()
    generate_adaos_comercial()
    generate_sales_transform()
    print(f"\nAll demo files saved to: {OUT_DIR}")
