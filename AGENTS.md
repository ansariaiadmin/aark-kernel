# AGENTS — aark-kernel

## Agents (10)

| # | Agent | File | Role |
|---|-------|------|------|
| 1 | Orchestrator | backend/app/api/v1/agent.py | Routes user query to brain + tools |
| 2 | AgentBrain | backend/app/agent/brain.py | Memory + summarization + tool orchestration |
| 3 | ModelRouter | backend/app/agent/llm.py | Multi-model (Ollama/OpenAI/Anthropic/Groq) |
| 4 | Tools Executor | backend/app/agent/tools.py | 13 tools (market, portfolio, orders, risk, news) |
| 5 | Nobitex Client | backend/app/services/trading.py | Real trading engine |
| 6 | Paper Trader | backend/app/services/paper_trader.py | Slippage + PnL simulation |
| 7 | Risk Engine | backend/app/risk_engine/advanced.py | VaR/CVaR/Stress/Correlation |
| 8 | Auth | backend/app/core/auth.py | JWT + RBAC |
| 9 | WebSocket Manager | backend/app/websockets/manager.py | Pub/sub real-time |
| 10 | Frontend Dashboard | frontend/src/app/page.tsx | Live chart + chat + logs |

## Flow

```mermaid
flowchart TB
    User --> Orchestrator
    Orchestrator --> Brain
    Brain --> Router
    Brain --> Tools
    Tools --> Trading
    Tools --> Paper
    Tools --> Risk
    Trading --> WS
    Paper --> WS
    Risk --> WS
    WS --> Frontend
```

## How to Extend

- Add new tool: edit `backend/app/agent/tools.py`, register in TOOLS dict, add test in `test_risk_engine.py` or new file
- Add new risk metric: edit `advanced.py`, add method + test
- Add new exchange: implement client similar to `trading.py`, register in portfolio manager

## Testing

```bash
cd backend
API_SECRET_KEY=test DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/test REDIS_URL=redis://:test@localhost:6379/0 pytest tests/ -q
# 46 passed (39 risk+paper + 7 v22)
```

## Env

See `.env.example` — API_SECRET_KEY, DATABASE_URL, REDIS_URL, NOBITEX_API_KEY optional
