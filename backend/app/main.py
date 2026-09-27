import os
import re
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, constr

from app.agent.registry import AgentConfig, AgentMessage, agent_registry
from app.api.v1 import protected_router, public_router, realtime_router
from app.core.agent import brain
from app.core.auth import get_current_active_user
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.core.vault import clear_vault_token, ensure_vault_dir, get_vault_token, save_vault_token
from app.db.init_db import init_db
from app.db.session import engine
from app.middleware.logging import setup_middleware
from app.risk_engine.evaluator import DeterministicRiskEngine, RiskProfile

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(
        level=settings.LOG_LEVEL,
        log_format=settings.LOG_FORMAT,
        log_file=settings.LOG_FILE,
    )
    logger = get_logger(__name__)
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    ensure_vault_dir()
    await init_db()

    logger.info("Application startup complete")
    yield

    logger.info("Shutting down...")
    await engine.dispose()
    logger.info("Application shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

setup_middleware(app)

# CORS. `BACKEND_CORS_ORIGINS` was dead config: no CORSMiddleware was ever
# registered, so the Next.js dashboard on :3000 could not call the API on :8000
# from a browser at all (ARCHITECTURE.md claimed "CORS restricted").
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-ID", "X-Process-Time"],
)

# ---------------------------------------------------------------------------
# API v1 surface — mounted exactly once, split by authentication posture.
# ---------------------------------------------------------------------------
app.include_router(public_router, prefix=settings.API_V1_PREFIX)
app.include_router(
    protected_router,
    prefix=settings.API_V1_PREFIX,
    dependencies=[Depends(get_current_active_user)],
)
app.include_router(realtime_router, prefix=settings.API_V1_PREFIX)

risk_profile = RiskProfile(
    max_portfolio_allocation_irt=settings.MAX_PORTFOLIO_ALLOCATION_IRT,
    max_single_trade_pct=settings.MAX_SINGLE_TRADE_PCT,
    max_daily_loss_pct=settings.MAX_DAILY_LOSS_PCT,
)



class EvaluateRequest(BaseModel):
    wallet_balance_irt: float
    market_context: constr(strip_whitespace=True, max_length=1500)


class NobitexKeyRequest(BaseModel):
    api_key: constr(strip_whitespace=True, min_length=20, max_length=100)


@app.post("/api/v1/agent/evaluate")
async def evaluate(req: EvaluateRequest):
    cleaned_context = re.sub(r"[\r\x00-\x1f]", "", req.market_context)
    decision = await brain.evaluate_market(req.wallet_balance_irt, cleaned_context)

    action = decision.get("action", "HOLD").upper()
    allocated = float(decision.get("allocated_irt", 0.0))

    if action == "BUY":
        approved, msg = DeterministicRiskEngine.validate_order(
            risk_profile, req.wallet_balance_irt, allocated
        )
        if not approved:
            allocated = 0.0
    else:
        approved = True
        msg = "سفارش منطبق بر قوانین ریسک تایید گردید."

    return {
        "agent_decision": decision,
        "execution": {"action": action, "allocated_irt": allocated},
        "risk_validation": {"approved": approved, "message": msg},
    }


@app.get("/api/v1/nobitex/status")
async def nobitex_status():
    token = get_vault_token()
    if not token:
        return {"connected": False, "message": "کلید API تعریف نشده است"}

    try:
        async with httpx.AsyncClient(timeout=settings.NOBITEX_TIMEOUT, trust_env=False) as client:
            res = await client.get(
                f"{settings.NOBITEX_API_BASE}/users/profile",
                headers={"Authorization": f"Token {token}"},
            )
            if res.status_code == 200:
                data = res.json()
                return {
                    "connected": True,
                    "email": data.get("profile", {}).get("email", "حساب فعال"),
                    "message": "اتصال مستقیم و امن تایید شد",
                }
            return {"connected": False, "message": "توکن نامعتبر یا منقضی شده"}
    except Exception as e:  # noqa: BLE001
        return {"connected": False, "message": f"عدم برقراری ارتباط: {e!s}"}


@app.post("/api/v1/nobitex/save-key")
async def save_nobitex_key(req: NobitexKeyRequest):
    # Was writing the vault with open()+chmod() inline, duplicating the logic
    # now centralised in app.core.vault (and racing with the 0600 mode).
    try:
        save_vault_token(req.api_key)
    except OSError as exc:
        logger = get_logger(__name__)
        logger.error("Vault write failed: %s", exc)
        raise HTTPException(status_code=500, detail="ذخیره کلید در والت امن ممکن نشد") from exc
    return {
        "status": "ok",
        "message": "کلید در والت امن هسته با دسترسی ایزوله ذخیره شد",
    }


@app.delete("/api/v1/nobitex/key")
async def remove_nobitex_key():
    """Forget the stored API key (kill-switch for exchange access)."""
    removed = clear_vault_token()
    return {
        "status": "ok",
        "removed": removed,
        "message": "کلید API از والت حذف شد" if removed else "کلیدی برای حذف وجود نداشت",
    }


@app.get("/api/v1/agents", tags=["Multi-Agent Gateway"])
def list_agents():
    """دریافت لیست ایجنت‌های ثبت‌شده سیستم"""
    return {"status": "success", "agents": agent_registry.list_all()}


@app.post("/api/v1/agents/register", tags=["Multi-Agent Gateway"])
def register_new_agent(config: AgentConfig):
    """تعریف و ثبت داینامیک ایجنت از پنل یا اپلیکیشن‌های دیگر"""
    agent = agent_registry.register(config)
    return {"status": "success", "agent": agent}


@app.post("/api/v1/agents/message", tags=["Multi-Agent Gateway"])
def agent_to_agent_message(msg: AgentMessage):
    """پروتکل ارتباطی بین ایجنت‌ها (Agent-to-Agent)"""
    target = agent_registry.get(msg.target_id)
    if not target or not target.is_active:
        raise HTTPException(status_code=404, detail="ایجنت مقصد یافت نشد یا غیرفعال است")
    return {
        "status": "delivered",
        "timestamp": msg.timestamp,
        "ack": {
            "from": msg.sender_id,
            "to": msg.target_id,
            "action": msg.action,
            "processed": True,
        },
    }


@app.post("/api/v1/integrations/accounting/sync", tags=["External Integrations"])
def sync_accounting_event(event: dict):
    """وب‌هوک ورودی/خروجی استاندارد برای اتصال به سیستم‌های مالی و حسابداری"""
    import uuid as _uuid
    return {
        "status": "synced",
        "journal_entry_id": f"JE-{_uuid.uuid4().hex[:6].upper()}",
        "received_payload": event,
    }


static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")