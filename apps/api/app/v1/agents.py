from typing import List
from fastapi import APIRouter, Depends, Query, status

from app.core.security import resolve_tenant_scope
from app.domain.coordination import AgentCreateRequest, AgentRecord
from app.domain.tenant import TenantScope
from app.services.coordination_service import get_coordination_service

router = APIRouter(prefix="/agents", tags=["Agent Registry & Coordination"])


@router.post("", response_model=AgentRecord, status_code=status.HTTP_201_CREATED)
def register_agent(
    req: AgentCreateRequest,
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> AgentRecord:
    """
    Registers an agent with name, role, and declared capabilities within the tenant scope (FR-009).
    """
    return get_coordination_service().register_agent(scope, req)


@router.get("", response_model=List[AgentRecord])
def list_agents(
    limit: int = Query(default=100, ge=1, le=200),
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> List[AgentRecord]:
    return get_coordination_service().list_agents(scope, limit=limit)


@router.get("/{agent_id}", response_model=AgentRecord)
def get_agent(
    agent_id: str,
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> AgentRecord:
    return get_coordination_service().get_agent(scope, agent_id)