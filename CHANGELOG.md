## [v1.0.1] - 2026-09-24 - Non-Technical Auto Install + Auto Update Edition

### Added - نصب خودکار برای افراد غیر فنی
- **install.sh**: نصب خودکار تمیز - چک Docker, ساخت .env با رمز تصادفی openssl, docker compose up --build -d, صبر 30s, سلامت چک, نمایش آدرس و رمز ورود
- **update.sh**: آپدیت خودکار - بکاپ به backups/YYYYMMDD-HHMMSS/, git pull origin main, docker compose pull + up --build -d, health check, rollback hint
- **start.sh, stop.sh, status.sh, logs.sh, backup.sh**: دستورات ساده روزانه
- **install.bat, start.bat, stop.bat, status.bat, logs.bat, update.bat, backup.bat**: نسخه ویندوز برای افراد غیر فنی
- **INSTALL.md**: راهنمای کامل فارسی نصب در 3 قدم (<5 دقیقه)
- **docs/USER_GUIDE_FA.md**: آموزش کامل تمام بخش‌ها - داشبورد, تنظیمات .env, Docker چیست, بکاپ, عیب‌یابی, امنیت, ورژن‌ها
- **docs/USER_GUIDE_EN.md**: Full English guide for non-technical
- **README**: بخش جدید "برای افراد غیر فنی / For Non-Technical Users — نصب در 1 دقیقه!" با one-liner

### Fixed
- Clean presentation: حذف cache artifacts, .env فقط .env.example
- Non-technical UX: پیام‌های فارسی + انگلیسی، رنگی، راهنمای قدم به قدم

### Docs
- README badge+mermaid+quickstart+sample output + non-technical section
- INSTALL.md + docs/USER_GUIDE_FA.md + docs/USER_GUIDE_EN.md

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
