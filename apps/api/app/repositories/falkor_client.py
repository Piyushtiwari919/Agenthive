import logging
from typing import Any, Dict, List, Optional, Set
from falkordb import FalkorDB, Graph

from app.config import get_settings
from app.core.errors import DatabaseUnavailableError

logger = logging.getLogger(__name__)


class FalkorClientManager:
    """
    Centralized connection lifecycle and schema/index manager for FalkorDB (C-01).
    Automatically negotiates TLS/non-TLS and ACL username variations for FalkorDB Cloud.
    """

    def __init__(self) -> None:
        self._client: Optional[FalkorDB] = None
        self._initialized_graphs: Set[str] = set()

    def _connect_with_auto_negotiation(self) -> FalkorDB:
        settings = get_settings()
        host = settings.falkordb_host.strip()
        # Strip accidental protocol or port if user pasted host:port into FALKORDB_HOST
        if "://" in host:
            host = host.split("://", 1)[1]
        if ":" in host:
            host = host.split(":", 1)[0]

        port = int(settings.falkordb_port)
        password = settings.falkordb_password.strip() if settings.falkordb_password else None
        configured_user = settings.falkordb_username.strip() if settings.falkordb_username else None

        # Candidate usernames to try if authentication is enabled
        user_candidates: List[Optional[str]] = []
        for u in (configured_user, "falkordb", "default", None):
            if u not in user_candidates:
                user_candidates.append(u)

        # Candidate SSL modes: try configured first, then the opposite
        ssl_candidates = [settings.falkordb_ssl, not settings.falkordb_ssl]

        last_error: Optional[Exception] = None

        for use_ssl in ssl_candidates:
            for username in user_candidates:
                kwargs: Dict[str, Any] = {
                    "host": host,
                    "port": port,
                    "ssl": use_ssl,
                    "socket_connect_timeout": 4.0,
                    "socket_timeout": 10.0,
                }
                if use_ssl:
                    kwargs["ssl_cert_reqs"] = None
                if username:
                    kwargs["username"] = username
                if password:
                    kwargs["password"] = password

                try:
                    candidate_client = FalkorDB(**kwargs)
                    test_graph = candidate_client.select_graph(settings.falkordb_control_graph)
                    res = test_graph.ro_query("RETURN 1 AS ok")
                    if res.result_set and res.result_set[0][0] == 1:
                        logger.info(
                            "Connected to FalkorDB successfully",
                            extra={
                                "operation": "falkor_connect",
                                "outcome": f"host={host}:{port} ssl={use_ssl} user={username or 'none'}",
                            },
                        )
                        return candidate_client
                except Exception as exc:
                    last_error = exc
                    continue

        err_type = last_error.__class__.__name__ if last_error else "ConnectionError"
        err_msg = str(last_error) if last_error else "Unable to reach FalkorDB host."
        raise DatabaseUnavailableError(
            message="FalkorDB health check failed. Memory operations are unavailable without FalkorDB (C-01).",
        ) from last_error

    def _get_driver(self) -> FalkorDB:
        if self._client is None:
            self._client = self._connect_with_auto_negotiation()
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
        except DatabaseUnavailableError as exc:
            self._client = None
            cause = exc.__cause__
            if cause is not None:
                exc.details = {
                    "host": get_settings().falkordb_host,
                    "port": get_settings().falkordb_port,
                    "reason": f"{cause.__class__.__name__}: {str(cause)}",
                }
            raise
        except Exception as exc:
            self._client = None
            err = DatabaseUnavailableError(
                "FalkorDB health check failed. Memory operations are unavailable without FalkorDB (C-01)."
            )
            err.details = {
                "host": get_settings().falkordb_host,
                "port": get_settings().falkordb_port,
                "reason": f"{exc.__class__.__name__}: {str(exc)}",
            }
            raise err from exc

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
        for stmt in ("CREATE INDEX FOR (t:Tenant) ON (t.tenant_id)",):
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
