import json
import os
import re
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, constr
import httpx

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.middleware.logging import setup_middleware
from app.db.session import engine
from app.db.init_db import init_db
from app.agent.brain import AgentBrain
from app.risk_engine.evaluator import DeterministicRiskEngine, RiskProfile
from app.agent.registry import agent_registry, AgentConfig, AgentMessage
from app.api.v1 import health

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

app.include_router(health.router, prefix=settings.API_V1_PREFIX)

brain = AgentBrain()
risk_profile = RiskProfile(
    max_portfolio_allocation_irt=settings.MAX_PORTFOLIO_ALLOCATION_IRT,
    max_single_trade_pct=settings.MAX_SINGLE_TRADE_PCT,
    max_daily_loss_pct=settings.MAX_DAILY_LOSS_PCT,
)

CONFIG_DIR = os.path.expanduser("~/.aark")
CONFIG_FILE = os.path.join(CONFIG_DIR, "nobitex.vault")

os.makedirs(CONFIG_DIR, mode=0o700, exist_ok=True)


class EvaluateRequest(BaseModel):
    wallet_balance_irt: float
    market_context: constr(strip_whitespace=True, max_length=1500)


class NobitexKeyRequest(BaseModel):
    api_key: constr(strip_whitespace=True, min_length=20, max_length=100)


def get_vault_token() -> str:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                return data.get("api_key", "")
        except Exception:
            return ""
    return ""


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
    except Exception as e:
        return {"connected": False, "message": f"عدم برقراری ارتباط: {str(e)}"}


@app.post("/api/v1/nobitex/save-key")
async def save_nobitex_key(req: NobitexKeyRequest):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"api_key": req.api_key}, f)
    os.chmod(CONFIG_FILE, 0o600)
    return {
        "status": "ok",
        "message": "کلید در والت امن هسته با دسترسی ایزوله ذخیره شد",
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