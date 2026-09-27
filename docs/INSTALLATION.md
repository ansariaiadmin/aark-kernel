# Installation & Operations Guide

**Version:** 3.3.0
**Audience:** system administrators and engineers
**Replaces:** the former root-level `INSTALL.md`

---

## Contents

1. [Deployment options](#deployment-options)
2. [Option A — automated install](#option-a--automated-install)
3. [Option B — manual, step by step](#option-b--manual-step-by-step)
4. [Environment variables](#environment-variables)
5. [Verifying the installation](#verifying-the-installation)
6. [Backup, update, rollback](#backup-update-rollback)
7. [Operations reference](#operations-reference)
8. [Production hardening checklist](#production-hardening-checklist)

---

## Deployment options

| Option | Best for | Effort |
|---|---|---|
| **A — `install.sh`** | most users, single host | 1 command |
| **B — manual Docker Compose** | custom ports, custom volumes | ~10 minutes |
| **C — local development** | contributors changing code | ~10 minutes |

---

## Option A — automated install

```bash
git clone https://github.com/ansariaiadmin/aark-kernel.git
cd aark-kernel
chmod +x install.sh
./install.sh
```

The installer is **idempotent**: running it twice will not duplicate data or
overwrite an existing `.env` unless you confirm.

What it does, in order:

1. Checks Docker and Docker Compose versions
2. Checks that ports 3000 and 8000 are free
3. Prompts for `ADMIN_EMAIL` and `ADMIN_PASSWORD` (minimum 12 characters)
4. Writes `.env` from `.env.example`, substituting freshly generated 32-character
   secrets for `API_SECRET_KEY`, `POSTGRES_PASSWORD` and `REDIS_PASSWORD`
5. Runs `docker compose up -d --build`
6. Waits for the backend health endpoint to answer
7. Prints the dashboard URL and the admin credentials

### Windows

```cmd
install.bat
```

Requires Docker Desktop with WSL2 enabled.

---

## Option B — manual, step by step

### 1. Create the environment file

```bash
cp .env.example .env
chmod 600 .env
```

### 2. Set the three mandatory secrets

`.env.example` ships with placeholders. Replace them:

```bash
python3 - <<'PY'
import pathlib, secrets
p = pathlib.Path(".env")
s = p.read_text()
for key in ("API_SECRET_KEY", "POSTGRES_PASSWORD", "REDIS_PASSWORD"):
    s = "\n".join(
        f"{key}={secrets.token_urlsafe(32)}" if line.startswith(f"{key}=") else line
        for line in s.splitlines()
    ) + "\n"
p.write_text(s)
PY
```

> `API_SECRET_KEY` is validated with `min_length=32` at startup. A shorter value
> aborts the boot — this is deliberate, there are no default secrets.

### 3. Set the admin bootstrap

```bash
# .env
ADMIN_EMAIL=admin@aark-kernel.dev
ADMIN_PASSWORD=<at-least-12-characters>
AARK_VAULT_DIR=/home/appuser/.aark
```

> **Why this exists:** `POST /api/v1/auth/register` itself requires an existing
> ADMIN. Without a bootstrap admin, a fresh deployment had no way to create the
> first account. `db/init_db.py::bootstrap_admin` resolves this on startup, and
> is idempotent — it upgrades the role if the user exists but never overwrites
> an existing password.

### 4. Start the infrastructure

```bash
docker compose up -d postgres redis
```

Wait until both report healthy:

```bash
docker compose ps
```

### 5. Start the backend

```bash
cd backend
pip install -r requirements.txt
python -m app.db.init_db          # tables + bootstrap admin
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 6. Start the frontend

In a second terminal:

```bash
cd frontend
npm ci
npm run build && npm start        # or: npm run dev
```

> **Important:** the Next.js `rewrites()` proxy target is resolved at **build
> time**, not at runtime. To point the dashboard at a different backend, pass
> the build argument, not a runtime environment variable:
>
> ```bash
> AARK_BACKEND_ORIGIN=http://backend:8000 npm run build
> ```

---

## Environment variables

The authoritative list is [`.env.example`](../.env.example). CI enforces that
every `${VAR}` referenced by `docker-compose.yml` is documented there.

### Required — no default

| Variable | Purpose | Constraint |
|---|---|---|
| `API_SECRET_KEY` | JWT signing secret | minimum 32 characters |
| `POSTGRES_PASSWORD` | database password | set by the installer |
| `REDIS_PASSWORD` | Redis password | set by the installer |
| `DATABASE_URL` | async SQLAlchemy URL | `postgresql+asyncpg://…` |
| `REDIS_URL` | Redis URL | `redis://:…@…/0` |

### Application

| Variable | Default | Purpose |
|---|---|---|
| `APP_VERSION` | `3.3.0` | single source of truth for the version |
| `ENVIRONMENT` | `production` | affects `/docs` exposure |
| `DEBUG` | `false` | `true` enables Swagger UI |
| `LOG_LEVEL` / `LOG_FORMAT` | `INFO` / `json` | structured logging |
| `BACKEND_CORS_ORIGINS` | localhost origins | comma-separated allowlist |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | empty | admin bootstrap |
| `AARK_VAULT_DIR` | `~/.aark` | exchange-key vault location |
| `AARK_BACKEND_PORT` | `8000` | host port for the backend |
| `LOCAL_OLLAMA_HOST` | `http://localhost:11434` | local LLM endpoint |

> **Do not commit `.env`.** It is listed in `.gitignore`. Keep it at mode `600`.

---

## Verifying the installation

Run all of these — none of them require external services:

```bash
# 1. Container configuration is valid
docker compose config -q

# 2. Backend liveness
curl -fsS http://localhost:8000/api/v1/health/live

# 3. Backend readiness (DB, Redis, Ollama)
curl -fsS http://localhost:8000/api/v1/health/ready

# 4. Full test suite
cd backend && pytest tests/ -q          # → 109 passed

# 5. Frontend verification
cd ../frontend && npm run verify        # → eslint ✓ tsc ✓ build ✓
```

### The live chain, end to end

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=admin@aark-kernel.dev&password=<ADMIN_PASSWORD>' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

curl -s http://localhost:8000/api/v1/auth/me -H "Authorization: Bearer $TOKEN"
curl -s "http://localhost:8000/api/v1/risk/summary" -H "Authorization: Bearer $TOKEN"
```

Expected: `200` with a valid token, `401` without one.

---

## Backup, update, rollback

### Backup

```bash
./backup.sh
```

Produces an AES-256 encrypted archive containing `.env`, the PostgreSQL dump,
the Redis append-only file, and the key vault. The encryption key comes from
`BACKUP_ENCRYPTION_KEY` in `.env`. The last 7 archives are retained.

### Update

```bash
./update.sh
```

Order of operations: backup → `git pull` → rebuild → health check. If the health
check fails, the script prints the rollback command instead of applying it.

### Manual rollback

```bash
./stop.sh
git checkout <previous-tag>
./start.sh
# then restore the matching backup archive
```

---

## Operations reference

| Task | Command |
|---|---|
| Start / stop | `./start.sh` · `./stop.sh` |
| Service status | `./status.sh` |
| Follow logs | `./logs.sh` · `./logs.sh backend` |
| Health check | `./smoke-test.sh` |
| Database shell | `docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB` |
| Redis shell | `docker compose exec redis redis-cli -a $REDIS_PASSWORD` |
| Rebuild one service | `docker compose build backend` |
| Regenerate API docs | `cd backend && python scripts/generate_api_docs.py` |
| OpenAPI schema | `GET /api/v1/../openapi.json` |

> `/docs` (Swagger UI) is disabled when `DEBUG=false`. Set `DEBUG=true` and
> rebuild to enable it.

---

## Production hardening checklist

Work through this before exposing the platform beyond localhost.

- [ ] `API_SECRET_KEY` is at least 32 characters and not the `.env.example` value
- [ ] `.env` is mode `600` and not tracked by git
- [ ] `ADMIN_PASSWORD` is at least 12 characters and unique to this deployment
- [ ] `BACKEND_CORS_ORIGINS` lists only the origins you actually serve
- [ ] Backend is published on `127.0.0.1`, not `0.0.0.0` (the default in `docker-compose.yml`)
- [ ] A reverse proxy with TLS and authentication fronts the backend
- [ ] `BACKUP_ENCRYPTION_KEY` is set and stored separately from the backups
- [ ] `AARK_VAULT_DIR` is on a persistent volume (`vaultdata` in Compose)
- [ ] Log rotation is configured for `logs/`
- [ ] You have read [`SECURITY.md`](../SECURITY.md) and understood the open items in [`ROADMAP.md`](../ROADMAP.md) phase 1

> **Open security item (v3.3.0):** seven business routes are still unauthenticated —
> `POST /api/v1/agent/evaluate`, the `/api/v1/agents/*` group,
> `POST /api/v1/nobitex/save-key`, `DELETE /api/v1/nobitex/key`,
> `GET /api/v1/nobitex/status`, and `POST /api/v1/integrations/accounting/sync`.
> Do not expose the backend to an untrusted network until phase 1 closes this.

---

<div align="center">

[`README.md`](../README.md) · [`USER_GUIDE_FA.md`](USER_GUIDE_FA.md) ·
[`USER_GUIDE_EN.md`](USER_GUIDE_EN.md) · [`ARCHITECTURE.md`](../ARCHITECTURE.md)

</div>
