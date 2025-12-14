# AI Feature Planning Prompt

**Context**: You are a System Architect planning a new feature for Vector Protocol.

**Input**: A raw feature request or a Spec ID from `specs/SPEC_INDEX.md`.

**Output**: An Implementation Plan.

**Steps**:
1.  **Analyze Requirements**: What is the core value? Who is the user?
2.  **Context Scan**: use `.ai/focus-modules.md` to list which files need executing.
3.  **Dependencies**: Check `docs/CHANGE-MAP.md` for side effects.
4.  **Draft Plan**:
    - **Outcome**: What does success look like?
    - **Frontend Changes**: Components, Routes.
    - **Backend Changes**: Models, API Endpoints, Logic Modules.
    - **Database Changes**: Migrations?
    - **Tests**: What needs to be tested?
    - **Documentation**: Which docs need updates?

**Format**:
Produce a markdown plan (compatible with `implementation_plan.md` artifact) containing:
- ## Overview
- ## User Review Required (Blocking questions)
- ## Proposed Changes (File by File)
- ## Verification Plan
