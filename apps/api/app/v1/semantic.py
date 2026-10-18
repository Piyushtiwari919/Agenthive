from typing import List, Optional
from fastapi import APIRouter, Depends, Query

from app.core.security import resolve_tenant_scope
from app.domain.memory import EntityRecord, FactRecord, ProvenanceResponse
from app.domain.tenant import TenantScope
from app.services.memory_service import get_memory_service

router = APIRouter(tags=["Semantic Memory & Provenance"])


@router.get("/entities", response_model=List[EntityRecord])
def list_entities(
    entity_type: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> List[EntityRecord]:
    return get_memory_service().list_entities(
        scope=scope, entity_type=entity_type, search=search, limit=limit
    )


@router.get("/entities/{entity_id}", response_model=EntityRecord)
def get_entity(
    entity_id: str,
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> EntityRecord:
    return get_memory_service().get_entity(scope, entity_id)


@router.get("/facts", response_model=List[FactRecord])
def list_facts(
    subject_entity_id: Optional[str] = Query(default=None),
    include_superseded: bool = Query(default=True),
    limit: int = Query(default=200, ge=1, le=500),
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> List[FactRecord]:
    return get_memory_service().list_facts(
        scope=scope,
        subject_entity_id=subject_entity_id,
        include_superseded=include_superseded,
        limit=limit,
    )


@router.get("/provenance/{target_id}", response_model=ProvenanceResponse)
def get_provenance(
    target_id: str,
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> ProvenanceResponse:
    """
    Returns source episode provenance for any Fact, Procedure, Entity, or Episode ID (FR-008, BR-002).
    """
    return get_memory_service().get_provenance(scope, target_id)