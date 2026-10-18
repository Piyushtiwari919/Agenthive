import hashlib
import hmac
import re
from typing import Optional

from fastapi import Depends, Header, Query

from app.config import Settings, get_settings
from app.core.errors import AgentHiveError, TenantAccessDeniedError
from app.domain.tenant import TenantScope

TENANT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,62}$")


def validate_tenant_id_format(tenant_id: str) -> str:
    if not tenant_id or not isinstance(tenant_id, str):
        raise TenantAccessDeniedError("Tenant identifier is required.")
    candidate = tenant_id.strip().lower()
    if not TENANT_ID_PATTERN.match(candidate):
        raise TenantAccessDeniedError(
            "Invalid tenant identifier format. Must be 2-63 lowercase alphanumeric, hyphen, or underscore characters."
        )
    return candidate


def derive_opaque_graph_name(tenant_id: str) -> str:
    """
    Deterministically derives a safe, opaque FalkorDB graph name from a validated tenant_id.
    Never interpolates raw user input into the graph name.
    """
    validated = validate_tenant_id_format(tenant_id)
    digest = hashlib.sha256(f"agenthive::tenant::{validated}".encode("utf-8")).hexdigest()[:16]
    return f"ah_tenant_{digest}"


def resolve_tenant_scope(
    x_tenant_id: Optional[str] = Header(default=None, alias="X-Tenant-ID"),
    x_tenant_token: Optional[str] = Header(default=None, alias="X-Tenant-Token"),
    tenant_id_query: Optional[str] = Query(default=None, alias="tenant_id"),
    settings: Settings = Depends(get_settings),
) -> TenantScope:
    """
    Central FastAPI dependency that resolves and validates the server-side TenantScope
    before any service or repository call executes (BR-001, FR-014, NFR-005).
    """
    if x_tenant_id and tenant_id_query and x_tenant_id.strip().lower() != tenant_id_query.strip().lower():
        raise TenantAccessDeniedError(
            "Conflicting tenant identifiers supplied in X-Tenant-ID header and tenant_id query parameter."
        )

    raw_tenant = x_tenant_id or tenant_id_query
    if not raw_tenant:
        raise TenantAccessDeniedError(
            "Missing tenant scope. Provide the 'X-Tenant-ID' header (or 'tenant_id' parameter for SSE streams)."
        )

    clean_tenant_id = validate_tenant_id_format(raw_tenant)

    if settings.agenthive_env == "production":
        expected_token = settings.production_tenant_tokens.get(clean_tenant_id)
        if not expected_token or not x_tenant_token:
            raise TenantAccessDeniedError(
                "Missing or invalid tenant authentication token for production mode.",
                status_code=401,
            )
        if not hmac.compare_digest(expected_token, x_tenant_token):
            raise TenantAccessDeniedError(
                "Tenant authentication token mismatch.",
                status_code=403,
            )

    from app.repositories.control_repository import get_control_repository

    control_repo = get_control_repository()
    tenant_record = control_repo.get_tenant(clean_tenant_id)
    if tenant_record is None:
        raise TenantAccessDeniedError(
            f"Tenant '{clean_tenant_id}' is not registered. Provision it first via POST /api/v1/tenants."
        )

    expected_graph = derive_opaque_graph_name(clean_tenant_id)
    if tenant_record.graph_name != expected_graph:
        raise AgentHiveError(
            message="Tenant graph integrity check failed.",
            code="TENANT_GRAPH_MISMATCH",
            status_code=500,
        )

    return TenantScope(
        tenant_id=clean_tenant_id,
        graph_name=expected_graph,
        display_name=tenant_record.display_name,
        is_demo=tenant_record.is_demo,
    )