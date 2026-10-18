from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.domain.coordination import HandoffRecord
from app.domain.memory import EntityRecord, EpisodeRecord, FactRecord, ProcedureRecord


class RelevanceTrace(BaseModel):
    matched_terms: List[str] = Field(default_factory=list)
    lexical_score: float = 0.0
    graph_boost: float = 0.0
    importance_score: float = 0.0
    recency_score: float = 0.0
    final_score: float = 0.0
    explanation: str


class RankedEpisode(BaseModel):
    episode: EpisodeRecord
    relevance_score: float
    trace: RelevanceTrace


class ContextAssembleRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    agent_id: Optional[str] = Field(default=None, max_length=120)
    session_id: Optional[str] = Field(default=None, max_length=120)
    max_episodes: int = Field(default=5, ge=1, le=25)
    max_facts: int = Field(default=15, ge=1, le=50)
    max_procedures: int = Field(default=5, ge=1, le=20)
    include_superseded_facts: bool = Field(default=False)
    include_proposed_procedures: bool = Field(default=True)


class AssembledContextPackage(BaseModel):
    tenant_id: str
    query: str
    requesting_agent_id: Optional[str] = None
    assembled_at: datetime
    duration_ms: float
    episodes: List[RankedEpisode]
    entities: List[EntityRecord]
    facts: List[FactRecord]
    procedures: List[ProcedureRecord]
    pending_handoffs: List[HandoffRecord]