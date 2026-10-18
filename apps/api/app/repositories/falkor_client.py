import logging
from typing import Any, Dict, List, Optional, Set
from falkordb import FalkorDB, Graph

from app.config import get_settings
from app.core.errors import DatabaseUnavailableError

logger = logging.getLogger(__name__)


class FalkorClientManager:
    """
    Centralized connection lifecycle and schema/index manager for FalkorDB (C-01).
    Supports both self-hosted Docker FalkorDB and FalkorDB Cloud Free Tier (A-01).
    """

    def __init__(self) -> None:
        self._client: Optional[FalkorDB] = None
        self._initialized_graphs: Set[str] = set()

    def _get_driver(self) -> FalkorDB:
        settings = get_settings()
        if self._client is None:
            kwargs: Dict[str, Any] = {
                "host": settings.falkordb_host,
                "port": settings.falkordb_port,
                "ssl": settings.falkordb_ssl,
                "socket_connect_timeout": 3.0,
                "socket_timeout": 10.0,
            }
            if settings.falkordb_username:
                kwargs["username"] = settings.falkordb_username
            if settings.falkordb_password:
                kwargs["password"] = settings.falkordb_password
            try:
                self._client = FalkorDB(**kwargs)
            except Exception as exc:
                self._client = None
                raise DatabaseUnavailableError(
                    f"Failed to initialize FalkorDB driver at {settings.falkordb_host}:{settings.falkordb_port}"
                ) from exc
        return self._client

    def reset_connection(self) -> None:
        self._client = None
        self._initialized_graphs.clear()

    def ping(self) -> bool:
        try:
            driver = self._get_driver()
            control_graph = driver.select_graph(get_settings().falkordb_control_graph)
            res = control_graph.ro_query("RETURN 1 AS ok")
            return bool(res.result_set and res.result_set[0][0] == 1)
        except Exception as exc:
            self._client = None
            raise DatabaseUnavailableError(
                "FalkorDB health check failed. Memory operations are unavailable without FalkorDB (C-01)."
            ) from exc

    def select_control_graph(self) -> Graph:
        try:
            driver = self._get_driver()
            graph_name = get_settings().falkordb_control_graph
            graph = driver.select_graph(graph_name)
            if graph_name not in self._initialized_graphs:
                self._ensure_control_indexes(graph)
                self._initialized_graphs.add(graph_name)
            return graph
        except DatabaseUnavailableError:
            raise
        except Exception as exc:
            self._client = None
            raise DatabaseUnavailableError("Unable to access FalkorDB control graph.") from exc

    def select_tenant_graph(self, graph_name: str) -> Graph:
        if not graph_name.startswith("ah_tenant_"):
            raise ValueError(f"Refusing to select non-tenant graph name: {graph_name}")
        try:
            driver = self._get_driver()
            graph = driver.select_graph(graph_name)
            if graph_name not in self._initialized_graphs:
                self._ensure_tenant_indexes(graph)
                self._initialized_graphs.add(graph_name)
            return graph
        except DatabaseUnavailableError:
            raise
        except Exception as exc:
            self._client = None
            raise DatabaseUnavailableError("Unable to access FalkorDB tenant graph.") from exc

    def query(
        self, graph: Graph, cypher: str, params: Optional[Dict[str, Any]] = None
    ) -> List[List[Any]]:
        try:
            result = graph.query(cypher, params=params or {})
            return list(result.result_set) if result.result_set else []
        except Exception as exc:
            self._client = None
            raise DatabaseUnavailableError(
                f"FalkorDB write/query execution failed: {exc.__class__.__name__}"
            ) from exc

    def ro_query(
        self, graph: Graph, cypher: str, params: Optional[Dict[str, Any]] = None
    ) -> List[List[Any]]:
        try:
            result = graph.ro_query(cypher, params=params or {})
            return list(result.result_set) if result.result_set else []
        except Exception as exc:
            self._client = None
            raise DatabaseUnavailableError(
                f"FalkorDB read-only query execution failed: {exc.__class__.__name__}"
            ) from exc

    def _ensure_control_indexes(self, graph: Graph) -> None:
        index_statements = [
            "CREATE INDEX FOR (t:Tenant) ON (t.tenant_id)",
        ]
        for stmt in index_statements:
            try:
                graph.query(stmt)
            except Exception:
                pass

    def _ensure_tenant_indexes(self, graph: Graph) -> None:
        index_statements = [
            "CREATE INDEX FOR (e:Episode) ON (e.id)",
            "CREATE INDEX FOR (e:Episode) ON (e.session_id)",
            "CREATE INDEX FOR (e:Episode) ON (e.timestamp)",
            "CREATE INDEX FOR (s:Session) ON (s.id)",
            "CREATE INDEX FOR (en:Entity) ON (en.id)",
            "CREATE INDEX FOR (en:Entity) ON (en.canonical_key)",
            "CREATE INDEX FOR (f:Fact) ON (f.id)",
            "CREATE INDEX FOR (p:Procedure) ON (p.id)",
            "CREATE INDEX FOR (a:Agent) ON (a.id)",
            "CREATE INDEX FOR (h:Handoff) ON (h.id)",
            "CREATE INDEX FOR (t:Task) ON (t.id)",
            "CREATE INDEX FOR (j:ExtractionJob) ON (j.id)",
        ]
        for stmt in index_statements:
            try:
                graph.query(stmt)
            except Exception:
                pass


falkor_manager = FalkorClientManager()
