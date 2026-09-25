"""Self-check for SGR Excel input (raw Borderou export + template + rejection).

Run:  python -m app.modules.core.test_sgr_borderou_excel
Builds synthetic workbooks (no external sample files) and asserts the
Netaxabil/SGR column is detected by LABEL, so the AUTOS layout (netax col 18)
and the FF layout (netax col 16) both extract the right value.
"""
import os
import sys
import tempfile
from datetime import datetime

_base = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(os.path.dirname(os.path.dirname(_base)))
if _root not in sys.path:
    sys.path.insert(0, _root)

import openpyxl

from app.modules.core.valoare_sgr import SGRValueProcessor, _cont_debit_simbol


def _save(rows) -> str:
    wb = openpyxl.Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    fd, path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    wb.save(path)
    return path


def _autos_rows():
    """AUTOS layout: 21% rate in its own column shifts Netaxabil to col 18."""
    title = ["Borderou de Vanzare (Incasare) In intervalul 01.05.2026 - 31.05.2026"]
    sec = [None, "Denumire", "Nr. Doc(Z)", "Data", None, "Total Valoare",
           "Scutit", "Scutit", "Taxabile", None, 0.21, "Taxabile", None, 0.11,
           "Nefolosit", None, "Nefolosit", None, "Netaxabil", None]
    sub = [None] * 8 + ["Baza Impozitare", "Val. TVA"] * 6
    d1 = [1, "Z POS", 920, datetime(2026, 5, 1), "Z emis la POS nr.1", 12737,
          0, 0, 510.33, 107.17, None, 10904.05, 1199.45, None, 0, 0, 0, 0, 16, 0]
    d2 = [2, "Z POS", 921, datetime(2026, 5, 2), "Z emis la POS nr.1", 100,
          0, 0, 0, 0, None, 0, 0, None, 0, 0, 0, 0, 0, 0]  # netax 0 -> skipped
    return [title, ["Nr. Crt"], sec, sub, d1, d2]


def _ff_rows():
    """FF layout: single 21% column => Netaxabil at col 16."""
    title = ["Borderou de Vanzare (Incasare) In intervalul 01.05.2026 - 31.05.2026"]
    sec = [None, "Denumire", "Nr. Doc(Z)", "Data", None, "Total Valoare",
           "Scutit", "Scutit", "Taxabile", 0.21, "Taxabile", None,
           "Nefolosit", None, "Nefolosit", None, "Netaxabil", None]
    sub = [None] * 8 + ["Baza Impozitare", "Val. TVA"] * 5
    d1 = [None, "Z POS", 187, datetime(2026, 5, 1), "Z emis la POS nr.1", 3359.67,
          None, None, 80.99, 17.01, 2936.19, 322.98, 0, 0, 0, 0, 2.5, None]
    return [title, ["Nr. Crt"], sec, sub, d1]


def _flat_rows():
    """Newer flat single-header layout."""
    hdr = ["Data Document", "Document", "Nr. Doc", "Explicatii",
           "Valoare Totala", "Baza", "TVA", "Valoare fara TVA E"]
    d1 = [datetime(2026, 5, 1), "Z POS", 55, "Z emis", 1000, 900, 90, 7.5]
    d2 = [datetime(2026, 5, 2), "Z POS", 56, "Z emis", 1000, 900, 90, 0]  # skipped
    return [["In intervalul 01.05.2026 - 31.05.2026"], hdr, d1, d2]


def main():
    p = SGRValueProcessor()

    # AUTOS: netax 16 extracted, the 0 row skipped. start_nr fills Nr. inreg.
    # and the AMT default debit account (5311) applies (no M tag in name).
    f = _save(_autos_rows())
    df = p.process_excel_file(f, start_nr=500)
    os.remove(f)
    assert df is not None and len(df) == 1, f"AUTOS rows: {df}"
    assert df.iloc[0]["Valoare"] == 16, df.iloc[0]["Valoare"]
    assert df.iloc[0]["Numar document"] == 920
    assert df.iloc[0]["Data"] == "20260501"
    assert df.iloc[0]["Explicatie"] == "SGR"
    assert df.iloc[0]["Nr. inreg."] == 500, df.iloc[0]["Nr. inreg."]
    assert df.iloc[0]["Cont debit simbol"] == "5311", df.iloc[0]["Cont debit simbol"]

    # Per-shop debit account (the M1/M2/M3 suffix bug).
    assert _cont_debit_simbol("M1") == "53111"
    assert _cont_debit_simbol("M2") == "53112"
    assert _cont_debit_simbol("M3") == "53113"
    assert _cont_debit_simbol("FF1") == "5311"
    assert _cont_debit_simbol("") == "5311"

    # start_nr increments by 1 per row; M2 debit account = 53112.
    parsed = [
        {"nr_doc": 1, "data": "20260501", "valoare": 5.0},
        {"nr_doc": 2, "data": "20260502", "valoare": 7.0},
    ]
    out = p._build_output(parsed, "info", "M2", start_nr=12448)
    assert list(out["Nr. inreg."]) == [12448, 12449], list(out["Nr. inreg."])
    assert set(out["Cont debit simbol"]) == {"53112"}, set(out["Cont debit simbol"])
    # No start_nr -> Nr. inreg. left blank.
    out2 = p._build_output(parsed, "info", "M2")
    assert list(out2["Nr. inreg."]) == ["", ""], list(out2["Nr. inreg."])

    # FF: netax at the shifted col 16 must read 2.5 (the borderou module's
    # hard-coded col-18 returns 0 here — that's the bug we avoid).
    f = _save(_ff_rows())
    df = p.process_excel_file(f)
    os.remove(f)
    assert df is not None and len(df) == 1, f"FF rows: {df}"
    assert df.iloc[0]["Valoare"] == 2.5, df.iloc[0]["Valoare"]
    assert df.iloc[0]["Numar document"] == 187

    # Flat layout.
    f = _save(_flat_rows())
    df = p.process_excel_file(f)
    os.remove(f)
    assert df is not None and len(df) == 1, f"flat rows: {df}"
    assert df.iloc[0]["Valoare"] == 7.5

    # Borderou OUTPUT (53-col) must be rejected with a clear message.
    f = _save([["Serie document", "Numar document", "Cod depozit"], ["F", 1, 3]])
    try:
        p.process_excel_file(f)
        raise AssertionError("expected ValueError for borderou-output file")
    except ValueError as e:
        assert "deja procesat" in str(e), e
    finally:
        os.remove(f)

    print("all SGR borderou-excel checks passed")


if __name__ == "__main__":
    main()
