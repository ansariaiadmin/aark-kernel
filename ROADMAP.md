# Roadmap

**Version:** 3.3.0

This document is the single place where planned work lives. Nothing here is
claimed as done. Each phase closes with a **release gate**; the version number
does not increase until its gate is green.

---

## Status at a glance

| Phase | Theme | Target | Status |
|---|---|---|---|
| **0** | Build integrity and wiring | v3.3.0 | ✅ **Complete** |
| **1** | Security hardening and documentation truth | v3.4.0 | 🔜 Next |
| **2** | Real data and a real agent | v3.5.0 | 📋 Planned |
| **3** | Product and operational maturity | v4.0.0 | 📋 Planned |

**Guard:** `backend/tests/test_release_consistency.py` turns CI red if
`README.md`, `CHANGELOG.md`, or `frontend/package.json` drift away from
`Settings.APP_VERSION`.

---

## Phase 0 — Build integrity and wiring — v3.3.0 ✅

Delivered 2026-09-27. See [`CHANGELOG.md`](CHANGELOG.md) for the full entry and
[`docs/AUDIT.md`](docs/AUDIT.md) for the findings that motivated it.

| # | Task | Artifacts |
|---|---|---|
| 0.1 | Restore 23 unmounted endpoints (11 → 39 live routes) | `app/main.py` |
| 0.2 | Repair `next build` (three TypeScript/recharts errors) | `frontend/src/app/page.tsx`, `package.json` |
| 0.3 | Replace passlib with direct bcrypt (incompatible with bcrypt ≥ 4.1) | `app/core/auth.py`, `requirements.txt` |
| 0.4 | Add an idempotent `bootstrap_admin()` | `app/db/init_db.py` |
| 0.5 | Break the fresh-install deadlock (register requires an ADMIN) | `.env.example`, `install.sh` |
| 0.6 | Fix the 31-character CI secret against `min_length=32` | `.github/workflows/ci.yml` |
| 0.7 | Fix three `next build` errors blocking every image build | `frontend/` |
| 0.8 | Add the `/api/v1/*` rewrite proxy; remove hardcoded origins | `next.config.mjs`, `src/lib/api.ts` |
| 0.9 | Real login page writing the JWT; live WebSocket | `src/lib/auth.ts`, `page.tsx` |
| 0.10 | Fix the `/risk/validate` body contract (422 on every call) | `app/api/v1/risk.py` |
| 0.11 | Fix `RuntimeError` in `broadcast_to_subscription` | `app/websockets/manager.py` |
| 0.12 | Translate WebSocket auth errors into close code 1008 | `app/websockets/manager.py` |
| 0.13 | Fix the string `sub` compared against an INTEGER key | `app/core/auth.py` |
| 0.14 | Fix the `Placeholder` price in `/trading/portfolio/value` | `app/api/v1/trading.py`, `services/trading.py` |
| 0.15 | Unify brain, vault, and RiskProfile — remove parallel sources | `app/core/agent.py`, `app/core/vault.py`, `risk_engine/*` |
| 0.16 | Remove the orphaned root `app/` package that shadowed `backend/app` | — |
| 0.17 | Fix frontend lint (ESLint config, globals, Tailwind tokens, `setAsks`) | `eslint.config.mjs`, `tailwind.config.js`, `OrderBook.tsx` |
| 0.18 | Bring the dead UI to life: tabs, kill switch, BUY/SELL, chart, order book | `page.tsx` |
| 0.19 | Add 55 tests (wiring 39 + release consistency 16) | `backend/tests/` |
| 0.20 | Split `requirements-dev.txt` from the production image | `backend/requirements*.txt` |
| 0.21 | Fix the permanently red Docker CI job and add a compose-variable guard | `.github/workflows/ci.yml`, `docker-compose.yml` |
| 0.22 | Working PWA assets and a persistent vault volume | `frontend/public/`, `docker-compose.yml` |

**Release gate — all green:**

- ✅ 109 tests passing
- ✅ `ruff check` zero errors
- ✅ `tsc --noEmit` zero errors
- ✅ `eslint .` zero errors
- ✅ `next build` exits 0
- ✅ 39 live routes, matching the OpenAPI schema
- ✅ Live chain verified: login → JWT → protected route
- ✅ All 4 CI jobs green

---

## Phase 1 — Security hardening and documentation truth — v3.4.0

**Theme:** close the security gaps that were disclosed rather than hidden, and
make every remaining documentation claim true.

### Security

| # | Task | Acceptance criteria |
|---|---|---|
| 1.1 | Authenticate the seven unprotected routes: `POST /agent/evaluate`, `/agents/*`, `POST /nobitex/save-key`, `DELETE /nobitex/key`, `GET /nobitex/status`, `POST /integrations/accounting/sync` | a test asserts 401 without a token and 200 with one, for each |
| 1.2 | Add rate limiting to `POST /auth/login` | repeated failures return 429; a test proves it |
| 1.3 | Move the ad-hoc routes out of `main.py` into the router split | `main.py` contains no route definitions |
| 1.4 | Add security headers (HSTS, X-Content-Type-Options, Referrer-Policy) | a test asserts the headers are present |
| 1.5 | Add an automated secret scan to CI | the job fails on a committed-looking secret |

### Documentation truth

| # | Task | Acceptance criteria |
|---|---|---|
| 1.6 | Read every `.env.example` key in `Settings`, or delete it | no key is silently dropped by `extra="ignore"`; a test asserts coverage |
| 1.7 | Reconcile `README.md` capability claims with the code | every row in the capability table is test-backed |
| 1.8 | Decide the fate of the orphaned subsystems (wire or delete) | no orphan module remains without a decision recorded here |
| 1.9 | Add an architecture decision record directory | each significant decision has an ADR |

### Quality

| # | Task | Acceptance criteria |
|---|---|---|
| 1.10 | Raise coverage on `api/v1/auth.py` and `api/v1/trading.py` | branch coverage ≥ 80% on both |
| 1.11 | Add a frontend test runner and the first component tests | `npm test` exists and passes in CI |

**Release gate for v3.4.0:**

- [ ] All seven routes authenticated, proven by tests
- [ ] Rate limiting on login, proven by a test
- [ ] Secret scan in CI
- [ ] No `.env.example` key silently ignored
- [ ] 109+ tests passing, all CI jobs green
- [ ] Documentation claims reconciled

---

## Phase 2 — Real data and a real agent — v3.5.0

**Theme:** replace synthetic and placeholder data with real market data, and
make the agent genuinely useful.

### Data

| # | Task | Acceptance criteria |
|---|---|---|
| 2.1 | Serve `/risk/var` from real historical prices | a test with recorded fixtures returns market-derived numbers, not `np.random` |
| 2.2 | Serve `/risk/correlation` from real price series | same |
| 2.3 | Persist market data to the `market_data` table | prices survive a restart |
| 2.4 | Add a historical backfill command | an operator can populate the price history |

### Agent

| # | Task | Acceptance criteria |
|---|---|---|
| 2.5 | Implement the 13 stub tools against real services | no tool returns a placeholder literal |
| 2.6 | Add tool-level tests | each implemented tool has a test |
| 2.7 | Make agent answers cite the tool output they used | responses include the data they relied on |

### Subsystem decisions

| # | Task | Acceptance criteria |
|---|---|---|
| 2.8 | Wire `paper_trader` into the application, or delete it | 87 test references and 0 application references is resolved either way |
| 2.9 | Wire `notification/` and `sms/` into the application, or delete them | the README promise matches reality |
| 2.10 | Resolve `robots/intelligence/` and `backend/app/static/index.html` | no parallel dashboard, no orphan package |

**Release gate for v3.5.0:**

- [ ] No synthetic data on any documented endpoint
- [ ] Every registered agent tool implemented and tested
- [ ] Every orphaned subsystem either wired or deleted
- [ ] All CI jobs green

---

## Phase 3 — Product and operational maturity — v4.0.0

**Theme:** the things that make this operable by a team rather than a single
operator.

| # | Task | Acceptance criteria |
|---|---|---|
| 3.1 | Alembic migrations replacing `init_db.py` | `alembic upgrade head` builds a fresh database; rollback tested |
| 3.2 | Two-factor authentication | TOTP enrolment and verification with tests |
| 3.3 | Header-based WebSocket authentication | the token no longer appears in URLs or logs |
| 3.4 | Real strategy framework with backtesting | at least one strategy runs against recorded data |
| 3.5 | Grafana dashboard and alert rules | latency, error rate, and readiness failures are alertable |
| 3.6 | Log aggregation guidance and rotation | `logs/` does not grow without bound |
| 3.7 | Load test the WebSocket fan-out | documented concurrent-connection ceiling |
| 3.8 | End-to-end tests in CI against real containers | the stack is exercised as a whole, not only in units |

**Release gate for v4.0.0:**

- [ ] Migrations tested forward and backward
- [ ] 2FA available and tested
- [ ] No token in any URL
- [ ] At least one backtestable strategy
- [ ] Observability stack documented and deployable
- [ ] End-to-end tests running in CI

---

## Technical debt register

Items that are not scheduled to a phase but are recorded so they are not lost.

| Item | Impact | Notes |
|---|---|---|
| `backend/app/static/index.html` | a second, parallel dashboard that will drift | phase 2.10 |
| ~30 unread `.env.example` keys | operators set values that do nothing | phase 1.6 |
| No Alembic | destructive schema changes are manual and risky | phase 3.1 |
| In-process agent memory | a restart loses conversation context | phase 3 |
| Single Ollama dependency | a hard dependency for the agent path | phase 2 |
| `robots/intelligence/` | dead code carried in the image | phase 2.10 |

---

## How to propose work

Open an issue describing the problem, then reference the phase it belongs to. If
it does not fit any phase, propose a new one — phases are cheap, undocumented
debt is not.
