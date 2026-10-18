from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.domain.enums import MemoryTier


class GraphNodeDTO(BaseModel):
    id: str
    label: str
    node_type: str
    tier: MemoryTier
    tenant_id: str
    status: Optional[str] = None
    is_glowing: bool = False
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphEdgeDTO(BaseModel):
    id: str
    source: str
    target: str
    label: str
    is_active_path: bool = False


class ActiveProcedureExecution(BaseModel):
    procedure_id: str
    procedure_name: str
    task_id: str
    task_title: str
    task_status: str
    agent_id: str


class OverviewMetricsDTO(BaseModel):
    tenant_id: str
    episode_count: int
    session_count: int
    entity_count: int
    current_fact_count: int
    superseded_fact_count: int
    confirmed_procedure_count: int
    proposed_procedure_count: int
    registered_agent_count: int
    pending_handoff_count: int
    active_task_count: int
    pending_extraction_jobs: int


class GraphSubgraphResponse(BaseModel):
    tenant_id: str
    metrics: OverviewMetricsDTO
    active_procedures: List[ActiveProcedureExecution]
    nodes: List[GraphNodeDTO]
    edges: List[GraphEdgeDTO]