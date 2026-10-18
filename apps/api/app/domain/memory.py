from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.domain.enums import (
    ConfirmationMethod,
    ExtractionStatus,
    FactStatus,
    ProcedureStatus,
)


class ProvenanceRef(BaseModel):
    episode_id: str
    session_id: str
    agent_id: str
    timestamp: datetime
    snippet: str


class EpisodeCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=16000)
    agent_id: str = Field(..., min_length=1, max_length=120)
    agent_name: Optional[str] = Field(default=None, max_length=120)
    session_id: str = Field(..., min_length=1, max_length=120)
    session_title: Optional[str] = Field(default=None, max_length=200)
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    timestamp: Optional[datetime] = None
    idempotency_key: Optional[str] = Field(default=None, max_length=128)
    process_extraction_inline: bool = Field(default=True)


class EpisodeRecord(BaseModel):
    id: str
    tenant_id: str
    content: str
    agent_id: str
    agent_name: str
    session_id: str
    timestamp: datetime
    importance_score: float
    extraction_status: ExtractionStatus
    archived: bool = False
    idempotency_key: Optional[str] = None
    created_at: datetime


class SessionSummary(BaseModel):
    session_id: str
    tenant_id: str
    title: str
    started_at: datetime
    last_activity_at: datetime
    episode_count: int


class SessionHistoryResponse(BaseModel):
    tenant_id: str
    session_id: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_episodes: int
    episodes: List[EpisodeRecord]


class EntityRecord(BaseModel):
    id: str
    tenant_id: str
    canonical_key: str
    canonical_name: str
    entity_type: str
    aliases: List[str] = Field(default_factory=list)
    source_episode_ids: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class FactRecord(BaseModel):
    id: str
    tenant_id: str
    subject_entity_id: str
    subject_name: str
    predicate: str
    object_value: str
    object_entity_id: Optional[str] = None
    status: FactStatus
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    source_episode_id: str
    observed_at: datetime
    superseded_by_id: Optional[str] = None
    provenance: Optional[ProvenanceRef] = None


class ProcedureCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=160)
    trigger_text: str = Field(..., min_length=3, max_length=500)
    steps: List[str] = Field(..., min_length=1, max_length=30)
    source_episode_id: str = Field(..., min_length=1, max_length=120)
    confirmed_by_user: bool = Field(default=False)


class ProcedureRecord(BaseModel):
    id: str
    tenant_id: str
    name: str
    trigger_text: str
    trigger_keywords: List[str] = Field(default_factory=list)
    steps: List[str]
    status: ProcedureStatus
    confirmation_method: ConfirmationMethod
    evidence_count: int
    source_episode_ids: List[str]
    provenance_refs: List[ProvenanceRef] = Field(default_factory=list)
    active_task_id: Optional[str] = None
    is_currently_active: bool = False
    last_executed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ProvenanceResponse(BaseModel):
    target_id: str
    target_type: str
    tenant_id: str
    source_episodes: List[EpisodeRecord]