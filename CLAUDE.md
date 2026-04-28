# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Hindsight Memory

This project uses Hindsight for persistent memory across sessions.
**Always follow this protocol — do not skip steps.**

### Session Start
Before touching any code, recall prior context:
```
hindsight_recall("MomAutomations <topic you're working on>")
```
Do not re-ask the user to explain the project — query Hindsight first.

### Task Complete
After every meaningful change, store what was done:
```
hindsight_retain("MomAutomations: <what was done, approach used, reason>")
```

### When Stuck
Before trying a new approach, reflect on past decisions:
```
hindsight_reflect("MomAutomations: <problem description>")
```

## Project Context

- **Stack:** Python, Flask, pandas, openpyxl, pystray, Pillow
- **Purpose:** Excel automation / processing desktop app for Mom
- **Memory bank:** `mom-automations`
- **Version:** tracked in `scripts/app_info.py` (`__version__`)

## Commands

```powershell
# Run the Flask dev server (browser UI at http://127.0.0.1:5000)
python app/server.py

# Run as full desktop app (system tray + auto-open browser)
python app/launcher.py

# Run CLI mode
python app/cli.py

# Install dependencies
pip install -r requirements.txt

# Build standalone .exe (requires PyInstaller)
python scripts/build.py
# Output: dist/ExcelProcessor.exe
```

> **Shell note:** This machine uses PowerShell 7. Use `;` not `&&` to chain commands.

## Architecture

The app is a **Flask web server** running inside a **system tray app** (`pystray`). The user accesses it via browser at `127.0.0.1:5000`.

```
app/
  launcher.py        — TrayApplication: starts Flask in a daemon thread, manages system tray icon & auto-updates
  server.py          — Flask app, single /process POST endpoint; dispatches to processing modules
  cli.py             — Headless CLI alternative to launcher
  templates/         — Jinja2 HTML (index.html)
  static/            — Frontend JS (script.js), CSS, icons
  modules/
    core/            — Shared utilities (valoare_sgr, valoare_minus, format_add_column, excel_data_extractor, pdf_extractor)
    borderou/        — BorderouPipeline: processes M1/M2 Excel files → 53-col output
    cardcec/         — POS processor: XLSX/CSV card transaction files → 53-col output
    sales_transform/ — SalesTransformProcessor

scripts/
  app_info.py        — Version, app name, host/port constants (single source of truth)
  auto_update.py     — GitHub Releases auto-update logic
  build.py           — PyInstaller build automation (uses excel_processor.spec)
  deploy_to_client_pc.py
```

### Request flow (`/process` POST)

1. Browser uploads file(s) + `process_type` form field
2. `server.py` validates extension, dispatches to the matching processor class/function
3. Processor returns a `pd.DataFrame` → saved to `BytesIO` → sent as `.xlsx` download (or `.zip` for multi-file)
4. On error: file + traceback saved to `errors/<process_type>/` for debugging; partial successes still returned

### Module imports in server.py
Each module is imported in its own `try/except` so one broken import doesn't crash the entire server. All modules are added to `sys.path` manually at startup.

### PyInstaller frozen mode
`launcher.py` and `server.py` check `getattr(sys, "frozen", False)` / `sys._MEIPASS` to locate templates, static files, and assets when running as a bundled `.exe`.

## Module Output Schema Rule — CRITICAL

**Every processing module must produce an identical schema on every run: same columns, same order, every time — including columns that are always empty.**

This is the single most important rule in the codebase. Breaking it causes silent import failures in the accounting software that consumes the output.

### Rules

1. Each module owns a fixed `OUTPUT_COLUMNS` list. Do not derive it dynamically.
2. Immediately after the list, add a guard: `assert len(OUTPUT_COLUMNS) == <N>`
3. Every column key in `OUTPUT_COLUMNS` must be **explicitly set** in the output row dict — even if the value is `""` or `0`. Never let pandas fill `NaN` because a key was missing.
4. Never assign scalars to an empty `pd.DataFrame` and expect the value to propagate to rows added later (pandas bug-trap). Instead, build one dict of arrays and call `pd.DataFrame(data, columns=OUTPUT_COLUMNS)` once.
5. Different modules have different schemas — they are **not** interchangeable.

### When creating a new module

```python
# 1. Define schema at top of file — one source of truth
OUTPUT_COLUMNS = [
    "Col A", "Col B", "Col C",  # ...all N columns
]
assert len(OUTPUT_COLUMNS) == N  # hard guard

# 2. Build each row as a complete dict — no missing keys
row = {col: "" for col in OUTPUT_COLUMNS}  # start with all-empty defaults
row["Col A"] = actual_value
row["Col B"] = other_value
# ...

# 3. Create DataFrame in one shot
df = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
```

### When fixing a broken module

- Check that `new_row` / data dict has a key for **every entry** in `OUTPUT_COLUMNS`.
- Check that no column gets `NaN` — search for `.fillna` calls that paper over this.
- Add the `assert` guard if it's missing.
- Reference implementations: `borderou/main.py` (53-col), `cardcec/pos_processor_fixed.py` (53-col).
