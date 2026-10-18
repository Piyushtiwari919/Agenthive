from fastapi.testclient import TestClient
from app.core.errors import DatabaseUnavailableError
from app.repositories.falkor_client import falkor_manager


def test_health_and_readiness(client: TestClient) -> None:
    """Verifies Phase 0 /health and /ready endpoints against live FalkorDB."""
    r_health = client.get("/api/v1/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "ok"

    r_ready = client.get("/api/v1/ready")
    assert r_ready.status_code == 200
    body = r_ready.json()
    assert body["status"] == "ready"
    assert body["database"] == "falkordb"
    assert body["database_connected"] is True


def test_falkordb_removal_fails_closed_503(client: TestClient, monkeypatch) -> None:
    """
    Verifies Sponsor Rule C-01 / K-09: If FalkorDB is unavailable, AgentHive fails closed
    with HTTP 503 and never serves hidden in-memory fallback data.
    """
    def _broken_ping() -> bool:
        raise DatabaseUnavailableError("Simulated FalkorDB container outage (C-01 removal test)")

    monkeypatch.setattr(falkor_manager, "ping", _broken_ping)
    r_ready = client.get("/api/v1/ready")
    assert r_ready.status_code == 503
    assert r_ready.json()["error"]["code"] == "FALKORDB_UNAVAILABLE"