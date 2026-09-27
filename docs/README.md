# Documentation

**Version:** 3.3.0

Everything in this directory is maintained. If a document disagrees with the
code, that is a bug — please report it.

---

## Start here

| If you are… | Read this |
|---|---|
| **New to the project, non-technical** | [`USER_GUIDE_FA.md`](USER_GUIDE_FA.md) · [`USER_GUIDE_EN.md`](USER_GUIDE_EN.md) |
| **Installing it on a server** | [`INSTALLATION.md`](INSTALLATION.md) |
| **Evaluating the code as an engineer** | [`../ARCHITECTURE.md`](../ARCHITECTURE.md) · [`AUDIT.md`](AUDIT.md) |
| **Evaluating it as an investor** | [`../README.md`](../README.md) · [`../ROADMAP.md`](../ROADMAP.md) |
| **Building an integration** | [`API.md`](API.md) |
| **Reporting a security issue** | [`../SECURITY.md`](../SECURITY.md) |

---

## Documents

### [`USER_GUIDE_FA.md`](USER_GUIDE_FA.md) — راهنمای کاربر (فارسی)

Step-by-step guide for a non-technical user, in Persian. Covers installation,
first sign-in, a tour of the dashboard, everyday commands, safety, and
troubleshooting. Every step assumes no prior knowledge.

### [`USER_GUIDE_EN.md`](USER_GUIDE_EN.md) — User guide (English)

The same guide in English, for international users and reviewers.

### [`INSTALLATION.md`](INSTALLATION.md) — Installation and operations

For system administrators. Automated and manual installation paths, the full
environment-variable reference, verification commands, backup and rollback
procedures, and a production hardening checklist.

### [`API.md`](API.md) — API reference

**Generated, not hand-written.** Produced from the live OpenAPI schema by:

```bash
cd backend && python scripts/generate_api_docs.py
```

A test (`test_api_docs_are_up_to_date`) fails if the committed copy is stale, so
this file cannot drift from the code. The previous hand-written copy documented
endpoints that never existed.

### [`AUDIT.md`](AUDIT.md) — Dimensional audit

A full review of the repository tree, the module graph, and the request wiring,
with 45 findings, each with evidence and a resolution. This is the document that
motivated the v3.3.0 release.

---

## Related documents in the repository root

| Document | Purpose |
|---|---|
| [`../README.md`](../README.md) | Project overview, capabilities, verification |
| [`../ARCHITECTURE.md`](../ARCHITECTURE.md) | Layers, request lifecycle, design decisions |
| [`../SECURITY.md`](../SECURITY.md) | Security policy and vulnerability reporting |
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | Contribution guide and quality gates |
| [`../CODE_OF_CONDUCT.md`](../CODE_OF_CONDUCT.md) | Community standards |
| [`../CHANGELOG.md`](../CHANGELOG.md) | Version history |
| [`../ROADMAP.md`](../ROADMAP.md) | Planned work with release gates |
| [`../AGENTS.md`](../AGENTS.md) | The internal agent and tool inventory |
| [`../HANDOFF.md`](../HANDOFF.md) | Engineering handoff notes |

---

## Documentation standards applied here

1. **Every claim is verifiable** — backed by a test or a runnable command.
2. **No aspirational content** — planned work lives in
   [`../ROADMAP.md`](../ROADMAP.md), not in the feature documentation.
3. **Generated over hand-written** — [`API.md`](API.md) is produced from the
   OpenAPI schema and cannot drift.
4. **Known gaps are stated** — see the "Known gaps" section of
   [`../CHANGELOG.md`](../CHANGELOG.md).
5. **Bilingual where it matters** — user-facing guides exist in Persian and
   English; engineering documents are English.
