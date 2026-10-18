from typing import List
from fastapi import APIRouter, status

from app.domain.tenant import TenantCreateRequest, TenantInfo
from app.services.tenant_service import get_tenant_service

router = APIRouter(prefix="/tenants", tags=["Tenancy & Isolation"])


@router.get("", response_model=List[TenantInfo])
def list_tenants() -> List[TenantInfo]:
    return get_tenant_service().list_tenants()


@router.post("", response_model=TenantInfo, status_code=status.HTTP_201_CREATED)
def provision_tenant(req: TenantCreateRequest) -> TenantInfo:
    """
    Provisions isolated memory graph for a new user or tenant on demand (FR-013).
    """
    return get_tenant_service().provision_tenant(req)