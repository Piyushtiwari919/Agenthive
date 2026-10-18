from datetime import datetime, timezone
from functools import lru_cache
from typing import List, Optional

from app.core.security import derive_opaque_graph_name, validate_tenant_id_format
from app.domain.tenant import TenantCreateRequest, TenantInfo
from app.repositories import cypher_catalog
from app.repositories.falkor_client import falkor_manager


class ControlRepository:
    """
    Manages the ah_control registry graph for tenant provisioning and lookup (FR-013).
    """

    def create_or_update_tenant(self, req: TenantCreateRequest) -> TenantInfo:
        clean_id = validate_tenant_id_format(req.tenant_id)
        graph_name = derive_opaque_graph_name(clean_id)
        now_iso = datetime.now(timezone.utc).isoformat()

        control_graph = falkor_manager.select_control_graph()
        rows = falkor_manager.query(
            control_graph,
            cypher_catalog.UPSERT_TENANT,
            params={
                "tenant_id": clean_id,
                "display_name": req.display_name.strip(),
                "description": req.description or "",
                "graph_name": graph_name,
                "is_demo": bool(req.is_demo),
                "created_at": now_iso,
            },
        )
        # Immediately initialize indexes on the isolated tenant graph
        falkor_manager.select_tenant_graph(graph_name)
        return self._row_to_tenant(rows[0])

    def get_tenant(self, tenant_id: str) -> Optional[TenantInfo]:
        clean_id = validate_tenant_id_format(tenant_id)
        control_graph = falkor_manager.select_control_graph()
        rows = falkor_manager.ro_query(
            control_graph,
            cypher_catalog.GET_TENANT,
            params={"tenant_id": clean_id},
        )
        if not rows:
            return None
        return self._row_to_tenant(rows[0])

    def list_tenants(self) -> List[TenantInfo]:
        control_graph = falkor_manager.select_control_graph()
        rows = falkor_manager.ro_query(control_graph, cypher_catalog.LIST_TENANTS)
        return [self._row_to_tenant(r) for r in rows]

    def ensure_default_demo_tenants(self) -> List[TenantInfo]:
        demo_specs = [
            TenantCreateRequest(
                tenant_id="alpha-eng",
                display_name="Tenant A — Alpha Core Engineering",
                description="Platform & Payments Engineering Team (Research + Implementation Agents)",
                is_demo=True,
            ),
            TenantCreateRequest(
                tenant_id="beta-sec",
                display_name="Tenant B — Beta Cloud Security",
                description="Zero-Trust Security Operations Team (Threat Intel + Remediation Agents)",
                is_demo=True,
            ),
        ]
        results: List[TenantInfo] = []
        for spec in demo_specs:
            existing = self.get_tenant(spec.tenant_id)
            if existing is None:
                results.append(self.create_or_update_tenant(spec))
            else:
                results.append(existing)
        return results

    @staticmethod
    def _row_to_tenant(row: list) -> TenantInfo:
        return TenantInfo(
            tenant_id=str(row[0]),
            display_name=str(row[1]),
            description=str(row[2]) if row[2] else None,
            graph_name=str(row[3]),
            is_demo=bool(row[4]),
            created_at=datetime.fromisoformat(str(row[5])),
        )


@lru_cache()
def get_control_repository() -> ControlRepository:
    return ControlRepository()