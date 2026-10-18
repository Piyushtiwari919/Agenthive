from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TenantScope(BaseModel):
    tenant_id: str
    graph_name: str
    display_name: str
    is_demo: bool = False


class TenantCreateRequest(BaseModel):
    tenant_id: str = Field(..., min_length=2, max_length=63, pattern=r"^[a-z0-9][a-z0-9_-]{1,62}$")
    display_name: str = Field(..., min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    is_demo: bool = Field(default=False)


class TenantInfo(BaseModel):
    tenant_id: str
    display_name: str
    description: Optional[str] = None
    graph_name: str
    is_demo: bool = False
    created_at: datetime
    