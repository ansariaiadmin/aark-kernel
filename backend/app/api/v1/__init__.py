"""API v1 aggregation.

The v1 surface is split into three routers by *authentication posture* so that
`app.main` can mount them with the right dependencies:

* :data:`public_router`     — health probes + auth (login must stay anonymous)
* :data:`protected_router`  — ai / trading / risk, mounted behind JWT + RBAC
* :data:`realtime_router`   — WebSocket, which authenticates via `?token=` in
  the handshake (OAuth2PasswordBearer cannot run on a WS upgrade request)

:data:`api_router` is the plain aggregate of all three and exists for
introspection/tests.

.. note::
   This module used to build a single ``api_router`` that `app.main` never
   mounted — only ``health.router`` was wired up — so every ai/auth/trading/
   risk/ws endpoint advertised in README, HANDOFF and docs/API.md returned 404.
"""

from fastapi import APIRouter

from app.api.v1.ai import router as ai_router
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.risk import router as risk_router
from app.api.v1.trading import router as trading_router
from app.websockets.manager import router as ws_router

#: Reachable without credentials.
public_router = APIRouter()
public_router.include_router(health_router)
public_router.include_router(auth_router)

#: Reachable only with a valid, active JWT (dependency applied in `app.main`).
protected_router = APIRouter()
protected_router.include_router(ai_router, prefix="/ai")
protected_router.include_router(trading_router, prefix="/trading")
protected_router.include_router(risk_router, prefix="/risk")

#: Self-authenticating WebSocket surface.
realtime_router = APIRouter()
realtime_router.include_router(ws_router, prefix="/ws")

#: Aggregate of the full v1 surface.
api_router = APIRouter()
api_router.include_router(public_router)
api_router.include_router(protected_router)
api_router.include_router(realtime_router)

__all__ = [
    "api_router",
    "public_router",
    "protected_router",
    "realtime_router",
]
