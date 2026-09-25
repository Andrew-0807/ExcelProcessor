"""Minimal guard for POS-type detection — the client's real filenames put a
space/dash between the magazine letter and digit ("m 2"), which used to fall
through to the AMT default and silently drop all TICHETE rows."""
from pos_processor_fixed import detect_pos_type, CREDIT_ACCOUNTS, POS_CONFIGS, _doc_number


def test_doc_number():
    # Model stores Numar document as a number, not text.
    assert _doc_number('890') == 890
    assert _doc_number(890) == 890
    assert _doc_number(890.0) == 890      # float-typed column
    assert _doc_number(float('nan')) == ''  # never the literal 'nan'
    assert _doc_number('') == ''
    assert _doc_number('Z890') == 'Z890'   # non-numeric stays text
    print('doc_number OK')


def test_credit_accounts():
    # Magazine firm (M1/M2/M3): every kind credits 51131. The complex firm
    # splits card/cec across 51131/51132. Both families process tichete.
    assert CREDIT_ACCOUNTS['AMT_M'] == {'CARD': '51131', 'TICHETE': '51131', 'CEC': '51131'}
    assert CREDIT_ACCOUNTS['AMT'] == {'CARD': '51131', 'TICHETE': '51131', 'CEC': '51132'}
    # Restaurant is a complex (AMT) subtype.
    assert POS_CONFIGS['Restaurant']['business'] == 'AMT'
    print('credit_accounts OK')


def test_detect():
    # The bug that started it all: space between m and digit.
    assert detect_pos_type('ìnital_m 2 POS__Incasari_Tichete_Valorice.pdf') == 'M2'
    # Other separators clients use.
    assert detect_pos_type('export_m-1.xlsx') == 'M1'
    assert detect_pos_type('export_m_3.csv') == 'M3'
    assert detect_pos_type('POS M2 centralizator.pdf') == 'M2'
    # Plain forms still work.
    assert detect_pos_type('m1_report.pdf') == 'M1'
    # AMT side must NOT be misdetected as a magazine.
    assert detect_pos_type('POS_Centralizator_AUTOSERVIRE.xlsx') == 'Autoservire'
    assert detect_pos_type('fast food 2 incasari.pdf') == 'Fast Food 2'
    print('detect_pos_type OK')


if __name__ == '__main__':
    test_detect()
    test_credit_accounts()
    test_doc_number()
