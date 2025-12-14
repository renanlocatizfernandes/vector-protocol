---
description: "Workflow for coding missions."
globs: "src/**/*, backend/**/*, frontend/**/*"
---

# Coding Mission

When asked to write code:

1. **Plan**: Create/Update `implementation_plan.md` if complex.
2. **Spec**: If it's a feature, find the Spec in `specs/SPEC_INDEX.md`.
3. **Execute**:
   - Write code.
   - Use `docs/CHANGE-MAP.md` to check dependencies.
4. **Verify**:
   - Run tests.
   - Or request user verification.
5. **Document**:
   - Update `docs/CHANGELOG.md`.
