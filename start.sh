#!/usr/bin/env bash
set -e
echo "شروع AARK Kernel — Trading Platform / Starting AARK Kernel — Trading Platform..."
if [ -f docker-compose.yml ]; then
  docker compose up -d
  docker compose ps
  echo "✓ اجرا شد / Started - http://localhost:3000 (Frontend) و http://localhost:8000/docs (API)"
else
  echo "برای CLI: ./project-robots --help یا source .venv/bin/activate && python -m app.main"
  if [ -f package.json ]; then npm run dev; fi
fi
