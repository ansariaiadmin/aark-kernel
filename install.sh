#!/usr/bin/env bash
set -e
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
ok() { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
err() { echo -e "${RED}❌ $1${NC}"; }
explain() { echo -e "${CYAN}   💡 $1${NC}"; }
example() { echo -e "${DIM}   📝 مثال: $1${NC}"; }
where() { echo -e "${MAGENTA}   🔗 کجا پیدا کنم؟ $1${NC}"; }

generate_secret() {
  if command -v openssl &> /dev/null; then
    openssl rand -base64 32 | tr -d '\n' | tr -d '/' | tr -d '+' | cut -c1-32
  else
    date +%s | sha256sum | head -c 32
  fi
}

ask_with_help() {
  local prompt="$1"; local help_text="$2"; local example_text="$3"; local where_text="$4"; local default_val="$5"; local is_secret="${6:-false}"
  echo ""; echo -e "${BOLD}${BLUE}❓ $prompt${NC}"
  if [ -n "$help_text" ]; then explain "$help_text"; fi
  if [ -n "$example_text" ]; then example "$example_text"; fi
  if [ -n "$where_text" ]; then where "$where_text"; fi
  if [ -n "$default_val" ]; then echo -e "${DIM}   ⏭️  Enter = پیش‌فرض: $default_val${NC}"; else echo -e "${DIM}   ⏭️  اگر نداری Enter = mock (بعداً می‌تونی اضافه کنی)${NC}"; fi
  local input=""; if [ "$is_secret" = "true" ]; then read -s -p "   👉 جواب: " input; echo ""; else read -p "   👉 جواب: " input; fi
  if [ -z "$input" ] && [ -n "$default_val" ]; then input="$default_val"; fi
  echo "$input"
}

ask_yes_no() {
  local prompt="$1"; local help_text="$2"; local default_yes="${3:-true}"
  echo ""; echo -e "${BOLD}${BLUE}❓ $prompt${NC}"
  if [ -n "$help_text" ]; then explain "$help_text"; fi
  if [ "$default_yes" = "true" ]; then echo -e "${DIM}   ⏭️  [Y/n] Enter=بله${NC}"; else echo -e "${DIM}   ⏭️  [y/N] Enter=خیر${NC}"; fi
  local input=""; read -p "   👉 جواب (y/n): " input; input=$(echo "$input" | tr '[:upper:]' '[:lower:]')
  if [ -z "$input" ]; then if [ "$default_yes" = "true" ]; then input="y"; else input="n"; fi; fi
  if [ "$input" = "y" ] || [ "$input" = "yes" ] || [ "$input" = "بله" ]; then echo "yes"; else echo "no"; fi
}

clear
echo -e "${CYAN}"
cat <<'BANNER'
    _    _    ____  _  __
   / \  / \  |  _ \| |/ /
  / _ \/ _ \ | |_) | ' /
 / ___/ ___ \|  _ <| . \
/_/  /_/  \_\_| \_\_|\_\

Kernel — Trading + AI + Risk + Notification — Zero Support
BANNER
echo -e "${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  🧙‍♂️ جادوگر نصب AARK v3.0.0 — پشتیبانی صفر${NC}"
echo -e "${BLUE}  ترید + AI + ریسک + SMS + ناتیف${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}سلام تریدر! 👋 من جادوگر AARK هستم${NC}"
echo -e "${CYAN}هدف: پشتیبانی صفر — همه چی همینجا توضیح می‌دم — فقط ضروری‌ها!${NC}"
echo ""
read -p "برای شروع جادو Enter بزنید... ✨ " _

echo ""
echo -e "${BLUE}[1/8] 🔍 سیستم${NC}"
ok "سیستم اوکیه — $(uname -s) $(uname -m)"
sleep 1

echo ""
echo -e "${BLUE}[2/8] 🐳 Docker — جعبه جادویی${NC}"
if ! command -v docker &> /dev/null; then err "Docker نیست"; where "https://docs.docker.com/get-docker/"; exit 1; else ok "Docker: $(docker --version)"; fi
sleep 1

echo ""
echo -e "${BLUE}[3/8] 🔑 رمزهای بانکی — خودکار${NC}"
SECRET_API=$(generate_secret)
SECRET_DB=$(generate_secret)
SECRET_REDIS=$(generate_secret)
ok "3 رمز 32 کاراکتری ساخته شد — مثل رمز بانکی"
sleep 1

echo ""
echo -e "${BLUE}[4/8] 🤖 AI Provider — برای تحلیل بازار${NC}"
explain "AARK از AI برای تحلیل ریسک و بازار استفاده می‌کنه — مثل مشاور هوشمند"
echo -e "${YELLOW}   گزینه‌ها: openai, anthropic, groq, ollama (لوکال رایگان), mock${NC}"
AI_PROVIDER=$(ask_with_help "پرووایدر AI کدوم؟" "برای تحلیل بازار و ریسک — اگر نمی‌دونی ollama یا mock بزن — ollama لوکال رایگان" "ollama یا openai یا mock" "https://platform.openai.com/api-keys یا Ollama نصب کن: https://ollama.com/" "ollama" "false")
AI_KEY=""
if [ "$AI_PROVIDER" != "ollama" ] && [ "$AI_PROVIDER" != "mock" ]; then
  AI_KEY=$(ask_with_help "کلید API $AI_PROVIDER؟" "از سایت پرووایدر کپی کن — با sk- شروع می‌شه" "sk-..." "https://platform.openai.com/api-keys" "" "true")
  [ -n "$AI_KEY" ] && ok "AI کلید تنظیم شد" || warn "AI mock می‌شه"
fi
sleep 1

echo ""
echo -e "${BLUE}[5/8] 💱 صرافی — Exchange Provider — برای ترید واقعی${NC}"
explain "صرافی چیه؟ جایی که ترید می‌کنی — مثل نوبیتکس — برای ترید واقعی نیاز به API Key داره — ولی paper trading بدون پول واقعی هم داره (پیش‌فرض)"
echo -e "${YELLOW}   گزینه‌ها: nobitex (ایرانی), mock (paper trading بدون پول واقعی)${NC}"
EXCHANGE=$(ask_with_help "کدوم صرافی؟" "برای ترید واقعی — اگر نمی‌خوای ترید واقعی کنی mock بزن — paper trading تمرینی بدون پول" "nobitex یا mock" "https://nobitex.ir/ → حساب → API" "mock" "false")
NOBITEX_KEY=""; NOBITEX_SECRET=""
if [ "$EXCHANGE" = "nobitex" ]; then
  NOBITEX_KEY=$(ask_with_help "API Key نوبیتکس؟" "از نوبیتکس → حساب کاربری → API" "api-key-..." "https://nobitex.ir/panel/api" "" "true")
  NOBITEX_SECRET=$(ask_with_help "API Secret نوبیتکس؟" "همونجا — Secret" "secret-..." "https://nobitex.ir/panel/api" "" "true")
  [ -n "$NOBITEX_KEY" ] && ok "Nobitex تنظیم شد" || warn "Nobitex mock می‌شه"
else
  EXCHANGE="mock"
  explain "حالت paper trading — بدون پول واقعی — امن برای تست — بعداً می‌تونی نوبیتکس اضافه کنی"
fi
sleep 1

echo ""
echo -e "${BLUE}[6/8] 📱 SMS + 📧 Email — برای ناتیف ترید${NC}"
explain "وقتی ترید انجام می‌شه یا ریسک بالا می‌ره، با پیامک/ایمیل خبر می‌ده"
SMS_PROVIDER=$(ask_with_help "پنل پیامکی کدوم؟" "برای ناتیف ترید — مثل 'ترید انجام شد' — اگر نداری mock" "ghasedak یا kavenegar یا mock" "https://ghasedak.me/ — API Key" "mock" "false")
SMS_KEY=""
if [ "$SMS_PROVIDER" != "mock" ]; then
  SMS_KEY=$(ask_with_help "کلید API پنل $SMS_PROVIDER؟" "از پنل کپی کن" "api-key-..." "پنل → تنظیمات → API" "" "true")
  ok "SMS تنظیم شد"
fi

EMAIL_PROVIDER=$(ask_with_help "ایمیل پرووایدر؟" "برای ناتیف ترید با ایمیل" "smtp یا mock" "Gmail App Passwords" "mock" "false")
SMTP_HOST=""; SMTP_USER=""; SMTP_PASS=""
if [ "$EMAIL_PROVIDER" = "smtp" ]; then
  SMTP_HOST=$(ask_with_help "SMTP Host؟" "مثل smtp.gmail.com" "smtp.gmail.com" "Gmail یا هاست" "smtp.gmail.com" "false")
  SMTP_USER=$(ask_with_help "SMTP User؟" "ایمیل" "you@gmail.com" "ایمیل خودت" "" "false")
  SMTP_PASS=$(ask_with_help "SMTP Pass؟" "App Password" "app-pass-..." "myaccount.google.com → App Passwords" "" "true")
  ok "SMTP تنظیم شد"
fi
sleep 1

echo ""
echo -e "${BLUE}[7/8] 🔔 سیستم ناتیفیکیشن — Notification — ترید + ریسک${NC}"
explain "وقتی ترید می‌شه، ریسک بالا می‌ره، یا خطا میاد — خبر می‌ده — کانال‌ها: داخل برنامه + ایمیل + پیامک + تلگرام"
NOTIF_EMAIL=$(ask_yes_no "ایمیل ناتیف برای ترید روشن باشه؟" "وقتی ترید انجام می‌شه ایمیل بره" "true")
NOTIF_SMS=$(ask_yes_no "پیامک ناتیف برای ترید روشن باشه؟" "وقتی ریسک بالا می‌ره پیامک بره" "true")
TELEGRAM_ENABLED=$(ask_yes_no "ربات تلگرام برای ناتیف ترید می‌خوای؟" "وقتی ترید یا خطا میاد تلگرام خبر می‌ده — رایگان" "false")
TELEGRAM_TOKEN=""; TELEGRAM_CHAT=""
if [ "$TELEGRAM_ENABLED" = "yes" ]; then
  echo -e "${BOLD}   چطور ربات بسازم؟ @BotFather → /newbot → توکن${NC}"
  TELEGRAM_TOKEN=$(ask_with_help "توکن ربات؟" "از @BotFather" "123456:ABC..." "@BotFather → /newbot" "" "true")
  TELEGRAM_CHAT=$(ask_with_help "Chat ID؟" "از getUpdates" "123456789" "https://api.telegram.org/bot<TOKEN>/getUpdates" "" "false")
  ok "Telegram تنظیم شد"
fi
sleep 1

echo ""
echo -e "${BLUE}[8/8] ⚙️ ساخت .env + 🏗️ اجرا${NC}"
cat > .env <<EOF
# AARK Kernel — .env — جادوگر v3.0.0 — پشتیبانی صفر — $(date)
# دیتابیس
API_SECRET_KEY=${SECRET_API}
POSTGRES_DB=aark_db
POSTGRES_USER=aark_admin
POSTGRES_PASSWORD=${SECRET_DB}
REDIS_PASSWORD=${SECRET_REDIS}
DATABASE_URL=postgresql+asyncpg://aark_admin:${SECRET_DB}@postgres:5432/aark_db
REDIS_URL=redis://:${SECRET_REDIS}@redis:6379/0

# AI Provider — برای تحلیل
# چیه؟ هوش مصنوعی برای تحلیل بازار — گزینه: openai, anthropic, groq, ollama, mock
AI_PROVIDER=${AI_PROVIDER}
OPENAI_API_KEY=${AI_KEY}
ANTHROPIC_API_KEY=${AI_KEY}
GROQ_API_KEY=${AI_KEY}
LOCAL_OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=qwen2.5:7b

# Exchange — صرافی — برای ترید واقعی
# چیه؟ نوبیتکس — اگر mock باشه paper trading بدون پول واقعی
EXCHANGE_PROVIDER=${EXCHANGE}
NOBITEX_API_KEY=${NOBITEX_KEY}
NOBITEX_API_SECRET=${NOBITEX_SECRET}

# SMS — پنل پیامکی — برای ناتیف ترید
SMS_PROVIDER=${SMS_PROVIDER}
SMS_API_KEY=${SMS_KEY}
SMS_SENDER=
GHASEDAK_API_KEY=${SMS_KEY}
KAVENEGAR_API_KEY=${SMS_KEY}

# Email — ایمیل — برای ناتیف
EMAIL_PROVIDER=${EMAIL_PROVIDER}
SMTP_HOST=${SMTP_HOST}
SMTP_PORT=587
SMTP_USER=${SMTP_USER}
SMTP_PASS=${SMTP_PASS}

# Notification System — سیستم ناتیف — سقف 10/10
# چیه؟ اطلاع‌رسانی ترید + ریسک + خطا — کانال‌ها: in_app + email + sms + telegram
NOTIF_IN_APP=true
NOTIF_EMAIL=${NOTIF_EMAIL}
NOTIF_SMS=${NOTIF_SMS}
NOTIF_TELEGRAM=${TELEGRAM_ENABLED}
TELEGRAM_BOT_TOKEN=${TELEGRAM_TOKEN}
TELEGRAM_CHAT_ID=${TELEGRAM_CHAT}

# Ports
AARK_BACKEND_PORT=8000
AARK_FRONTEND_PORT=3000
LOG_LEVEL=INFO
ENVIRONMENT=development
EOF

ok ".env ساخته شد — $(wc -l < .env) خط — با توضیح فارسی"

echo -e "${MAGENTA}  docker compose up --build -d${NC}"
docker compose up --build -d 2>&1 | tail -n 20 || docker compose up -d
echo ""
echo -e "${BLUE}  ⏳ 30 ثانیه صبر — چای دم کردن...${NC}"
echo -n "  "
for i in {1..30}; do echo -n "."; sleep 1; if curl -sf http://localhost:3000 >/dev/null 2>&1; then echo ""; ok "آماده!"; break; fi; done
echo ""
docker compose ps 2>/dev/null || true

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  🎉 جادو تمام! AARK آماده — پشتیبانی صفر! 🎉${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BOLD}${BLUE}📍 دسترسی:${NC}"
echo -e "${GREEN}  🌐 Frontend: http://localhost:3000 — LineChart + OrderBook زنده${NC}"
echo -e "${GREEN}  📚 API Docs: http://localhost:8000/docs${NC}"
echo ""
echo -e "${BOLD}${BLUE}✅ چک‌لیست:${NC}"
echo -e "  $([ "$AI_PROVIDER" != "mock" ] && echo "✅" || echo "⚠️") AI: $AI_PROVIDER"
echo -e "  $([ "$EXCHANGE" != "mock" ] && echo "✅" || echo "⚠️") Exchange: $EXCHANGE — $([ "$EXCHANGE" = "mock" ] && echo "paper trading بدون پول واقعی — امن" || echo "ترید واقعی — مراقب باش!")"
echo -e "  $([ "$SMS_PROVIDER" != "mock" ] && echo "✅" || echo "⚠️") SMS: $SMS_PROVIDER"
echo -e "  ✅ In-App Notif: همیشه روشن"
echo -e "  $([ "$NOTIF_EMAIL" = "yes" ] && echo "✅" || echo "⚪") Email Notif: $NOTIF_EMAIL"
echo -e "  $([ "$NOTIF_SMS" = "yes" ] && echo "✅" || echo "⚪") SMS Notif: $NOTIF_SMS"
echo -e "  $([ "$TELEGRAM_ENABLED" = "yes" ] && echo "✅" || echo "⚪") Telegram Notif: $TELEGRAM_ENABLED"
echo ""
echo -e "${BOLD}${BLUE}🎯 حالا چی؟${NC}"
echo -e "${YELLOW}  1. مرورگر → localhost:3000 → داشبورد ترید → LineChart + OrderBook${NC}"
echo -e "${YELLOW}  2. Paper trading تست کن — بدون پول واقعی${NC}"
echo -e "${YELLOW}  3. اگر mock بود: .env → کلید واقعی → docker compose restart${NC}"
echo ""
echo -e "${CYAN}📚 docs/SETUP-WIZARD-FA.md — برای مامان بزرگ!${NC}"
echo ""
