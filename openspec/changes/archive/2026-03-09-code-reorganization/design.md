## Context
The current codebase suffers from inefficient module organization, disorganized files, and leftover useless scripts and folders. Furthermore, there is no standardized way for the AI assistant to manage input/output models or store temporary scripts. This limits the robustness of the program and leads to workspace clutter.

## Goals / Non-Goals

**Goals:**
- Establish a clear and efficient module directory structure.
- Define a dedicated `models/` directory with `in/` and `out/` subfolders for easy feature testing and modification.
- Create a `tmp/` directory for AI temporary scripts with clear rules to enforce its usage.
- Clean up existing useless scripts and folders to make the workspace robust.

**Non-Goals:**
- Completely rewriting existing business logic that is not related to module organization.
- Changing the primary deployment strategy unless directly impacted by folder moves.

## Decisions

1. **Module Reorganization**: Move all independent capabilities into modular packages. This isolates features and makes them easier to maintain and test independently. 
2. **Dedicated Models Directory**: We will create a top-level `models/` directory containing `in/` and `out/` folders for sample data, templates, and reference outputs. This decision centralizes test and reference data, avoiding clutter in feature directories.
3. **Dedicated Temporary Directory**: We will create a `tmp/` root directory explicitly for AI scripts, isolating experimental code from production code. A rule will ensure these aren't committed, and AI workspace rules will mandate its use.

## Risks / Trade-offs

- [Import Breakages] -> Mitigation: We will systematically update all import paths during the reorganization and rely on existing tests to catch breakages.
- [AI Rule Compliance] -> Mitigation: By adding explicit rules in the agent configuration (e.g. `.agent/rules`), we compel the AI to strictly use the `tmp/` directory.
