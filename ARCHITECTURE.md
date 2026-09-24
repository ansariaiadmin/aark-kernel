# ARCHITECTURE.md — aark-kernel — Enterprise Financial Trading Platform

## ۲. aark-kernel — Enterprise Financial Trading Platform

### Purpose
AI trading platform with risk engine, agent brain, paper trading, Nobitex integration, multi-user vaults, real-time WebSocket.

### Graph
```mermaid
graph TD
    User --> Frontend[frontend<br/>Next.js 22 standalone<br/>USER nextjs<br/>HOSTNAME 0.0.0.0]
    Frontend --> Backend[backend<br/>FastAPI<br/>python:3.12-slim<br/>USER appuser<br/>lifespan]
    Backend --> Postgres[(Postgres 16<br/>pgdata<br/>healthcheck)]
    Backend --> Redis[(Redis 7<br/>requirepass<br/>healthcheck)]
    Backend --> Ollama[Ollama<br/>host.docker.internal:11434<br/>extra_hosts]

    subgraph BackendInternal[Backend Internal Graph]
        Main[main.py<br/>FastAPI lifespan<br/>setup_logging + init_db]
        Main --> Config[core/config.py<br/>get_settings<br/>env only]
        Main --> Logging[core/logging.py<br/>json format]
        Main --> Middleware[middleware/logging.py]
        Main --> Health[api/v1/health.py<br/>/health/live + /ready]
        Main --> Agent[agent/brain.py<br/>AgentBrain]
        Main --> Registry[agent/registry.py<br/>AgentConfig + Message]
        Main --> Risk[risk_engine/evaluator.py<br/>DeterministicRiskEngine<br/>RiskProfile]
        Main --> Services[services/*<br/>trading, market]
        Main --> WS[websockets/manager.py<br/>pub/sub]
        Main --> DB[db/session.py<br/>engine + dispose]
        Main --> InitDB[db/init_db.py]
        Risk --> Vault[~/.aark/nobitex.vault<br/>mode 0o700<br/>isolated]
        Agent --> Ollama
        Services --> Postgres
        Services --> Redis
    end

    Backend --> HealthCheck[HEALTHCHECK curl /api/v1/health/live]
    Frontend --> HealthCheckFE[HEALTHCHECK node fetch]
```

### Connections
- **Frontend → Backend:** NEXT_PUBLIC_API_URL=http://localhost:${AARK_BACKEND_PORT:-8000}/api/v1 — via env, not hardcoded
- **Backend → Postgres:** DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB} — from env, no hardcoded
- **Backend → Redis:** REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0 — from env
- **Backend → Ollama:** LOCAL_OLLAMA_HOST=http://host.docker.internal:11434 via extra_hosts host-gateway — local LLM
- **Risk → Vault:** ~/.aark/nobitex.vault with 0o700, isolated per user, not in DB
- **Lifespan:** setup_logging → init_db → yield → engine.dispose — clean startup/shutdown

### Modern Standards Check
- ✅ **Clean Architecture:** api (delivery), core (config), services (use cases), models (domain), db (infra), risk_engine (domain service) — layered
- ✅ **12-Factor:** Config via env_file, no hardcoded secrets, logs json, port binding, healthchecks, disposability via lifespan
- ✅ **Security:** JWT 30-min HS256, bcrypt cost 12, RBAC Admin/Trader/Viewer, audit logging, non-root USER appuser+nextjs, secrets via env only, vault 0o700
- ✅ **Observability:** /health/live + /ready, logging json, middleware logging, healthcheck in compose
- ✅ **Scalability:** Stateless FastAPI (except vault file), horizontal scalable, Redis for pub/sub, Postgres for persistence
- ✅ **Docker Best:** Multi-stage builder+runner, python:3.12-slim-bookworm + node:22-alpine, USER, HEALTHCHECK, depends_on service_healthy, env_file
- ✅ **Frontend Best:** Standalone output, poweredByHeader false, compress true, HOSTNAME 0.0.0.0, USER nextjs
- ⚠️ **Product Gap:** Needs real LineChart, order book, ML risk — product 8.0/10

### Deep Issues Fixed
- **Hardcoded Secrets:** Previously POSTGRES_PASSWORD:-secure_aark_pass_2026 hardcoded — fixed to require from .env, no defaults
- **Root Docker:** Previously ran as root — fixed to USER appuser 1001 + USER nextjs 1001
- **No HEALTHCHECK Frontend:** Fixed
- **No Standalone:** Fixed next.config.mjs standalone
- **CVE-2025-66478:** next 15.1.0 → 16.3.6 fixed
- **Vault Permissions:** Ensure 0o700 — checked

---


