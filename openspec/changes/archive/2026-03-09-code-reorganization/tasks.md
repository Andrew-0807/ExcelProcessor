## 1. Environment Setup

- [x] 1.1 Create `models/in` and `models/out` directories.
- [x] 1.2 Create `tmp/` root directory specifically for AI scripts.
- [x] 1.3 Update `.gitignore` to ignore the `tmp/` directory contents.

## 2. Rule Enforcement

- [x] 2.1 Update agent rules (e.g., in `.agent/rules` or `.cursorrules`) to strictly enforce the use of `tmp/` for AI temporary scripts.
- [x] 2.2 Update rules to mandate the placement of test/reference models in the `models/` directory structure.

## 3. Code Reorganization & Cleanup

- [x] 3.1 Identify and remove useless scripts and folders in the root workspace.
- [x] 3.2 Move loosely coupled features/scripts into designated modular directories (e.g. `processors/` or `modules/`).
- [x] 3.3 Systematically update import paths in the moved modules to ensure there are no breakages.
- [x] 3.4 Run existing tests to verify that the overall program remains robust after reorganization.
