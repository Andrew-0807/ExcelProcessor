## 1. Directory Renaming & Restructuring

- [x] 1.1 Rename `app/processors` to `app/modules`.
- [x] 1.2 In `app/modules/cardcec/`, move all Python files from `app/modules/cardcec/CardCec/` (if any still exist) up to `app/modules/cardcec/`.
- [x] 1.3 Ensure `app/modules/cardcec/` is flat and delete any empty subdirectories (like `CardCec`).
- [x] 1.4 Repeat flattening for `app/modules/borderou/` ensuring all scripts are at the root of `borderou/`.
- [x] 1.5 Repeat flattening for any other modules like `core` and `sales_transform`.

## 2. Refactoring Code Imports

- [x] 2.1 Search and replace `app.processors` with `app.modules` across all python files (e.g. `server.py`, `launcher.py`, spec files).
- [x] 2.2 Update internal module imports. For example, change `from processors.cardcec.pos_processor` or similar localized imports within the modules themselves to use `app.modules`.
- [x] 2.3 Update the `excel_processor.spec` file's `datas` and `hiddenimports` arrays to reference `app.modules` instead of `app.processors`.
- [x] 2.4 Verify all `sys.path.insert` or dynamic path manipulation in `server.py` properly points to `modules` rather than `processors`.

## 3. Verification

- [x] 3.1 Run `python -c "import app.server"` and ensure it exits cleanly with no `ModuleNotFoundError`.
- [x] 3.2 Run `python -c "import app.launcher"` and ensure it exits cleanly.
- [x] 3.3 Verify the PyInstaller build script (`python scripts/build.py`) succeeds with the updated spec file.
