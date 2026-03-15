# workspace-rules Specification

## Purpose
TBD - created by archiving change code-reorganization. Update Purpose after archive.
## Requirements
### Requirement: AI Temporary Script Management
The system SHALL provide a `tmp/` directory for any AI-generated temporary or scratchpad scripts.

#### Scenario: AI creates a script
- **WHEN** the AI assistant creates a script for testing, exploration, or validation
- **THEN** it must place the script solely inside the `tmp/` folder and not pollute the root workspace

### Requirement: Enforced AI Rules
The system SHALL include rules that enforce the use of the `tmp/` folder and compel the AI to respect the project's folder organization rules.

#### Scenario: Enforcing workspace cleanliness
- **WHEN** the AI assistant is prompted to work on a task
- **THEN** the system rules must compel it to use the designated folders and avoid creating or keeping useless scripts in production areas, ensuring a robust program overall

