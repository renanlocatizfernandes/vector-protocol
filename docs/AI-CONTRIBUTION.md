# AI Contribution Policy

## 1. Principles
- **Augmentation, not Replacement**: AI helps humans build faster and safer.
- **Human Responsibility**: The human user is ultimately responsible for all committed code.
- **Transparency**: AI-generated code must be treated with the same (or higher) scrutiny as human code.

## 2. When to use AI
| Activity | AI Role | Human Role |
|----------|---------|------------|
| **Brainstorming** | Propose ideas, summaries. | Select direction. |
| **Docs** | Write drafts, fix typos, translations. | Verify accuracy. |
| **Refactoring** | Propose cleaner syntax. | Verify logic is preserved. |
| **New Feature** | Draft initial implementation. | Architectural review, Security audit. |
| **Debugging** | Analyze logs, suggest fixes. | Apply and verify fix. |

## 3. Review Checklist for AI-Generated Code
Before accepting an AI change, the Human must verify:

- [ ] **Hallucinations**: Does it call non-existent functions?
- [ ] **Security**: Did it hardcode a secret? (Check `.env` usage).
- [ ] **Logic**: Does the `if/else` logic actually make sense?
- [ ] **Bloat**: Did it add 100 lines where 5 would do?
- [ ] **Context**: Did it respect `docs/CHANGE-MAP.md`?

## 4. Workflows
- **Commits**: Ideally, use a co-author tag if supported, or mention "Assist by Antigravity" in body.
- **PRs**: Label as `ai-assisted`.

## 5. Tools
- **Antigravity**: Primary IDE.
- **Context**: Rely on `project-knowledge.md` and `.ai/` folder.
