from functools import lru_cache
from typing import Dict, List

from app.domain.memory import FactRecord
from app.domain.tenant import TenantScope
from app.repositories import cypher_catalog
from app.repositories.falkor_client import falkor_manager
from app.repositories.memory_repository import get_memory_repository


class ContextRepository:
    """
    Executes bounded FalkorDB graph traversals to support hybrid graph + lexical context assembly
    (FR-006, FR-007, FR-008).
    """

    def find_episodes_mentioning_entities(
        self, scope: TenantScope, entity_ids: List[str]
    ) -> Dict[str, List[str]]:
        """
        Traverses (Episode)-[:MENTIONS]->(Entity) in FalkorDB to boost episodes connected to
        entities matched by the query.
        """
        if not entity_ids:
            return {}
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        rows = falkor_manager.ro_query(
            graph,
            cypher_catalog.FIND_EPISODES_MENTIONING_ENTITIES,
            params={"tenant_id": scope.tenant_id, "entity_ids": entity_ids},
        )
        mapping: Dict[str, List[str]] = {}
        for r in rows:
            ep_id = str(r[0])
            names = [str(x) for x in (r[1] or [])]
            mapping[ep_id] = names
        return mapping

    def find_connected_facts(
        self,
        scope: TenantScope,
        entity_ids: List[str],
        episode_ids: List[str],
        include_superseded: bool = False,
        limit: int = 20,
    ) -> List[FactRecord]:
        """
        Traverses Facts connected to matched Entities or top-ranked Episodes and attaches provenance.
        """
        if not entity_ids and not episode_ids:
            return []
        graph = falkor_manager.select_tenant_graph(scope.graph_name)
        mem_repo = get_memory_repository()
        rows = falkor_manager.ro_query(
            graph,
            cypher_catalog.FIND_FACTS_FOR_ENTITIES_OR_EPISODES,
            params={
                "tenant_id": scope.tenant_id,
                "entity_ids": entity_ids or ["__none__"],
                "episode_ids": episode_ids or ["__none__"],
                "include_superseded": bool(include_superseded),
                "limit": min(max(limit, 1), 50),
            },
        )
        facts = [mem_repo._row_to_fact(r) for r in rows]
        return mem_repo._attach_bulk_fact_provenance(scope, facts)


@lru_cache()
def get_context_repository() -> ContextRepository:
    return ContextRepository()