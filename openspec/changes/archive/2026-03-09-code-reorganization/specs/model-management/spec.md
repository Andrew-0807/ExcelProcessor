## ADDED Requirements

### Requirement: Dedicated Model Folders
The system SHALL have a top-level `models/` directory containing `in/` and `out/` subfolders specifically designed for test and reference data.

#### Scenario: Storing new input models
- **WHEN** a new data model is required for a new feature or feature modification
- **THEN** its sample inputs must be placed in `models/in/` and expected outputs in `models/out/`
