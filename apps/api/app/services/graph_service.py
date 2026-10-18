from functools import lru_cache

from app.domain.graph_view import GraphSubgraphResponse, OverviewMetricsDTO
from app.domain.tenant import TenantScope
from app.repositories.graph_viz_repository import get_graph_viz_repository


class GraphService:
    def get_metrics(self, scope: TenantScope) -> OverviewMetricsDTO:
        return get_graph_viz_repository().get_overview_metrics(scope)

    def get_subgraph(self, scope: TenantScope, max_episodes: int = 40) -> GraphSubgraphResponse:
        return get_graph_viz_repository().get_subgraph(scope, max_episodes=max_episodes)


@lru_cache()
def get_graph_service() -> GraphService:
    return GraphService()