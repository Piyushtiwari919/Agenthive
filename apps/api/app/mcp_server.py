import hmac
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from app.config import get_settings
from app.core.errors import TenantAccessDeniedError
from app.core.security import derive_opaque_graph_name, validate_tenant_id_format
from app.domain.context import ContextAssembleRequest
from app.domain.coordination import HandoffCreateRequest
from app.domain.enums import ProcedureStatus
from app.domain.memory import EpisodeCreateRequest
from app.domain.tenant import TenantScope
from app.repositories.control_repository import get_control_repository
from app.services.context_service import get_context_service
from app.services.coordination_service import get_coordination_service
from app.services.memory_service import get_memory_service
from app.services.tenant_service import get_tenant_service

mcp = FastMCP("AgentHive")


def resolve_mcp_tenant_scope() -> TenantScope:
    """
    Resolves the server-side tenant scope for the MCP process from environment configuration.
    Never allows arbitrary cross-tenant overrides from untrusted tool arguments (BR-001).
    """
    settings = get_settings()
    raw_tenant = os.getenv("AGENTHIVE_MCP_TENANT_ID", settings.demo_default_tenant)
    clean_tenant_id = validate_tenant_id_format(raw_tenant)

    if settings.agenthive_env == "production":
        token = os.getenv("AGENTHIVE_MCP_TENANT_TOKEN", "")
        expected = settings.production_tenant_tokens.get(clean_tenant_id)
        if not expected or not token or not hmac.compare_digest(expected, token):
            raise TenantAccessDeniedError(
                "MCP server requires valid AGENTHIVE_MCP_TENANT_TOKEN in production mode.",
                status_code=401,
            )

    control_repo = get_control_repository()
    tenant_info = control_repo.get_tenant(clean_tenant_id)
    if tenant_info is None and settings.agenthive_env in ("demo", "test"):
        get_tenant_service().ensure_demo_tenants()
        tenant_info = control_repo.get_tenant(clean_tenant_id)

    if tenant_info is None:
        raise TenantAccessDeniedError(f"MCP tenant '{clean_tenant_id}' is not provisioned.")

    return TenantScope(
        tenant_id=clean_tenant_id,
        graph_name=derive_opaque_graph_name(clean_tenant_id),
        display_name=tenant_info.display_name,
        is_demo=tenant_info.is_demo,
    )


@mcp.tool()
def remember_episode(
    content: str,
    agent_id: str,
    session_id: str,
    importance_score: float = 0.7,
    agent_name: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Records a completed agent interaction into FalkorDB episodic memory and extracts
    entities, facts, and procedures (FR-001, FR-003, FR-004).
    """
    scope = resolve_mcp_tenant_scope()
    req = EpisodeCreateRequest(
        content=content,
        agent_id=agent_id,
        agent_name=agent_name or agent_id,
        session_id=session_id,
        importance_score=max(0.0, min(1.0, float(importance_score))),
        idempotency_key=idempotency_key,
        process_extraction_inline=True,
    )
    ep = get_memory_service().record_episode(scope, req)
    return ep.model_dump(mode="json")


@mcp.tool()
def assemble_context(
    query: str,
    agent_id: Optional[str] = None,
    session_id: Optional[str] = None,
    max_episodes: int = 5,
) -> Dict[str, Any]:
    """
    Assembles a unified 4-part context package (ranked episodes, canonical entities & facts,
    applicable procedures, and pending handoffs) with source episode provenance (FR-006, FR-007, FR-008).
    """
    scope = resolve_mcp_tenant_scope()
    req = ContextAssembleRequest(
        query=query,
        agent_id=agent_id,
        session_id=session_id,
        max_episodes=max(1, min(20, int(max_episodes))),
    )
    pkg = get_context_service().assemble_context(scope, req)
    return pkg.model_dump(mode="json")


@mcp.tool()
def search_memory(
    query: str,
    max_results: int = 5,
) -> Dict[str, Any]:
    """
    Searches tenant-scoped episodes and semantic facts with full source provenance.
    """
    scope = resolve_mcp_tenant_scope()
    req = ContextAssembleRequest(
        query=query,
        max_episodes=max(1, min(20, int(max_results))),
    )
    pkg = get_context_service().assemble_context(scope, req)
    return {
        "tenant_id": scope.tenant_id,
        "query": query,
        "episodes": [item.model_dump(mode="json") for item in pkg.episodes],
        "entities": [ent.model_dump(mode="json") for ent in pkg.entities],
        "facts": [f.model_dump(mode="json") for f in pkg.facts],
    }


@mcp.tool()
def get_session_history(
    session_id: str,
    start_time_iso: Optional[str] = None,
    end_time_iso: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """
    Retrieves chronologically ordered conversation history for a session within the resolved tenant (FR-005).
    """
    scope = resolve_mcp_tenant_scope()
    start_dt = datetime.fromisoformat(start_time_iso) if start_time_iso else None
    end_dt = datetime.fromisoformat(end_time_iso) if end_time_iso else None
    hist = get_memory_service().get_session_history(
        scope=scope,
        session_id=session_id,
        start_time=start_dt,
        end_time=end_dt,
        limit=max(1, min(250, int(limit))),
    )
    return hist.model_dump(mode="json")


@mcp.tool()
def create_handoff(
    origin_agent_id: str,
    target_agent_id: str,
    task_title: str,
    context_summary: str,
    state_payload: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Transfers a task, context summary, and structured state payload between registered agents
    in the same tenant (FR-010, BR-006).
    """
    scope = resolve_mcp_tenant_scope()
    req = HandoffCreateRequest(
        origin_agent_id=origin_agent_id,
        target_agent_id=target_agent_id,
        task_title=task_title,
        context_summary=context_summary,
        state_payload=state_payload or {},
        session_id=session_id,
    )
    ho = get_coordination_service().create_handoff(scope, req)
    return ho.model_dump(mode="json")


@mcp.tool()
def get_task_status(
    owner_agent_id: Optional[str] = None,
    limit: int = 25,
) -> Dict[str, Any]:
    """
    Reads current shared task states and pending handoffs within the resolved tenant (FR-012).
    """
    scope = resolve_mcp_tenant_scope()
    coord = get_coordination_service()
    tasks = coord.list_tasks(scope, owner_agent_id=owner_agent_id, limit=limit)
    handoffs = coord.list_handoffs(scope, target_agent_id=owner_agent_id, limit=limit)
    return {
        "tenant_id": scope.tenant_id,
        "tasks": [t.model_dump(mode="json") for t in tasks],
        "handoffs": [h.model_dump(mode="json") for h in handoffs],
    }


@mcp.tool()
def list_procedures(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Lists procedural memories (trigger + ordered steps + confirmation status) in the tenant (FR-004).
    """
    scope = resolve_mcp_tenant_scope()
    proc_status = ProcedureStatus(status.upper()) if status else None
    procs = get_memory_service().list_procedures(scope, status=proc_status)
    return [p.model_dump(mode="json") for p in procs]


@mcp.tool()
def confirm_procedure(procedure_id: str) -> Dict[str, Any]:
    """
    Explicitly confirms a proposed procedure in the active tenant scope (BR-003).
    """
    scope = resolve_mcp_tenant_scope()
    proc = get_memory_service().confirm_procedure(scope, procedure_id)
    return proc.model_dump(mode="json")


if __name__ == "__main__":
    mcp.run(transport="stdio")