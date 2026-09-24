# Roadmap — aark-kernel

## Done (v1.0.0)

- [x] **Level 1 Production Hardening**: structured JSON logging + correlation IDs, health liveness/readiness, error middleware, Pydantic Settings, Prometheus metrics, DB models
- [x] **Level 2 Advanced AI**: multi-model router (Ollama/OpenAI/Anthropic/Groq), conversation memory + summarization, SSE streaming, 13 tools, dynamic model registration
- [x] **Level 3 Real Trading**: Nobitex client market/limit/stop, position tracking + PnL, portfolio manager, trading API
- [x] **Level 4 Risk**: VaR Historical/Parametric/Monte Carlo, CVaR, 6 stress scenarios, correlation + HHI, dynamic position sizing
- [x] **Level 5 Enterprise**: JWT + bcrypt + RBAC, audit logging, WebSocket pub/sub, multi-user vaults
- [x] **Frontend**: Next.js dashboard with TradingView iframe live chart, real-time WebSocket market/position/order updates
- [x] **Tests**: 39 risk+paper + 7 v22 = 46 passed, zero env via mocking
- [x] **Docker**: compose healthy postgres+redis+backend+frontend
- [x] **CI**: ruff + pytest + build
- [x] **Docs**: README badge+mermaid+quickstart, CHANGELOG, AGENTS

## v2 (Explicit, Honest — No Hidden Gaps)

### Why v2?
- **recharts LineChart**: Current uses TradingView iframe for live chart (external dependency). v2 will implement custom LineChart via recharts for offline analytics, backtest visualization, PnL history. Reason: TradingView covers MVP live chart; custom chart needs historical data pipeline + recharts dependency (currently not installed to keep bundle small).
- **VaR Backtest**: Historical vs Parametric backtest exists in tests (test_var_parametric_vs_historical_similar) but needs formal backtest report endpoint GET /risk/var/backtest with Kupiec POF test. Reason: requires 1-year historical price DB + scheduler.
- **Nobitex WebSocket Real**: Paper trader simulates WebSocket via price polling. v2 will add real Nobitex WebSocket client (private channel for order updates, public for ticker). Reason: needs live Nobitex API key + WS infra, currently mocked for deterministic tests.
- **OCR/Translation/Layout**: Not applicable — trading platform.
- **Multi-Exchange**: Currently Nobitex only. v2: Binance, OKX adapters. Reason: exchange-specific order types + fee models.

### Next Steps
1. Implement recharts LineChart component for PnL + backtest
2. Add GET /risk/var/backtest with Kupiec test + historical VaR violation count
3. Real Nobitex WS client + reconnection + heartbeat
4. Multi-exchange abstraction + fee model
5. Formal audit + pen-test for JWT + RBAC
