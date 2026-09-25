# Changes Summary: Build, Runtime & Launcher Fixes

**Date**: 2026-09-07  
**Scope**: MomAutomations application runtime, PyInstaller onedir packaging, and test runner compatibility.

---

## 1. PyInstaller Onedir Packaging & Verification
- **File**: `scripts/build.py`
- **Change**: Updated build workflow to align with `excel_processor.spec` onedir configuration.
- **Details**:
  - Implemented `get_exe_path()` checking `dist/ExcelProcessor/ExcelProcessor.exe` before fallback.
  - Added `copy_source_to_dist()` to copy loose source directories (`app/`, `scripts/`) beside the binary, omitting `__pycache__` artifacts.
  - Adjusted `verify_build()` and `create_build_info()` to write build metadata directly into the distribution folder.

## 2. Dual-Mode Runtime Entry Point
- **File**: `bootstrap.py`
- **Change**: Added runtime environment branching for `sys.path` initialization.
- **Details**:
  - Frozen mode (`getattr(sys, "frozen", False)`): Resolves path relative to `sys.executable` directory.
  - Unfrozen mode: Resolves path relative to `__file__` directory for direct script execution.

## 3. Test Runner Direct Execution
- **File**: `app/modules/core/test_sgr_borderou_excel.py`
- **Change**: Added project root insertion into `sys.path`.
- **Details**: Allows running test file directly (`python test_sgr_borderou_excel.py`) in addition to module mode (`python -m app.modules.core.test_sgr_borderou_excel`).

## 4. Application Startup Script
- **File**: `start_server.bat`
- **Change**: Created Windows launcher batch file.
- **Details**:
  - Automatically detects the Scoop Python environment (`E:\Apps\scoop\apps\python\current\python.exe`) or `python3` / `py -3` on system PATH.
  - Launches `bootstrap.py` to start the tray application, local web server, and default browser UI.

## 5. Python Environment Dependencies
- **Target**: `E:\Apps\scoop\apps\python\current`
- **Change**: Installed `pyinstaller` package to enable automated builds within the primary dependency-configured environment.
