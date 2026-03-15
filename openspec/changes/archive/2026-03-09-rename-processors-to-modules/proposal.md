## Why
The previous reorganization moved the `processors/` folder into `app/`, but inside `app/processors/` the individual components (like `cardcec` and `borderou`) are still inconsistently structured and awkwardly named. Renaming `processors` to `modules` and flattening the internal structure of each module (so files aren't buried in subdirectories) will make the codebase much cleaner, easier to navigate, and consistent with the new architecture.

## What Changes
- **Directory Rename**: Rename `app/processors/` to `app/modules/`.
- **Module Flattening**: Inside each module (e.g., `cardcec`, `borderou`, `core`, `sales_transform`), ensure all Python scripts and resources are at the top level of the module directory rather than nested in redundant subfolders (like the former `CardCec/` inside `cardcec/`).
- **Code Updates**: Systematically update all import paths across the application (`server.py`, `launcher.py`, `excel_processor.spec`, etc.) to use `app.modules.*` instead of `app.processors.*`.

## Capabilities

### New Capabilities
- `module-structure-refinement`: Defines the exact flat structure required for individual modules within the `app/modules/` directory.

### Modified Capabilities

## Impact
- **Code Structure**: The `app/processors/` directory goes away in favor of `app/modules/`.
- **Import Paths**: All references to processors throughout the codebase and build scripts will have to be updated.
- **Maintainability**: A flatter, more uniformly named structure reduces cognitive load when adding or editing features.
