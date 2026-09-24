# AARK Kernel v2.2.0 - Enterprise Financial Trading Platform

A production-grade, multi-agent financial trading system with advanced AI, real-time risk management, and enterprise-grade architecture.

## 🚀 Features Overview

### Level 1: Production Hardening ✅
- **Structured JSON Logging** with correlation IDs, request tracing, and performance metrics
- **Health Checks** (liveness/readiness) with database, Redis, and Ollama connectivity verification
- **Error Handling Middleware** with correlation IDs for debugging
- **Configuration Management** via Pydantic Settings with environment-specific configs
- **Prometheus Metrics** endpoint for monitoring
- **Database Migrations** with SQLAlchemy async models

### Level 2: Advanced AI Features ✅
- **Multi-Model Router** supporting Ollama (local), OpenAI, Anthropic, Groq
- **Conversation Memory** with automatic summarization and token management
- **Streaming Responses** via Server-Sent Events (SSE)
- **Tool Calling** with 13 built-in tools (market data, portfolio, orders, risk, news)
- **Dynamic Model Registration** via API

### Level 3: Real Trading Engine ✅
- **Nobitex Exchange Integration** with full order lifecycle management
- **Order Management** (market, limit, stop, stop-limit) with batch support
- **Position Tracking** with real-time PnL calculation
- **Portfolio Management** with multi-asset balance aggregation
- **WebSocket Real-time Updates** for orders, positions, market data

### Level 4: Advanced Risk Management ✅
- **Multi-method VaR** (Historical, Parametric, Monte Carlo)
- **Expected Shortfall (CVaR)** calculation
- **Stress Testing** with 6 built-in scenarios (crash, crypto winter, flash crash, etc.)
- **Correlation Analysis** with concentration risk (HHI)
- **Dynamic Position Sizing** with volatility targeting and risk parity
- **Comprehensive Risk Validation** with 6 metric categories

### Level 5: Enterprise Features ✅
- **JWT Authentication** with bcrypt password hashing
- **Role-Based Access Control** (Admin, Trader, Viewer)
- **Audit Logging** for all critical operations
- **WebSocket Server** with subscription-based pub/sub
- **Multi-user Support** with isolated vaults
- **API Versioning** with OpenAPI documentation

## 📁 Project Structure

```
aark-kernel-master/
├── backend/
│   ├── app/
│   │   ├── api/v1/           # API routes
│   │   │   ├── health.py     # Health checks & metrics
│   │   │   ├── ai.py         # Advanced AI endpoints
│   │   │   ├── trading.py    # Trading engine endpoints
│   │   │   ├── risk.py       # Advanced risk management
│   │   │   ├── auth.py       # Authentication & RBAC
│   │   │   └── __init__.py
│   │   ├── agent/
│   │   │   ├── brain.py      # AgentBrain with memory & streaming
│   │   │   ├── llm.py        # Multi-model router & LLM client
│   │   │   └── tools.py      # 13 built-in tools + executor
│   │   ├── risk_engine/
│   │   │   ├── evaluator.py  # Legacy deterministic engine
│   │   │   └── advanced.py   # Advanced risk engine (VaR, stress, correlation)
│   │   ├── services/
│   │   │   └── trading.py    # Nobitex client, order/portfolio managers
│   │   ├── db/
│   │   │   ├── session.py    # Async SQLAlchemy session
│   │   │   ├── models.py     # User, Trade, Position, AuditLog, etc.
│   │   │   └── init_db.py    # Database initialization
│   │   ├── core/
│   │   │   ├── config.py     # Pydantic Settings
│   │   │   ├── logging.py    # Structured JSON logging
│   │   │   └── auth.py       # JWT, bcrypt, RBAC
│   │   ├── middleware/
│   │   │   └── logging.py    # Request logging & error handling
│   │   ├── websockets/
│   │   │   └── manager.py    # WebSocket connection manager
│   │   └── main.py           # FastAPI application entry
│   ├── requirements.txt
│   ├── Dockerfile
│   └── pytest.ini
├── frontend/
│   ├── src/app/page.tsx      # Enhanced React dashboard
│   └── package.json
├── docker-compose.yml
└── install_and_run.sh
```

## 🛠 Quick Start

### Prerequisites
- Docker & Docker Compose
- Ollama running locally (`ollama serve`) with `qwen2.5:7b` model
- Ubuntu 24.04+ / Linux / macOS / Windows WSL2

### Automated Installation
```bash
chmod +x install_and_run.sh
./install_and_run.sh
```

This will:
1. Install Docker if missing
2. Generate secure `.env` with random secrets
3. Build and start all services
4. Initialize database schema
5. Launch frontend at http://localhost:3000
6. Launch backend API at http://localhost:8000/docs

### Manual Setup
```bash
# 1. Copy env template
cp .env.example .env  # Edit with your values

# 2. Start infrastructure
docker compose up -d postgres redis

# 3. Initialize database
cd backend && python -m app.db.init_db

# 4. Start backend
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 5. Start frontend (separate terminal)
cd frontend && npm install && npm run dev
```

## 🔧 Configuration

Key environment variables (`.env`):
```env
# Database
POSTGRES_DB=aark_db
POSTGRES_USER=aark_admin
POSTGRES_PASSWORD=secure_random_password
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/aark_db

# Redis
REDIS_PASSWORD=secure_random_password
REDIS_URL=redis://:pass@redis:6379/0

# Security
API_SECRET_KEY=32+_character_random_string

# AI
LOCAL_OLLAMA_HOST=http://host.docker.internal:11434
DEFAULT_MODEL=qwen2.5:7b

# Risk Limits
MAX_PORTFOLIO_ALLOCATION_IRT=10000000
MAX_SINGLE_TRADE_PCT=0.20
MAX_DAILY_LOSS_PCT=0.015

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## 📡 API Endpoints

### Health & Monitoring
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Basic health check |
| GET | `/api/v1/health/live` | Kubernetes liveness probe |
| GET | `/api/v1/health/ready` | Kubernetes readiness probe |
| GET | `/api/v1/metrics` | Prometheus metrics |

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | JWT login (OAuth2) |
| POST | `/api/v1/auth/register` | Create user (Admin only) |
| GET | `/api/v1/auth/me` | Current user profile |
| GET | `/api/v1/auth/users` | List users (Admin) |

### Advanced AI
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/ai/models` | List registered models |
| POST | `/api/v1/ai/models/register` | Register new model |
| POST | `/api/v1/ai/agent/chat` | Chat with tools |
| POST | `/api/v1/ai/agent/evaluate/stream` | Streaming evaluation |
| GET | `/api/v1/ai/tools` | List available tools |
| POST | `/api/v1/ai/tools/execute` | Execute tool manually |

### Trading Engine
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/trading/orders` | Place order |
| DELETE | `/api/v1/trading/orders/{id}` | Cancel order |
| GET | `/api/v1/trading/orders` | List orders |
| GET | `/api/v1/trading/portfolio/balances` | Account balances |
| GET | `/api/v1/trading/portfolio/positions` | Open positions |
| GET | `/api/v1/trading/portfolio/pnl` | Profit/Loss summary |

### Advanced Risk
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/risk/var` | Calculate VaR (3 methods) |
| POST | `/api/v1/risk/stress-test` | Run stress scenarios |
| GET | `/api/v1/risk/correlation` | Correlation analysis |
| POST | `/api/v1/risk/validate` | Full portfolio validation |
| POST | `/api/v1/risk/position-size` | Dynamic sizing |

### WebSocket
```
WS /api/v1/ws/ws?token=<JWT>
```
Messages:
- `{"type": "subscribe", "topic": "market.BTCUSDT"}`
- `{"type": "subscribe", "topic": "portfolio"}`
- `{"type": "subscribe", "topic": "risk"}`
- Server pushes: `market_update`, `order_update`, `position_update`, `risk_alert`, `portfolio_update`, `agent_message`, `notification`

## 🧪 Testing

```bash
cd backend
# Run all tests
pytest -v

# Run with coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/test_v22.py -v
```

## 🐳 Production Deployment

```bash
# Build images
docker compose build

# Start in production mode
docker compose -f docker-compose.yml up -d

# Scale backend workers
docker compose up -d --scale backend=3

# View logs
docker compose logs -f backend

# Health check
curl http://localhost:8000/api/v1/health/ready
```

## 🔐 Security Features

- **JWT Tokens** with 30-min expiry, HS256 signing
- **Bcrypt** password hashing (cost factor 12)
- **API Key Vault** with isolated file permissions (600)
- **CORS** restricted to configured origins
- **Rate Limiting** (add via middleware)
- **Audit Trail** for all mutations
- **Non-root Docker** user
- **Secrets** via environment variables only

## 📊 Monitoring

- **Prometheus** metrics at `/api/v1/metrics`
- **Structured JSON logs** with correlation IDs
- **Health endpoints** for Kubernetes probes
- **WebSocket** real-time alerting

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

## 📄 License

Proprietary - AARK Kernel Project

## 🙏 Acknowledgments

- FastAPI for the async web framework
- Ollama for local LLM inference
- TradingView for charting widget
- Nobitex for exchange API
- Vazirmatn for Persian font

---

**AARK Kernel v2.2.0** - Built for production trading operations.