## Why
The current codebase lacks a clean, efficient module organization and clear rules for AI-assisted development. This leads to clutter (useless scripts and folders) and makes it harder to cleanly introduce or modify models for new features. A reorganization is needed now to ensure a more robust program overall and to enforce clean development practices, especially when using AI coding assistants.

## What Changes
- **Module Reorganization**: Restructure the project to have a more efficient and robust module organization.
- **Model Directory**: Create a dedicated, clean folder structure for placing input and output models, making it easy to add or modify features.
- **Cleanup**: Remove useless scripts and folders that are cluttering the workspace.
- **AI Workspace Rules**: Create a `tmp` directory specifically for AI temporary scripts and enforce rules that compel the AI to respect this workspace boundary.

## Capabilities

### New Capabilities
- `module-organization`: Define the new, efficient module structure and guidelines for a robust program overall.
- `model-management`: Specify the folder structure and workflow for managing in/out models for feature additions or modifications.
- `workspace-rules`: Define the workspace cleanup procedures, the `tmp` directory setup for AI scripts, and the enforced rules for AI behavior.

### Modified Capabilities

## Impact
- **Code Structure**: Extensive changes to the folder hierarchy and module imports.
- **Developer Workflow**: Improved workflow for both human developers and AI assistants, with clear rules for temporary files.
- **System Stability**: A cleaner, more robust architecture that simplifies feature development.
