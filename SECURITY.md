# Security Policy

**Version:** 3.3.0
**Applies to:** AARK Kernel 3.x

---

## Supported versions

Only the latest minor series receives security fixes.

| Version | Supported |
|---|---|
| 3.3.x | ✅ Active |
| 3.2.x | ⚠️ Critical fixes only until 3.4.0 ships |
| 3.1.x and earlier | ❌ End of life |

---

## Reporting a vulnerability

**Please do not report security issues in public issues or discussions.** A
public report exposes every deployment before a fix exists.

Report privately through one of these channels:

| Channel | Address |
|---|---|
| GitHub Security Advisories — **preferred** | [New advisory](https://github.com/ansariaiadmin/aark-kernel/security/advisories/new) |
| Email | `security@ansariai.ir` |

**Use GitHub Security Advisories when you can.** It is private by default, keeps
a tracked record of the report, and needs no mail setup on our side. The email
address becomes active once the `ansariai.ir` domain is connected to a mail
provider; until then an advisory is the reliable route.

Telegram, issues, discussions and pull requests are **not** accepted channels for
security reports — they are public or unmoderated spaces, and a public report
exposes every deployment before a fix exists.

### What to include

1. **What** the vulnerability is, and **why** it is dangerous
2. **How to reproduce it** — exact steps, or a script
3. **Which version** you tested against
4. **Impact** — what an attacker gains
5. **Suggested fix**, if you have one

### What happens next

| Time | Commitment |
|---|---|
| 24 hours | Acknowledgement that we received it |
| 72 hours | Initial assessment and severity rating |
| 7 days | A patch or a documented mitigation |
| 14 days | A release containing the fix |

If we cannot meet a deadline, we will tell you why and give a new date. You will
be credited in the release notes and the Hall of Fame unless you prefer to stay
anonymous.

---

## Scope

### In scope

- The FastAPI backend (`backend/app/`)
- The Next.js frontend (`frontend/src/`)
- Authentication, authorisation, and the key vault
- The Docker images and `docker-compose.yml`
- The install and update scripts

### Out of scope

- Third-party dependencies (report those upstream, and tell us so we can track them)
- Issues requiring an already-compromised host
- Social engineering of maintainers or users
- Denial of service against a self-hosted instance you control

---

## Security measures in place

### Authentication and secrets

| Control | Detail |
|---|---|
| Password hashing | bcrypt, cost factor 12, `$2b$` prefix, used directly without passlib |
| Token | JWT HS256, claims `sub` / `iat` / `exp` / `role`, 30-minute lifetime |
| Secret strength | `API_SECRET_KEY` is validated with `min_length=32`; there is no default value |
| Admin bootstrap | `ADMIN_PASSWORD` shorter than 12 characters is rejected |
| Secret storage | all secrets come from `.env`, which is in `.gitignore` |

### Authorisation

| Control | Detail |
|---|---|
| RBAC | Admin / Trader / Viewer, enforced through FastAPI dependencies |
| User management | `POST /auth/register` and `/auth/users/*` require ADMIN |
| Audit trail | successful and failed logins, plus every user mutation, are recorded |

### Key vault

Exchange API keys never touch the database. They are written to a dedicated
directory with mode `0700`, inside a file with mode `0600`, using an atomic
write so a crash cannot leave a truncated key. The location is configurable via
`AARK_VAULT_DIR` and is backed by a persistent `vaultdata` volume in Compose.

### Containers

| Control | Detail |
|---|---|
| Non-root | `appuser` (uid 1001) and `nextjs` (uid 1001) |
| Multi-stage builds | build tooling is not present in the runtime image |
| Health checks | `curl` on the backend, `node fetch` on the frontend |
| Network exposure | backend publishes on `127.0.0.1` by default |

### Backups

`./backup.sh` produces AES-256-CBC encrypted archives containing `.env`, a
PostgreSQL dump, the Redis append-only file, and the key vault. The key is read
from `BACKUP_ENCRYPTION_KEY`. Store that key **separately** from the backups —
an encrypted backup next to its key is not encrypted.

---

## Known open security items

These are disclosed deliberately. A hidden gap is worse than a tracked one.

| Item | Severity | Status |
|---|---|---|
| Seven business routes are unauthenticated: `POST /api/v1/agent/evaluate`, `/api/v1/agents/*`, `POST /api/v1/nobitex/save-key`, `DELETE /api/v1/nobitex/key`, `GET /api/v1/nobitex/status`, `POST /api/v1/integrations/accounting/sync` | **High** | [`ROADMAP.md`](ROADMAP.md) phase 1 |
| No rate limiting on `/auth/login` | Medium | Phase 1 |
| No two-factor authentication | Medium | Phase 3 |
| WebSocket token passed as a query parameter | Low | Phase 3 — header-based upgrade is not possible in the browser API |

### Interim mitigation for the unauthenticated routes

Until phase 1 closes, do one of the following:

1. Keep the backend bound to `127.0.0.1` (the Compose default), **or**
2. Place an authenticating reverse proxy in front of it, **or**
3. Run it on an isolated network with no external route.

---

## Hardening checklist for operators

- [ ] Replace every placeholder secret in `.env`
- [ ] `chmod 600 .env`
- [ ] Confirm `.env` is not tracked: `git status --porcelain` shows nothing
- [ ] Set `BACKEND_CORS_ORIGINS` to the exact origins you serve
- [ ] Set `DEBUG=false` so Swagger UI stays disabled
- [ ] Publish the backend on `127.0.0.1`, never `0.0.0.0`, without a proxy
- [ ] Put TLS in front of everything
- [ ] Store `BACKUP_ENCRYPTION_KEY` away from the backup archives
- [ ] Mount `AARK_VAULT_DIR` on a persistent, encrypted volume
- [ ] Rotate `API_SECRET_KEY` on a schedule — note that this invalidates live tokens
- [ ] Subscribe to repository security advisories

---

## Hall of Fame

We thank the following people for responsible disclosure. Add yourself by
reporting privately.

| Researcher | Finding | Date |
|---|---|---|
| — | — | — |

---

<div align="center">

[`README.md`](README.md) · [`CONTRIBUTING.md`](CONTRIBUTING.md) ·
[`ROADMAP.md`](ROADMAP.md) · [Report privately](https://github.com/ansariaiadmin/aark-kernel/security/advisories/new)

</div>
