# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**Version source of truth:** `backend/app/core/config.py` → `Settings.APP_VERSION`.
The test `backend/tests/test_release_consistency.py` fails in CI if `README.md`,
`CHANGELOG.md`, or `frontend/package.json` drift away from it.

---

## [3.3.0] — 2026-09-27

**Phase 0 — build integrity and wiring.**

This release closes the first phase of [`ROADMAP.md`](ROADMAP.md): making the
project build, install, and actually reach its own endpoints. It follows a full
dimensional audit of the repository tree, the module graph, and the request
wiring — see [`docs/AUDIT.md`](docs/AUDIT.md) for the 45 findings with evidence.

### Fixed — critical (the application did not work)

- **23 endpoints returned to the application.** `app.api.v1.api_router` was
  created as an import side effect and then discarded; `main.py` mounted only
  `health.router`. Live routes went from **11 to 39** (ai, auth, trading, risk,
  WebSocket).
- **`next build` succeeded.** Three errors (`TS2304: Cannot find name '_e'` ×2 in
  `page.tsx`, and `TS2307: Cannot find module 'recharts'`) meant the frontend
  image could never be built, which killed `docker compose build`, `install.sh`,
  and CI.
- **Password hashing repaired.** `passlib 1.7.4` is incompatible with
  `bcrypt>=4.1`: it probes `bcrypt.__about__`, which was removed, and raises
  `ValueError` on passwords longer than 72 bytes. Every call to
  `get_password_hash()` failed, so `POST /auth/register` always returned 500 and
  **no user could ever be created**. passlib was removed and bcrypt is now used
  directly. The `$2b$` prefix is preserved, so previously stored hashes still
  verify.
- **The fresh-install deadlock is broken.** `install.sh` wrote
  `ADMIN_EMAIL` / `ADMIN_PASSWORD` into `.env`, but no code created that user,
  and `POST /auth/register` itself requires an existing ADMIN. An idempotent
  `bootstrap_admin()` was added: it rejects passwords shorter than 12
  characters, upgrades the role of an existing user, and never overwrites an
  existing password.
- **CI repaired.** `API_SECRET_KEY=test_secret_32_bytes_min_for_ci` is exactly
  31 characters against `Field(..., min_length=32)`, so the entire job died
  during collection and no test ran.
- **The Docker CI job is repaired — this one had never been seen before.** All
  four Compose services declared `env_file: - .env`, but the Docker job only ran
  `actions/checkout` and never created a `.env`. Docker Compose v2 exits 1 with
  `env file .env not found`, so `docker compose config` had **never** passed in
  CI since the workflow was added. `env_file` is now `path: .env` with
  `required: false` (a fresh clone works without `.env`, because every value the
  application needs is also declared under `environment:` with a default), and
  the job materialises a real `.env` from `.env.example`, replacing the
  placeholder secrets with 32-character values.
- **New CI guard:** every `${VAR}` referenced by `docker-compose.yml` must either
  be documented in `.env.example` or carry an inline default; otherwise a fresh
  install silently receives a blank value and the job fails.

### Fixed — wiring and contracts

- **CORS is actually registered.** `BACKEND_CORS_ORIGINS` was dead configuration
  and no `CORSMiddleware` existed, so the frontend on `:3000` could not reach the
  API on `:8000`.
- **The frontend reaches the correct origin.** All calls were relative
  `fetch('/api/v1/...')` and landed on the Next server. `next.config.mjs` now
  has `rewrites()` and `src/lib/api.ts` is the single source of addresses.
- **WebSocket is live.** `page.tsx` read `localStorage['aark_token']`, which
  nothing in the application ever wrote, and the address was hardcoded to
  `ws://localhost:8000` (blocked as mixed content under HTTPS). A real login
  page, `src/lib/auth.ts`, `wsUrl()`, and reconnect with backoff were added.
- **The `POST /risk/validate` contract is fixed.** Because `daily_pnl` and
  `portfolio_value` are scalars, FastAPI bound them as **query** parameters while
  the dashboard sent everything in a JSON body, so the call always returned 422.
  Explicit request models (`RiskValidateRequest`, `StressTestRequest`,
  `LegacyValidateRequest`) were added.
- **`GET /trading/portfolio/value` is fixed.** The ticker was fetched and
  discarded, and `Decimal(0)  # Placeholder` stood in for the price, so every
  non-IRR asset had a value of zero. A real `NobitexClient.get_price()` was
  added.
- **`RuntimeError` in `broadcast_to_subscription` is fixed.** `disconnect()`
  mutated the same dictionary being iterated, so the first dead socket killed
  publishing for every subscriber.
- **WebSocket authentication errors are fixed.** A `RuntimeError` escaped
  `get_websocket_user` before the `try/finally`; `WebSocketAuthError` is now
  translated into a clean close code 1008.
- **`get_current_user` is fixed.** The JWT emits `sub` as a string, but it was
  passed to `get_user_by_id` without conversion, comparing against an INTEGER
  primary key.
- **`GET /auth/login` and `Token.expires_in` are joined to a single TTL
  source**, and the `iat` claim was added so token age is now determinable.

### Changed — parallel sources of truth removed

- **`AgentBrain` is a singleton.** `main.py` and `api/v1/ai.py` each built one,
  producing two separate conversation memories; `/ai/agent/memory/clear` cleared
  the wrong one. It now lives in `app/core/agent.py`.
- **The exchange-key vault is unified.** `main.py` wrote with mode `0600` while
  `api/v1/trading.py` read the same path with no checks at all. `app/core/vault.py`
  now performs an atomic write with `0700` on the directory and `0600` on the
  file.
- **`RiskProfile` / `DeterministicRiskEngine` are merged.** Two separate
  definitions existed in `evaluator.py` and `advanced.py`; the agent path and the
  API path could silently diverge.
- **The orphaned root `app/` package was removed.** Without `__init__.py` it
  formed a namespace package that shadowed `backend/app` whenever the repository
  root was on `sys.path`, so `import app.main` failed with `ModuleNotFoundError`.
  Its content was a byte-for-byte duplicate of `backend/app/lib/logger.py`.

### Added

- **55 new tests** — `test_api_wiring.py` (39) and
  `test_release_consistency.py` (16). None require an external service: real
  SQLite and `ASGITransport`, with **no mocks at the HTTP boundary**, because
  mocking is precisely what allowed these bugs to stay hidden. Total: **54 → 109**.
- `DELETE /api/v1/nobitex/key` — a real kill switch for removing the exchange key.
- **Dead UI brought to life:** chat / orders / positions / analytics tabs with
  active state, order and position tables (previously fetched data was discarded
  into `_orders` / `_positions`), BUY/SELL buttons, a Refresh button, a working
  kill switch, and a login page.
- `LineChart.tsx` and `OrderBook.tsx`, previously fully orphaned, now render in
  the Analytics tab.
- `src/lib/api.ts` and `src/lib/auth.ts` — the single source of addresses and
  session handling.
- `backend/requirements-dev.txt` — pytest and ruff are no longer installed into
  the production image.
- `backend/scripts/generate_api_docs.py` — regenerates `docs/API.md` from the
  live OpenAPI schema. A test fails if the committed copy is stale.
- CI: a separate frontend job (eslint, tsc, `next build`), an import smoke test,
  and an aggregate `ci` status check for branch protection.
- **Working PWA assets.** `manifest.json` previously referenced `/icon-192.png`
  and `/icon-512.png`, neither of which existed, and the file itself sat in an
  orphaned root `public/` directory that Next.js never serves. The manifest and
  both icons now live in `frontend/public/` and are linked from `layout.tsx`.
- **A persistent vault volume.** `docker-compose.yml` now mounts `vaultdata` at
  `AARK_VAULT_DIR`; previously the exchange key was lost on every restart.
- `ADMIN_EMAIL`, `ADMIN_PASSWORD` and `AARK_VAULT_DIR` are documented in
  `.env.example` with Persian explanations of what each one is and why it exists.

### Fixed — quality

- `RequestLoggingMiddleware` excluded `/health` and `/metrics`, but the real paths
  are `/api/v1/...`, so every Docker health check produced two INFO log lines.
- `from datetime import ...` moved from the **end** of `api/v1/risk.py` to the top;
  three duplicate local `import numpy` statements and a meaningless
  `if 'np' in globals()` expression were removed.
- The deprecated Pydantic v1 `class Config:` replaced with `ConfigDict`.
- The deprecated `pythonjsonlogger.jsonlogger` import path replaced with one
  compatible with both versions.
- `eslint.config.mjs` configured the `react-hooks/exhaustive-deps` rule although
  that plugin is not installed, so ESLint 9 aborted the entire lint run.
- `postcss.config.js` and `tailwind.config.js` use `module.exports` but the ESLint
  config assumed ESM, producing `'module' is not defined`.
- `bg-card` and `text-muted-foreground` defined in the Tailwind configuration;
  they were previously silently dropped.
- Unused `setAsks` in `OrderBook.tsx` and unused `background_tasks` in
  `/trading/orders/batch` removed.
- `tsconfig.tsbuildinfo` untracked and added to `.gitignore`.
- `.gitignore` completed with `runtime/`, `backups/`, `*.vault`, `*.tsbuildinfo`,
  `.pytest_cache/`, and `.ruff_cache/`.

### Security

- **Seven business routes remain unauthenticated** — `POST /api/v1/agent/evaluate`,
  the `/api/v1/agents/*` group, `POST /api/v1/nobitex/save-key`,
  `DELETE /api/v1/nobitex/key`, `GET /api/v1/nobitex/status`, and
  `POST /api/v1/integrations/accounting/sync`. This is disclosed rather than
  hidden and is scheduled for phase 1 of [`ROADMAP.md`](ROADMAP.md). Until then,
  run the backend on `127.0.0.1` or behind an authenticating reverse proxy; the
  Compose default already binds to `127.0.0.1`.
- No default secrets exist. `API_SECRET_KEY` is validated with `min_length=32`
  and the admin bootstrap rejects passwords shorter than 12 characters.

### Known gaps — deliberately open, tracked in ROADMAP

The following were **documentation claims that the code did not support**. Rather
than hiding them, they are recorded explicitly in phases 1–3 of
[`ROADMAP.md`](ROADMAP.md):

- All 13 agent tools are still stubs (`{"price": 0}`, `{"order_id": "new_order_id"}`).
- `/risk/var` and `/risk/correlation` return `np.random.normal` output rather than
  real market data.
- `services/notification/` and `services/sms/` are still orphaned — the README
  promised real SMS with fallback and throttling.
- `services/paper_trader.py` is still not wired into the application (87
  references in tests, 0 in the application).
- Around 30 `.env.example` keys are still not read by `Settings`;
  `extra="ignore"` silently discards them.
- `robots/intelligence/` is entirely orphaned.
- `backend/app/static/index.html` is a second, parallel dashboard.
- No database migrations (no Alembic); the schema is created by `init_db.py`.

---

## Earlier releases

The following entries are preserved for history and use the older, less
structured format.

### [1.0.1] — 2026-09-24 — Non-Technical Auto Install + Auto Update Edition

**Added**

- `install.sh`: automated clean install — checks Docker, creates `.env` with
  random `openssl` secrets, runs `docker compose up --build -d`, waits, health
  checks, and prints the URL and credentials.
- `update.sh`: automated update — backup to `backups/YYYYMMDD-HHMMSS/`,
  `git pull origin main`, `docker compose pull` + `up --build -d`, health check,
  rollback hint.
- `start.sh`, `stop.sh`, `status.sh`, `logs.sh`, `backup.sh` — simple daily
  commands.
- `install.bat`, `start.bat`, `stop.bat`, `status.bat`, `logs.bat`, `update.bat`,
  `backup.bat` — Windows equivalents for non-technical users.
- `docs/INSTALLATION.md`, `docs/USER_GUIDE_FA.md`, `docs/USER_GUIDE_EN.md`.
- A "For Non-Technical Users" section in the README with a one-line installer.

**Fixed**

- Clean presentation: cache artifacts removed, only `.env.example` tracked.
- Non-technical UX: bilingual, colourised, step-by-step messages.

### [1.0.0] — 2026-09-24

**Added**

- Multi-model AI router (Ollama, OpenAI, Anthropic, Groq) with dynamic registration.
- Conversation memory with summarisation, SSE streaming, 13 built-in tools.
- Nobitex trading engine and paper trading with 0.1–0.3% slippage and PnL tracking.
- Advanced risk engine: VaR (historical, parametric, Monte Carlo), CVaR, 6 stress
  scenarios, correlation and HHI.
- JWT authentication (HS256, 30-minute expiry), bcrypt cost 12, RBAC
  (Admin / Trader / Viewer).
- WebSocket manager with pub/sub and per-user isolated vaults.
- Docker Compose with healthy PostgreSQL 16, Redis 7, FastAPI backend and a
  Next.js frontend.
- CI: ruff, pytest, build, Docker health check.
- Tests: 39 risk and paper-trading tests plus 7 v22 tests, 46 passing.

**Fixed**

- `test_v22` fixtures patched `init_db` and the engine so no environment is required.
- `utcnow` deprecation fixed across 8 files.
- recharts integrated via the analytics chart.

**Security**

- No private keys, `.env.example` complete, non-root containers, secrets from the
  environment only.

### [0.9.0] — 2026-09-07

Previous enterprise release, 39 tests.

---

[Unreleased]: https://github.com/ansariaiadmin/aark-kernel/compare/v3.3.0...HEAD
[3.3.0]: https://github.com/ansariaiadmin/aark-kernel/releases/tag/v3.3.0
