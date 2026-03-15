## Context
The application previously placed all processing logic inside the `app/processors/` directory. While this was a vast improvement over the old root-level scattered scripts, the internal structure of individual processor folders remained inconsistent (e.g., `app/processors/cardcec/CardCec/`). To fully embrace a modular architecture, we need to flatten these structures and use a more standard naming convention (`modules/` rather than `processors/`).

## Goals / Non-Goals

**Goals:**
- Rename `app/processors/` to `app/modules/`.
- Flatten the file structure inside `cardcec` and `borderou` (and any other modules) so that Python files reside directly in `app/modules/<module-name>/`.
- Update all internal imports in `server.py`, `launcher.py`, and the `excel_processor.spec` build script to reflect the new `app.modules` path.

**Non-Goals:**
- We will not rewrite the internal logic of the processors themselves, only their physical locations and import paths.
- We will not change how the frontend interacts with the backend routes.

## Decisions

1. **Rename to `modules/`**: This is a standard Python and application development convention that scales better than verbs like "processors". 
2. **Flatten Module Contents**: A heavily nested structure like `app/processors/cardcec/CardCec/*.py` adds unnecessary friction and path complexity for imports. By flattening these directories so that `app/modules/cardcec/*.py` is the convention, we eliminate redundant namespace nesting and simplify maintenance. All imports will be consistently structured as `from app.modules.<name> import <script>`.

## Risks / Trade-offs

- [Import Errors] -> Mitigation: After renaming and flattening, we will perform extensive search-and-replace for `app.processors` to `app.modules`. We will then verify by spinning up the app (`app.server` and `app.launcher`) in a test environment to ensure no `ModuleNotFoundError` occurs.
- [PyInstaller Build Breakage] -> Mitigation: We will explicitly update the `excel_processor.spec` file's `datas` and `hiddenimports` arrays to properly pack `app/modules/` instead of `app/processors/`.
