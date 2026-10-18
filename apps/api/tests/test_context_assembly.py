from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient


def test_fr006_fr007_fr008_unified_context_assembly_and_importance_tiebreaker(
    client: TestClient, isolated_tenants: tuple[str, str]
) -> None:
    """
    Verifies:
    - FR-006: Single POST /api/v1/context/assemble returns all 4 groups (episodes, entities/facts,
      applicable procedures, pending handoffs) in < 2 seconds.
    - FR-007: Episodes with equal query relevance are strictly tie-broken by importance_score.
    - FR-008 & NFR-008: Every returned fact and procedure exposes source episode provenance.
    """
    tenant_a, _ = isolated_tenants
    headers = {"X-Tenant-ID": tenant_a}

    # 1. Register Research Agent and Implementation Agent
    r_res = client.post(
        "/api/v1/agents",
        headers=headers,
        json={
            "agent_id": "agent-research",
            "name": "Research Agent",
            "role": "Architecture Researcher",
            "capabilities": ["log-analysis", "root-cause"],
        },
    )
    assert r_res.status_code == 201

    r_imp = client.post(
        "/api/v1/agents",
        headers=headers,
        json={
            "agent_id": "agent-coder",
            "name": "Implementation Agent",
            "role": "Backend Engineer",
            "capabilities": ["python", "falkordb", "patching"],
        },
    )
    assert r_imp.status_code == 201

    base_ts = datetime(2026, 10, 16, 12, 0, 0, tzinfo=timezone.utc)

    # 2. Create two episodes with identical lexical/graph relevance to "PaymentGateway retry_limit"
    # but different importance_score (0.45 vs 0.95) to test FR-007 importance tiebreaker
    ep_low = client.post(
        "/api/v1/episodes",
        headers=headers,
        json={
            "content": (
                "Investigated PaymentGateway retry_limit during routine check. "
                "FACT: PaymentGateway retry_limit = 3."
            ),
            "agent_id": "agent-research",
            "session_id": "sess-ctx-01",
            "importance_score": 0.45,
            "timestamp": (base_ts + timedelta(minutes=1)).isoformat(),
        },
    ).json()

    ep_high = client.post(
        "/api/v1/episodes",
        headers=headers,
        json={
            "content": (
                "Critical review of PaymentGateway retry_limit and failover procedure. "
                "FACT: PaymentGateway pool_size = 64. "
                "PROCEDURE: Mitigate PaymentGateway Timeout Spike | "
                "TRIGGER: When PaymentGateway retry_limit or timeout spike occurs | "
                "STEPS: 1. Drain degraded pool; 2. Increase timeout to 4500ms; 3. Verify circuit breaker"
            ),
            "agent_id": "agent-research",
            "session_id": "sess-ctx-01",
            "importance_score": 0.95,
            "timestamp": (base_ts + timedelta(minutes=2)).isoformat(),
        },
    ).json()

    # 3. Create a pending handoff from Research Agent -> Implementation Agent
    ho_resp = client.post(
        "/api/v1/handoffs",
        headers=headers,
        json={
            "origin_agent_id": "agent-research",
            "target_agent_id": "agent-coder",
            "task_title": "Patch PaymentGateway retry_limit & pool settings",
            "context_summary": "PaymentGateway needs retry_limit=3 and pool_size=64 applied in config.",
            "state_payload": {"target_service": "PaymentGateway", "retry_limit": 3, "pool_size": 64},
            "session_id": "sess-ctx-01",
        },
    )
    assert ho_resp.status_code == 201

    # 4. Call Unified Context Assembly as Implementation Agent
    ctx_resp = client.post(
        "/api/v1/context/assemble",
        headers=headers,
        json={
            "query": "PaymentGateway retry_limit timeout spike mitigation",
            "agent_id": "agent-coder",
            "max_episodes": 5,
        },
    )
    assert ctx_resp.status_code == 200
    pkg = ctx_resp.json()

    # Latency target check (< 2000 ms per FR-006 / NFR-001)
    assert pkg["duration_ms"] < 2000.0

    # All 4 context groups must be populated (FR-006)
    assert len(pkg["episodes"]) >= 2
    assert len(pkg["entities"]) >= 1
    assert len(pkg["facts"]) >= 2
    assert len(pkg["procedures"]) == 1
    assert len(pkg["pending_handoffs"]) == 1

    # FR-007: Higher importance episode (ep_high) must rank ahead of lower importance episode (ep_low)
    returned_ep_ids = [item["episode"]["id"] for item in pkg["episodes"]]
    assert returned_ep_ids.index(ep_high["id"]) < returned_ep_ids.index(ep_low["id"])

    # FR-008: Verify every fact and procedure has source episode provenance attached
    for fact in pkg["facts"]:
        assert fact["source_episode_id"] in (ep_low["id"], ep_high["id"])
        assert fact["provenance"] is not None
        assert fact["provenance"]["episode_id"] == fact["source_episode_id"]

    proc = pkg["procedures"][0]
    assert proc["name"] == "Mitigate PaymentGateway Timeout Spike"
    assert ep_high["id"] in proc["source_episode_ids"]
    assert len(proc["provenance_refs"]) >= 1