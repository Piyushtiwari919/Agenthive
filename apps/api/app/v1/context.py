from fastapi import APIRouter, Depends

from app.core.security import resolve_tenant_scope
from app.domain.context import AssembledContextPackage, ContextAssembleRequest
from app.domain.tenant import TenantScope
from app.services.context_service import get_context_service

router = APIRouter(prefix="/context", tags=["Unified Context Assembly"])


@router.post("/assemble", response_model=AssembledContextPackage)
def assemble_context(
    req: ContextAssembleRequest,
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> AssembledContextPackage:
    """
    Returns a single unified context package containing ranked episodes, extracted entities/facts,
    applicable procedures, and pending handoffs with source provenance (FR-006, FR-007, FR-008, FR-011).
    """
    return get_context_service().assemble_context(scope, req)
