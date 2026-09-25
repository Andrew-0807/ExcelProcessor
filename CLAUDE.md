# Project Context
Stack: Python, Flask, pandas, openpyxl, pystray, Pillow
Purpose: Excel automation / processing desktop app for Mom

# Rule for all modules
The output should always have all of the header columns in the model even if some have empty rows

# Module imports in server.py
Each module is imported in its own try/except so one broken import doesn't crash the entire server. All modules are added to sys.path manually at startup.

# Module Isolation Rule — CRITICAL
When working on a specific module (e.g., app/modules/borderou/), do NOT modify files outside that module unless explicitly asked. In particular, never touch:

#Other modules in app/modules/ — each module is independent; do not "fix" or "improve" adjacent modules.
- server.py — unless you are adding a new route to wire up a brand-new module.
- Core utilities in app/modules/core/ — unless the task specifically requires a core change.
- Frontend files (templates/, static/) — unless the task specifically requires UI changes.

# Models
All modules have models test the module with the input after the edit, make sure the output maches the model final file, verify cell by cell not just the general structure.

### Rules

1. Each module owns a fixed `OUTPUT_COLUMNS` list. Do not derive it dynamically.
2. Immediately after the list, add a guard: `assert len(OUTPUT_COLUMNS) == <N>`
3. Every column key in `OUTPUT_COLUMNS` must be **explicitly set** in the output row dict — even if the value is `""` or `0`. Never let pandas fill `NaN` because a key was missing.
4. Never assign scalars to an empty `pd.DataFrame` and expect the value to propagate to rows added later (pandas bug-trap). Instead, build one dict of arrays and call `pd.DataFrame(data, columns=OUTPUT_COLUMNS)` once.
5. Different modules have different schemas — they are **not** interchangeable.


## Business Structure — CRITICAL (applies to ALL modules)

There is **one parent firm** with **two sub-firms**. This split affects every processing module — different account codes, export info, and location identifiers per sub-firm.

| Sub-firm | Also known as | Locations / sections | 
|----------|---------------|----------------------|
| **AMT** | Complex | Fast Food 1, Fast Food 2, Autoservire, Restaurant | `
| **AMT_M** | AMATO, Magazine | M1, M2, M3 | 

**These are independent.** A fix or change targeting AMT data must not break AMT_M data and vice-versa. When modifying **any** module:

1. Always test with **both** sub-firms (e.g., an Autoservire file AND an M1 file).
2. Account codes, export info, and punt de lucru differ per sub-firm — never hardcode values that assume only one sub-firm exists.
3. The sub-firm is typically detected from the filename (e.g., "M1" / "M2" / "M3" → AMT_M, otherwise → AMT).
