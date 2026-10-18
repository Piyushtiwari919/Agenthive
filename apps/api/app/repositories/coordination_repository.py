import json
import re
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from typing import List, Optional

from app.core.errors import ResourceNotFoundError
from app.domain.coordination import (
    AgentCreateRequest,
    AgentRecord,
    HandoffRecord,
    TaskRecord,
)
from app.domain.enums import AgentStatus, HandoffStatus, TaskStatus
from app.domain.tenant import TenantScope
from app.repositories import cypher_catalog
from app.repositories.falkor_client import falkor_manager


class CoordinationRepository:
    """
    Tenant-scoped FalkorDB repository for Agents, Handoffs, and Shared Task State
    (FR-009, FR-010, FR-011, FR-012, BR-006).
    """

    # -----------------------------------------------------------------------
    # Agent Registry (FR-009)
    # -----------------------------------------------------------------------
    def upsert_agent(self, scope: TenantScope, req: AgentCreateRequest) -> AgentRecord:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        now_iso = datetime.now(timezone.utc).isoformat()
        if req.agent_id:
            clean_id = re.sub(r"[^a-zA-Z0-9_-]", "-", req.agent_id.strip())
        else:
            slug = re.sub(r"[^a-z0-9]+", "-", req.name.lower()).strip("-")
            clean_id = f"agent-{slug}-{uuid.uuid4().hex[:6]}"

        rows = falkor_manager.query(
            graph,
            cypher_catalog.UPSERT_AGENT,
            params={
                "agent_id": clean_id,
                "tenant_id": scope.tenant_id,
                "name": req.name.strip(),
                "role": req.role.strip(),
                "capabilities_json": json.dumps(req.capabilities),
                "status": req.status.value,
                "now": now_iso,
            },
        )
        return self._row_to_agent(rows[0])

    def get_agent(self, scope: TenantScope, agent_id: str) -> AgentRecord:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        rows = falkor_manager.ro_query(
            graph,
            cypher_catalog.GET_AGENT_BY_ID,
            params={"agent_id": agent_id, "tenant_id": scope.tenant_id},
        )
        if not rows:
            raise ResourceNotFoundError("Agent", agent_id)
        return self._row_to_agent(rows[0])

    def list_agents(self, scope: TenantScope, limit: int = 100) -> List[AgentRecord]:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        rows = falkor_manager.ro_query(
            graph,
            cypher_catalog.LIST_AGENTS,
            params={"tenant_id": scope.tenant_id, "limit": min(max(limit, 1), 200)},
        )
        return [self._row_to_agent(r) for r in rows]

    # -----------------------------------------------------------------------
    # Shared Task State (FR-012)
    # -----------------------------------------------------------------------
    def create_task(
        self,
        scope: TenantScope,
        title: str,
        owner_agent_id: str,
        status: TaskStatus = TaskStatus.PENDING,
        session_id: Optional[str] = None,
        active_procedure_id: Optional[str] = None,
        result_summary: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> TaskRecord:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        now_iso = datetime.now(timezone.utc).isoformat()
        tid = task_id or f"task_{uuid.uuid4().hex[:12]}"

        rows = falkor_manager.query(
            graph,
            cypher_catalog.CREATE_TASK,
            params={
                "task_id": tid,
                "tenant_id": scope.tenant_id,
                "title": title.strip(),
                "status": status.value,
                "owner_agent_id": owner_agent_id,
                "session_id": session_id or "",
                "active_procedure_id": active_procedure_id or "",
                "result_summary": result_summary or "",
                "now": now_iso,
            },
        )
        if not rows:
            raise ResourceNotFoundError("Agent", owner_agent_id)
        return self._row_to_task(rows[0])

    def get_task(self, scope: TenantScope, task_id: str) -> TaskRecord:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        rows = falkor_manager.ro_query(
            graph,
            cypher_catalog.GET_TASK_BY_ID,
            params={"task_id": task_id, "tenant_id": scope.tenant_id},
        )
        if not rows:
            raise ResourceNotFoundError("Task", task_id)
        return self._row_to_task(rows[0])

    def update_task_status(
        self,
        scope: TenantScope,
        task_id: str,
        status: TaskStatus,
        owner_agent_id: str,
        active_procedure_id: Optional[str] = None,
        result_summary: Optional[str] = None,
    ) -> TaskRecord:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        now_iso = datetime.now(timezone.utc).isoformat()
        rows = falkor_manager.query(
            graph,
            cypher_catalog.UPDATE_TASK_STATUS,
            params={
                "task_id": task_id,
                "tenant_id": scope.tenant_id,
                "status": status.value,
                "owner_agent_id": owner_agent_id,
                "active_procedure_id": active_procedure_id or "",
                "result_summary": result_summary or "",
                "now": now_iso,
            },
        )
        if not rows:
            raise ResourceNotFoundError("Task", task_id)
        return self._row_to_task(rows[0])

    def list_tasks(
        self,
        scope: TenantScope,
        owner_agent_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        limit: int = 100,
    ) -> List[TaskRecord]:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        rows = falkor_manager.ro_query(
            graph,
            cypher_catalog.LIST_TASKS,
            params={
                "tenant_id": scope.tenant_id,
                "owner_agent_id": owner_agent_id or "",
                "status": status.value if status else "",
                "limit": min(max(limit, 1), 250),
            },
        )
        return [self._row_to_task(r) for r in rows]

    # -----------------------------------------------------------------------
    # Agent Handoffs (FR-010, FR-011, BR-006)
    # -----------------------------------------------------------------------
    def create_handoff(
        self,
        scope: TenantScope,
        task_id: str,
        task_title: str,
        origin_agent_id: str,
        target_agent_id: str,
        context_summary: str,
        state_payload: dict,
        session_id: Optional[str] = None,
    ) -> HandoffRecord:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        now_iso = datetime.now(timezone.utc).isoformat()
        handoff_id = f"ho_{uuid.uuid4().hex[:12]}"

        rows = falkor_manager.query(
            graph,
            cypher_catalog.CREATE_HANDOFF,
            params={
                "handoff_id": handoff_id,
                "tenant_id": scope.tenant_id,
                "task_id": task_id,
                "task_title": task_title.strip(),
                "origin_agent_id": origin_agent_id,
                "target_agent_id": target_agent_id,
                "context_summary": context_summary.strip(),
                "state_payload_json": json.dumps(state_payload),
                "status": HandoffStatus.PENDING.value,
                "session_id": session_id or "",
                "now": now_iso,
            },
        )
        if not rows:
            raise ResourceNotFoundError("AgentOrTask", f"{origin_agent_id}->{target_agent_id}")
        return self._row_to_handoff(rows[0])

    def get_handoff(self, scope: TenantScope, handoff_id: str) -> HandoffRecord:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        rows = falkor_manager.ro_query(
            graph,
            cypher_catalog.GET_HANDOFF_BY_ID,
            params={"handoff_id": handoff_id, "tenant_id": scope.tenant_id},
        )
        if not rows:
            raise ResourceNotFoundError("Handoff", handoff_id)
        return self._row_to_handoff(rows[0])

    def update_handoff_status(
        self, scope: TenantScope, handoff_id: str, status: HandoffStatus
    ) -> HandoffRecord:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        now_iso = datetime.now(timezone.utc).isoformat()
        rows = falkor_manager.query(
            graph,
            cypher_catalog.UPDATE_HANDOFF_STATUS,
            params={
                "handoff_id": handoff_id,
                "tenant_id": scope.tenant_id,
                "status": status.value,
                "now": now_iso,
            },
        )
        if not rows:
            raise ResourceNotFoundError("Handoff", handoff_id)
        return self._row_to_handoff(rows[0])

    def list_handoffs(
        self,
        scope: TenantScope,
        target_agent_id: Optional[str] = None,
        origin_agent_id: Optional[str] = None,
        status: Optional[HandoffStatus] = None,
        limit: int = 100,
    ) -> List[HandoffRecord]:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        rows = falkor_manager.ro_query(
            graph,
            cypher_catalog.LIST_HANDOFFS,
            params={
                "tenant_id": scope.tenant_id,
                "target_agent_id": target_agent_id or "",
                "origin_agent_id": origin_agent_id or "",
                "status": status.value if status else "",
                "limit": min(max(limit, 1), 250),
            },
        )
        return [self._row_to_handoff(r) for r in rows]

    def list_pending_handoffs_for_agent(
        self, scope: TenantScope, target_agent_id: Optional[str] = None, limit: int = 25
    ) -> List[HandoffRecord]:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        rows = falkor_manager.ro_query(
            graph,
            cypher_catalog.LIST_PENDING_HANDOFFS_FOR_AGENT,
            params={
                "tenant_id": scope.tenant_id,
                "target_agent_id": target_agent_id or "",
                "limit": min(max(limit, 1), 100),
            },
        )
        return [self._row_to_handoff(r) for r in rows]

    # -----------------------------------------------------------------------
    # Deserializers
    # -----------------------------------------------------------------------
    @staticmethod
    def _row_to_agent(row: list) -> AgentRecord:
        return AgentRecord(
            id=str(row[0]),
            tenant_id=str(row[1]),
            name=str(row[2]),
            role=str(row[3]),
            capabilities=json.loads(str(row[4])) if row[4] else [],
            status=AgentStatus(str(row[5])),
            created_at=datetime.fromisoformat(str(row[6])),
        )

    @staticmethod
    def _row_to_task(row: list) -> TaskRecord:
        return TaskRecord(
            id=str(row[0]),
            tenant_id=str(row[1]),
            title=str(row[2]),
            status=TaskStatus(str(row[3])),
            owner_agent_id=str(row[4]),
            session_id=str(row[5]) if row[5] else None,
            active_procedure_id=str(row[6]) if row[6] else None,
            result_summary=str(row[7]) if row[7] else None,
            created_at=datetime.fromisoformat(str(row[8])),
            updated_at=datetime.fromisoformat(str(row[9])),
        )

    @staticmethod
    def _row_to_handoff(row: list) -> HandoffRecord:
        return HandoffRecord(
            id=str(row[0]),
            tenant_id=str(row[1]),
            task_id=str(row[2]),
            task_title=str(row[3]),
            origin_agent_id=str(row[4]),
            target_agent_id=str(row[5]),
            context_summary=str(row[6]),
            state_payload=json.loads(str(row[7])) if row[7] else {},
            status=HandoffStatus(str(row[8])),
            session_id=str(row[9]) if row[9] else None,
            created_at=datetime.fromisoformat(str(row[10])),
            updated_at=datetime.fromisoformat(str(row[11])),
        )


@lru_cache()
def get_coordination_repository() -> CoordinationRepository:
    return CoordinationRepository()