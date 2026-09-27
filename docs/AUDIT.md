# AUDIT — aark-kernel — ابعادبندی کامل درخت پروژه و سیم‌کشی

**تاریخ:** 2026-09-27
**نسخهٔ ممیزی‌شده:** commit `acb98e2` (قبل از فیکس‌ها)
**نسخهٔ مهرشده بعد از ممیزی:** **3.3.0**
**روش:** اجرای واقعی lint / typecheck / build / test + تحلیل گراف ایمپورت با AST + بالا آوردن زندهٔ هر دو سرویس و تست زنجیرهٔ کامل

---

## ۰. خلاصهٔ مدیریتی

پروژه **کد خوبی دارد ولی سیم‌کشی‌اش قطع بود**. موتور ریسک، paper trader،
مدیر WebSocket و لایهٔ auth همه پیاده‌سازی شده و تست‌شده بودند — اما به بدنهٔ
اپلیکیشن وصل نشده بودند. نتیجه: اپلیکیشنی که بالا می‌آمد، **۱۱ روت** داشت،
در حالی که مستندات **۳۹ روت** را تبلیغ می‌کردند.

| شاخص | قبل | بعد |
|---|---|---|
| روت‌های واقعی در اپ | **11** | **39** + WebSocket |
| `next build` | ❌ **شکست** (۳ خطا) | ✅ پاس |
| `tsc --noEmit` | ❌ ۳ خطا | ✅ ۰ |
| `eslint .` | ❌ ۳ خطا | ✅ ۰ |
| `ruff check` | ✅ ۰ | ✅ ۰ |
| تست‌ها | 54 پاس **اما CI قرمز** | **109 پاس** |
| CI (workflow) | ❌ در مرحلهٔ collection می‌مرد | ✅ |
| ساخت ایمیج فرانت | ❌ غیرممکن | ✅ |
| `install.sh` برای کاربر نهایی | ❌ شکست | ✅ |
| هش کردن پسورد | ❌ **۱۰۰٪ شکست** | ✅ |
| لاگین در نصب تازه | ❌ **غیرممکن** | ✅ |
| ورژن اعلام‌شده | ۵ ورژن همزمان | ۱ منبع حقیقت |

---

## ۱. درخت ابعادی پروژه

### ۱.۱ لایه‌ها

```
aark-kernel/
├── backend/                      ← لایهٔ هسته (FastAPI, Python 3.11+)
│   ├── app/
│   │   ├── main.py               [入口] نقطهٔ ورود + lifespan + روت‌های ad-hoc
│   │   ├── api/v1/               [delivery]  ai · auth · health · risk · trading
│   │   ├── agent/                [domain]    brain · llm · registry · tools
│   │   ├── risk_engine/          [domain]    advanced (VaR/CVaR/stress) · evaluator
│   │   ├── services/             [infra]     trading (Nobitex) · paper_trader
│   │   │   ├── notification/     [infra]     ⚠ یتیم
│   │   │   └── sms/              [infra]     ⚠ یتیم
│   │   ├── core/                 [config]    config · auth · logging · agent✚ · vault✚
│   │   ├── db/                   [infra]     session · models · init_db
│   │   ├── middleware/           [cross]     logging + error handling
│   │   ├── websockets/           [delivery]  manager (pub/sub)
│   │   ├── lib/logger.py                     ⚠ یتیم (تکراری با core/logging)
│   │   ├── models/__init__.py                ⚠ خالی — ARCHITECTURE ادعای «لایهٔ domain» داشت
│   │   └── static/index.html     [delivery]  ⚠ داشبورد دوم، موازی با frontend/
│   └── tests/                    5 فایل
├── frontend/                     ← لایهٔ ارائه (Next.js 16, React 19)
│   └── src/{app,components,lib✚}
├── docker-compose.yml            ← لایهٔ استقرار (postgres16 · redis7 · backend · frontend)
├── *.sh / *.bat                  ← لایهٔ عملیات (install/update/status/logs/backup/smoke)
├── docs/                         ← لایهٔ مستندات
└── robots/intelligence/          ⚠ یتیم کامل — هیچ‌جا import نشده
```
✚ = در این ممیزی اضافه شد

### ۱.۲ گراف عصب‌کشی واقعی (بعد از فیکس)

```
Browser
  │  same-origin  /api/v1/*            ws(s)://<host>/api/v1/ws/ws?token=JWT
  ▼                                          │
Next.js :3000  ──rewrites()──►  FastAPI :8000│
  src/lib/api.ts  (apiUrl / wsUrl)           │
  src/lib/auth.ts (JWT store)                │
                                             ▼
                              ┌──────────────────────────────┐
                              │ main.py  lifespan            │
                              │  setup_logging → ensure_vault│
                              │  → init_db → bootstrap_admin │
                              └──────┬───────────────────────┘
        CORS ─► RequestLogging ─► ErrorHandling │
                                              ▼
     public_router ─────────── health · auth(login/register/me/users)
     protected_router ──────── ai · trading · risk     [Depends(JWT+RBAC)]
     realtime_router ───────── ws/ws                   [self-auth ?token=]
     ad-hoc (main.py) ──────── agent/evaluate · nobitex/* · agents/* · integrations/*
                                              │
              ┌───────────────┬───────────────┼────────────────┬─────────────┐
              ▼               ▼               ▼                ▼             ▼
     core.agent(brain)  core.auth        core.vault     risk_engine     services
       │  singleton       │ JWT+bcrypt     │ 0700/0600   evaluator ←── advanced
       ▼                  ▼                ▼                            (re-export)
     agent.llm         db.session ──► db.models (7 جدول) ──► Postgres
     (ModelRouter)        │
     agent.tools ⚠        └──► Redis
     (13 stub)
```

---

## ۲. یافته‌ها — به ترتیب شدت

### 🔴 S1 — بحرانی (اپ عملاً کار نمی‌کرد)

| # | یافته | شاهد | وضعیت |
|---|---|---|---|
| 1 | **`api_router` ساخته می‌شد ولی هرگز mount نمی‌شد.** `main.py` فقط `health.router` را include می‌کرد. ۲۳ اندپوینت ai/auth/trading/risk + کل WebSocket **۴۰۴** بودند | dump واقعی OpenAPI: ۱۱ روت زنده در برابر ۳۹ روت مستندشده | ✅ فیکس |
| 2 | **`next build` شکست می‌خورد** → ایمیج فرانت ساخته نمی‌شد → `docker compose build` و `install.sh` و CI همه می‌مردند | `TS2304: Cannot find name '_e'` ×2 + `TS2307: Cannot find module 'recharts'` | ✅ فیکس |
| 3 | **هش پسورد ۱۰۰٪ شکست می‌خورد.** passlib 1.7.4 با bcrypt≥4.1 ناسازگار است؛ passlib نسخهٔ bcrypt را از `bcrypt.__about__` می‌خواند (حذف شده) و سپس یک هش آزمایشی >۷۲ بایت می‌زند که bcrypt جدید به‌جای truncate **raise** می‌کند | `ValueError: password cannot be longer than 72 bytes` روی `get_password_hash('S3cret!pass')` | ✅ فیکس (passlib حذف، bcrypt مستقیم) |
| 4 | **بن‌بست نصب تازه: هیچ ادمینی نمی‌توانست وجود داشته باشد.** `install.sh` مقدار `ADMIN_EMAIL/ADMIN_PASSWORD` را در `.env` می‌نویسد، ولی هیچ کدی آن کاربر را نمی‌ساخت؛ از طرفی `POST /auth/register` خودش به یک ADMIN موجود نیاز دارد | `init_db.py` فقط `create_all` می‌کرد | ✅ فیکس (`bootstrap_admin()` idempotent) |
| 5 | **CI هرگز اجرا نمی‌شد.** `API_SECRET_KEY=test_secret_32_bytes_min_for_ci` دقیقاً **۳۱ کاراکتر** است، در حالی که `Field(..., min_length=32)` | `wc -c` = 31 → `ValidationError` در مرحلهٔ **collection** → هیچ تستی اجرا نمی‌شد | ✅ فیکس |

### 🟠 S2 — شدید (سیم‌کشی قطع / قرارداد شکسته)

| # | یافته | شاهد | وضعیت |
|---|---|---|---|
| 6 | **فرانت به origin اشتباه می‌زد.** همهٔ فراخوانی‌ها `fetch('/api/v1/...')` نسبی بودند → به سرور Next (:3000) می‌رفتند نه بک‌اند (:8000). هیچ rewrite/proxy وجود نداشت | `ARCHITECTURE.md` ادعا می‌کرد `NEXT_PUBLIC_API_URL` استفاده می‌شود؛ `page.tsx` هرگز آن را نمی‌خواند | ✅ فیکس (rewrites + `src/lib/api.ts`) |
| 7 | **`BACKEND_CORS_ORIGINS` پیکربندی مرده بود.** هیچ `CORSMiddleware` ثبت نشده بود، پس حتی فراخوانی مستقیم cross-origin از مرورگر بلاک می‌شد | `grep -rn CORS backend/` → فقط یک خط در `config.py` | ✅ فیکس |
| 8 | **قرارداد `/risk/validate` شکسته بود.** `daily_pnl` و `portfolio_value` چون scalar بودند توسط FastAPI به **query** نگاشت شدند، در حالی که `positions/prices` در body بودند. داشبورد هر چهار را در یک JSON body می‌فرستاد → همیشه **۴۲۲** | پاسخ واقعی: `{"loc":["query","daily_pnl"],"msg":"Field required"}` | ✅ فیکس (مدل‌های درخواست صریح) |
| 9 | **WebSocket هرگز وصل نمی‌شد.** `page.tsx` مقدار `localStorage['aark_token']` را می‌خواند ولی **هیچ‌جای اپ آن را نمی‌نوشت** (هیچ UI لاگینی وجود نداشت). به‌علاوه آدرس hardcode شده بود: `ws://localhost:8000` → در https به‌عنوان mixed-content بلاک می‌شد و پشت هر پروکسی/preview می‌مرد | `grep -rn setItem frontend/src` → صفر نتیجه | ✅ فیکس (صفحهٔ ورود + `src/lib/auth.ts` + `wsUrl()` + reconnect) |
| 10 | **`get_current_user` شناسهٔ رشته‌ای را به کلید اصلی INTEGER می‌داد.** JWT طبق استاندارد `sub` را رشته صادر می‌کند؛ کد بدون تبدیل آن را به `get_user_by_id` می‌داد | `user_id: int = payload.get("sub")` سپس `get_user_by_id(db, token_data.sub)` | ✅ فیکس |
| 11 | **`broadcast_to_subscription` روی dict در حال پیمایش تغییر ایجاد می‌کرد.** اولین سوکت مرده، `disconnect()` را صدا می‌زد که همان dict را حذف می‌کرد → `RuntimeError: dictionary changed size during iteration` → کل publish برای همهٔ مشترکین می‌مرد | کد: `for ws, meta in self.connection_metadata.items(): ... self.disconnect(ws)` | ✅ فیکس (snapshot) |
| 12 | **خطای auth در WebSocket به‌صورت unhandled فرار می‌کرد.** `get_websocket_user` قبل از `try/finally` صدا زده می‌شد و `RuntimeError` می‌انداخت | هر توکن منقضی = یک خطای سمت سرور | ✅ فیکس (`WebSocketAuthError` → close 1008 تمیز) |
| 13 | **`GET /trading/portfolio/value` همیشه صفر برمی‌گرداند.** تیکر گرفته می‌شد، دور ریخته می‌شد و `prices[f"{asset}IRT"] = Decimal(0)  # Placeholder` نوشته می‌شد → هر دارایی غیر IRT ارزش صفر داشت | کامنت `# Placeholder` در کد | ✅ فیکس (`client.get_price()` واقعی) |
| 14 | **دو `AgentBrain` مستقل.** `main.py` و `api/v1/ai.py` هر کدام یکی می‌ساختند → دو حافظهٔ مکالمهٔ جدا؛ `/ai/agent/memory/clear` حافظهٔ اشتباه را پاک می‌کرد | `grep -n "AgentBrain()" backend/` → ۲ مورد | ✅ فیکس (`core/agent.py` singleton) |
| 15 | **دو منبع حقیقت برای محدودیت‌های ریسک.** `RiskProfile` و `DeterministicRiskEngine` هم در `evaluator.py` و هم در `advanced.py` تعریف شده بودند؛ `main.py` از اولی و `api/v1/risk.py` از دومی import می‌کرد → مسیر ایجنت و مسیر API می‌توانستند ساکتانه اختلاف پیدا کنند | diff دو تعریف | ✅ فیکس (re-export) |
| 16 | **دو پیاده‌سازی والت کلید صرافی.** `main.py` vault را با `0600` می‌نوشت؛ `api/v1/trading.py` همان مسیر را **بدون** هیچ سخت‌گیری مجوز می‌خواند | copy-paste با drift | ✅ فیکس (`core/vault.py` + نوشتن اتمیک) |
| 17 | **پکیج یتیم `app/` در ریشه، `backend/app` را shadow می‌کرد.** چون `app/__init__.py` نداشت، یک namespace package می‌ساخت؛ وقتی ریشهٔ ریپو در `sys.path` بود، `import app.main` با `ModuleNotFoundError` می‌مرد | تست واقعی: `app.__path__ = ['/…/aark-kernel/app']` → `No module named 'app.main'` | ✅ فیکس (حذف؛ بایت‌به‌بایت تکراری بود) |

### 🟡 S3 — متوسط (کیفیت / dead code / صحت مستندات)

| # | یافته | وضعیت |
|---|---|---|
| 18 | `RequestLoggingMiddleware` مسیرهای `/health` و `/metrics` را exclude می‌کرد ولی مسیرهای واقعی `/api/v1/health/...` هستند → هر health check داکر (هر ۳۰ ثانیه) دو خط لاگ INFO تولید می‌کرد | ✅ فیکس |
| 19 | `from datetime import …` در **انتهای** `api/v1/risk.py` + سه `import numpy` محلی تکراری + عبارت بی‌معنی `if 'np' in globals()` | ✅ فیکس |
| 20 | `class Config:` پایدارگی‌نیافتهٔ Pydantic v1 در `core/auth.py` → `PydanticDeprecatedSince20` | ✅ فیکس (`ConfigDict`) |
| 21 | JWT فاقد `iat` بود → سن توکن قابل تشخیص نبود و پنجرهٔ rotation لنگر نداشت؛ TTL هم در سه جا hardcode شده بود | ✅ فیکس (`ACCESS_TOKEN_TTL_MINUTES`) |
| 22 | `background_tasks` در `/trading/orders/batch` اعلام شده ولی هرگز استفاده نمی‌شد | ✅ فیکس |
| 23 | `import pythonjsonlogger.jsonlogger` → مسیر منسوخ (به `pythonjsonlogger.json` منتقل شده) | ✅ فیکس (import سازگار با هر دو) |
| 24 | `eslint.config.mjs` قاعدهٔ `react-hooks/exhaustive-deps` را تنظیم می‌کرد در حالی که `eslint-plugin-react-hooks` نصب نیست → ESLint 9 با «Definition for rule not found» **کل lint را abort می‌کرد** | ✅ فیکس |
| 25 | `postcss.config.js` و `tailwind.config.js` با `module.exports` نوشته شده‌اند ولی کانفیگ eslint آن‌ها را ESM فرض می‌کرد → `'module' is not defined` | ✅ فیکس (globals.node) |
| 26 | کلاس‌های `bg-card` و `text-muted-foreground` در `LineChart`/`OrderBook` استفاده می‌شدند ولی در `tailwind.config.js` تعریف نشده بودند → Tailwind ساکتانه حذفشان می‌کرد | ✅ فیکس |
| 27 | `setAsks` در `OrderBook` گرفته می‌شد ولی هرگز صدا زده نمی‌شد → خطای lint خودِ پروژه | ✅ فیکس |
| 28 | `tsconfig.tsbuildinfo` در گیت commit شده بود (آرتیفکت ماشین‌خاص) | ✅ فیکس (.gitignore) |
| 29 | `pytest>=9` و `ruff` در `requirements.txt` بودند → داخل ایمیج **پروداکشن** نصب می‌شدند | ✅ فیکس (`requirements-dev.txt`) |
| 30 | دکمه‌های «Start Engine» و «Kill Switch» هیچ `onClick` نداشتند؛ تب‌های `orders`/`positions` هیچ handler و active-state نداشتند و فقط پنل chat رندر می‌شد؛ دادهٔ fetch‌شده در `_orders`/`_positions` دور ریخته می‌شد | ✅ فیکس (تب‌های واقعی + جدول‌ها + Kill Switch کاربردی) |
| 31 | `LineChart.tsx` و `OrderBook.tsx` کاملاً یتیم بودند (هیچ‌جا import نشده) | ✅ فیکس (تب Analytics) |
| 32 | `_placeOrder` هرگز صدا زده نمی‌شد → از UI نمی‌شد سفارش گذاشت | ✅ فیکس (دکمه‌های BUY/SELL) |

### ⚫ S4 — بدهی فنی مستند (عمداً دست‌نخورده — نیاز به تصمیم محصولی)

| # | یافته | چرا هنوز باز است |
|---|---|---|
| 33 | **هر ۱۳ ابزار ایجنت stub هستند.** `ToolExecutor` فقط schema می‌سازد؛ پیاده‌سازی‌ها `{"price": 0}` / `{"balances": {}}` / `{"order_id": "new_order_id"}` برمی‌گردانند و `ToolExecutor()` بدون client/db ساخته می‌شود | اتصال واقعی به Nobitex = تصمیم محصولی (فاز ۲) |
| 34 | **`/risk/var` و `/risk/correlation` دادهٔ تصادفی برمی‌گردانند** (`np.random.normal`)، نه دادهٔ واقعی بازار | نیاز به پایپ‌لاین دادهٔ تاریخی (فاز ۲) |
| 35 | **`services/notification/` و `services/sms/` کاملاً یتیم‌اند.** README نسخهٔ «v3.1.0» وعدهٔ SMS واقعی Ghasedak/Kavenegar، fallback و throttling می‌دهد؛ کد وجود دارد ولی **هیچ‌جا import یا صدا زده نمی‌شود** | تصمیم: وصل شود یا حذف (فاز ۲) |
| 36 | **`services/paper_trader.py` یتیم است.** ۸۷ ارجاع در تست‌ها، صفر ارجاع در اپ. `EXCHANGE_PROVIDER=mock` در `.env.example` هیچ اثری ندارد | فاز ۲ |
| 37 | **۳۰+ کلید `.env.example` توسط `Settings` خوانده نمی‌شوند** (`AI_PROVIDER`, `SMS_*`, `NOTIF_*`, `TELEGRAM_*`, `EXCHANGE_PROVIDER`, `NOBITEX_API_KEY/SECRET`, `SMTP_*`, `AARK_*_PORT`). چون `extra="ignore"` است، ساکتانه دور ریخته می‌شوند | فاز ۱/۲ |
| 38 | **`robots/intelligence/` یتیم کامل** — هیچ‌جا import نشده | تصمیم: حذف یا ادغام |
| 39 | **`public/manifest.json` در ریشه** — به `icon-192.png`/`icon-512.png` ارجاع می‌دهد که وجود ندارند؛ از `frontend/public/` سرو نمی‌شود و `layout.tsx` هیچ `<link rel="manifest">` ندارد → PWA کار نمی‌کند | فاز ۳ |
| 40 | **`backend/app/static/index.html` یک داشبورد دوم و موازی است** که توسط FastAPI روی `/` سرو می‌شود، در حالی که `frontend/` داشبورد Next.js است | تصمیم معماری (فاز ۱) |
| 41 | **روت‌های ad-hoc در `main.py` بدون auth هستند**، از جمله `POST /api/v1/nobitex/save-key` که کلید صرافی را روی دیسک می‌نویسد | فاز ۱ — نیاز به تصمیم (تست‌های موجود به آن وابسته‌اند) |
| 42 | **OrderManager/PortfolioManager global هستند** — بین همهٔ کاربران مشترک‌اند، در برابر ادعای «multi-user isolated vaults» در README | فاز ۲ |
| 43 | **مهاجرت DB دستی است** (`create_all`)؛ Alembic وجود ندارد | فاز ۲ |
| 44 | **Rate limiting وجود ندارد** | فاز ۲ |
| 45 | `HANDOFF.md` یک مسیر اشتباه دارد: `api/v1/websockets/manager.py` (مسیر واقعی `app/websockets/manager.py` است) | فاز ۱ (docs) |

---

## ۳. ادعاهای مستندات در برابر واقعیت (قبل از فیکس)

| ادعا | منبع | واقعیت |
|---|---|---|
| «۵۴ تست پاس» | README badge | درست، **اما CI به‌خاطر کلید ۳۱ کاراکتری هرگز به اجرای تست نمی‌رسید** |
| «۲۳ اندپوینت ai/auth/trading/risk» | HANDOFF, README, AGENTS | **۴۰۴** — هیچ‌کدام mount نشده بود |
| «JWT + RBAC محافظت‌شده» | README, SECURITY | نه mount بود، نه bcrypt کار می‌کرد، نه ادمینی وجود داشت |
| «WebSocket pub/sub زنده» | README, ARCHITECTURE | روت mount نشده + توکن هرگز نوشته نمی‌شد + آدرس hardcode |
| «CORS محدود به originهای پیکربندی‌شده» | ARCHITECTURE | **هیچ** CORS middleware ثبت نشده بود |
| «۱۳ ابزار واقعی (market, portfolio, orders, risk, news)» | README | همه stub با دادهٔ ساختگی |
| «SMS واقعی با تست و اعتبار» | README v3.1.0 | ماژول یتیم؛ هرگز import نشده |
| «۶ سناریوی stress» | README | ✅ درست — موتور ریسک واقعاً پیاده و تست‌شده است |
| «VaR Historical/Parametric/Monte Carlo + CVaR» | README | ✅ درست |
| «`pytest tests/test_paper_trader.py`» | README | ❌ چنین فایلی وجود ندارد (نام واقعی `test_nobitex_paper_trading.py`) |
| «`curl /api/v1/risk/var?method=historical`» | README | ❌ ۴۲۲ — `portfolio_value` الزامی است |
| «`POST /risk/stress-test -d '{"scenario":"crypto_winter"}'`» | README | ❌ schema اشتباه |
| «Web Setup Wizard `/setup`» | README v4.0.0 | ❌ چنین روتی وجود ندارد |
| «`POST /api/notifications/send`» | docs/API.md | ❌ وجود ندارد |
| «`POST /api/auth/login`» | docs/API.md | ❌ prefix واقعی `/api/v1/` است |
| نسخهٔ پروژه | ۶ فایل مختلف | 2.2.0 / v2.2 / 1.0.4 / 1.0.1 / 3.1.2 / 3.2.3 / 4.0.0 همزمان |

---

## ۴. اثبات‌های اجرایی (نه ادعا)

```bash
# بک‌اند
$ ruff check .                        → All checks passed!
$ pytest tests/ -q                    → 109 passed, 1 warning
$ python -c "from app.main import app; print(len(app.openapi()['paths']))"
                                      → 39   (قبلاً 11)

# فرانت
$ npx tsc --noEmit                    → exit 0   (قبلاً 3 خطا)
$ npx eslint .                        → exit 0   (قبلاً 3 خطا)
$ npx next build                      → ✓ Compiled successfully  (قبلاً exit 1)

# زنجیرهٔ زندهٔ کامل (هر دو سرویس واقعی بالا آمده)
GET  :3000/                                → 200  (داشبورد)
GET  :3000/api/v1/health/live              → {"status":"alive"}   ← پروکسی Next کار می‌کند
POST :3000/api/v1/auth/login               → JWT صادر شد (184 کاراکتر)
GET  :3000/api/v1/auth/me                  → {"id":1,"role":"admin","is_superuser":true}
GET  :3000/api/v1/risk/summary   (بی‌توکن)  → 401
GET  :3000/api/v1/risk/summary   (با توکن)  → 200
POST :3000/api/v1/risk/validate            → 200 با body واقعی داشبورد (قبلاً 422)
لاگ بک‌اند هنگام startup:  "Bootstrap admin created: admin@aark-kernel.dev"
```

---

## ۵. نقشهٔ پوشش تست بعد از فیکس

| فایل | تست | چه چیزی را ثابت می‌کند |
|---|---|---|
| `test_api_wiring.py` ✚ | **39** | mount بودن همهٔ روت‌ها، زنجیرهٔ واقعی bcrypt→JWT→DB، 401/403، CORS، قرارداد body، vault 0600/0700، singleton بودن brain، bootstrap ادمین |
| `test_release_consistency.py` ✚ | **16** | یکسان بودن ورژن در کد/فرانت/CHANGELOG/README، نبود ورژن کهنه در مستندات، پوشش `.env.example` |
| `test_risk_engine.py` | 25 | VaR/CVaR/stress/correlation/HHI/sizing |
| `test_nobitex_paper_trading.py` | 14 | market/limit/stop، slippage، PnL، rebalance |
| `test_var_backtest.py` | 8 | Kupiec POF، mock WebSocket |
| `test_v22.py` | 7 | مسیر ایجنت + کنترل ریسک ۲۰٪ |
| **مجموع** | **109** | |

تست‌های جدید **بدون هیچ سرویس خارجی** اجرا می‌شوند: SQLite واقعی + ASGITransport،
بدون mock در مرز HTTP — چون دقیقاً mock کردن همان چیزی بود که اجازه داد
۲۳ اندپوینت گم‌شده و bcrypt شکسته برای مدت‌ها پنهان بمانند.
