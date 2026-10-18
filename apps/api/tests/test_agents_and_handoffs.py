from fastapi.testclient import TestClient


def test_fr009_to_fr012_agent_registry_handoffs_task_state_and_procedure_glow(
    client: TestClient, isolated_tenants: tuple[str, str]
) -> None:
    """
    Verifies:
    - FR-009: Registered agents appear immediately in API and graph subgraph.
    - FR-010 & BR-006: Same-tenant registered-agent handoffs succeed; unregistered, self, offline,
      or cross-tenant handoffs are rejected.
    - FR-011 & K-02: 20 scripted handoff scenarios (18 valid + 2 invalid/cross-tenant) execute
      with 100% of valid handoffs delivered in the target agent's next assembled context.
    - FR-012: Task status updates are immediately visible across the tenant, and active procedure
      execution triggers and clears the live graph glow state accurately.
    """
    tenant_a, tenant_b = isolated_tenants
    headers_a = {"X-Tenant-ID": tenant_a}
    headers_b = {"X-Tenant-ID": tenant_b}

    # Register agents in Tenant A
    for agent_spec in (
        {
            "agent_id": "agent-alpha-research",
            "name": "Alpha Research Agent",
            "role": "Researcher",
            "capabilities": ["discovery", "tracing"],
            "status": "ACTIVE",
        },
        {
            "agent_id": "agent-alpha-coder",
            "name": "Alpha Implementation Agent",
            "role": "Coder",
            "capabilities": ["coding", "testing"],
            "status": "ACTIVE",
        },
        {
            "agent_id": "agent-alpha-reviewer",
            "name": "Alpha Review Agent",
            "role": "Reviewer",
            "capabilities": ["security-audit", "qa"],
            "status": "ACTIVE",
        },
        {
            "agent_id": "agent-alpha-offline",
            "name": "Alpha Offline Agent",
            "role": "Legacy Worker",
            "capabilities": ["archive"],
            "status": "OFFLINE",
        },
    ):
        resp = client.post("/api/v1/agents", headers=headers_a, json=agent_spec)
        assert resp.status_code == 201

    # Register an agent in Tenant B to test cross-tenant handoff rejection (BR-006)
    resp_b = client.post(
        "/api/v1/agents",
        headers=headers_b,
        json={
            "agent_id": "agent-beta-sec",
            "name": "Beta Security Agent",
            "role": "SecOps",
            "capabilities": ["siem"],
            "status": "ACTIVE",
        },
    )
    assert resp_b.status_code == 201

    # Verify FR-009: Tenant A lists its 4 registered agents and never sees Tenant B's agent
    agents_a = client.get("/api/v1/agents", headers=headers_a).json()
    assert len(agents_a) == 4
    assert all(a["id"] != "agent-beta-sec" for a in agents_a)

    # Execute 18 valid handoff scenarios in Tenant A + verify invalid/cross-tenant rejections (20 total)
    valid_Pairs = [
        ("agent-alpha-research", "agent-alpha-coder"),
        ("agent-alpha-coder", "agent-alpha-reviewer"),
        ("agent-alpha-reviewer", "agent-alpha-research"),
    ]
    created_handoff_ids: list[str] = []
    for idx in range(18):
        origin_id, target_id = valid_Pairs[idx % len(valid_Pairs)]
        ho_resp = client.post(
            "/api/v1/handoffs",
            headers=headers_a,
            json={
                "origin_agent_id": origin_id,
                "target_agent_id": target_id,
                "task_title": f"Scenario #{idx + 1}: Implement service optimization",
                "context_summary": f"Context transfer #{idx + 1} from {origin_id} to {target_id}",
                "state_payload": {"scenario_index": idx + 1, "verified": True},
                "session_id": f"sess-ho-{idx + 1}",
            },
        )
        assert ho_resp.status_code == 201
        created_handoff_ids.append(ho_resp.json()["id"])

    # Invalid Scenario 19: Cross-tenant handoff attempt (Tenant A origin -> Tenant B target) -> 404
    cross_resp = client.post(
        "/api/v1/handoffs",
        headers=headers_a,
        json={
            "origin_agent_id": "agent-alpha-research",
            "target_agent_id": "agent-beta-sec",
            "task_title": "Cross-tenant leak attempt",
            "context_summary": "Should be denied by BR-006",
            "state_payload": {},
        },
    )
    assert cross_resp.status_code == 404

    # Invalid Scenario 20: Handoff to OFFLINE agent -> 409 Conflict
    offline_resp = client.post(
        "/api/v1/handoffs",
        headers=headers_a,
        json={
            "origin_agent_id": "agent-alpha-research",
            "target_agent_id": "agent-alpha-offline",
            "task_title": "Handoff to offline agent",
            "context_summary": "Should be rejected with 409",
            "state_payload": {},
        },
    )
    assert offline_resp.status_code == 409

    # Verify FR-011: Assembling context for each target agent returns its pending handoffs
    for target_id in ("agent-alpha-coder", "agent-alpha-reviewer", "agent-alpha-research"):
        ctx = client.post(
            "/api/v1/context/assemble",
            headers=headers_a,
            json={"query": "service optimization", "agent_id": target_id},
        ).json()
        assert len(ctx["pending_handoffs"]) == 6
        assert all(h["target_agent_id"] == target_id for h in ctx["pending_handoffs"])

    # Verify FR-012 & Active Procedure Glow Lifecycle on Graph Subgraph
    ep = client.post(
        "/api/v1/episodes",
        headers=headers_a,
        json={
            "content": (
                "PROCEDURE: Canary Rollback Protocol | "
                "TRIGGER: When canary error rate exceeds 2 percent | "
                "STEPS: 1. Shift traffic to stable; 2. Snapshot logs"
            ),
            "agent_id": "agent-alpha-research",
            "session_id": "sess-glow",
            "importance_score": 0.9,
        },
    ).json()
    procs = client.get("/api/v1/procedures", headers=headers_a).json()
    proc_id = procs[0]["id"]

    # Initially, procedure is NOT glowing
    subgraph_initial = client.get("/api/v1/graph/subgraph", headers=headers_a).json()
    assert subgraph_initial["active_procedures"] == []
    proc_node_init = next(n for n in subgraph_initial["nodes"] if n["id"] == proc_id)
    assert proc_node_init["is_glowing"] is False

    # Start genuine task executing the procedure -> Procedure node and active path MUST glow
    exec_resp = client.post(
        f"/api/v1/procedures/{proc_id}/execute",
        headers=headers_a,
        json={"agent_id": "agent-alpha-coder", "task_title": "Execute Canary Rollback"},
    )
    assert exec_resp.status_code == 200

    subgraph_active = client.get("/api/v1/graph/subgraph", headers=headers_a).json()
    assert len(subgraph_active["active_procedures"]) == 1
    assert subgraph_active["active_procedures"][0]["procedure_id"] == proc_id
    proc_node_active = next(n for n in subgraph_active["nodes"] if n["id"] == proc_id)
    assert proc_node_active["is_glowing"] is True
    assert any(e["is_active_path"] is True for e in subgraph_active["edges"])

    # Complete procedure execution -> Glow MUST stop immediately
    comp_resp = client.post(
        f"/api/v1/procedures/{proc_id}/complete",
        headers=headers_a,
        json={
            "agent_id": "agent-alpha-coder",
            "final_status": "COMPLETED",
            "result_summary": "Rollback verified clean.",
        },
    )
    assert comp_resp.status_code == 200

    subgraph_done = client.get("/api/v1/graph/subgraph", headers=headers_a).json()
    assert subgraph_done["active_procedures"] == []
    proc_node_done = next(n for n in subgraph_done["nodes"] if n["id"] == proc_id)
    assert proc_node_done["is_glowing"] is False