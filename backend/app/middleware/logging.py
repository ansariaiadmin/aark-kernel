import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.types import ASGIApp
from fastapi import FastAPI
import logging
import traceback

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, excluded_paths: set = None):
        super().__init__(app)
        self.excluded_paths = excluded_paths or {"/health", "/health/live", "/health/ready", "/metrics", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id

        start_time = time.time()
        method = request.method
        url = str(request.url)
        client_host = request.client.host if request.client else "unknown"

        logger.info(
            "Request started",
            extra={
                "correlation_id": correlation_id,
                "method": method,
                "url": url,
                "client_ip": client_host,
            },
        )

        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            logger.info(
                "Request completed",
                extra={
                    "correlation_id": correlation_id,
                    "method": method,
                    "url": url,
                    "status_code": response.status_code,
                    "duration_ms": round(process_time * 1000, 2),
                },
            )

            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Process-Time"] = str(process_time)
            return response

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                "Request failed",
                extra={
                    "correlation_id": correlation_id,
                    "method": method,
                    "url": url,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "duration_ms": round(process_time * 1000, 2),
                },
            )
            raise


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))

            logger.error(
                "Unhandled exception",
                extra={
                    "correlation_id": correlation_id,
                    "path": request.url.path,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                },
            )

            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "correlation_id": correlation_id,
                    "message": "An unexpected error occurred. Please contact support with the correlation ID.",
                },
                headers={"X-Correlation-ID": correlation_id},
            )


def setup_middleware(app: FastAPI) -> None:
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(RequestLoggingMiddleware)