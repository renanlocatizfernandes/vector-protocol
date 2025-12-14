---
description: "Workflow for documentation missions."
globs: "docs/**/*, *.md"
---

# Docs Mission

When asked to update docs:

1. **Read**: Understand what changed in the code.
2. **Update**:
   - `docs/ARCHITECTURE.md` if components changed.
   - `docs/RUNBOOK.md` if commands changed.
3. **Link**: Ensure `project-knowledge.md` links are valid.
4. **Log**: Update `docs/CHANGELOG.md` with "[Docs]" prefix.
