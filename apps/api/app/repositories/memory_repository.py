import json
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from app.core.errors import ResourceNotFoundError
from app.domain.enums import (
    ConfirmationMethod,
    ExtractionStatus,
    FactStatus,
    ProcedureStatus,
)
from app.domain.memory import (
    EntityRecord,
    EpisodeCreateRequest,
    EpisodeRecord,
    FactRecord,
    ProcedureRecord,
    ProvenanceRef,
    SessionHistoryResponse,
    SessionSummary,
)
from app.domain.tenant import TenantScope
from app.repositories import cypher_catalog
from app.repositories.falkor_client import falkor_manager


class MemoryRepository:
    """
    Tenant-scoped FalkorDB repository for Episodic, Semantic, and Procedural memory.
    Every method requires a server-validated TenantScope and queries only scope.graph_name.
    """

    # -----------------------------------------------------------------------
    # Episodic Memory & Sessions (FR-001, FR-002, FR-005, BR-008)
    # -----------------------------------------------------------------------
    def create_episode(
        self, scope: TenantScope, req: EpisodeCreateRequest, initial_status: ExtractionStatus
    ) -> EpisodeRecord:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)

        if req.idempotency_key:
            existing = falkor_manager.ro_query(
                graph,
                cypher_catalog.FIND_EPISODE_BY_IDEMPOTENCY,
                params={
                    "tenant_id": scope.tenant_id,
                    "idempotency_key": req.idempotency_key,
                },
            )
            if existing:
                return self._row_to_episode(existing[0])

        now_utc = datetime.now(timezone.utc)
        ep_ts = req.timestamp.astimezone(timezone.utc) if req.timestamp else now_utc
        episode_id = f"ep_{uuid.uuid4().hex[:12]}"

        rows = falkor_manager.query(
            graph,
            cypher_catalog.CREATE_EPISODE_AND_SESSION,
            params={
                "id": episode_id,
                "tenant_id": scope.tenant_id,
                "content": req.content,
                "agent_id": req.agent_id,
                "agent_name": req.agent_name or req.agent_id,
                "session_id": req.session_id,
                "session_title": req.session_title or f"Session {req.session_id}",
                "timestamp": ep_ts.isoformat(),
                "importance_score": float(req.importance_score),
                "extraction_status": initial_status.value,
                "archived": False,
                "idempotency_key": req.idempotency_key or "",
                "created_at": now_utc.isoformat(),
            },
        )
        return self._row_to_episode(rows[0])

    def get_episode(self, scope: TenantScope, episode_id: str) -> EpisodeRecord:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        rows = falkor_manager.ro_query(
            graph,
            cypher_catalog.GET_EPISODE_BY_ID,
            params={"episode_id": episode_id, "tenant_id": scope.tenant_id},
        )
        if not rows:
            raise ResourceNotFoundError("Episode", episode_id)
        return self._row_to_episode(rows[0])

    def get_episodes_by_ids(self, scope: TenantScope, episode_ids: List[str]) -> List[EpisodeRecord]:
        if not episode_ids:
            return []
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        rows = falkor_manager.ro_query(
            graph,
            cypher_catalog.GET_EPISODES_BY_IDS,
            params={"tenant_id": scope.tenant_id, "episode_ids": list(set(episode_ids))},
        )
        return [self._row_to_episode(r) for r in rows]

    def list_episodes(
        self,
        scope: TenantScope,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        include_archived: bool = False,
        limit: int = 100,
    ) -> List[EpisodeRecord]:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        rows = falkor_manager.ro_query(
            graph,
            cypher_catalog.LIST_EPISODES,
            params={
                "tenant_id": scope.tenant_id,
                "session_id": session_id or "",
                "agent_id": agent_id or "",
                "include_archived": bool(include_archived),
                "limit": min(max(limit, 1), 500),
            },
        )
        return [self._row_to_episode(r) for r in rows]

    def get_session_history(
        self,
        scope: TenantScope,
        session_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 250,
    ) -> SessionHistoryResponse:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        start_iso = start_time.astimezone(timezone.utc).isoformat() if start_time else ""
        end_iso = end_time.astimezone(timezone.utc).isoformat() if end_time else ""

        rows = falkor_manager.ro_query(
            graph,
            cypher_catalog.GET_SESSION_HISTORY,
            params={
                "tenant_id": scope.tenant_id,
                "session_id": session_id,
                "start_iso": start_iso,
                "end_iso": end_iso,
                "limit": min(max(limit, 1), 500),
            },
        )
        episodes = [self._row_to_episode(r) for r in rows]
        return SessionHistoryResponse(
            tenant_id=scope.tenant_id,
            session_id=session_id,
            start_time=start_time,
            end_time=end_time,
            total_episodes=len(episodes),
            episodes=episodes,
        )

    def list_sessions(self, scope: TenantScope, limit: int = 100) -> List[SessionSummary]:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        rows = falkor_manager.ro_query(
            graph,
            cypher_catalog.LIST_SESSIONS,
            params={"tenant_id": scope.tenant_id, "limit": min(max(limit, 1), 250)},
        )
        return [
            SessionSummary(
                session_id=str(r[0]),
                tenant_id=str(r[1]),
                title=str(r[2]),
                started_at=datetime.fromisoformat(str(r[3])),
                last_activity_at=datetime.fromisoformat(str(r[4])),
                episode_count=int(r[5]),
            )
            for r in rows
        ]

    def update_episode_extraction_status(
        self, scope: TenantScope, episode_id: str, status: ExtractionStatus
    ) -> None:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        falkor_manager.query(
            graph,
            cypher_catalog.UPDATE_EPISODE_EXTRACTION_STATUS,
            params={
                "episode_id": episode_id,
                "tenant_id": scope.tenant_id,
                "extraction_status": status.value,
            },
        )

    def archive_episode(self, scope: TenantScope, episode_id: str) -> EpisodeRecord:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        rows = falkor_manager.query(
            graph,
            cypher_catalog.ARCHIVE_EPISODE,
            params={"episode_id": episode_id, "tenant_id": scope.tenant_id},
        )
        if not rows:
            raise ResourceNotFoundError("Episode", episode_id)
        return self.get_episode(scope, episode_id)

    # -----------------------------------------------------------------------
    # Durable Extraction Queue (NFR-004)
    # -----------------------------------------------------------------------
    def upsert_extraction_job(
        self,
        scope: TenantScope,
        episode_id: str,
        status: ExtractionStatus,
        provider: str,
        attempt_count: int = 0,
        retry_after: Optional[datetime] = None,
        last_error_category: str = "",
    ) -> None:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        now = datetime.now(timezone.utc)
        retry_iso = (retry_after or now).astimezone(timezone.utc).isoformat()
        falkor_manager.query(
            graph,
            cypher_catalog.UPSERT_EXTRACTION_JOB,
            params={
                "job_id": f"job_{episode_id}",
                "episode_id": episode_id,
                "tenant_id": scope.tenant_id,
                "status": status.value,
                "provider": provider,
                "attempt_count": int(attempt_count),
                "retry_after": retry_iso,
                "last_error_category": last_error_category,
                "now": now.isoformat(),
            },
        )

    def fetch_due_extraction_jobs(
        self, scope: TenantScope, limit: int = 20
    ) -> List[Tuple[str, str, str, str, int]]:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        now_iso = datetime.now(timezone.utc).isoformat()
        rows = falkor_manager.ro_query(
            graph,
            cypher_catalog.FETCH_DUE_EXTRACTION_JOBS,
            params={"tenant_id": scope.tenant_id, "now": now_iso, "limit": limit},
        )
        return [(str(r[0]), str(r[1]), str(r[2]), str(r[3]), int(r[4])) for r in rows]

    # -----------------------------------------------------------------------
    # Semantic Memory: Canonical Entities & Facts (FR-003, FR-008, BR-004, BR-007)
    # -----------------------------------------------------------------------
    def upsert_canonical_entity(
        self,
        scope: TenantScope,
        canonical_key: str,
        canonical_name: str,
        entity_type: str,
        aliases: List[str],
        source_episode_id: str,
    ) -> EntityRecord:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        existing_rows = falkor_manager.ro_query(
            graph,
            cypher_catalog.GET_ENTITY_BY_CANONICAL_KEY,
            params={"canonical_key": canonical_key, "tenant_id": scope.tenant_id},
        )

        merged_aliases: List[str] = []
        merged_episodes: List[str] = []
        entity_id = f"ent_{uuid.uuid4().hex[:12]}"

        if existing_rows:
            existing = self._row_to_entity(existing_rows[0])
            entity_id = existing.id
            merged_aliases = list(existing.aliases)
            merged_episodes = list(existing.source_episode_ids)

        for alias in [canonical_name, *aliases]:
            clean_alias = alias.strip()
            if clean_alias and clean_alias not in merged_aliases:
                merged_aliases.append(clean_alias)

        if source_episode_id and source_episode_id not in merged_episodes:
            merged_episodes.append(source_episode_id)

        now_iso = datetime.now(timezone.utc).isoformat()
        rows = falkor_manager.query(
            graph,
            cypher_catalog.UPSERT_CANONICAL_ENTITY,
            params={
                "entity_id": entity_id,
                "canonical_key": canonical_key,
                "tenant_id": scope.tenant_id,
                "canonical_name": canonical_name,
                "entity_type": entity_type,
                "aliases_json": json.dumps(merged_aliases),
                "source_episode_ids_json": json.dumps(merged_episodes),
                "episode_id": source_episode_id,
                "now": now_iso,
            },
        )
        return self._row_to_entity(rows[0])

    def get_entity(self, scope: TenantScope, entity_id: str) -> EntityRecord:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        rows = falkor_manager.ro_query(
            graph,
            cypher_catalog.GET_ENTITY_BY_ID,
            params={"entity_id": entity_id, "tenant_id": scope.tenant_id},
        )
        if not rows:
            raise ResourceNotFoundError("Entity", entity_id)
        return self._row_to_entity(rows[0])

    def list_entities(
        self,
        scope: TenantScope,
        entity_type: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 200,
    ) -> List[EntityRecord]:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        rows = falkor_manager.ro_query(
            graph,
            cypher_catalog.LIST_ENTITIES,
            params={
                "tenant_id": scope.tenant_id,
                "entity_type": entity_type or "",
                "search": search or "",
                "limit": min(max(limit, 1), 500),
            },
        )
        return [self._row_to_entity(r) for r in rows]

    def record_fact_with_conflict_resolution(
        self,
        scope: TenantScope,
        subject_entity_id: str,
        subject_name: str,
        predicate: str,
        object_value: str,
        source_episode_id: str,
        observed_at: datetime,
        confidence: float = 0.92,
        object_entity_id: Optional[str] = None,
    ) -> FactRecord:
        """
        Stores a semantic fact and applies BR-004 temporal conflict precedence:
        - If an identical CURRENT fact exists, updates its provenance reference or returns it.
        - If a conflicting CURRENT fact exists for the same (subject_entity_id, predicate),
          the newer timestamp stays CURRENT and the older fact is marked SUPERSEDED (never deleted).
        """
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        observed_iso = observed_at.astimezone(timezone.utc).isoformat()

        existing_rows = falkor_manager.ro_query(
            graph,
            cypher_catalog.FIND_CURRENT_FACTS_FOR_SUBJECT_PREDICATE,
            params={
                "tenant_id": scope.tenant_id,
                "subject_entity_id": subject_entity_id,
                "predicate": predicate,
            },
        )
        existing_facts = [self._row_to_fact(r) for r in existing_rows]

        for ef in existing_facts:
            if ef.object_value.strip().lower() == object_value.strip().lower():
                return self._attach_fact_provenance(scope, ef)

        new_fact_id = f"fact_{uuid.uuid4().hex[:12]}"
        new_status = FactStatus.CURRENT
        superseded_by_id = ""

        # Check if any existing fact has a strictly newer timestamp than this incoming fact
        newer_existing: Optional[FactRecord] = None
        for ef in existing_facts:
            if ef.observed_at > observed_at.astimezone(timezone.utc):
                newer_existing = ef
                break

        if newer_existing is not None:
            new_status = FactStatus.SUPERSEDED
            superseded_by_id = newer_existing.id

        created_rows = falkor_manager.query(
            graph,
            cypher_catalog.CREATE_FACT,
            params={
                "fact_id": new_fact_id,
                "tenant_id": scope.tenant_id,
                "subject_entity_id": subject_entity_id,
                "subject_name": subject_name,
                "predicate": predicate,
                "object_value": object_value,
                "object_entity_id": object_entity_id or "",
                "status": new_status.value,
                "confidence": float(confidence),
                "source_episode_id": source_episode_id,
                "observed_at": observed_iso,
                "superseded_by_id": superseded_by_id,
            },
        )
        created_fact = self._row_to_fact(created_rows[0])

        if new_status == FactStatus.CURRENT:
            for ef in existing_facts:
                falkor_manager.query(
                    graph,
                    cypher_catalog.SUPERSEDE_FACT,
                    params={
                        "old_fact_id": ef.id,
                        "new_fact_id": created_fact.id,
                        "tenant_id": scope.tenant_id,
                    },
                )
        else:
            falkor_manager.query(
                graph,
                cypher_catalog.SUPERSEDE_FACT,
                params={
                    "old_fact_id": created_fact.id,
                    "new_fact_id": newer_existing.id if newer_existing else "",
                    "tenant_id": scope.tenant_id,
                },
            )

        return self._attach_fact_provenance(scope, created_fact)

    def list_facts(
        self,
        scope: TenantScope,
        subject_entity_id: Optional[str] = None,
        include_superseded: bool = True,
        limit: int = 200,
    ) -> List[FactRecord]:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        rows = falkor_manager.ro_query(
            graph,
            cypher_catalog.LIST_FACTS,
            params={
                "tenant_id": scope.tenant_id,
                "subject_entity_id": subject_entity_id or "",
                "include_superseded": bool(include_superseded),
                "limit": min(max(limit, 1), 500),
            },
        )
        facts = [self._row_to_fact(r) for r in rows]
        return self._attach_bulk_fact_provenance(scope, facts)

    def get_fact(self, scope: TenantScope, fact_id: str) -> FactRecord:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        rows = falkor_manager.ro_query(
            graph,
            cypher_catalog.GET_FACT_BY_ID,
            params={"fact_id": fact_id, "tenant_id": scope.tenant_id},
        )
        if not rows:
            raise ResourceNotFoundError("Fact", fact_id)
        return self._attach_fact_provenance(scope, self._row_to_fact(rows[0]))

    # -----------------------------------------------------------------------
    # Procedural Memory (FR-004, BR-002, BR-003)
    # -----------------------------------------------------------------------
    def upsert_procedure(
        self,
        scope: TenantScope,
        name: str,
        trigger_text: str,
        trigger_keywords: List[str],
        steps: List[str],
        source_episode_id: str,
        confirmed_by_user: bool = False,
    ) -> ProcedureRecord:
        """
        Enforces BR-003: A procedure starts as PROPOSED unless explicitly confirmed by the user
        OR corroborated by at least 3 distinct episodes.
        """
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        existing_rows = falkor_manager.ro_query(
            graph,
            cypher_catalog.GET_PROCEDURE_BY_NAME,
            params={"name": name.strip(), "tenant_id": scope.tenant_id},
        )

        procedure_id = f"proc_{uuid.uuid4().hex[:12]}"
        source_ids: List[str] = []
        status = ProcedureStatus.PROPOSED
        confirmation_method = ConfirmationMethod.UNCONFIRMED
        active_task_id = ""
        last_executed_at = ""

        if existing_rows:
            existing = self._row_to_procedure(existing_rows[0])
            procedure_id = existing.id
            source_ids = list(existing.source_episode_ids)
            status = existing.status
            confirmation_method = existing.confirmation_method
            active_task_id = existing.active_task_id or ""
            last_executed_at = (
                existing.last_executed_at.isoformat() if existing.last_executed_at else ""
            )

        if source_episode_id and source_episode_id not in source_ids:
            source_ids.append(source_episode_id)

        evidence_count = len(source_ids)
        if confirmed_by_user:
            status = ProcedureStatus.CONFIRMED
            confirmation_method = ConfirmationMethod.USER_CONFIRMED
        elif evidence_count >= 3 and status != ProcedureStatus.CONFIRMED:
            status = ProcedureStatus.CONFIRMED
            confirmation_method = ConfirmationMethod.CORROBORATED_3X
        elif status == ProcedureStatus.CONFIRMED and confirmation_method == ConfirmationMethod.UNCONFIRMED:
            confirmation_method = ConfirmationMethod.CORROBORATED_3X

        now_iso = datetime.now(timezone.utc).isoformat()
        rows = falkor_manager.query(
            graph,
            cypher_catalog.UPSERT_PROCEDURE,
            params={
                "procedure_id": procedure_id,
                "name": name.strip(),
                "tenant_id": scope.tenant_id,
                "trigger_text": trigger_text.strip(),
                "trigger_keywords_json": json.dumps(trigger_keywords),
                "steps_json": json.dumps(steps),
                "status": status.value,
                "confirmation_method": confirmation_method.value,
                "evidence_count": evidence_count,
                "source_episode_ids_json": json.dumps(source_ids),
                "active_task_id": active_task_id,
                "last_executed_at": last_executed_at,
                "source_episode_id": source_episode_id,
                "now": now_iso,
            },
        )
        return self._attach_procedure_provenance(scope, self._row_to_procedure(rows[0]))

    def confirm_procedure(self, scope: TenantScope, procedure_id: str) -> ProcedureRecord:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        now_iso = datetime.now(timezone.utc).isoformat()
        rows = falkor_manager.query(
            graph,
            cypher_catalog.CONFIRM_PROCEDURE,
            params={
                "procedure_id": procedure_id,
                "tenant_id": scope.tenant_id,
                "now": now_iso,
            },
        )
        if not rows:
            raise ResourceNotFoundError("Procedure", procedure_id)
        return self._attach_procedure_provenance(scope, self._row_to_procedure(rows[0]))

    def set_procedure_active_task(
        self, scope: TenantScope, procedure_id: str, active_task_id: Optional[str]
    ) -> ProcedureRecord:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        now_iso = datetime.now(timezone.utc).isoformat()
        rows = falkor_manager.query(
            graph,
            cypher_catalog.SET_PROCEDURE_ACTIVE_TASK,
            params={
                "procedure_id": procedure_id,
                "tenant_id": scope.tenant_id,
                "active_task_id": active_task_id or "",
                "now": now_iso,
            },
        )
        if not rows:
            raise ResourceNotFoundError("Procedure", procedure_id)
        return self._attach_procedure_provenance(scope, self._row_to_procedure(rows[0]))

    def get_procedure(self, scope: TenantScope, procedure_id: str) -> ProcedureRecord:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        rows = falkor_manager.ro_query(
            graph,
            cypher_catalog.GET_PROCEDURE_BY_ID,
            params={"procedure_id": procedure_id, "tenant_id": scope.tenant_id},
        )
        if not rows:
            raise ResourceNotFoundError("Procedure", procedure_id)
        return self._attach_procedure_provenance(scope, self._row_to_procedure(rows[0]))

    def list_procedures(
        self, scope: TenantScope, status: Optional[ProcedureStatus] = None, limit: int = 100
    ) -> List[ProcedureRecord]:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        rows = falkor_manager.ro_query(
            graph,
            cypher_catalog.LIST_PROCEDURES,
            params={
                "tenant_id": scope.tenant_id,
                "status": status.value if status else "",
                "limit": min(max(limit, 1), 200),
            },
        )
        procs = [self._row_to_procedure(r) for r in rows]
        return [self._attach_procedure_provenance(scope, p) for p in procs]

    # -----------------------------------------------------------------------
    # Provenance Attachment Helpers (FR-008, BR-002, NFR-008)
    # -----------------------------------------------------------------------
    def _attach_fact_provenance(self, scope: TenantScope, fact: FactRecord) -> FactRecord:
        episodes = self.get_episodes_by_ids(scope, [fact.source_episode_id])
        if episodes:
            ep = episodes[0]
            fact.provenance = ProvenanceRef(
                episode_id=ep.id,
                session_id=ep.session_id,
                agent_id=ep.agent_id,
                timestamp=ep.timestamp,
                snippet=ep.content[:240],
            )
        return fact

    def _attach_bulk_fact_provenance(
        self, scope: TenantScope, facts: List[FactRecord]
    ) -> List[FactRecord]:
        if not facts:
            return []
        ep_ids = list({f.source_episode_id for f in facts if f.source_episode_id})
        episodes_map: Dict[str, EpisodeRecord] = {
            ep.id: ep for ep in self.get_episodes_by_ids(scope, ep_ids)
        }
        for f in facts:
            ep = episodes_map.get(f.source_episode_id)
            if ep:
                f.provenance = ProvenanceRef(
                    episode_id=ep.id,
                    session_id=ep.session_id,
                    agent_id=ep.agent_id,
                    timestamp=ep.timestamp,
                    snippet=ep.content[:240],
                )
        return facts

    def _attach_procedure_provenance(
        self, scope: TenantScope, proc: ProcedureRecord
    ) -> ProcedureRecord:
        episodes = self.get_episodes_by_ids(scope, proc.source_episode_ids)
        proc.provenance_refs = [
            ProvenanceRef(
                episode_id=ep.id,
                session_id=ep.session_id,
                agent_id=ep.agent_id,
                timestamp=ep.timestamp,
                snippet=ep.content[:240],
            )
            for ep in episodes
        ]
        return proc

    # -----------------------------------------------------------------------
    # Row Deserializers
    # -----------------------------------------------------------------------
    @staticmethod
    def _row_to_episode(row: list) -> EpisodeRecord:
        return EpisodeRecord(
            id=str(row[0]),
            tenant_id=str(row[1]),
            content=str(row[2]),
            agent_id=str(row[3]),
            agent_name=str(row[4]),
            session_id=str(row[5]),
            timestamp=datetime.fromisoformat(str(row[6])),
            importance_score=float(row[7]),
            extraction_status=ExtractionStatus(str(row[8])),
            archived=bool(row[9]),
            idempotency_key=str(row[10]) if row[10] else None,
            created_at=datetime.fromisoformat(str(row[11])),
        )

    @staticmethod
    def _row_to_entity(row: list) -> EntityRecord:
        return EntityRecord(
            id=str(row[0]),
            tenant_id=str(row[1]),
            canonical_key=str(row[2]),
            canonical_name=str(row[3]),
            entity_type=str(row[4]),
            aliases=json.loads(str(row[5])) if row[5] else [],
            source_episode_ids=json.loads(str(row[6])) if row[6] else [],
            created_at=datetime.fromisoformat(str(row[7])),
            updated_at=datetime.fromisoformat(str(row[8])),
        )

    @staticmethod
    def _row_to_fact(row: list) -> FactRecord:
        return FactRecord(
            id=str(row[0]),
            tenant_id=str(row[1]),
            subject_entity_id=str(row[2]),
            subject_name=str(row[3]),
            predicate=str(row[4]),
            object_value=str(row[5]),
            object_entity_id=str(row[6]) if row[6] else None,
            status=FactStatus(str(row[7])),
            confidence=float(row[8]),
            source_episode_id=str(row[9]),
            observed_at=datetime.fromisoformat(str(row[10])),
            superseded_by_id=str(row[11]) if row[11] else None,
        )

    @staticmethod
    def _row_to_procedure(row: list) -> ProcedureRecord:
        active_task_id = str(row[10]) if row[10] else None
        last_exec = datetime.fromisoformat(str(row[11])) if row[11] else None
        return ProcedureRecord(
            id=str(row[0]),
            tenant_id=str(row[1]),
            name=str(row[2]),
            trigger_text=str(row[3]),
            trigger_keywords=json.loads(str(row[4])) if row[4] else [],
            steps=json.loads(str(row[5])) if row[5] else [],
            status=ProcedureStatus(str(row[6])),
            confirmation_method=ConfirmationMethod(str(row[7])),
            evidence_count=int(row[8]),
            source_episode_ids=json.loads(str(row[9])) if row[9] else [],
            active_task_id=active_task_id,
            is_currently_active=bool(active_task_id),
            last_executed_at=last_exec,
            created_at=datetime.fromisoformat(str(row[12])),
            updated_at=datetime.fromisoformat(str(row[13])),
        )


@lru_cache()
def get_memory_repository() -> MemoryRepository:
    return MemoryRepository()