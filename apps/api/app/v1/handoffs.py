from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status

from app.core.security import resolve_tenant_scope
from app.domain.coordination import (
    HandoffCreateRequest,
    HandoffRecord,
    HandoffStatusUpdateRequest,
)
from app.domain.enums import HandoffStatus
from app.domain.tenant import TenantScope
from app.services.coordination_service import get_coordination_service

router = APIRouter(prefix="/handoffs", tags=["Agent Handoffs"])


@router.post("", response_model=HandoffRecord, status_code=status.HTTP_201_CREATED)
def create_handoff(
    req: HandoffCreateRequest,
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> HandoffRecord:
    """
    Initiates a structured task handoff between two registered agents in the same tenant (FR-010, BR-006).
    """
    return get_coordination_service().create_handoff(scope, req)


@router.get("", response_model=List[HandoffRecord])
def list_handoffs(
    target_agent_id: Optional[str] = Query(default=None),
    origin_agent_id: Optional[str] = Query(default=None),
    status_filter: Optional[HandoffStatus] = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=250),
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> List[HandoffRecord]:
    return get_coordination_service().list_handoffs(
        scope=scope,
        target_agent_id=target_agent_id,
        origin_agent_id=origin_agent_id,
        status=status_filter,
        limit=limit,
    )


@router.get("/{handoff_id}", response_model=HandoffRecord)
def get_handoff(
    handoff_id: str,
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> HandoffRecord:
    return get_coordination_service().get_handoff(scope, handoff_id)


@router.patch("/{handoff_id}/status", response_model=HandoffRecord)
def update_handoff_status(
    handoff_id: str,
    req: HandoffStatusUpdateRequest,
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> HandoffRecord:
    return get_coordination_service().update_handoff_status(scope, handoff_id, req)