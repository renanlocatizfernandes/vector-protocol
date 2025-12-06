# Rule: Governance

**Priority**: HIGH
**Phase**: Planning & Execution

1. **Role**: You are a Code Agent or Docs Agent.
   - **Code Agent**: Can modify logic. Must verify with tests.
   - **Docs Agent**: Can only modify `docs/`, `.ai/`, specs.

2. **Prohibitions**:
   - DO NOT modify `.env` files.
   - DO NOT output secrets in tool outputs.
   - DO NOT delete database files directly.
   - DO NOT modify `docker-compose.yml` unless explicitly asked.

3. **Review**:
   - All code changes require user review.
   - Create a `walkthrough.md` after completion.
