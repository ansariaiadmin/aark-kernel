# Changelog — aark-kernel

همهٔ تغییرات قابل‌توجه این پروژه در این فایل مستند می‌شود.
قالب بر پایهٔ [Keep a Changelog](https://keepachangelog.com/fa-IR/1.1.0/) و
ورژن‌گذاری بر پایهٔ [SemVer](https://semver.org/lang/fa/) است.

**منبع حقیقت ورژن:** `backend/app/core/config.py → Settings.APP_VERSION`.
تست `backend/tests/test_release_consistency.py` در CI جلوی جدا افتادن
README / CHANGELOG / `frontend/package.json` از آن را می‌گیرد.

---

## [3.3.0] - 2026-09-27 — فاز ۰: یکپارچگی ساخت و سیم‌کشی

نسخهٔ مهرشده پس از ممیزی کامل درخت پروژه و سیم‌کشی آن.
جزئیات کامل یافته‌ها: [`docs/AUDIT.md`](docs/AUDIT.md) · نقشهٔ فازها: [`ROADMAP.md`](ROADMAP.md)

### 🔴 Fixed — بحرانی (اپ عملاً کار نمی‌کرد)

- **۲۳ اندپوینت گم‌شده به اپ برگشتند.** `app.api.v1.api_router` به‌عنوان اثر جانبی import ساخته می‌شد و سپس دور ریخته می‌شد؛ `main.py` فقط `health.router` را mount می‌کرد. روت‌های زنده از **۱۱ به ۳۹** رسید (ai / auth / trading / risk / WebSocket).
- **`next build` رفع شد.** سه خطا (`TS2304: Cannot find name '_e'` ×۲ در `page.tsx`، و `TS2307: Cannot find module 'recharts'`) باعث می‌شد ایمیج فرانت هرگز ساخته نشود → `docker compose build`، `install.sh` و CI همه می‌مردند.
- **هش پسورد رفع شد.** `passlib 1.7.4` با `bcrypt>=4.1` ناسازگار است و هر فراخوانی `get_password_hash()` با `ValueError: password cannot be longer than 72 bytes` می‌مرد → `POST /auth/register` همیشه ۵۰۰ بود و **هیچ کاربری نمی‌توانست ساخته شود**. passlib حذف و bcrypt مستقیم استفاده شد (قالب `$2b$` بدون تغییر، پس هش‌های قبلی هم verify می‌شوند).
- **بن‌بست نصب تازه شکسته شد.** `install.sh` مقدار `ADMIN_EMAIL`/`ADMIN_PASSWORD` را در `.env` می‌نوشت ولی هیچ کدی آن کاربر را نمی‌ساخت، و `POST /auth/register` خودش به یک ADMIN موجود نیاز داشت. `bootstrap_admin()` idempotent اضافه شد (رمز <۱۲ کاراکتر را رد می‌کند، کاربر موجود را ارتقا می‌دهد، رمز را بازنویسی نمی‌کند).
- **CI رفع شد.** `API_SECRET_KEY=test_secret_32_bytes_min_for_ci` دقیقاً ۳۱ کاراکتر بود در برابر `Field(..., min_length=32)` → کل job در مرحلهٔ *collection* می‌مرد و هیچ تستی اجرا نمی‌شد.
- **job داکر در CI رفع شد — این یکی پیش‌تر دیده نشده بود.** هر چهار سرویس
  `env_file: - .env` داشتند، ولی job داکر فقط `actions/checkout` می‌کرد و هیچ `.env`
  نمی‌ساخت؛ Docker Compose v2 در نبود آن فایل با exit 1 بیرون می‌آید
  (`env file .env not found`). یعنی `docker compose config` **هرگز** در CI پاس نشده بود.
  اکنون `env_file` به شکل `path: .env` + `required: false` آمده (کلون تازه بدون `.env`
  هم کار می‌کند — همهٔ مقادیر لازم در `environment:` با default تعریف شده‌اند) و job
  داکر پیش از اعتبارسنجی یک `.env` واقعی از `.env.example` می‌سازد و placeholderهای
  رمز را با مقدار ۳۲+ کاراکتری جایگزین می‌کند.
- **نگهبان جدید CI:** هر `${VAR}` که `docker-compose.yml` ارجاع می‌دهد باید یا در
  `.env.example` مستند باشد یا default درون‌خطی داشته باشد؛ وگرنه نصب تازه بی‌صدا
  مقدار خالی می‌گیرد و job قرمز می‌شود.

### 🟠 Fixed — سیم‌کشی و قراردادها

- **CORS واقعاً ثبت شد.** `BACKEND_CORS_ORIGINS` پیکربندی مرده بود؛ هیچ `CORSMiddleware` وجود نداشت، پس فرانت روی `:3000` نمی‌توانست به API روی `:8000` برسد.
- **فرانت به origin درست وصل شد.** همهٔ فراخوانی‌ها `fetch('/api/v1/...')` نسبی بودند و به سرور Next می‌رفتند. `next.config.mjs` حالا `rewrites()` دارد و `src/lib/api.ts` تنها منبع آدرس‌هاست.
- **WebSocket زنده شد.** `page.tsx` مقدار `localStorage['aark_token']` را می‌خواند ولی **هیچ‌جای اپ آن را نمی‌نوشت**؛ آدرس هم `ws://localhost:8000` hardcode بود (در https به‌عنوان mixed-content بلاک می‌شد). صفحهٔ ورود واقعی + `src/lib/auth.ts` + `wsUrl()` + reconnect با backoff اضافه شد.
- **قرارداد `POST /risk/validate` رفع شد.** `daily_pnl` و `portfolio_value` به‌خاطر scalar بودن توسط FastAPI به **query** نگاشت می‌شدند در حالی که داشبورد همه را در JSON body می‌فرستاد → همیشه **۴۲۲**. مدل‌های درخواست صریح (`RiskValidateRequest`, `StressTestRequest`, `LegacyValidateRequest`) اضافه شد.
- **`GET /trading/portfolio/value` رفع شد.** تیکر گرفته و دور ریخته می‌شد و `Decimal(0)  # Placeholder` جای قیمت می‌نشست → هر دارایی غیر IRT ارزش **صفر** داشت. `NobitexClient.get_price()` واقعی اضافه شد.
- **`RuntimeError` در `broadcast_to_subscription` رفع شد.** `disconnect()` همان dict را که در حال پیمایش بود تغییر می‌داد → اولین سوکت مرده، کل publish را برای همهٔ مشترکین می‌کشت.
- **خطای auth در WebSocket رفع شد.** `RuntimeError` از `get_websocket_user` قبل از `try/finally` فرار می‌کرد؛ حالا `WebSocketAuthError` به close تمیز ۱۰۸۰ ترجمه می‌شود.
- **`get_current_user` رفع شد.** JWT مقدار `sub` را رشته صادر می‌کند ولی بدون تبدیل به `get_user_by_id` داده می‌شد که با کلید اصلی INTEGER مقایسه می‌کرد.
- **`GET /auth/login` و `Token.expires_in` به یک منبع TTL وصل شدند** و claim `iat` اضافه شد (قبلاً سن توکن قابل تشخیص نبود).

### ♻️ Changed — حذف منابع حقیقت موازی

- **`AgentBrain` singleton شد.** `main.py` و `api/v1/ai.py` هر کدام یکی می‌ساختند → دو حافظهٔ مکالمهٔ جدا؛ `/ai/agent/memory/clear` حافظهٔ اشتباه را پاک می‌کرد. حالا `app/core/agent.py`.
- **والیت کلید صرافی یکسان شد.** `main.py` با `0600` می‌نوشت ولی `api/v1/trading.py` همان مسیر را بدون هیچ سخت‌گیری می‌خواند. حالا `app/core/vault.py` با نوشتن اتمیک، `0700` روی پوشه و `0600` روی فایل.
- **`RiskProfile`/`DeterministicRiskEngine` یکی شدند.** در `evaluator.py` و `advanced.py` دو تعریف جدا وجود داشت؛ مسیر ایجنت و مسیر API می‌توانستند ساکتانه اختلاف پیدا کنند.
- **پکیج یتیم `app/` در ریشه حذف شد.** چون `__init__.py` نداشت یک namespace package می‌ساخت و وقتی ریشهٔ ریپو در `sys.path` بود، `backend/app` را shadow می‌کرد → `import app.main` با `ModuleNotFoundError` می‌مرد. محتوایش بایت‌به‌بایت تکرار `backend/app/lib/logger.py` بود.

### ✨ Added

- **۵۵ تست جدید** — `test_api_wiring.py` (۳۹) و `test_release_consistency.py` (۱۶). هیچ‌کدام به سرویس خارجی نیاز ندارند: SQLite واقعی + `ASGITransport`، **بدون mock در مرز HTTP** (چون دقیقاً mock کردن باعث شد این باگ‌ها مدت‌ها پنهان بمانند). مجموع: **۵۴ → ۱۰۹**.
- `DELETE /api/v1/nobitex/key` — Kill Switch واقعی برای حذف کلید صرافی.
- **UI مرده زنده شد:** تب‌های chat/orders/positions/analytics با active-state، جدول‌های سفارش و پوزیشن (داده‌های fetch‌شده قبلاً در `_orders`/`_positions` دور ریخته می‌شدند)، دکمه‌های BUY/SELL، دکمهٔ Refresh، Kill Switch کاربردی، و صفحهٔ ورود.
- `LineChart.tsx` و `OrderBook.tsx` که کاملاً یتیم بودند حالا در تب Analytics رندر می‌شوند.
- `src/lib/api.ts` و `src/lib/auth.ts` — تنها منبع آدرس‌ها و مدیریت نشست.
- `requirements-dev.txt` — pytest/ruff دیگر داخل ایمیج پروداکشن نصب نمی‌شوند.
- CI: job جداگانهٔ فرانت (eslint + tsc + `next build`)، تست smoke برای import، و status check تجمیعی `ci` برای branch protection.

### 🧹 Fixed — کیفیت

- `RequestLoggingMiddleware` مسیرهای `/health` و `/metrics` را exclude می‌کرد ولی مسیرهای واقعی `/api/v1/...` هستند → هر health check داکر دو خط لاگ INFO تولید می‌کرد.
- `from datetime import ...` از **انتهای** `api/v1/risk.py` به بالا منتقل شد؛ سه `import numpy` محلی تکراری و عبارت بی‌معنی `if 'np' in globals()` حذف شدند.
- `class Config:` منسوخ Pydantic v1 → `ConfigDict` (هشدار `PydanticDeprecatedSince20` رفع شد).
- مسیر منسوخ `pythonjsonlogger.jsonlogger` → import سازگار با هر دو نسخه.
- `eslint.config.mjs` قاعدهٔ `react-hooks/exhaustive-deps` را تنظیم می‌کرد در حالی که آن پلاگین نصب نیست → ESLint 9 کل lint را abort می‌کرد.
- `postcss.config.js` / `tailwind.config.js` با `module.exports` نوشته شده‌اند ولی کانفیگ eslint آن‌ها را ESM فرض می‌کرد → `'module' is not defined`.
- کلاس‌های `bg-card` و `text-muted-foreground` در Tailwind تعریف شدند (قبلاً ساکتانه حذف می‌شدند).
- `setAsks` بلااستفاده در `OrderBook.tsx` (خطای lint خودِ پروژه).
- `background_tasks` بلااستفاده در `/trading/orders/batch`.
- `tsconfig.tsbuildinfo` از گیت خارج و به `.gitignore` اضافه شد.
- `.gitignore` کامل شد: `runtime/`, `backups/`, `*.vault`, `*.tsbuildinfo`, `.pytest_cache/`, `.ruff_cache/`.

### 📋 Known gaps — عمداً باز، مستند در ROADMAP

موارد زیر **ادعای مستندات بودند که کد پشتیبانی‌شان نمی‌کرد**. به‌جای پنهان کردن،
صریحاً در `ROADMAP.md` فاز ۱ تا ۳ ثبت شدند:

- هر ۱۳ ابزار ایجنت هنوز stub هستند (`{"price": 0}`, `{"order_id": "new_order_id"}`).
- `/risk/var` و `/risk/correlation` هنوز `np.random.normal` برمی‌گردانند، نه دادهٔ واقعی.
- `services/notification/` و `services/sms/` هنوز یتیم‌اند (README وعدهٔ SMS واقعی و fallback و throttling می‌داد).
- `services/paper_trader.py` هنوز به اپ وصل نیست (۸۷ ارجاع در تست، ۰ در اپ).
- ~۳۰ کلید `.env.example` هنوز توسط `Settings` خوانده نمی‌شوند (`extra="ignore"` ساکتانه دورشان می‌ریزد).
- `robots/intelligence/` یتیم کامل است.
- `public/manifest.json` به آیکون‌های ناموجود ارجاع می‌دهد و سرو نمی‌شود → PWA کار نمی‌کند.
- `backend/app/static/index.html` یک داشبورد دوم و موازی است.
- روت‌های ad-hoc در `main.py` (از جمله `POST /nobitex/save-key`) هنوز بدون auth هستند.

---

## [1.0.1] - 2026-09-24 - Non-Technical Auto Install + Auto Update Edition

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
