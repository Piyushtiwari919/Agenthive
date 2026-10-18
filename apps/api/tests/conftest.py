from collections.abc import Generator
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.falkor_client import falkor_manager
from app.workers.extraction_worker import extraction_orchestrator


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def isolated_tenants(client: TestClient) -> Generator[tuple[str, str], None, None]:
    """
    Provisions two fresh, completely isolated tenants in FalkorDB for each test run.
    """
    extraction_orchestrator.set_simulate_outage(False)
    suffix = uuid.uuid4().hex[:8]
    tenant_a = f"test-alpha-{suffix}"
    tenant_b = f"test-beta-{suffix}"

    resp_a = client.post(
        "/api/v1/tenants",
        json={
            "tenant_id": tenant_a,
            "display_name": f"Test Tenant Alpha {suffix}",
            "description": "Isolated test tenant A",
            "is_demo": False,
        },
    )
    assert resp_a.status_code == 201

    resp_b = client.post(
        "/api/v1/tenants",
        json={
            "tenant_id": tenant_b,
            "display_name": f"Test Tenant Beta {suffix}",
            "description": "Isolated test tenant B",
            "is_demo": False,
        },
    )
    assert resp_b.status_code == 201

    yield tenant_a, tenant_b

    # Cleanup ephemeral test tenant graphs
    try:
        driver = falkor_manager._get_driver()
        for t_id in (tenant_a, tenant_b):
            from app.core.security import derive_opaque_graph_name
            g = driver.select_graph(derive_opaque_graph_name(t_id))
            g.delete()
    except Exception:
        pass