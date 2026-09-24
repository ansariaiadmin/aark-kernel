from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis
import httpx
import time
from typing import Dict, Any

from app.core.config import get_settings
from app.core.logging import get_logger

router = APIRouter(tags=["Health & Monitoring"])
logger = get_logger(__name__)
settings = get_settings()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": time.time(),
    }


@router.get("/health/live")
async def liveness_probe() -> Dict[str, str]:
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_probe() -> Dict[str, Any]:
    checks = {}
    overall = "ready"

    # Database check
    try:
        from app.db.session import get_async_session
        async for session in get_async_session():
            await session.execute(text("SELECT 1"))
        checks["database"] = {"status": "healthy", "latency_ms": 0}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}
        overall = "not_ready"

    # Redis check
    try:
        start = time.time()
        client = redis.from_url(settings.REDIS_URL)
        await client.ping()
        await client.close()
        checks["redis"] = {"status": "healthy", "latency_ms": round((time.time() - start) * 1000, 2)}
    except Exception as e:
        checks["redis"] = {"status": "unhealthy", "error": str(e)}
        overall = "not_ready"

    # Ollama check
    try:
        start = time.time()
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.LOCAL_OLLAMA_HOST}/api/tags")
            resp.raise_for_status()
        checks["ollama"] = {"status": "healthy", "latency_ms": round((time.time() - start) * 1000, 2)}
    except Exception as e:
        checks["ollama"] = {"status": "degraded", "error": str(e)}

    return {
        "status": overall,
        "checks": checks,
        "timestamp": time.time(),
    }


@router.get("/metrics")
async def metrics() -> str:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from fastapi.responses import Response
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)