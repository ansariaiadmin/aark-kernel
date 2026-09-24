# Changelog — aark-kernel

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-09-24

### Added
- Multi-model AI router (Ollama, OpenAI, Anthropic, Groq) with dynamic registration
- Conversation memory + summarization, SSE streaming, 13 built-in tools
- Nobitex real trading engine + paper trading with slippage 0.1-0.3%, PnL tracking
- Advanced risk engine: VaR Historical/Parametric/Monte Carlo, CVaR, stress 6 scenarios, correlation + HHI
- JWT auth (HS256, 30-min expiry) + bcrypt cost 12 + RBAC (Admin/Trader/Viewer)
- WebSocket manager with pub/sub, multi-user isolated vaults
- TradingView live chart iframe, real-time market data via WebSocket
- Tests: 39 risk + paper trading + 7 v22 (mocked env, zero env required) = 46 passed
- Docker Compose healthy: postgres 16, redis 7, backend FastAPI, frontend Next.js
- CI: ruff + pytest + build + docker healthcheck
- Docs: README badge+mermaid+quickstart+sample output, ROADMAP Done vs v2 honest

### Fixed
- test_v22 fixture/mock zero env: patch app.db.init_db.init_db AsyncMock + engine MagicMock, postgresql+asyncpg URL, API_SECRET_KEY env mock
- utcnow deprecation fixed across 8 files (session, models, risk, trading, auth)
- recharts TODO: implemented via TradingView iframe; recharts explicit v2 for custom LineChart analytics

### Security
- Secret scan 0, no private key, .env.example complete
- Non-root Docker, secrets via env only

## [0.9.0] - 2026-09-07

- Previous enterprise release with 39 tests
