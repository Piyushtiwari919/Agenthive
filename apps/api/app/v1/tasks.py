from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status

from app.core.security import resolve_tenant_scope
from app.domain.coordination import (
    TaskCreateRequest,
    TaskRecord,
    TaskStatusUpdateRequest,
)
from app.domain.enums import TaskStatus
from app.domain.tenant import TenantScope
from app.services.coordination_service import get_coordination_service

router = APIRouter(prefix="/tasks", tags=["Shared Task State"])


@router.post("", response_model=TaskRecord, status_code=status.HTTP_201_CREATED)
def create_task(
    req: TaskCreateRequest,
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> TaskRecord:
    return get_coordination_service().create_task(scope, req)


@router.get("", response_model=List[TaskRecord])
def list_tasks(
    owner_agent_id: Optional[str] = Query(default=None),
    status_filter: Optional[TaskStatus] = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=250),
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> List[TaskRecord]:
    return get_coordination_service().list_tasks(
        scope=scope,
        owner_agent_id=owner_agent_id,
        status=status_filter,
        limit=limit,
    )


@router.get("/{task_id}", response_model=TaskRecord)
def get_task(
    task_id: str,
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> TaskRecord:
    return get_coordination_service().get_task(scope, task_id)


@router.patch("/{task_id}/status", response_model=TaskRecord)
def update_task_status(
    task_id: str,
    req: TaskStatusUpdateRequest,
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> TaskRecord:
    """
    Updates shared task state and broadcasts change to all same-tenant agents within 5s (FR-012).
    """
    return get_coordination_service().update_task_status(scope, task_id, req)