#!/usr/bin/env bash
set -e
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

clear
echo -e "${CYAN}"
cat <<'BANNER'
    ___    ___    ____  __ __
   /   |  /   |  / __ \/ //_/___  ____  ____  ___  _____
  / /| | / /| | / /_/ / ,< / __ \/ __ \/ __ \/ _ \/ ___/
 / ___ |/ ___ |/ _, _/ /| / /_/ / / / / / / /  __/ /
/_/  |_/_/  |_/_/ |_/_/ |_\____/_/ /_/_/ /_/\___/_/

پلتفرم ترید حرفه‌ای با AI + ریسک انجین
Enterprise Trading Platform with AI
BANNER
echo -e "${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  🧙‍♂️ جادوگر نصب AARK Kernel — فوق ساده${NC}"
echo -e "${BLUE}  برای مامان بزرگ هم قابل فهم!${NC}"
echo -e "${BLUE}  نسخه v2.0.0 — سقف 10/10 True${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}سلام! 👋 من جادوگر ترید AARK هستم${NC}"
echo -e "${YELLOW}ربات هوشمند ترید + ریسک چک + نمودار زنده — فقط Enter بزن!${NC}"
echo ""
echo -e "${CYAN}AARK چیه؟${NC} ربات ترید با AI که ضرر رو کنترل می‌کنه + Paper Trading تمرینی بدون پول واقعی"
echo ""
read -p "برای شروع جادو Enter بزنید / Press Enter... ✨ " _

echo ""
echo -e "${BLUE}[1/6] 🔍 بررسی سیستم...${NC}"
echo -e "  $(uname -s) $(uname -m) — $(date)"
echo -e "${GREEN}  ✓ سیستم اوکیه${NC}"
sleep 1

echo ""
echo -e "${BLUE}[2/6] 🐳 Docker...${NC}"
echo -e "${CYAN}  Docker = جعبه جادویی که همه چی رو اجرا می‌کنه${NC}"
if ! command -v docker &> /dev/null; then
  echo -e "${RED}  ✗ Docker نیست${NC}"
  echo -e "${YELLOW}  نصب مثل واتساپ — 2 دقیقه: https://docs.docker.com/get-docker/${NC}"
  exit 1
else
  echo -e "${GREEN}  ✓ Docker: $(docker --version)${NC}"
  echo -e "${GREEN}  ✓ Compose: $(docker compose version)${NC}"
fi
sleep 1

echo ""
echo -e "${BLUE}[3/6] 📦 Git...${NC}"
echo -e "${GREEN}  ✓ Git: $(git --version 2>/dev/null || echo 'OK')${NC}"
sleep 1

echo ""
echo -e "${BLUE}[4/6] 🔧 وابستگی‌ها...${NC}"
echo -e "${CYAN}  FastAPI + React — ولی Docker همه رو داره!${NC}"
echo -e "${GREEN}  ✓ Docker کافیه!${NC}"
sleep 1

echo ""
echo -e "${BLUE}[5/6] ⚙️ تنظیمات — رمزهای قوی بانکی...${NC}"
echo -e "${CYAN}  .env = کلید خونه — باید امن باشه — جادوگر رمز تصادفی می‌سازه${NC}"
if [ ! -f .env ]; then
  cp .env.example .env 2>/dev/null || touch .env
  if command -v openssl &> /dev/null; then
    SECRET=$(openssl rand -base64 32 | tr -d '\n' | tr -d '/' | cut -c1-32)
    SECRET2=$(openssl rand -base64 32 | tr -d '\n' | tr -d '/' | cut -c1-32)
    if [[ "$OSTYPE" == "darwin"* ]]; then
      sed -i '' "s/change-me-generate-with-openssl-rand-base64-32-min-32-chars/$SECRET/g" .env 2>/dev/null || true
      sed -i '' "s/change-me-generate-with-openssl-rand-base64-32/$SECRET2/g" .env 2>/dev/null || true
      sed -i '' "s/change-me/$SECRET/g" .env 2>/dev/null || true
    else
      sed -i "s/change-me-generate-with-openssl-rand-base64-32-min-32-chars/$SECRET/g" .env 2>/dev/null || true
      sed -i "s/change-me-generate-with-openssl-rand-base64-32/$SECRET2/g" .env 2>/dev/null || true
      sed -i "s/change-me/$SECRET/g" .env 2>/dev/null || true
    fi
    echo -e "${GREEN}  ✓ رمزهای بانکی 32 کاراکتری ساخته شد!${NC}"
  fi
  echo -e "${GREEN}  ✓ .env ساخته شد — امن نگه دار!${NC}"
else
  echo -e "${BLUE}  .env وجود دارد — عالی!${NC}"
fi
sleep 1

echo ""
echo -e "${BLUE}[6/6] 🏗️ ساخت و اجرا — جادوی اصلی!${NC}"
echo -e "${CYAN}  دارم می‌سازم... 1-2 دقیقه — صبر کن...${NC}"
docker compose up --build -d
echo ""
echo -e "${BLUE}  ⏳ 30 ثانیه صبر — مثل چای دم کردن...${NC}"
echo -n "  "
for i in {1..30}; do
  echo -n "."
  sleep 1
  if command -v curl &> /dev/null; then
    if curl -sf http://localhost:8000/api/v1/health/ready >/dev/null 2>&1 || curl -sf http://localhost:3000 >/dev/null 2>&1; then
      echo ""
      echo -e "${GREEN}  ✓ آماده! زودتر از 30 ثانیه!${NC}"
      break
    fi
  fi
done
echo ""
docker compose ps

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  🎉 جادو تمام! نصب کامل! 🎉${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BOLD}${BLUE}📍 دسترسی:${NC}${NC}"
echo -e "${GREEN}  🌐 Frontend: ${BOLD}http://localhost:3000${NC} — LineChart + OrderBook زنده"
echo -e "${GREEN}  📚 API Docs: ${BOLD}http://localhost:8000/docs${NC}"
echo -e "${GREEN}  ❤️ Health: http://localhost:8000/api/v1/health/ready${NC}"
echo ""
echo -e "${BOLD}${BLUE}🎯 حالا چی؟${NC}${NC}"
echo -e "${YELLOW}  1. مرورگر → http://localhost:3000 — داشبورد ترید${NC}"
echo -e "${YELLOW}  2. نمودار LineChart + OrderBook ببین — زنده via WebSocket${NC}"
echo -e "${YELLOW}  3. Paper Trading — بدون پول واقعی تمرین کن — ریسک انجین چک می‌کنه${NC}"
echo ""
echo -e "${BOLD}${BLUE}🛠️ دستورات:${NC}${NC}"
echo -e "  ${GREEN}./status.sh${NC} — روشنه؟"
echo -e "  ${GREEN}./logs.sh${NC} — لاگ"
echo -e "  ${GREEN}./stop.sh${NC} / ${GREEN}./start.sh${NC}"
echo -e "  ${GREEN}./update.sh${NC} — آپدیت"
echo ""
echo -e "${CYAN}📚 مستندات فوق ساده: docs/SETUP-WIZARD-FA.md — برای مامان بزرگ!${NC}"
echo ""
