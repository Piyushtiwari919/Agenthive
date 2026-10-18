from fastapi import APIRouter, Depends, Query

from app.core.security import resolve_tenant_scope
from app.domain.graph_view import GraphSubgraphResponse, OverviewMetricsDTO
from app.domain.tenant import TenantScope
from app.services.graph_service import get_graph_service

router = APIRouter(prefix="/graph", tags=["FalkorDB Graph Visualization"])


@router.get("/metrics", response_model=OverviewMetricsDTO)
def get_overview_metrics(
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> OverviewMetricsDTO:
    return get_graph_service().get_metrics(scope)


@router.get("/subgraph", response_model=GraphSubgraphResponse)
def get_tenant_subgraph(
    max_episodes: int = Query(default=40, ge=5, le=200),
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> GraphSubgraphResponse:
    """
    Returns live FalkorDB nodes, relationships, and active procedure glow state for the selected tenant (FR-015).
    """
    return get_graph_service().get_subgraph(scope, max_episodes=max_episodes)
