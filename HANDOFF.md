# Engineering Handoff Notes

**Version:** 3.3.0
**Last updated:** 2026-09-27
**Purpose:** orient the next engineer in under ten minutes

---

## Read these first, in this order

1. [`README.md`](README.md) — what the platform does and how it is verified
2. [`ARCHITECTURE.md`](ARCHITECTURE.md) — layers, request lifecycle, design decisions
3. [`ROADMAP.md`](ROADMAP.md) — what is planned, with release gates
4. [`docs/AUDIT.md`](docs/AUDIT.md) — the 45 findings that drove v3.3.0
5. [`CHANGELOG.md`](CHANGELOG.md) — what changed and why

---

## Where the project actually stands

Phase 0 of [`ROADMAP.md`](ROADMAP.md) is complete. The platform **builds,
installs, and reaches its own endpoints** — which it did not before v3.3.0.

| Dimension | State |
|---|---|
| Build | `next build`, `ruff`, `tsc --noEmit`, `eslint` all clean |
| Tests | 109 passing, no external services required |
| CI | 4/4 jobs green, including the Docker image build |
| Endpoints | 39 live, matching the OpenAPI schema |
| Authentication | bcrypt, JWT with 30-minute expiry, RBAC — working and tested |
| Risk engine | Deterministic, no I/O, 25 tests |
| Data realism | **Synthetic** — see phase 2 |
| Agent tools | **13 stubs** — see phase 2 |

### The one thing to understand before changing anything

The pre-v3.3.0 codebase had **parallel sources of truth**: two `AgentBrain`
instances, two `RiskProfile` definitions, two key-vault implementations, and a
risk implementation duplicated between the engine and the API layer. Those have
been unified. If you find yourself about to add a second copy of something,
stop — extend the existing one instead.

---

## What was fixed in v3.3.0, in one paragraph

`main.py` mounted only the health router, so 23 endpoints were unreachable.
`passlib` was incompatible with `bcrypt>=4.1`, so no user could ever be
registered. `install.sh` wrote admin credentials that nothing created, and
`POST /auth/register` itself required an ADMIN, so a fresh install had no way
in. The frontend never wrote the JWT it read, so the WebSocket never connected.
`next build` failed on three errors, so no image could be built. CI had a
31-character secret against a 32-character minimum, and the Docker job required
a `.env` that it never created. All of it is fixed and tested; the details are in
[`CHANGELOG.md`](CHANGELOG.md).

---

## Running it

```bash
./install.sh          # full install, idempotent
./start.sh            # start
./status.sh           # status
./logs.sh backend     # logs
./smoke-test.sh       # full-chain smoke test
./update.sh           # backup → pull → rebuild → health check
```

```bash
# Backend tests
cd backend
API_SECRET_KEY=<32+ chars> \
DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/test \
REDIS_URL=redis://:test@localhost:6379/0 \
pytest tests/ -q
```

```bash
# Frontend verification
cd frontend && npm run verify
```

> **Keep the virtual environment outside the repository.** It is easy to commit
> accidentally otherwise.

---

## Traps that have already cost time

| Trap | What happens | Avoid it by |
|---|---|---|
| `rewrites()` is evaluated at **build time** | a runtime `AARK_BACKEND_ORIGIN` is ignored | passing it as a build argument |
| Scalar parameters mixed with a dict body | FastAPI binds them as query → 422 | using Pydantic request models |
| `API_SECRET_KEY` under 32 characters | startup aborts, no test runs | using a 32+ character value |
| `passlib` with `bcrypt>=4.1` | `ValueError` on every hash | using bcrypt directly |
| Root `public/` directory | Next.js serves only `frontend/public` | keeping assets under `frontend/` |
| Mocking at the HTTP boundary | broken contracts stay invisible | using `ASGITransport` and real SQLite |
| Committing `tsconfig.tsbuildinfo` | noisy diffs after every build | it is in `.gitignore` |

---

## Open items, by priority

Taken from [`ROADMAP.md`](ROADMAP.md) — the full list with acceptance criteria
lives there.

| Priority | Item | Phase |
|---|---|---|
| **P0 — security** | Seven business routes are unauthenticated, including `POST /nobitex/save-key` | 1.1 |
| **P1 — security** | No rate limiting on `/auth/login` | 1.2 |
| **P1 — correctness** | `/risk/var` and `/risk/correlation` return synthetic data | 2.1, 2.2 |
| **P2 — product** | 13 agent tools are stubs | 2.5 |
| **P2 — hygiene** | `paper_trader`, `notification/`, `sms/`, `robots/` are orphaned | 2.8–2.10 |
| **P3 — operations** | No Alembic migrations | 3.1 |

---

## Things that are *not* broken, despite looking it

| Looks wrong | Actually |
|---|---|
| `/risk/var` returns different numbers each call | it is Monte Carlo on synthetic data by design until phase 2 |
| The WebSocket takes `?token=` | browsers cannot set headers on an upgrade request |
| `env_file` is optional in Compose | deliberate, so a fresh clone can be validated |
| `docs/API.md` looks machine-generated | it is — regenerated from OpenAPI, and a test enforces freshness |

---

## If you only do one thing

Close **1.1** — authenticate the seven unprotected routes. It is the highest
severity item in the project and it is a small, well-scoped change with clear
acceptance criteria.
