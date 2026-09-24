from fastapi import APIRouter

from app.api.v1.ai import router as ai_router
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.risk import router as risk_router
from app.api.v1.trading import router as trading_router
from app.websockets.manager import router as ws_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(ai_router, prefix="/ai")
api_router.include_router(trading_router, prefix="/trading")
api_router.include_router(risk_router, prefix="/risk")
api_router.include_router(auth_router)
api_router.include_router(ws_router, prefix="/ws")