# 🧙‍♂️ جادوگر نصب AARK Kernel — فوق ساده — برای مامان بزرگ!

**نسخه:** v2.0.0 — سقف 10/10 — Ceiling — Trading Platform
**زمان:** ۱ دقیقه — فقط ۳ کلیک!
**برای:** کسی که حتی نمی‌دونه ترید چیه — فقط می‌خواد پلتفرم ترید داشته باشه

---

## 🎯 AARK چیه؟ به زبان مامان بزرگ:

فرض کن می‌خوای ترید کنی — بیت‌کوین بخری و بفروشی — ولی می‌ترسی ضرر کنی.

**قبلاً:** باید ۱ سال ترید یاد می‌گرفتی، ریسک، تحلیل، استرس — سخت!

**الان با AARK:** یک ربات هوشمند داری که برات تحلیل می‌کنه + ریسک چک می‌کنه + با خیال راحت paper trading (تمرینی) می‌کنی بدون پول واقعی!

- **ربات:** AgentBrain + RiskEngine — هوشمند
- **امنیت:** JWT ۳۰ دقیقه + bcrypt + RBAC + vault با قفل ۰o700 — مثل گاوصندوق
- **نمودار:** LineChart واقعی + OrderBook زنده — مثل تابلو بورس

---

## 🚀 جادوگر نصب — فقط ۳ قدم!

### قدم ۰: چی لازم داری؟ (۳۰ ثانیه)

یک کامپیوتر با اینترنت — همین! Docker مثل جعبه جادویی — جادوگر خودش چک می‌کنه.

### قدم ۱: دانلود (۳۰ ثانیه)

```bash
git clone https://github.com/ansariaiadmin/aark-kernel.git
cd aark-kernel
```
یا zip دانلود از Releases → Extract

### قدم ۲: جادوگر نصب — فقط Enter! (۱ دقیقه)

**ویندوز:** `install.bat` دوبار کلیک

**مک/لینوکس:**
```bash
chmod +x install.sh
./install.sh
```

**چی می‌بینی؟**
```
[1/6] بررسی سیستم... ✓
[2/6] بررسی Docker... ✓ Docker 24.0.5
[3/6] بررسی Git... ✓
[4/6] وابستگی‌ها... ✓
[5/6] ساخت .env با رمز تصادفی قوی... ✓
[6/6] docker compose up --build -d
....................
✓ سرویس آماده!

آدرس Frontend: http://localhost:3000
آدرس API Docs: http://localhost:8000/docs
```

### قدم ۳: استفاده (۱۰ ثانیه)

مرورگر → `http://localhost:3000` — داشبورد ترید
API Docs → `http://localhost:8000/docs` — برای دولوپرها

**ورود:** JWT login via `/api/v1/auth/login`

**چی می‌بینی؟**
- 📈 LineChart واقعی — قیمت + حجم + ریسک — زنده via WebSocket
- 📊 OrderBook — Bids سبز + Asks قرمز — زنده
- 🤖 ML Risk Engine — Risk Low, Allocation OK, Agent Bullish

---

## 🔄 آپدیت — `./update.sh` — ۳۰ ثانیه — بکاپ خودکار

## 🛠️ دستورات — مثل کنترل تلویزیون:
- `./status.sh` — روشنه؟
- `./logs.sh` — چی می‌گذره؟
- `./stop.sh` / `./start.sh`

## 🆘 عیب‌یابی — به زبان ساده:

**پورت اشغال:** `./stop.sh` + `docker compose down` + `./start.sh`

**Docker نیست:** https://docs.docker.com/get-docker/ — Docker Desktop نصب

**.env خراب:** `rm .env` + `cp .env.example .env` + `./install.sh`

**سرویس بالا نمی‌آد:** `./logs.sh` — لاگ بخون — معمولاً رمز دیتابیس

---

## 🔒 امنیت — به زبان ساده:
- `.env` کلید خونه — به کسی نده!
- Vault `~/.aark/nobitex.vault` با قفل 0o700 — گاوصندوق
- JWT 30 دقیقه + bcrypt cost 12 + RBAC Admin/Trader/Viewer
- Non-root Docker USER appuser 1001 + USER nextjs 1001 — نه root

---

**برای غیر فنی:** فقط `install.sh` → مرورگر → localhost:3000 → LineChart + OrderBook — همین! 🎉

**نویسنده:** Fleet 10/10 — سطح اعلی — نهایت سادگی
**نسخه:** v2.0.0 — سقف
