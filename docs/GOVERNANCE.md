# Governance

This document defines the roles, workflows, and rules for contributing to the Crypto Trading Bot repository.

## Roles

### 1. Human Developer
- **Responsibility**: Strategic decisions, complex architecture, final review of all changes.
- **Authority**: Can merge PRs, deploy to production, and change secrets.
- **Constraints**: Must review all AI-generated code before merging.

### 2. Code Agent (LLM)
- **Responsibility**: Implementation of features, bug fixes, refactoring, and unit tests.
- **Authority**: Can create branches, commit code, and open PRs.
- **Constraints**: 
    - Cannot access keys/secrets.
    - Cannot merge PRs.
    - Cannot execute system-level commands that are destructive (e.g., `rm -rf /`).
    - Must follow `specs/` and `docs/`.

### 3. Docs Agent (LLM)
- **Responsibility**: Maintenance of documentation (`docs/`, `.ai/`, `README.md`).
- **Authority**: Can update markdown files directly or via PR.
- **Constraints**: Must not change logical code files (`.py`, `.ts`, etc.).

## Workflows

### Standard Change Flow
1. **Spec**: A feature or fix must begin with a clear specification (or issue description).
2. **Branch**: Create a branch following conventions (see `VERSIONING.md`).
3. **Implementation**: Code changes + Tests.
4. **PR**: Open a Pull Request with description of changes.
5. **Review**: Human validation (mandatory for logic changes).
6. **Merge**: DevOps/Human merges to `main`.

### AI Interaction Rules
- **Transparency**: Commits made by AI should be ideally marked or documented in PR.
- **Safety**: AI agents must never output full secrets in cleartext in logs or comments.
- **Verification**: All AI-written code must include tests or a verification plan (e.g., `walkthrough.md`).
