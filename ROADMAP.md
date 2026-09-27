# ROADMAP — aark-kernel

**نسخهٔ جاری:** 3.3.0 (مهرشده)
**منبع حقیقت ورژن:** `backend/app/core/config.py → Settings.APP_VERSION`
**نگهبان:** `backend/tests/test_release_consistency.py` — اگر README/CHANGELOG/`frontend/package.json` از آن جدا بیفتند، CI قرمز می‌شود.

> سیاست ورژن‌گذاری: هر فاز با یک **دروازهٔ انتشار** بسته می‌شود. تا وقتی همهٔ
> معیارهای دروازه سبز نباشند، ورژن bump نمی‌شود و فاز بعدی شروع نمی‌شود.

---

## دروازهٔ جهانی (برای همهٔ فازها الزامی)

```bash
# بک‌اند
cd backend && ruff check . && pytest tests/ -q          # 0 خطا، 109 پاس
python -c "from app.main import app; assert len(app.openapi()['paths'])>=39"

# فرانت
cd frontend && npm run verify                            # lint + typecheck + build

# استقرار
docker compose config -q && docker compose build         # هر دو ایمیج
./smoke-test.sh                                          # زنجیرهٔ زنده
```

هیچ PR بدون سبز شدن هر سه بخش merge نمی‌شود.

---

## ✅ فاز ۰ — یکپارچگی ساخت و سیم‌کشی — **v3.3.0 (انجام شد)**

**هدف:** چیزی که در مستندات ادعا شده، واقعاً وجود داشته باشد و build بشکند نه.

| # | تسک | فایل |
|---|---|---|
| 0.1 | mount کردن `api_router` (۱۱ → ۳۹ روت) | `main.py`, `api/v1/__init__.py` |
| 0.2 | تفکیک روترها به public / protected(JWT) / realtime | `api/v1/__init__.py` |
| 0.3 | ثبت `CORSMiddleware` از `BACKEND_CORS_ORIGINS` | `main.py` |
| 0.4 | حذف passlib → bcrypt مستقیم، رفع شکست ۱۰۰٪ هش | `core/auth.py`, `requirements.txt` |
| 0.5 | `bootstrap_admin()` — شکستن بن‌بست نصب تازه | `db/init_db.py` |
| 0.6 | رفع کلید ۳۱ کاراکتری CI | `.github/workflows/ci.yml` |
| 0.7 | رفع ۳ خطای `next build` (`_e` ×2، recharts) | `page.tsx`, `package.json` |
| 0.8 | پروکسی `/api/v1/*` در Next + حذف آدرس hardcode | `next.config.mjs`, `src/lib/api.ts` |
| 0.9 | صفحهٔ ورود واقعی → نوشتن `aark_token` → WS زنده | `src/lib/auth.ts`, `page.tsx` |
| 0.10 | رفع قرارداد body در `/risk/validate` و `/risk/legacy/validate` | `api/v1/risk.py` |
| 0.11 | رفع `RuntimeError` در `broadcast_to_subscription` | `websockets/manager.py` |
| 0.12 | رفع close ناموفق WS با توکن بد | `websockets/manager.py` |
| 0.13 | رفع `sub` رشته‌ای → کلید INTEGER | `core/auth.py` |
| 0.14 | رفع قیمت Placeholder=0 در `/portfolio/value` | `api/v1/trading.py`, `services/trading.py` |
| 0.15 | یکسان‌سازی brain، vault، RiskProfile (حذف منابع موازی) | `core/agent.py`, `core/vault.py`, `risk_engine/*` |
| 0.16 | حذف `app/` یتیم ریشه که `backend/app` را shadow می‌کرد | — |
| 0.17 | رفع lint فرانت (eslint config, globals, tailwind tokens, `setAsks`) | `eslint.config.mjs`, `tailwind.config.js`, `OrderBook.tsx` |
| 0.18 | زنده کردن UI مرده: تب‌ها، Kill Switch، BUY/SELL، LineChart، OrderBook | `page.tsx` |
| 0.19 | ۵۵ تست جدید (wiring + release consistency) | `tests/test_api_wiring.py`, `tests/test_release_consistency.py` |
| 0.20 | تفکیک `requirements-dev.txt` از ایمیج پروداکشن | `backend/requirements*.txt` |

**دروازهٔ انتشار v3.3.0:** ✅ ۱۰۹ تست · ✅ ruff 0 · ✅ tsc 0 · ✅ eslint 0 · ✅ `next build` · ✅ ۳۹ روت · ✅ زنجیرهٔ زنده (login → JWT → protected route)

---

## 🔜 فاز ۱ — صحت مستندات و سخت‌سازی امنیتی — هدف: **v3.4.0**

**چرا اول این؟** چون فاز ۰ کد را با مستندات آشتی داد؛ حالا مستندات باید با کد آشتی کنند،
و سه حفرهٔ امنیتی باقی‌مانده باید بسته شوند.

| # | تسک | اولویت | معیار پذیرش |
|---|---|---|---|
| 1.1 | محافظت از روت‌های ad-hoc در `main.py` — به‌ویژه `POST /nobitex/save-key` (نوشتن کلید صرافی **بدون auth**) و `POST /agents/register` | 🔴 | بدون توکن → ۴۰۱؛ تست‌های `test_v22.py` به‌روز شوند |
| 1.2 | تصمیم دربارهٔ داشبورد دوم: `backend/app/static/index.html` حذف شود یا به `/ui` منتقل شود و با فرانت یکی شود | 🔴 | فقط یک UI رسمی؛ `Mount("/")` حذف یا مستند شود |
| 1.3 | بازنویسی `README.md` — حذف هر ادعای اثبات‌نشده (۱۳ ابزار، SMS، `/setup` wizard، curl‌های اشتباه) | 🔴 | هر دستور curl در README با تست اجرا شده باشد |
| 1.4 | بازنویسی `docs/API.md` از OpenAPI واقعی (تولید خودکار) | 🟠 | diff بین doc و `app.openapi()` صفر باشد |
| 1.5 | اصلاح `HANDOFF.md` (مسیر اشتباه `api/v1/websockets/manager.py`) و `ARCHITECTURE.md` | 🟠 | مسیرها با درخت واقعی یکی باشند |
| 1.6 | افزودن `ADMIN_EMAIL/ADMIN_PASSWORD/AARK_VAULT_DIR` به `.env.example` با توضیح فارسی | 🟠 | تست `test_release_consistency` پاس بماند |
| 1.7 | افزودن rate limiting روی `/auth/login` (جلوگیری از brute-force) | 🟠 | تست: ۶ تلاش → ۴۲۹ |
| 1.8 | انتقال توکن WS از query param به `Sec-WebSocket-Protocol` (توکن در لاگ پروکسی نماند) | 🟡 | لاگ دسترسی حاوی توکن نباشد |
| 1.9 | افزودن `pytest --cov` با آستانه (هدف ≥۷۵٪) به CI | 🟡 | badge پوشش در README |
| 1.10 | افزودن `mypy`/`pyright` با حالت تدریجی | 🟡 | صفر خطا روی `core/`, `api/` |

**دروازهٔ انتشار v3.4.0:** همهٔ S1/S2 بسته · مستندات با OpenAPI یکسان · هیچ روت پولی بدون auth · پوشش ≥۷۵٪

---

## فاز ۲ — واقعی‌سازی لایهٔ داده و ایجنت — هدف: **v3.5.0**

**چرا؟** چون هستهٔ محاسباتی واقعی است ولی **دادهٔ ورودی ساختگی** است.

| # | تسک | معیار پذیرش |
|---|---|---|
| 2.1 | اتصال ۱۳ ابزار `ToolExecutor` به `services/trading.py` و `risk_engine` واقعی (الان همه `{"price": 0}` برمی‌گردانند) | هر ابزار یک تست integration با mock در سطح HTTP صرافی داشته باشد |
| 2.2 | جایگزینی `np.random.normal` در `/risk/var` و `/risk/correlation` با دادهٔ واقعی از جدول `market_data` | پاسخ برای دادهٔ ورودی یکسان، قطعی (deterministic) باشد |
| 2.3 | پایپ‌لاین جمع‌آوری قیمت تاریخچه (scheduler + Nobitex public API) | ۲۵۲ روز داده برای ۵ نماد |
| 2.4 | **تصمیم:** `services/paper_trader.py` وصل شود یا حذف — الان ۸۷ ارجاع در تست، ۰ در اپ | `EXCHANGE_PROVIDER=mock` واقعاً paper trader را فعال کند |
| 2.5 | **تصمیم:** `services/notification/` + `services/sms/` وصل شود یا حذف — README وعدهٔ SMS واقعی و fallback و throttling می‌دهد | یا کد وصل است و تست دارد، یا ماژول و ادعای README با هم حذف می‌شوند |
| 2.6 | نگاشت ~۳۰ کلید `.env.example` به `Settings` (الان `extra="ignore"` ساکتانه دورشان می‌ریزد) | هر کلید مستند، یا خوانده می‌شود یا از `.env.example` حذف |
| 2.7 | ایزوله‌سازی چندکاربره: `OrderManager`/`PortfolioManager` global هستند (ادعای «isolated vaults» نقض می‌شود) | هر `user_id` مدیر و vault خودش را داشته باشد + تست |
| 2.8 | راه‌اندازی Alembic به‌جای `create_all` دستی | migration برای هر تغییر مدل |
| 2.9 | persistence سفارش/پوزیشن در DB (الان در dict حافظه‌اند و با restart می‌پرند) | restart سرویس → سفارش‌ها باقی باشند |
| 2.10 | حذف یا ادغام `robots/intelligence/` (یتیم کامل) | هیچ ماژول یتیم در ریپو نماند |

**دروازهٔ انتشار v3.5.0:** صفر stub در مسیر کاربر · صفر دادهٔ تصادفی در پاسخ مالی · صفر ماژول یتیم · restart-safe

---

## فاز ۳ — بلوغ محصول و عملیات — هدف: **v4.0.0**

| # | تسک |
|---|---|
| 3.1 | PWA واقعی: انتقال `public/manifest.json` به `frontend/public/`، ساخت `icon-192/512.png` (الان ارجاع به فایل‌های ناموجود)، افزودن `<link rel="manifest">` به `layout.tsx` + service worker |
| 3.2 | Web Setup Wizard واقعی روی `/setup` (الان در README تبلیغ می‌شود ولی روت وجود ندارد) |
| 3.3 | LineChart با دادهٔ واقعی (PnL history / backtest) به‌جای `mockData` |
| 3.4 | OrderBook با دادهٔ واقعی از `/market/orderbook` به‌جای jitter تصادفی |
| 3.5 | Grafana dashboard + alerting روی `/metrics` (چک‌لیست HANDOFF) |
| 3.6 | چندصرافی: Binance/OKX adapter پشت انتزاع مشترک |
| 3.7 | WebSocket خصوصی Nobitex (order updates) به‌جای polling |
| 3.8 | Pen-test رسمی JWT + RBAC + vault |
| 3.9 | 2FA (وعدهٔ داده‌شده در SECURITY.md) |

**دروازهٔ انتشار v4.0.0:** هر وعدهٔ README یا پیاده‌سازی شده یا حذف · هیچ فایل manifest/آیکون شکسته · داشبوردها با دادهٔ واقعی

---

## بدهی فنی باز (پیوسته)

- `db/session.py` موتور را در زمان import می‌سازد → هر import به درایور DB و URL معتبر نیاز دارد
- `get_risk_engine()` و `get_nobitex_client()` از global بدون lock استفاده می‌کنند (race در startup همزمان)
- `NobitexClient.session` هرگز در lifespan بسته نمی‌شود
- `structlog` در requirements است ولی استفاده نمی‌شود
- `frontend/public/` فقط `.gitkeep` دارد؛ `backend/app/static/` داشبورد موازی است
- `smoke-test.sh` و `status.sh` اندپوینت‌های قدیمی را صدا می‌زنند — باید با ۳۹ روت واقعی هم‌راستا شوند
