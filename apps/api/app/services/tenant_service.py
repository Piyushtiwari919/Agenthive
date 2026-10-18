from functools import lru_cache
from typing import List

from app.domain.tenant import TenantCreateRequest, TenantInfo
from app.repositories.control_repository import get_control_repository


class TenantService:
    def provision_tenant(self, req: TenantCreateRequest) -> TenantInfo:
        return get_control_repository().create_or_update_tenant(req)

    def list_tenants(self) -> List[TenantInfo]:
        return get_control_repository().list_tenants()

    def ensure_demo_tenants(self) -> List[TenantInfo]:
        return get_control_repository().ensure_default_demo_tenants()


@lru_cache()
def get_tenant_service() -> TenantService:
    return TenantService()