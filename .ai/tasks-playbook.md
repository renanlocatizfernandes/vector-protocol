# Tasks Playbook

Standard procedures for executing common tasks in this repository.

## 1. Investigation / Bug Fix

**Trigger**: User reports a bug or error log.

**Steps**:
1. **Reproduce**: Ask for logs or reproduction steps. Check `logs/` folder.
2. **Context**: Read relevant files from `.ai/context-map.md`.
3. **Hypothesis**: Formulate what might be wrong.
4. **Read**: Use `view_file` to inspect code around the error.
5. **Plan**: Propose a fix (don't code yet).
6. **Implement**: Apply fix via `replace_file_content`.
7. **Verify**: Run `pytest` or ask user to check `GET /health`.

## 2. New Feature

**Trigger**: User initiates a request found in `specs/`.

**Steps**:
1. **Spec Review**: Read the spec in `specs/`. If none, ask specific questions to create one.
2. **Impact Analysis**: Which files need changing? (Use `.ai/prompts/feature-plan.md`).
3. **Draft**: Create the code skeleton.
4. **Refine**: Fill in logic, ensuring `docs/ARCHITECTURE.md` compliance.
5. **Test**: Add unit tests in `backend/tests/`.
6. **Docs**: Update `README.md` and `UPDATING.md` if config changed.

## 3. Documentation Update

**Trigger**: Code change or "Explain this to me".

**Steps**:
1. **Identify**: Scope of changes.
2. **Draft**: Update markdown files.
3. **Review**: Ensure no technical inaccuracies.
4. **Link**: Check internal links.
