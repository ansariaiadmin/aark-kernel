@echo off
echo ========================================
echo   AARK Kernel — Trading Platform - Auto Installer
echo   پلتفرم ترید حرفه‌ای با AI
echo ========================================
echo.
echo For non-technical - just press Enter
echo.

echo [1/4] Checking Docker...
docker --version
if %errorlevel% neq 0 (
  echo Docker not found - please install Docker Desktop https://docs.docker.com/get-docker/
  pause
  exit /b 1
)
docker compose version
if %errorlevel% neq 0 (
  echo Docker Compose V2 not found
  pause
  exit /b 1
)

echo [2/4] Checking Git...
git --version

echo [3/4] Creating .env...
if not exist .env (
  if exist .env.example (
    copy .env.example .env
    echo .env created from .env.example
  ) else (
    echo . > .env
  )
) else (
  echo .env already exists
)

echo [4/4] Building and starting...
docker compose up --build -d
timeout /t 15
docker compose ps

echo.
echo ========================================
echo Installation Complete! / نصب تمام شد!
echo URL: http://localhost:3000 (Frontend) و http://localhost:8000/docs (API)
echo Login: JWT login via /api/v1/auth/login
echo ========================================
echo For logs: logs.bat
echo For status: status.bat
echo For update: update.bat
pause
