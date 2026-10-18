from functools import lru_cache
from typing import Dict, List, Set

from app.domain.enums import FactStatus, MemoryTier, ProcedureStatus, TaskStatus
from app.domain.graph_view import (
    ActiveProcedureExecution,
    GraphEdgeDTO,
    GraphNodeDTO,
    GraphSubgraphResponse,
    OverviewMetricsDTO,
)
from app.domain.tenant import TenantScope
from app.repositories import cypher_catalog
from app.repositories.coordination_repository import get_coordination_repository
from app.repositories.falkor_client import falkor_manager
from app.repositories.memory_repository import get_memory_repository


class GraphVizRepository:
    """
    Queries live FalkorDB nodes, relationships, and counts for the interactive 3-tier Memory Graph
    and Hero Metrics dashboard (FR-015, C-01).
    """

    def get_overview_metrics(self, scope: TenantScope) -> OverviewMetricsDTO:
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        rows = falkor_manager.ro_query(
            graph,
            cypher_catalog.COUNT_BY_LABEL,
            params={"tenant_id": scope.tenant_id},
        )

        ep_count = 0
        sess_count = 0
        ent_count = 0
        cur_fact_count = 0
        sup_fact_count = 0
        conf_proc_count = 0
        prop_proc_count = 0
        agent_count = 0
        pending_ho_count = 0
        active_task_count = 0
        pending_jobs = 0

        for r in rows:
            label = str(r[0]) if r[0] else ""
            status = str(r[1]) if r[1] else ""
            cnt = int(r[2])
            if label == "Episode":
                ep_count += cnt
            elif label == "Session":
                sess_count += cnt
            elif label == "Entity":
                ent_count += cnt
            elif label == "Fact":
                if status == FactStatus.CURRENT.value:
                    cur_fact_count += cnt
                else:
                    sup_fact_count += cnt
            elif label == "Procedure":
                if status == ProcedureStatus.CONFIRMED.value:
                    conf_proc_count += cnt
                else:
                    prop_proc_count += cnt
            elif label == "Agent":
                agent_count += cnt
            elif label == "Handoff":
                if status in ("PENDING", "ACCEPTED", "IN_PROGRESS"):
                    pending_ho_count += cnt
            elif label == "Task":
                if status in ("PENDING", "IN_PROGRESS"):
                    active_task_count += cnt
            elif label == "ExtractionJob":
                if status in ("PENDING", "DEFERRED"):
                    pending_jobs += cnt

        return OverviewMetricsDTO(
            tenant_id=scope.tenant_id,
            episode_count=ep_count,
            session_count=sess_count,
            entity_count=ent_count,
            current_fact_count=cur_fact_count,
            superseded_fact_count=sup_fact_count,
            confirmed_procedure_count=conf_proc_count,
            proposed_procedure_count=prop_proc_count,
            registered_agent_count=agent_count,
            pending_handoff_count=pending_ho_count,
            active_task_count=active_task_count,
            pending_extraction_jobs=pending_jobs,
        )

    def get_subgraph(self, scope: TenantScope, max_episodes: int = 40) -> GraphSubgraphResponse:
        mem_repo = get_memory_repository()
        coord_repo = get_coordination_repository()
        metrics = self.get_overview_metrics(scope)

        episodes = mem_repo.list_episodes(scope, limit=max_episodes)
        entities = mem_repo.list_entities(scope, limit=80)
        facts = mem_repo.list_facts(scope, include_superseded=True, limit=100)
        procedures = mem_repo.list_procedures(scope, limit=50)
        agents = coord_repo.list_agents(scope, limit=50)
        tasks = coord_repo.list_tasks(scope, limit=50)
        handoffs = coord_repo.list_handoffs(scope, limit=50)

        active_tasks_by_id = {
            t.id: t for t in tasks if t.status == TaskStatus.IN_PROGRESS
        }

        active_procedures: List[ActiveProcedureExecution] = []
        glowing_node_ids: Set[str] = set()

        for p in procedures:
            if p.active_task_id and p.active_task_id in active_tasks_by_id:
                t = active_tasks_by_id[p.active_task_id]
                active_procedures.append(
                    ActiveProcedureExecution(
                        procedure_id=p.id,
                        procedure_name=p.name,
                        task_id=t.id,
                        task_title=t.title,
                        task_status=t.status.value,
                        agent_id=t.owner_agent_id,
                    )
                )
                glowing_node_ids.add(p.id)
                glowing_node_ids.add(t.id)
                glowing_node_ids.add(t.owner_agent_id)
                for src_ep_id in p.source_episode_ids:
                    glowing_node_ids.add(src_ep_id)

        nodes: Dict[str, GraphNodeDTO] = {}

        for ep in episodes:
            nodes[ep.id] = GraphNodeDTO(
                id=ep.id,
                label=f"Episode {ep.id[-6:]}",
                node_type="Episode",
                tier=MemoryTier.EPISODIC,
                tenant_id=scope.tenant_id,
                status=ep.extraction_status.value,
                is_glowing=ep.id in glowing_node_ids,
                properties={
                    "content": ep.content,
                    "agent_id": ep.agent_id,
                    "agent_name": ep.agent_name,
                    "session_id": ep.session_id,
                    "timestamp": ep.timestamp.isoformat(),
                    "importance_score": ep.importance_score,
                },
            )

        for ent in entities:
            nodes[ent.id] = GraphNodeDTO(
                id=ent.id,
                label=ent.canonical_name,
                node_type="Entity",
                tier=MemoryTier.SEMANTIC,
                tenant_id=scope.tenant_id,
                status=ent.entity_type,
                is_glowing=ent.id in glowing_node_ids,
                properties={
                    "canonical_key": ent.canonical_key,
                    "entity_type": ent.entity_type,
                    "aliases": ent.aliases,
                    "source_episode_ids": ent.source_episode_ids,
                },
            )

        for f in facts:
            nodes[f.id] = GraphNodeDTO(
                id=f.id,
                label=f"{f.subject_name}.{f.predicate} = {f.object_value}",
                node_type="Fact",
                tier=MemoryTier.SEMANTIC,
                tenant_id=scope.tenant_id,
                status=f.status.value,
                is_glowing=f.id in glowing_node_ids,
                properties={
                    "subject_name": f.subject_name,
                    "predicate": f.predicate,
                    "object_value": f.object_value,
                    "source_episode_id": f.source_episode_id,
                    "observed_at": f.observed_at.isoformat(),
                    "superseded_by_id": f.superseded_by_id,
                },
            )

        for p in procedures:
            is_proc_glowing = p.id in glowing_node_ids
            nodes[p.id] = GraphNodeDTO(
                id=p.id,
                label=p.name,
                node_type="Procedure",
                tier=MemoryTier.PROCEDURAL,
                tenant_id=scope.tenant_id,
                status=p.status.value,
                is_glowing=is_proc_glowing,
                properties={
                    "trigger_text": p.trigger_text,
                    "steps": p.steps,
                    "confirmation_method": p.confirmation_method.value,
                    "evidence_count": p.evidence_count,
                    "source_episode_ids": p.source_episode_ids,
                    "active_task_id": p.active_task_id,
                },
            )

        for a in agents:
            nodes[a.id] = GraphNodeDTO(
                id=a.id,
                label=a.name,
                node_type="Agent",
                tier=MemoryTier.COORDINATION,
                tenant_id=scope.tenant_id,
                status=a.status.value,
                is_glowing=a.id in glowing_node_ids,
                properties={
                    "role": a.role,
                    "capabilities": a.capabilities,
                },
            )

        for t in tasks:
            nodes[t.id] = GraphNodeDTO(
                id=t.id,
                label=t.title,
                node_type="Task",
                tier=MemoryTier.COORDINATION,
                tenant_id=scope.tenant_id,
                status=t.status.value,
                is_glowing=t.id in glowing_node_ids,
                properties={
                    "owner_agent_id": t.owner_agent_id,
                    "active_procedure_id": t.active_procedure_id,
                    "result_summary": t.result_summary,
                },
            )

        for h in handoffs:
            nodes[h.id] = GraphNodeDTO(
                id=h.id,
                label=f"Handoff: {h.task_title[:28]}",
                node_type="Handoff",
                tier=MemoryTier.COORDINATION,
                tenant_id=scope.tenant_id,
                status=h.status.value,
                is_glowing=h.id in glowing_node_ids,
                properties={
                    "origin_agent_id": h.origin_agent_id,
                    "target_agent_id": h.target_agent_id,
                    "context_summary": h.context_summary,
                    "state_payload": h.state_payload,
                },
            )

        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        edge_rows = falkor_manager.ro_query(
            graph,
            cypher_catalog.LIST_GRAPH_EDGES,
            params={"tenant_id": scope.tenant_id, "limit": 600},
        )

        edges: List[GraphEdgeDTO] = []
        for idx, r in enumerate(edge_rows):
            src_id, rel_type, dst_id = str(r[0]), str(r[1]), str(r[2])
            if src_id in nodes and dst_id in nodes:
                is_active_edge = (src_id in glowing_node_ids) and (dst_id in glowing_node_ids)
                edges.append(
                    GraphEdgeDTO(
                        id=f"edge_{idx}_{src_id}_{dst_id}",
                        source=src_id,
                        target=dst_id,
                        label=rel_type,
                        is_active_path=is_active_edge,
                    )
                )

        return GraphSubgraphResponse(
            tenant_id=scope.tenant_id,
            metrics=metrics,
            active_procedures=active_procedures,
            nodes=list(nodes.values()),
            edges=edges,
        )


@lru_cache()
def get_graph_viz_repository() -> GraphVizRepository:
    return GraphVizRepository()