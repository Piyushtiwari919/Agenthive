from datetime import datetime
from functools import lru_cache
from typing import List, Optional

from app.core.errors import ResourceNotFoundError
from app.domain.enums import ExtractionStatus, ProcedureStatus
from app.domain.memory import (
    EntityRecord,
    EpisodeCreateRequest,
    EpisodeRecord,
    FactRecord,
    ProcedureCreateRequest,
    ProcedureRecord,
    ProvenanceResponse,
    SessionHistoryResponse,
    SessionSummary,
)
from app.domain.tenant import TenantScope
from app.extraction.canonicalizer import extract_keywords
from app.repositories.memory_repository import get_memory_repository
from app.workers.extraction_worker import extraction_orchestrator


class MemoryService:
    """
    Application service for Episodic, Semantic, and Procedural memory operations.
    Persists episodes first (<200ms) and orchestrates extraction with durable fallback (NFR-001, NFR-004).
    """

    def record_episode(self, scope: TenantScope, req: EpisodeCreateRequest) -> EpisodeRecord:
        mem_repo = get_memory_repository()
        episode = mem_repo.create_episode(
            scope=scope,
            req=req,
            initial_status=ExtractionStatus.PENDING,
        )
        mem_repo.upsert_extraction_job(
            scope=scope,
            episode_id=episode.id,
            status=ExtractionStatus.PENDING,
            provider=extraction_orchestrator.get_active_provider().provider_name,
            attempt_count=0,
        )

        if req.process_extraction_inline:
            final_status = extraction_orchestrator.process_episode_extraction(
                scope=scope,
                episode_id=episode.id,
                content=episode.content,
                episode_timestamp=episode.timestamp,
                attempt_count=0,
            )
            episode.extraction_status = final_status

        return episode

    def get_episode(self, scope: TenantScope, episode_id: str) -> EpisodeRecord:
        return get_memory_repository().get_episode(scope, episode_id)

    def list_episodes(
        self,
        scope: TenantScope,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        include_archived: bool = False,
        limit: int = 100,
    ) -> List[EpisodeRecord]:
        return get_memory_repository().list_episodes(
            scope=scope,
            session_id=session_id,
            agent_id=agent_id,
            include_archived=include_archived,
            limit=limit,
        )

    def archive_episode(self, scope: TenantScope, episode_id: str) -> EpisodeRecord:
        return get_memory_repository().archive_episode(scope, episode_id)

    def get_session_history(
        self,
        scope: TenantScope,
        session_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 250,
    ) -> SessionHistoryResponse:
        return get_memory_repository().get_session_history(
            scope=scope,
            session_id=session_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    def list_sessions(self, scope: TenantScope, limit: int = 100) -> List[SessionSummary]:
        return get_memory_repository().list_sessions(scope=scope, limit=limit)

    def list_entities(
        self,
        scope: TenantScope,
        entity_type: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 200,
    ) -> List[EntityRecord]:
        return get_memory_repository().list_entities(
            scope=scope, entity_type=entity_type, search=search, limit=limit
        )

    def get_entity(self, scope: TenantScope, entity_id: str) -> EntityRecord:
        return get_memory_repository().get_entity(scope, entity_id)

    def list_facts(
        self,
        scope: TenantScope,
        subject_entity_id: Optional[str] = None,
        include_superseded: bool = True,
        limit: int = 200,
    ) -> List[FactRecord]:
        return get_memory_repository().list_facts(
            scope=scope,
            subject_entity_id=subject_entity_id,
            include_superseded=include_superseded,
            limit=limit,
        )

    def create_procedure(
        self, scope: TenantScope, req: ProcedureCreateRequest
    ) -> ProcedureRecord:
        mem_repo = get_memory_repository()
        # Verify source episode exists in this tenant scope
        mem_repo.get_episode(scope, req.source_episode_id)
        keywords = extract_keywords(f"{req.name} {req.trigger_text}")
        return mem_repo.upsert_procedure(
            scope=scope,
            name=req.name,
            trigger_text=req.trigger_text,
            trigger_keywords=keywords,
            steps=req.steps,
            source_episode_id=req.source_episode_id,
            confirmed_by_user=req.confirmed_by_user,
        )

    def confirm_procedure(self, scope: TenantScope, procedure_id: str) -> ProcedureRecord:
        return get_memory_repository().confirm_procedure(scope, procedure_id)

    def list_procedures(
        self, scope: TenantScope, status: Optional[ProcedureStatus] = None, limit: int = 100
    ) -> List[ProcedureRecord]:
        return get_memory_repository().list_procedures(scope=scope, status=status, limit=limit)

    def get_provenance(self, scope: TenantScope, target_id: str) -> ProvenanceResponse:
        mem_repo = get_memory_repository()
        if target_id.startswith("fact_"):
            fact = mem_repo.get_fact(scope, target_id)
            episodes = mem_repo.get_episodes_by_ids(scope, [fact.source_episode_id])
            return ProvenanceResponse(
                target_id=target_id,
                target_type="Fact",
                tenant_id=scope.tenant_id,
                source_episodes=episodes,
            )
        if target_id.startswith("proc_"):
            proc = mem_repo.get_procedure(scope, target_id)
            episodes = mem_repo.get_episodes_by_ids(scope, proc.source_episode_ids)
            return ProvenanceResponse(
                target_id=target_id,
                target_type="Procedure",
                tenant_id=scope.tenant_id,
                source_episodes=episodes,
            )
        if target_id.startswith("ent_"):
            ent = mem_repo.get_entity(scope, target_id)
            episodes = mem_repo.get_episodes_by_ids(scope, ent.source_episode_ids)
            return ProvenanceResponse(
                target_id=target_id,
                target_type="Entity",
                tenant_id=scope.tenant_id,
                source_episodes=episodes,
            )
        if target_id.startswith("ep_"):
            ep = mem_repo.get_episode(scope, target_id)
            return ProvenanceResponse(
                target_id=target_id,
                target_type="Episode",
                tenant_id=scope.tenant_id,
                source_episodes=[ep],
            )
        raise ResourceNotFoundError("ProvenanceTarget", target_id)


@lru_cache()
def get_memory_service() -> MemoryService:
    return MemoryService()