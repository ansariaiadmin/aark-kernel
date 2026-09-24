import time
from typing import Any

import httpx
import redis.asyncio as redis
from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.core.logging import get_logger

router = APIRouter(tags=["Health & Monitoring"])
logger = get_logger(__name__)
settings = get_settings()


@router.get("/health")
async def health_check() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": time.time(),
    }


@router.get("/health/live")
async def liveness_probe() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_probe() -> dict[str, Any]:
    checks = {}
    overall = "ready"

    # Database check
    try:
        from app.db.session import get_async_session
        async for session in get_async_session():
            await session.execute(text("SELECT 1"))
        checks["database"] = {"status": "healthy", "latency_ms": 0}
    except Exception as e:  # noqa: BLE001
        checks["database"] = {"status": "unhealthy", "error": str(e)}
        overall = "not_ready"

    # Redis check
    try:
        start = time.time()
        client = redis.from_url(settings.REDIS_URL)
        await client.ping()
        await client.close()
        checks["redis"] = {"status": "healthy", "latency_ms": round((time.time() - start) * 1000, 2)}
    except Exception as e:  # noqa: BLE001
        checks["redis"] = {"status": "unhealthy", "error": str(e)}
        overall = "not_ready"

    # Ollama check
    try:
        start = time.time()
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.LOCAL_OLLAMA_HOST}/api/tags")
            resp.raise_for_status()
        checks["ollama"] = {"status": "healthy", "latency_ms": round((time.time() - start) * 1000, 2)}
    except Exception as e:  # noqa: BLE001
        checks["ollama"] = {"status": "degraded", "error": str(e)}

    return {
        "status": overall,
        "checks": checks,
        "timestamp": time.time(),
    }


@router.get("/metrics")
async def metrics() -> str:
    from fastapi.responses import Response
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)