from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.domain.enums import AgentStatus, HandoffStatus, TaskStatus


class AgentCreateRequest(BaseModel):
    agent_id: Optional[str] = Field(default=None, max_length=120)
    name: str = Field(..., min_length=2, max_length=120)
    role: str = Field(..., min_length=2, max_length=120)
    capabilities: List[str] = Field(..., min_length=1, max_length=30)
    status: AgentStatus = Field(default=AgentStatus.ACTIVE)


class AgentRecord(BaseModel):
    id: str
    tenant_id: str
    name: str
    role: str
    capabilities: List[str]
    status: AgentStatus
    created_at: datetime


class HandoffCreateRequest(BaseModel):
    origin_agent_id: str = Field(..., min_length=1, max_length=120)
    target_agent_id: str = Field(..., min_length=1, max_length=120)
    task_title: str = Field(..., min_length=2, max_length=240)
    context_summary: str = Field(..., min_length=2, max_length=4000)
    state_payload: Dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = Field(default=None, max_length=120)
    task_id: Optional[str] = Field(default=None, max_length=120)


class HandoffStatusUpdateRequest(BaseModel):
    status: HandoffStatus
    acting_agent_id: str = Field(..., min_length=1, max_length=120)
    note: Optional[str] = Field(default=None, max_length=1000)


class HandoffRecord(BaseModel):
    id: str
    tenant_id: str
    task_id: str
    task_title: str
    origin_agent_id: str
    target_agent_id: str
    context_summary: str
    state_payload: Dict[str, Any]
    status: HandoffStatus
    session_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=240)
    owner_agent_id: str = Field(..., min_length=1, max_length=120)
    session_id: Optional[str] = Field(default=None, max_length=120)
    active_procedure_id: Optional[str] = Field(default=None, max_length=120)


class TaskStatusUpdateRequest(BaseModel):
    status: TaskStatus
    acting_agent_id: str = Field(..., min_length=1, max_length=120)
    active_procedure_id: Optional[str] = Field(default=None, max_length=120)
    result_summary: Optional[str] = Field(default=None, max_length=2000)


class TaskRecord(BaseModel):
    id: str
    tenant_id: str
    title: str
    status: TaskStatus
    owner_agent_id: str
    session_id: Optional[str] = None
    active_procedure_id: Optional[str] = None
    result_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime