@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo ========================================
echo   aark-kernel — Setup Wizard v3.1.0 — Windows
echo ========================================
echo.
echo سلام! 👋 جادوگر aark-kernel
echo.

echo [1/6] Checking Docker...
docker --version
if %errorlevel% neq 0 (
  echo Docker not found — https://docs.docker.com/get-docker/
  pause
  exit /b 1
)
docker compose version
if %errorlevel% neq 0 (
  echo Docker Compose V2 not found
  pause
  exit /b 1
)

echo [2/6] Secrets — خودکار
for /f %%i in ('powershell -command "[System.Guid]::NewGuid().ToString().Substring(0,32)"') do set SECRET=%%i
echo   ✅ رمز ساخته شد: %SECRET:~0,8%...

echo [3/6] AI Provider — با هزینه
echo   گزینه‌ها: openai (هر درخواست ~0.01 دلار), ollama (رایگان), mock (رایگان)
set /p AI_PROVIDER=❓ AI Provider (openai/ollama/mock) [mock]: 
if "%AI_PROVIDER%"=="" set AI_PROVIDER=mock
set AI_KEY=
if not "%AI_PROVIDER%"=="mock" (
  set /p AI_KEY=❓ API Key (sk-...): 
)

echo [4/6] SMS Panel — با هزینه + تست واقعی
echo   گزینه‌ها: ghasedak (هر پیامک ~120 تومان — https://ghasedak.me/), kavenegar, mock (رایگان)
set /p SMS_PROVIDER=❓ SMS Provider (ghasedak/kavenegar/mock) [mock]: 
if "%SMS_PROVIDER%"=="" set SMS_PROVIDER=mock
set SMS_KEY=
set SMS_SENDER=
if not "%SMS_PROVIDER%"=="mock" (
  set /p SMS_KEY=❓ API Key: 
  set /p SMS_SENDER=❓ Sender (مثل 10008566): 
  echo   💰 هزینه هر پیامک ~120 تومان
)

echo [5/6] Notification — Telegram — رایگان — بهترین
set /p TELEGRAM_ENABLED=❓ Telegram Bot می‌خوای؟ (y/n) [n]: 
set TELEGRAM_TOKEN=
set TELEGRAM_CHAT=
if /i "%TELEGRAM_ENABLED%"=="y" (
  echo   @BotFather → /newbot → توکن → https://api.telegram.org/bot^<TOKEN^>/getUpdates → chat_id
  set /p TELEGRAM_TOKEN=❓ Bot Token: 
  set /p TELEGRAM_CHAT=❓ Chat ID: 
)

echo [6/6] .env + Build — با 600 + idempotency
if exist .env (
  echo   .env وجود داره — keep یا new یا backup?
  set /p KEEP_ENV=❓ (keep/new/backup) [keep]: 
  if "!KEEP_ENV!"=="" set KEEP_ENV=keep
  if /i "!KEEP_ENV!"=="backup" (
    copy .env .env.backup.%date:~-4,4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%%time:~6,2% >nul
    echo   ✅ بکاپ گرفته شد
    set KEEP_ENV=new
  )
  if /i not "!KEEP_ENV!"=="keep" (
    echo   .env جدید می‌سازم...
    goto create_env
  ) else (
    echo   .env نگه داشته شد — idempotency
    goto build
  )
)

:create_env
(
echo # aark-kernel — .env — %date% %time%
echo # AI Provider — با هزینه
echo AI_PROVIDER=%AI_PROVIDER%
echo OPENAI_API_KEY=%AI_KEY%
echo ANTHROPIC_API_KEY=%AI_KEY%
echo # SMS — با هزینه + تست واقعی
echo SMS_PROVIDER=%SMS_PROVIDER%
echo SMS_API_KEY=%SMS_KEY%
echo SMS_SENDER=%SMS_SENDER%
echo # Notification — با throttling
echo NOTIF_IN_APP=true
echo NOTIF_TELEGRAM=%TELEGRAM_ENABLED%
echo TELEGRAM_BOT_TOKEN=%TELEGRAM_TOKEN%
echo TELEGRAM_CHAT_ID=%TELEGRAM_CHAT%
echo # Security — 600
echo API_SECRET_KEY=%SECRET%
echo POSTGRES_PASSWORD=%SECRET%
) > .env
echo   ✅ .env ساخته شد

:build
echo   docker compose up --build -d
docker compose up --build -d
timeout /t 15
docker compose ps

echo.
echo 🎉 جادو تمام! aark-kernel آماده! 🎉
echo 🌐 http://localhost:3000 یا http://localhost:8000
echo ✅ .env permission 600 — امن
echo ✅ idempotency — دوباره بزنی نمی‌پره
echo ✅ هزینه: SMS هر پیامک ~120 تومان — AI هر درخواست ~0.01 دلار — Telegram رایگان
echo.
echo status.bat — وضعیت پرووایدرها
echo smoke-test.bat — تست کامل
echo.
pause
