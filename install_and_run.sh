#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}====================================================${NC}"
echo -e "${GREEN}   🚀 AARK Kernel Auto-Installer & Launcher       ${NC}"
echo -e "${CYAN}====================================================${NC}"

# Target desktop deployment
TARGET_DIR="$HOME/Desktop/aark-core"
if [ ! -d "$HOME/Desktop" ]; then
    TARGET_DIR="$HOME/aark-core"
fi

echo -e "${CYAN}[1/4] کپی سورس پروژه به پوشه هدف: ${TARGET_DIR} ...${NC}"
mkdir -p "$TARGET_DIR"
cp -r ./* "$TARGET_DIR/" 2>/dev/null || true
cd "$TARGET_DIR"

SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo &>/dev/null; then
        SUDO="sudo"
    else
        echo -e "${RED}[ERROR] نیاز به دسترسی root یا ابزار sudo دارید.${NC}"
        exit 1
    fi
fi

# Docker & Compose check/install
echo -e "${CYAN}[2/4] بررسی و نصب خودکار وابستگی‌های سیستمی...${NC}"
if ! command -v docker &>/dev/null; then
    echo -e "${YELLOW}[INFO] در حال نصب Docker Engine...${NC}"
    $SUDO apt-get update -y
    $SUDO apt-get install -y ca-certificates curl gnupg lsb-release
    $SUDO install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | $SUDO gpg --dearmor --yes -o /etc/apt/keyrings/docker.gpg
    $SUDO chmod a+r /etc/apt/keyrings/docker.gpg

    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | $SUDO tee /etc/apt/sources.list.d/docker.list > /dev/null

    $SUDO apt-get update -y
    $SUDO apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    $SUDO systemctl enable --now docker
    $SUDO usermod -aG docker "$USER" || true
else
    echo -e "${GREEN}[OK] Docker از قبل نصب است.${NC}"
fi

# Generate Secrets
echo -e "${CYAN}[3/4] بررسی و تولید سکرت‌ها (.env)...${NC}"
if [ ! -f .env ]; then
    cat <<EOF > .env
POSTGRES_DB=aark_db
POSTGRES_USER=aark_admin
POSTGRES_PASSWORD=$(openssl rand -hex 16 2>/dev/null || echo "aark_pass_$(date +%s)")
REDIS_PASSWORD=$(openssl rand -hex 16 2>/dev/null || echo "redis_pass_$(date +%s)")
API_SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || echo "jwt_secret_key_$(date +%s)")
LOCAL_OLLAMA_HOST=http://host.docker.internal:11434
EOF
    echo -e "${GREEN}[OK] فایل .env ایجاد شد.${NC}"
fi

# Spin up
echo -e "${CYAN}[4/4] در حال بیلد و بالا آوردن سرویس‌ها...${NC}"
$SUDO docker compose down --remove-orphans || true
$SUDO docker compose up --build -d

echo ""
echo -e "${GREEN}====================================================${NC}"
echo -e "${GREEN} ✨ سیستم با موفقیت مستقر و اجرا شد!             ${NC}"
echo -e "${CYAN} 📂 مسیر پروژه:  ${TARGET_DIR}                    ${NC}"
echo -e "${CYAN} 🌐 داشبورد وب:  http://localhost:3000            ${NC}"
echo -e "${CYAN} ⚙️ بک‌اند API:   http://localhost:8000/docs       ${NC}"
echo -e "${GREEN}====================================================${NC}"
