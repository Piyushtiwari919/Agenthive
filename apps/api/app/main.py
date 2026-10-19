import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.v1.router import v1_router
from app.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, hash_tenant_for_log
from app.services.tenant_service import get_tenant_service
from app.workers.extraction_worker import background_extraction_loop

logger = logging.getLogger("agenthive.http")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    settings.validate_startup_security()

    stop_event = asyncio.Event()
    worker_task: asyncio.Task[None] | None = None

    try:
        if settings.agenthive_env in ("demo", "test"):
            get_tenant_service().ensure_demo_tenants()
    except Exception as exc:
        logger.warning(
            "Startup demo tenant bootstrap skipped (FalkorDB not yet reachable)",
            extra={"error_category": exc.__class__.__name__},
        )

    if settings.extraction_worker_enabled:
        worker_task = asyncio.create_task(background_extraction_loop(stop_event))

    yield

    stop_event.set()
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AgentHive API",
        description="Persistent Multi-Agent Memory and Coordination Platform on FalkorDB (Graph Hacks 2026 — Track 02)",
        version="1.0.0",
        lifespan=lifespan,
    )

    origins = settings.cors_origin_list
    allow_all = "*" in origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if allow_all else origins,
        allow_credentials=not allow_all,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_correlation_middleware(request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id
        tenant_header = request.headers.get("X-Tenant-ID") or request.query_params.get("tenant_id")
        start = time.perf_counter()

        response: Response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000.0, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = str(duration_ms)

        logger.info(
            "HTTP request processed",
            extra={
                "request_id": request_id,
                "route": request.url.path,
                "operation": request.method,
                "duration_ms": duration_ms,
                "tenant_hash": hash_tenant_for_log(tenant_header),
                "outcome": response.status_code,
            },
        )
        return response

    register_exception_handlers(app)
    app.include_router(v1_router)
    return app


app = create_app()