from functools import lru_cache
from typing import Dict, List, Optional, Set

from app.core.errors import AgentHiveError, ConflictStateError
from app.core.events import tenant_event_bus
from app.domain.coordination import (
    AgentCreateRequest,
    AgentRecord,
    HandoffCreateRequest,
    HandoffRecord,
    HandoffStatusUpdateRequest,
    TaskCreateRequest,
    TaskRecord,
    TaskStatusUpdateRequest,
)
from app.domain.enums import AgentStatus, HandoffStatus, TaskStatus
from app.domain.memory import ProcedureRecord
from app.domain.tenant import TenantScope
from app.repositories.coordination_repository import get_coordination_repository
from app.repositories.memory_repository import get_memory_repository

VALID_HANDOFF_TRANSITIONS: Dict[HandoffStatus, Set[HandoffStatus]] = {
    HandoffStatus.PENDING: {
        HandoffStatus.ACCEPTED,
        HandoffStatus.IN_PROGRESS,
        HandoffStatus.COMPLETED,
        HandoffStatus.FAILED,
        HandoffStatus.CANCELLED,
    },
    HandoffStatus.ACCEPTED: {
        HandoffStatus.IN_PROGRESS,
        HandoffStatus.COMPLETED,
        HandoffStatus.FAILED,
        HandoffStatus.CANCELLED,
    },
    HandoffStatus.IN_PROGRESS: {
        HandoffStatus.COMPLETED,
        HandoffStatus.FAILED,
        HandoffStatus.CANCELLED,
    },
    HandoffStatus.COMPLETED: set(),
    HandoffStatus.FAILED: set(),
    HandoffStatus.CANCELLED: set(),
}


class CoordinationService:
    """
    Domain service for Agent Registry, Same-Tenant Handoffs, Shared Task State,
    and Genuine Active Procedure Execution Events (FR-009..FR-012, BR-006).
    """

    # -----------------------------------------------------------------------
    # Agent Registry (FR-009)
    # -----------------------------------------------------------------------
    def register_agent(self, scope: TenantScope, req: AgentCreateRequest) -> AgentRecord:
        agent = get_coordination_repository().upsert_agent(scope, req)
        tenant_event_bus.publish(
            scope.tenant_id,
            "agent_registered",
            {"agent_id": agent.id, "name": agent.name, "role": agent.role, "status": agent.status.value},
        )
        return agent

    def get_agent(self, scope: TenantScope, agent_id: str) -> AgentRecord:
        return get_coordination_repository().get_agent(scope, agent_id)

    def list_agents(self, scope: TenantScope, limit: int = 100) -> List[AgentRecord]:
        return get_coordination_repository().list_agents(scope, limit=limit)

    # -----------------------------------------------------------------------
    # Handoffs (FR-010, FR-011, BR-006)
    # -----------------------------------------------------------------------
    def create_handoff(self, scope: TenantScope, req: HandoffCreateRequest) -> HandoffRecord:
        coord_repo = get_coordination_repository()

        if req.origin_agent_id.strip() == req.target_agent_id.strip():
            raise AgentHiveError(
                message="Origin agent and target agent must be distinct registered agents.",
                code="SELF_HANDOFF_NOT_ALLOWED",
                status_code=400,
            )

        # Verify both origin and target agents exist in the SAME resolved tenant graph (BR-006)
        origin_agent = coord_repo.get_agent(scope, req.origin_agent_id)
        target_agent = coord_repo.get_agent(scope, req.target_agent_id)

        if origin_agent.status == AgentStatus.OFFLINE:
            raise ConflictStateError(
                f"Origin agent '{origin_agent.id}' is OFFLINE and cannot initiate handoffs."
            )
        if target_agent.status == AgentStatus.OFFLINE:
            raise ConflictStateError(
                f"Target agent '{target_agent.id}' is OFFLINE and cannot receive handoffs."
            )

        # Ensure an underlying Task record exists in the tenant graph
        if req.task_id:
            task = coord_repo.get_task(scope, req.task_id)
            task = coord_repo.update_task_status(
                scope=scope,
                task_id=task.id,
                status=TaskStatus.PENDING,
                owner_agent_id=target_agent.id,
                active_procedure_id=task.active_procedure_id,
                result_summary=task.result_summary,
            )
        else:
            task = coord_repo.create_task(
                scope=scope,
                title=req.task_title,
                owner_agent_id=target_agent.id,
                status=TaskStatus.PENDING,
                session_id=req.session_id,
            )

        handoff = coord_repo.create_handoff(
            scope=scope,
            task_id=task.id,
            task_title=req.task_title,
            origin_agent_id=origin_agent.id,
            target_agent_id=target_agent.id,
            context_summary=req.context_summary,
            state_payload=req.state_payload,
            session_id=req.session_id,
        )

        tenant_event_bus.publish(
            scope.tenant_id,
            "handoff_created",
            {
                "handoff_id": handoff.id,
                "task_id": handoff.task_id,
                "task_title": handoff.task_title,
                "origin_agent_id": handoff.origin_agent_id,
                "target_agent_id": handoff.target_agent_id,
                "status": handoff.status.value,
            },
        )
        return handoff

    def update_handoff_status(
        self, scope: TenantScope, handoff_id: str, req: HandoffStatusUpdateRequest
    ) -> HandoffRecord:
        coord_repo = get_coordination_repository()
        # Verify acting agent is registered in this tenant
        coord_repo.get_agent(scope, req.acting_agent_id)

        existing = coord_repo.get_handoff(scope, handoff_id)
        if req.status != existing.status:
            allowed = VALID_HANDOFF_TRANSITIONS.get(existing.status, set())
            if req.status not in allowed:
                raise ConflictStateError(
                    f"Invalid handoff status transition from '{existing.status.value}' to '{req.status.value}'."
                )

        updated = coord_repo.update_handoff_status(scope, handoff_id, req.status)

        # Synchronize linked task status so all same-tenant agents see the update within 5s (FR-012)
        mapped_task_status: Optional[TaskStatus] = None
        if req.status in (HandoffStatus.ACCEPTED, HandoffStatus.IN_PROGRESS):
            mapped_task_status = TaskStatus.IN_PROGRESS
        elif req.status == HandoffStatus.COMPLETED:
            mapped_task_status = TaskStatus.COMPLETED
        elif req.status == HandoffStatus.FAILED:
            mapped_task_status = TaskStatus.FAILED
        elif req.status == HandoffStatus.CANCELLED:
            mapped_task_status = TaskStatus.CANCELLED

        if mapped_task_status is not None:
            task = coord_repo.get_task(scope, updated.task_id)
            self.update_task_status(
                scope,
                task.id,
                TaskStatusUpdateRequest(
                    status=mapped_task_status,
                    acting_agent_id=req.acting_agent_id,
                    active_procedure_id=task.active_procedure_id,
                    result_summary=req.note or task.result_summary,
                ),
            )

        tenant_event_bus.publish(
            scope.tenant_id,
            "handoff_status_updated",
            {
                "handoff_id": updated.id,
                "task_id": updated.task_id,
                "status": updated.status.value,
                "acting_agent_id": req.acting_agent_id,
            },
        )
        return updated

    def get_handoff(self, scope: TenantScope, handoff_id: str) -> HandoffRecord:
        return get_coordination_repository().get_handoff(scope, handoff_id)

    def list_handoffs(
        self,
        scope: TenantScope,
        target_agent_id: Optional[str] = None,
        origin_agent_id: Optional[str] = None,
        status: Optional[HandoffStatus] = None,
        limit: int = 100,
    ) -> List[HandoffRecord]:
        return get_coordination_repository().list_handoffs(
            scope=scope,
            target_agent_id=target_agent_id,
            origin_agent_id=origin_agent_id,
            status=status,
            limit=limit,
        )

    # -----------------------------------------------------------------------
    # Shared Task State & Active Procedure Glow Lifecycle (FR-012)
    # -----------------------------------------------------------------------
    def create_task(self, scope: TenantScope, req: TaskCreateRequest) -> TaskRecord:
        coord_repo = get_coordination_repository()
        mem_repo = get_memory_repository()

        coord_repo.get_agent(scope, req.owner_agent_id)
        initial_status = TaskStatus.IN_PROGRESS if req.active_procedure_id else TaskStatus.PENDING

        if req.active_procedure_id:
            mem_repo.get_procedure(scope, req.active_procedure_id)

        task = coord_repo.create_task(
            scope=scope,
            title=req.title,
            owner_agent_id=req.owner_agent_id,
            status=initial_status,
            session_id=req.session_id,
            active_procedure_id=req.active_procedure_id,
        )

        if req.active_procedure_id:
            proc = mem_repo.set_procedure_active_task(scope, req.active_procedure_id, task.id)
            tenant_event_bus.publish(
                scope.tenant_id,
                "procedure_activity",
                {
                    "procedure_id": proc.id,
                    "procedure_name": proc.name,
                    "task_id": task.id,
                    "task_title": task.title,
                    "task_status": task.status.value,
                    "agent_id": task.owner_agent_id,
                    "is_active": True,
                },
            )

        tenant_event_bus.publish(
            scope.tenant_id,
            "task_status_updated",
            {
                "task_id": task.id,
                "title": task.title,
                "status": task.status.value,
                "owner_agent_id": task.owner_agent_id,
                "active_procedure_id": task.active_procedure_id,
            },
        )
        return task

    def update_task_status(
        self, scope: TenantScope, task_id: str, req: TaskStatusUpdateRequest
    ) -> TaskRecord:
        coord_repo = get_coordination_repository()
        mem_repo = get_memory_repository()

        coord_repo.get_agent(scope, req.acting_agent_id)
        existing_task = coord_repo.get_task(scope, task_id)

        proc_id = (
            req.active_procedure_id
            if req.active_procedure_id is not None
            else existing_task.active_procedure_id
        )

        updated_task = coord_repo.update_task_status(
            scope=scope,
            task_id=task_id,
            status=req.status,
            owner_agent_id=req.acting_agent_id,
            active_procedure_id=proc_id if req.status == TaskStatus.IN_PROGRESS else "",
            result_summary=req.result_summary
            if req.result_summary is not None
            else existing_task.result_summary,
        )

        # Manage genuine active procedure glow state
        if proc_id:
            if req.status == TaskStatus.IN_PROGRESS:
                proc = mem_repo.set_procedure_active_task(scope, proc_id, updated_task.id)
                tenant_event_bus.publish(
                    scope.tenant_id,
                    "procedure_activity",
                    {
                        "procedure_id": proc.id,
                        "procedure_name": proc.name,
                        "task_id": updated_task.id,
                        "task_title": updated_task.title,
                        "task_status": updated_task.status.value,
                        "agent_id": updated_task.owner_agent_id,
                        "is_active": True,
                    },
                )
            elif req.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                proc = mem_repo.set_procedure_active_task(scope, proc_id, None)
                tenant_event_bus.publish(
                    scope.tenant_id,
                    "procedure_activity",
                    {
                        "procedure_id": proc.id,
                        "procedure_name": proc.name,
                        "task_id": updated_task.id,
                        "task_title": updated_task.title,
                        "task_status": updated_task.status.value,
                        "agent_id": updated_task.owner_agent_id,
                        "is_active": False,
                    },
                )

        tenant_event_bus.publish(
            scope.tenant_id,
            "task_status_updated",
            {
                "task_id": updated_task.id,
                "title": updated_task.title,
                "status": updated_task.status.value,
                "owner_agent_id": updated_task.owner_agent_id,
                "active_procedure_id": updated_task.active_procedure_id,
                "result_summary": updated_task.result_summary,
            },
        )
        return updated_task

    def start_procedure_execution(
        self, scope: TenantScope, procedure_id: str, agent_id: str, task_title: Optional[str] = None
    ) -> tuple[ProcedureRecord, TaskRecord]:
        mem_repo = get_memory_repository()
        proc = mem_repo.get_procedure(scope, procedure_id)
        title = task_title or f"Execute Procedure: {proc.name}"
        task = self.create_task(
            scope,
            TaskCreateRequest(
                title=title,
                owner_agent_id=agent_id,
                active_procedure_id=proc.id,
            ),
        )
        updated_proc = mem_repo.get_procedure(scope, procedure_id)
        return updated_proc, task

    def stop_procedure_execution(
        self,
        scope: TenantScope,
        procedure_id: str,
        agent_id: str,
        final_status: TaskStatus = TaskStatus.COMPLETED,
        result_summary: Optional[str] = None,
    ) -> ProcedureRecord:
        mem_repo = get_memory_repository()
        proc = mem_repo.get_procedure(scope, procedure_id)
        if proc.active_task_id:
            self.update_task_status(
                scope,
                proc.active_task_id,
                TaskStatusUpdateRequest(
                    status=final_status,
                    acting_agent_id=agent_id,
                    active_procedure_id=proc.id,
                    result_summary=result_summary or "Procedure execution finished.",
                ),
            )
        else:
            mem_repo.set_procedure_active_task(scope, procedure_id, None)
        return mem_repo.get_procedure(scope, procedure_id)

    def get_task(self, scope: TenantScope, task_id: str) -> TaskRecord:
        return get_coordination_repository().get_task(scope, task_id)

    def list_tasks(
        self,
        scope: TenantScope,
        owner_agent_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        limit: int = 100,
    ) -> List[TaskRecord]:
        return get_coordination_repository().list_tasks(
            scope=scope,
            owner_agent_id=owner_agent_id,
            status=status,
            limit=limit,
        )


@lru_cache()
def get_coordination_service() -> CoordinationService:
    return CoordinationService()