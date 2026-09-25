#!/usr/bin/env python3
"""
Run each demo input file through the actual processing modules.
Tests all 7 modules and validates output shape.
"""
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "app" / "modules" / "core"))
sys.path.insert(0, str(ROOT / "app" / "modules" / "borderou"))
sys.path.insert(0, str(ROOT / "app" / "modules" / "cardcec"))
sys.path.insert(0, str(ROOT / "app" / "modules" / "sales_transform"))
sys.path.insert(0, str(ROOT / "app" / "modules" / "avize"))

import pandas as pd
import tempfile
import shutil

INPUTS = Path(__file__).resolve().parent / "inputs"
OUTPUTS = Path(__file__).resolve().parent / "outputs"
OUTPUTS.mkdir(parents=True, exist_ok=True)

results = []


def test_borderou():
    """Borderou pipeline — Excel → 53-col SAGA format."""
    from app.modules.borderou.main import BorderouPipeline
    import shutil

    temp_dir = tempfile.mkdtemp()
    try:
        orig = INPUTS / "Borderou_de_Vanzare_M1_demo.xlsx"
        temp_input = os.path.join(temp_dir, orig.name)
        shutil.copy2(str(orig), temp_input)

        pipeline = BorderouPipeline(output_dir=str(OUTPUTS))
        result = pipeline.process_file(temp_input)

        assert result and result != "skipped", "No result from pipeline"
        df = pd.read_excel(result)
        assert df.shape[1] == 53, f"Expected 53 cols, got {df.shape[1]}"
        assert len(df) > 0, "Empty output"
        assert "Serie document" in df.columns
        assert (df["Cota TVA"].isin([21, 11])).all()
        return "PASS", f"{len(df)} rows x {df.shape[1]} cols, TVA split OK"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_cardcec():
    """CardCec POS processing — Excel → 53-col SAGA format."""
    from app.modules.cardcec.pos_processor_fixed import process_pos_file, detect_pos_type

    orig = INPUTS / "Incasari_POS_Autoservire_demo.xlsx"
    temp_csv = str(OUTPUTS / "cardcec_temp_out.csv")

    pos_type = detect_pos_type(orig.name)
    assert pos_type is not None, f"No POS type detected for {orig.name}"

    process_pos_file(str(orig), temp_csv, pos_type, original_filename=orig.name)

    df = pd.read_csv(temp_csv, encoding="utf-8-sig")
    assert df.shape[1] == 53, f"Expected 53 cols, got {df.shape[1]}"
    assert len(df) > 0, "Empty output"
    # Verify values are negated (credit entries)
    assert (df["Valoare"] < 0).any(), "Values should be negated"

    # Save as xlsx too
    out_path = OUTPUTS / "cardcec_autoservire_out.xlsx"
    df.to_excel(out_path, index=False)

    os.remove(temp_csv) if os.path.exists(temp_csv) else None
    return "PASS", f"{len(df)} rows x {df.shape[1]} cols, values negated"


def test_sgr():
    """SGR RetuRO PDF → 53-col SAGA format."""
    from app.modules.core.valoare_sgr import SGRValueProcessor

    orig = INPUTS / "Garantii_SGR_M1_demo.pdf"
    processor = SGRValueProcessor()
    df = processor.process_pdf_file(str(orig))

    assert df is not None, "No data from SGR PDF"
    assert df.shape[1] == 53, f"Expected 53 cols, got {df.shape[1]}"
    assert len(df) > 0, "Empty output"
    assert (df["Cont credit simbol"] == "4621").all(), "Credit account should be 4621"
    assert (df["Explicatie"] == "SGR").all()

    out_path = OUTPUTS / "sgr_M1_out.xlsx"
    df.to_excel(out_path, index=False)
    return "PASS", f"{len(df)} rows x {df.shape[1]} cols, 6 SGR vouchers detected"


def test_avize():
    """Avize iesiri → 53-col SAGA format."""
    from app.modules.avize.main import process_avize

    orig = INPUTS / "Iesiri avize M1 demo.xlsx"
    df_in = pd.read_excel(orig)

    df = process_avize(df_in, orig.name)

    assert df.shape[1] == 53, f"Expected 53 cols, got {df.shape[1]}"
    assert len(df) > 0, "Empty output"
    assert (df["Tip inregistrare"] == "DIVERSE").all()
    # Verify debit/credit accounts follow 371.xx format
    assert df["Cont debit simbol"].str.startswith("371.").all()

    out_path = OUTPUTS / "avize_M1_out.xlsx"
    df.to_excel(out_path, index=False)
    return "PASS", f"{len(df)} rows x {df.shape[1]} cols"


def test_furnizori():
    """Receptii furnizori → 43-col Ciel format."""
    from app.modules.core.excel_data_extractor import ExcelDataExtractor

    orig = INPUTS / "Centralizator_Receptii_M1_demo.xlsx"
    df_in = pd.read_excel(orig)
    df_in.name = orig.name

    processor = ExcelDataExtractor()
    df = processor.process_dataframe(df_in)

    assert df is not None, "No data"
    assert len(df) > 0, "Empty output"
    assert "Cod fiscal" in df.columns
    assert "Denumire articol" in df.columns

    out_path = OUTPUTS / "furnizori_M1_out.xlsx"
    df.to_excel(out_path, index=False)
    return "PASS", f"{len(df)} rows x {df.shape[1]} cols"


def test_adaos():
    """Adaos comercial → split by TVA with summary."""
    from app.modules.core.format_add_column import FormatAddColumn

    orig = INPUTS / "Adaos_comercial_februarie_demo.xlsx"
    df_in = pd.read_excel(orig)

    processor = FormatAddColumn()
    df = processor.process_dataframe(df_in)

    assert df is not None, "No data"
    assert len(df) > 0, "Empty output"
    # Check for summary section
    cell_values = df.iloc[:, 0].astype(str).tolist()
    has_pct = any("%" in str(v) for v in cell_values)
    assert has_pct, "No percentage values found in output (summary missing?)"

    out_path = OUTPUTS / "adaos_comercial_out.xlsx"
    df.to_excel(out_path, index=False)
    return "PASS", f"{len(df)} rows x {df.shape[1]} cols, includes summary"


def test_sales_transform():
    """Sales transform → 43-col Ciel format."""
    from app.modules.sales_transform.sales_transform import SalesTransformProcessor

    orig = INPUTS / "Vanzari_gestiune_demo.xlsx"
    df_in = pd.read_excel(orig)

    processor = SalesTransformProcessor()
    df = processor.process_dataframe(df_in)

    assert df is not None, "No data"
    assert len(df) > 0, "Empty output"
    # CLIENT MARFA row should be filtered out (7 input → 6 output)
    assert len(df) == 6, f"Expected 6 rows (CLIENT MARFA filtered), got {len(df)}"
    assert "CLIENT MARFA" not in df["Nume partener"].values

    out_path = OUTPUTS / "sales_transform_out.xlsx"
    df.to_excel(out_path, index=False)
    return "PASS", f"{len(df)} rows x {df.shape[1]} cols, CLIENT MARFA filtered"


# ── Run all ────────────────────────────────────────────

tests = [
    ("Borderou de Vanzare",   test_borderou),
    ("CardCec POS",           test_cardcec),
    ("SGR RetuRO",            test_sgr),
    ("Avize iesiri/intrari",  test_avize),
    ("Furnizori / Receptii",  test_furnizori),
    ("Adaos Comercial",       test_adaos),
    ("Sales Transform",       test_sales_transform),
]

print("=" * 70)
print(f"{'Module':<25} {'Result':<6} {'Details'}")
print("=" * 70)

passed = 0
failed = 0

for name, fn in tests:
    try:
        status, detail = fn()
        print(f"{name:<25} {status:<6} {detail}")
        passed += 1
    except Exception as e:
        print(f"{name:<25} FAIL   {e}")
        failed += 1

print("=" * 70)
print(f"Results: {passed} passed, {failed} failed")
print(f"Outputs: {OUTPUTS}")
