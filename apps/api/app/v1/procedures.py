from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from app.core.security import resolve_tenant_scope
from app.domain.coordination import TaskRecord
from app.domain.enums import ProcedureStatus, TaskStatus
from app.domain.memory import ProcedureCreateRequest, ProcedureRecord
from app.domain.tenant import TenantScope
from app.services.coordination_service import get_coordination_service
from app.services.memory_service import get_memory_service

router = APIRouter(prefix="/procedures", tags=["Procedural Memory"])


class ProcedureExecuteRequest(BaseModel):
    agent_id: str = Field(..., min_length=1, max_length=120)
    task_title: Optional[str] = Field(default=None, max_length=240)


class ProcedureStopRequest(BaseModel):
    agent_id: str = Field(..., min_length=1, max_length=120)
    final_status: TaskStatus = Field(default=TaskStatus.COMPLETED)
    result_summary: Optional[str] = Field(default=None, max_length=1000)


class ProcedureExecutionResponse(BaseModel):
    procedure: ProcedureRecord
    task: TaskRecord


@router.get("", response_model=List[ProcedureRecord])
def list_procedures(
    status_filter: Optional[ProcedureStatus] = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=200),
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> List[ProcedureRecord]:
    return get_memory_service().list_procedures(scope=scope, status=status_filter, limit=limit)


@router.post("", response_model=ProcedureRecord, status_code=status.HTTP_201_CREATED)
def create_procedure(
    req: ProcedureCreateRequest,
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> ProcedureRecord:
    return get_memory_service().create_procedure(scope, req)


@router.post("/{procedure_id}/confirm", response_model=ProcedureRecord)
def confirm_procedure(
    procedure_id: str,
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> ProcedureRecord:
    """
    Explicitly confirms a proposed procedure (BR-003).
    """
    return get_memory_service().confirm_procedure(scope, procedure_id)


@router.post("/{procedure_id}/execute", response_model=ProcedureExecutionResponse)
def execute_procedure(
    procedure_id: str,
    req: ProcedureExecuteRequest,
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> ProcedureExecutionResponse:
    """
    Starts a genuine task using the matched procedure and activates the live graph glow.
    """
    proc, task = get_coordination_service().start_procedure_execution(
        scope=scope,
        procedure_id=procedure_id,
        agent_id=req.agent_id,
        task_title=req.task_title,
    )
    return ProcedureExecutionResponse(procedure=proc, task=task)


@router.post("/{procedure_id}/complete", response_model=ProcedureRecord)
def complete_procedure_execution(
    procedure_id: str,
    req: ProcedureStopRequest,
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> ProcedureRecord:
    """
    Completes/fails/cancels the active task using this procedure and stops the live graph glow.
    """
    return get_coordination_service().stop_procedure_execution(
        scope=scope,
        procedure_id=procedure_id,
        agent_id=req.agent_id,
        final_status=req.final_status,
        result_summary=req.result_summary,
    )
