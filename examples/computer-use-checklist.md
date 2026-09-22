# Computer-Use Agent Preflight Checklist

Use before shipping a browser/desktop (computer-use) agent—especially when it pairs with RAG runbooks.

Related: [docs/12-computer-use-tools.md](../docs/12-computer-use-tools.md) · [docs/07-mcp-tools-for-rag.md](../docs/07-mcp-tools-for-rag.md) · [docs/05-production.md](../docs/05-production.md) · [rag-principles-checklist.md](rag-principles-checklist.md)

## Prefer tools first

- [ ] Confirmed **no stable API / MCP tool** covers the task (or computer use is only for UI verification)
- [ ] Typed tools remain allowlisted and preferred when both paths exist

## Scope and allowlists

- [ ] Host / app **allowlist** documented and enforced in the runtime
- [ ] Default deny for arbitrary web navigation and unknown desktop apps
- [ ] Session length, action-rate, and download-path caps set
- [ ] Non-production / least-privilege account used for automation where possible

## Safety gates

- [ ] Destructive actions (delete, pay, permission change, prod writes) require **human confirm**
- [ ] No scraping of passwords, cookies, OTP, or API keys from the screen into prompts or logs
- [ ] Credentials come from vault / browser store / server injection—not model-typed secrets
- [ ] On-screen text treated as **untrusted** (prompt-injection aware)

## RAG + runbooks (if applicable)

- [ ] Agent retrieves the runbook via search/get-document **before** UI steps
- [ ] Steps are grounded in cited chunks; model cannot invent undocumented procedures
- [ ] Runbook and index versions recorded with the session

## Observe → act quality

- [ ] Re-observe after every navigation or async UI change (no stale screenshots)
- [ ] Ambiguous or missing controls → **fail closed** / ask user, not guess
- [ ] Golden-path smoke tests cover layout drift and auth walls

## Observability

- [ ] Action trail logged (goal id, steps, outcomes)—secrets redacted
- [ ] Screenshots or a11y snapshots retained at decision points with access controls
- [ ] Success / blocked / needs-confirm metrics defined
- [ ] Runbook `chunk_id`s + UI evidence attachable to tickets or change records

## Sign-off

| Item | Owner | Date |
| --- | --- | --- |
| Allowlist & least privilege | | |
| Destructive-action policy | | |
| Secret-handling review | | |
| Observability / retention | | |
| RAG runbook grounding (if any) | | |
