from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status

from app.core.security import resolve_tenant_scope
from app.domain.memory import (
    EpisodeCreateRequest,
    EpisodeRecord,
    SessionHistoryResponse,
    SessionSummary,
)
from app.domain.tenant import TenantScope
from app.services.memory_service import get_memory_service

router = APIRouter(tags=["Episodic Memory & Sessions"])


@router.post("/episodes", response_model=EpisodeRecord, status_code=status.HTTP_201_CREATED)
def create_episode(
    req: EpisodeCreateRequest,
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> EpisodeRecord:
    """
    Captures a completed agent interaction as an episodic memory entry (FR-001).
    """
    return get_memory_service().record_episode(scope, req)


@router.get("/episodes", response_model=List[EpisodeRecord])
def list_episodes(
    session_id: Optional[str] = Query(default=None),
    agent_id: Optional[str] = Query(default=None),
    include_archived: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> List[EpisodeRecord]:
    return get_memory_service().list_episodes(
        scope=scope,
        session_id=session_id,
        agent_id=agent_id,
        include_archived=include_archived,
        limit=limit,
    )


@router.get("/episodes/{episode_id}", response_model=EpisodeRecord)
def get_episode(
    episode_id: str,
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> EpisodeRecord:
    return get_memory_service().get_episode(scope, episode_id)


@router.post("/episodes/{episode_id}/archive", response_model=EpisodeRecord)
def archive_episode(
    episode_id: str,
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> EpisodeRecord:
    """
    Archives a low-importance episode without deleting it (BR-008).
    """
    return get_memory_service().archive_episode(scope, episode_id)


@router.get("/sessions", response_model=List[SessionSummary])
def list_sessions(
    limit: int = Query(default=100, ge=1, le=250),
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> List[SessionSummary]:
    return get_memory_service().list_sessions(scope=scope, limit=limit)


@router.get("/sessions/{session_id}/history", response_model=SessionHistoryResponse)
def get_session_history(
    session_id: str,
    start_time: Optional[datetime] = Query(default=None),
    end_time: Optional[datetime] = Query(default=None),
    limit: int = Query(default=250, ge=1, le=500),
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> SessionHistoryResponse:
    """
    Returns ordered, timestamped conversation history per session and tenant,
    retrievable by session and time range (FR-005).
    """
    return get_memory_service().get_session_history(
        scope=scope,
        session_id=session_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )