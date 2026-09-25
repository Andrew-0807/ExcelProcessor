# -*- mode: python ; coding: utf-8 -*-
# onedir build. Bundles the Python runtime + third-party deps only.
# app/ and scripts/ are NOT bundled — they ship as loose source beside the exe
# (see bootstrap.py) so updates are a file copy, not a rebuild.

a = Analysis(
    ['bootstrap.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'flask',
        'pandas',
        'openpyxl',
        'openpyxl.cell._writer',
        'openpyxl.styles',
        'xlrd',
        'pdfplumber',
        'rich',
        'pystray',
        'pystray._win32',
        'PIL',
        'PIL.Image',
        'werkzeug.serving',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'torchvision', 'torchaudio', 'tensorflow', 'matplotlib', 'scipy', 'pytest'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ExcelProcessor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon='app/assets/icons/excel-processor-icon.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='ExcelProcessor',
)
