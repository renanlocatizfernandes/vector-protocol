---
status: filled
generated: 2026-01-12
---

# Security & Compliance Notes

Capture the policies and guardrails that keep this project secure and compliant.

## Authentication & Authorization

API access can be protected with an API key header (`API_AUTH_ENABLED`, `API_KEY`, `API_KEY_HEADER`). There is no multi-user auth layer; access control is environment and network based. The frontend authenticates implicitly by pointing at the configured API base URL.

## Secrets & Sensitive Data

Secrets live in `.env` (local) or injected via Docker/Kubernetes environment variables. Critical secrets include Binance API keys and Telegram bot tokens. Do not commit secrets; rotate keys on credential leaks or unusual trading activity. Logs may include symbols and trade metadata, so treat `logs/` as sensitive operational data.

## Compliance & Policies

No formal compliance framework is documented. Follow internal governance in `docs/GOVERNANCE.md` and AI contribution rules in `docs/AI-CONTRIBUTION.md`.

## Incident Response

Use `docs/RUNBOOK.md` and `ACOMPANHAMENTO_README.md` for incident checks. First actions: stop trading loops, verify container health, inspect `logs/`, and rotate compromised keys. Capture follow-ups in validation reports or improvement logs.
