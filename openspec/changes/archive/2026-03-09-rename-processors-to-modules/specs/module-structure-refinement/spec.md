## ADDED Requirements

### Requirement: Modular Core Renaming
The system SHALL organize all domain-specific logic inside an `app/modules/` directory, replacing the legacy `app/processors/` directory.

#### Scenario: Backend Execution
- **WHEN** the server or launcher starts
- **THEN** it must successfully import all required modules from `app.modules` without throwing `ModuleNotFoundError`

### Requirement: Flat Module Interiors
The system SHALL ensure that each individual module directory (e.g., `cardcec`, `borderou`) is flat, containing its Python scripts directly without redundant subfolders of the same name.

#### Scenario: Code Maintenance
- **WHEN** a developer inspects the `cardcec` module code
- **THEN** they will find `pos_processor.py` and other related scripts directly inside `app/modules/cardcec/`, not buried in further subdirectories
