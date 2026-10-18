from fastapi.testclient import TestClient


def test_fr013_and_fr014_ten_case_adversarial_tenant_isolation_suite(
    client: TestClient, isolated_tenants: tuple[str, str]
) -> None:
    """
    Verifies FR-013, FR-014, NFR-005, and BR-001 across 10 adversarial cross-tenant test cases:
    1. Newly provisioned tenant starts with 0 episodes, entities, facts, procedures, agents, handoffs.
    2. Direct Episode ID lookup across tenants returns 404 (zero leakage).
    3. Direct Entity ID & Provenance lookup across tenants returns 404.
    4. Session history lookup of Tenant A's session_id from Tenant B returns 0 episodes.
    5. Unified Context Assembly (/context/assemble) in Tenant B returns 0 records for Tenant A's secret terms.
    6. Graph Visualization (/graph/subgraph) in Tenant B returns 0 nodes/edges from Tenant A.
    7. Cross-tenant Handoff creation & Handoff ID access from Tenant B returns 404.
    8. Confirming or executing Tenant A's procedure from Tenant B returns 404.
    9. Parameter pollution (Header X-Tenant-ID vs query tenant_id) is rejected with 403.
    10. Crafted/injection tenant IDs (Cypher injection / control graph access) are rejected with 403.
    """
    tenant_a, tenant_b = isolated_tenants
    headers_a = {"X-Tenant-ID": tenant_a}
    headers_b = {"X-Tenant-ID": tenant_b}

    # Case 1: Newly provisioned Tenant B starts completely empty (FR-013)
    assert client.get("/api/v1/episodes", headers=headers_b).json() == []
    assert client.get("/api/v1/entities", headers=headers_b).json() == []
    assert client.get("/api/v1/facts", headers=headers_b).json() == []
    assert client.get("/api/v1/procedures", headers=headers_b).json() == []
    assert client.get("/api/v1/agents", headers=headers_b).json() == []
    assert client.get("/api/v1/handoffs", headers=headers_b).json() == []

    # Seed confidential Episode, Entity, Fact, Procedure, Agents, and Handoff into Tenant A
    client.post(
        "/api/v1/agents",
        headers=headers_a,
        json={"agent_id": "ag-a1", "name": "Alpha 1", "role": "Research", "capabilities": ["read"]},
    )
    client.post(
        "/api/v1/agents",
        headers=headers_a,
        json={"agent_id": "ag-a2", "name": "Alpha 2", "role": "Code", "capabilities": ["write"]},
    )
    ho_a = client.post(
        "/api/v1/handoffs",
        headers=headers_a,
        json={
            "origin_agent_id": "ag-a1",
            "target_agent_id": "ag-a2",
            "task_title": "Alpha Secret Task",
            "context_summary": "Confidential handoff payload",
            "state_payload": {"secret_key": "ALPHA_ONLY"},
        },
    ).json()

    ep_a_resp = client.post(
        "/api/v1/episodes",
        headers=headers_a,
        json={
            "content": (
                "Tenant A confidential architecture. FACT: TokenVault encryption_mode = AES-256-GCM. "
                "PROCEDURE: Emergency TokenVault Seal | TRIGGER: When TokenVault anomaly detected | "
                "STEPS: 1. Revoke root lease; 2. Seal vault nodes"
            ),
            "agent_id": "ag-a1",
            "session_id": "sess-secret-alpha",
            "importance_score": 0.95,
        },
    )
    assert ep_a_resp.status_code == 201
    ep_a_id = ep_a_resp.json()["id"]

    entities_a = client.get("/api/v1/entities", headers=headers_a).json()
    facts_a = client.get("/api/v1/facts", headers=headers_a).json()
    procs_a = client.get("/api/v1/procedures", headers=headers_a).json()
    ent_a_id = entities_a[0]["id"]
    fact_a_id = facts_a[0]["id"]
    proc_a_id = procs_a[0]["id"]

    # Case 2: Tenant B attempts direct Episode ID fetch of Tenant A's episode -> 404
    assert client.get(f"/api/v1/episodes/{ep_a_id}", headers=headers_b).status_code == 404

    # Case 3: Tenant B attempts direct Entity ID & Fact Provenance fetch -> 404
    assert client.get(f"/api/v1/entities/{ent_a_id}", headers=headers_b).status_code == 404
    assert client.get(f"/api/v1/provenance/{fact_a_id}", headers=headers_b).status_code == 404

    # Case 4: Tenant B requests Tenant A's session history -> 0 episodes
    hist_b = client.get("/api/v1/sessions/sess-secret-alpha/history", headers=headers_b).json()
    assert hist_b["total_episodes"] == 0
    assert hist_b["episodes"] == []

    # Case 5: Tenant B calls /context/assemble searching for Tenant A's secret terms -> 0 results
    ctx_b = client.post(
        "/api/v1/context/assemble",
        headers=headers_b,
        json={"query": "TokenVault AES-256-GCM Emergency Seal", "agent_id": "ag-a2"},
    ).json()
    assert ctx_b["episodes"] == []
    assert ctx_b["entities"] == []
    assert ctx_b["facts"] == []
    assert ctx_b["procedures"] == []
    assert ctx_b["pending_handoffs"] == []

    # Case 6: Tenant B calls /graph/subgraph -> 0 nodes and 0 edges from Tenant A
    graph_b = client.get("/api/v1/graph/subgraph", headers=headers_b).json()
    assert graph_b["nodes"] == []
    assert graph_b["edges"] == []
    assert graph_b["metrics"]["episode_count"] == 0

    # Case 7: Tenant B attempts to fetch or update Tenant A's Handoff ID -> 404
    assert client.get(f"/api/v1/handoffs/{ho_a['id']}", headers=headers_b).status_code == 404
    assert (
        client.patch(
            f"/api/v1/handoffs/{ho_a['id']}/status",
            headers=headers_b,
            json={"status": "ACCEPTED", "acting_agent_id": "ag-a2"},
        ).status_code
        == 404
    )

    # Case 8: Tenant B attempts to confirm or execute Tenant A's procedure -> 404
    assert (
        client.post(f"/api/v1/procedures/{proc_a_id}/confirm", headers=headers_b).status_code == 404
    )
    assert (
        client.post(
            f"/api/v1/procedures/{proc_a_id}/execute",
            headers=headers_b,
            json={"agent_id": "ag-a2"},
        ).status_code
        == 404
    )

    # Case 9: Parameter pollution (Header says Tenant B, query param says Tenant A) -> 403
    polluted = client.get(f"/api/v1/episodes?tenant_id={tenant_a}", headers=headers_b)
    assert polluted.status_code == 403

    # Case 10: Crafted Cypher / control graph access headers -> 403
    for malicious_tenant in ("alpha-eng' OR 1=1--", "../ah_control", "ah_control", ""):
        bad_resp = client.get("/api/v1/episodes", headers={"X-Tenant-ID": malicious_tenant})
        assert bad_resp.status_code == 403
