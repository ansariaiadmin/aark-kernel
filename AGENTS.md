# Agents and Tools

**Version:** 3.3.0

An inventory of the AI agent layer: what exists, what it does, and what is still
a stub. This document is deliberately explicit about the stubs.

---

## Architecture

```
user query
    │
    ▼
AgentBrain  (app/agent/brain.py)          — memory, summarisation, tool selection
    │
    ├──► ModelRouter (app/agent/llm.py)   — Ollama / OpenAI / Anthropic / Groq
    │
    └──► Tool Executor (app/agent/tools.py)
              │
              ├──► market data      → services/trading.py  (Nobitex)
              ├──► portfolio        → services/trading.py
              ├──► orders           → services/trading.py
              ├──► risk             → risk_engine/
              └──► news             → (stub)
```

`AgentBrain` is a **singleton** created in `app/core/agent.py`. Before v3.3.0
both `main.py` and `api/v1/ai.py` constructed their own instance, producing two
separate conversation memories — `/ai/agent/memory/clear` cleared the wrong one.

---

## Components

| # | Component | File | Responsibility | Status |
|---|---|---|---|---|
| 1 | Orchestrator | `backend/app/api/v1/ai.py` | Routes queries to the brain and tools | ✅ |
| 2 | AgentBrain | `backend/app/agent/brain.py` | Memory, summarisation, tool orchestration | ✅ |
| 3 | ModelRouter | `backend/app/agent/llm.py` | Multi-provider routing | ✅ |
| 4 | Tool Executor | `backend/app/agent/tools.py` | Registry and dispatch | ⚠️ see below |
| 5 | Nobitex client | `backend/app/services/trading.py` | Orders, balances, positions, prices | ✅ |
| 6 | Paper trader | `backend/app/services/paper_trader.py` | Slippage, PnL simulation | ⚠️ not wired in |
| 7 | Risk engine | `backend/app/risk_engine/advanced.py` | VaR, CVaR, stress, correlation | ✅ |
| 8 | Auth | `backend/app/core/auth.py` | JWT, bcrypt, RBAC | ✅ |
| 9 | WebSocket manager | `backend/app/websockets/manager.py` | Topic pub/sub | ✅ |
| 10 | Dashboard | `frontend/src/app/page.tsx` | Live UI | ✅ |

---

## Tools

13 tools are registered in `backend/app/agent/tools.py`.

> **Status as of v3.3.0:** the registry and dispatch work, but most tool bodies
> are **stubs** that return placeholder values such as `{"price": 0}` or
> `{"order_id": "new_order_id"}`. This is disclosed rather than hidden, and is
> scheduled for phase 2 of [`ROADMAP.md`](ROADMAP.md).

| Tool | Category | Status |
|---|---|---|
| Market price | market | ⚠️ stub |
| Order book | market | ⚠️ stub |
| Recent trades | market | ⚠️ stub |
| Portfolio balances | portfolio | ✅ real |
| Open positions | portfolio | ⚠️ stub |
| PnL summary | portfolio | ⚠️ stub |
| Place order | orders | ⚠️ stub |
| Cancel order | orders | ⚠️ stub |
| Order status | orders | ⚠️ stub |
| Risk summary | risk | ✅ real |
| VaR calculation | risk | ✅ real |
| Correlation | risk | ⚠️ synthetic data |
| News feed | news | ⚠️ stub |

---

## Extending

### Add a tool

1. Implement the function in `backend/app/agent/tools.py`
2. Register it in the `TOOLS` dictionary with a JSON schema
3. Add a test — ideally one that fails before the implementation

### Add a risk metric

1. Implement it in `backend/app/risk_engine/advanced.py` as a **pure function**
   with no I/O
2. Expose it through `backend/app/api/v1/risk.py` using a Pydantic request model
3. Add tests to `backend/tests/test_risk_engine.py`

> **Layering rule:** `risk_engine` must not perform I/O. That is what keeps the
> 25 risk tests deterministic and auditable.

### Add an exchange

1. Implement a client alongside `backend/app/services/trading.py`
2. Register it in the portfolio manager
3. Add tests to `backend/tests/test_nobitex_paper_trading.py`

---

## Testing

```bash
cd backend
API_SECRET_KEY=<at-least-32-characters> \
DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/test \
REDIS_URL=redis://:test@localhost:6379/0 \
pytest tests/ -q
# → 109 passed
```

> `API_SECRET_KEY` must be at least 32 characters; a shorter value aborts
> startup. `tests/` needs no running database — SQLite is used in-process.
