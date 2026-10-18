from datetime import datetime, timezone
from fastapi import APIRouter

from app.config import get_settings
from app.repositories.falkor_client import falkor_manager

router = APIRouter(tags=["Health & Readiness"])


@router.get("/health")
def health_liveness() -> dict:
    return {
        "status": "ok",
        "service": "agenthive-api",
        "track": "Graph Hacks 2026 - Track 02: Agent Memory and Coordination",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready")
def readiness_check() -> dict:
    """
    Verifies FalkorDB primary database connectivity (C-01, K-09).
    If FalkorDB is unreachable, falkor_manager.ping() raises DatabaseUnavailableError -> HTTP 503.
    """
    falkor_manager.ping()
    settings = get_settings()
    return {
        "status": "ready",
        "database": "falkordb",
        "database_connected": True,
        "environment": settings.agenthive_env,
        "extraction_provider": settings.extraction_provider,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }