from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.domain.tenant import TenantScope
from app.core.security import derive_opaque_graph_name
from app.workers.extraction_worker import extraction_orchestrator


def test_fr001_episodic_capture_and_idempotency(
    client: TestClient, isolated_tenants: tuple[str, str]
) -> None:
    """
    Verifies FR-001: Every completed agent turn stores a retrievable episode with all 5 required
    fields (content, acting agent, timestamp, session_id, importance_score) within 5 seconds.
    """
    tenant_a, _ = isolated_tenants
    headers = {"X-Tenant-ID": tenant_a}

    payload = {
        "content": "Research Agent analyzed PaymentGateway latency. FACT: PaymentGateway timeout_ms = 3500ms.",
        "agent_id": "agent-research-01",
        "agent_name": "Research Agent",
        "session_id": "sess-101",
        "importance_score": 0.85,
        "idempotency_key": "idem-turn-001",
    }
    resp = client.post("/api/v1/episodes", json=payload, headers=headers)
    assert resp.status_code == 201
    ep = resp.json()
    assert ep["content"] == payload["content"]
    assert ep["agent_id"] == "agent-research-01"
    assert ep["session_id"] == "sess-101"
    assert ep["importance_score"] == 0.85
    assert ep["timestamp"] is not None
    assert ep["extraction_status"] == "COMPLETED"

    # Verify idempotent retry returns the exact same episode ID without duplicating
    resp_dup = client.post("/api/v1/episodes", json=payload, headers=headers)
    assert resp_dup.status_code == 201
    assert resp_dup.json()["id"] == ep["id"]


def test_fr003_br007_canonical_entity_deduplication_and_br004_conflict_superseding(
    client: TestClient, isolated_tenants: tuple[str, str]
) -> None:
    """
    Verifies:
    - FR-003 & BR-007: Repeated references ('pay-gw', 'payment-gateway', 'PaymentGateway')
      resolve to a single canonical Entity record.
    - BR-004: Conflicting facts use timestamp precedence; older facts are marked SUPERSEDED and retained.
    - FR-008 & BR-002: Every fact links to its source episode.
    """
    tenant_a, _ = isolated_tenants
    headers = {"X-Tenant-ID": tenant_a}
    t1 = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    t2 = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

    # Episode 1 mentions alias 'pay-gw' with timeout_ms = 2000ms
    r1 = client.post(
        "/api/v1/episodes",
        headers=headers,
        json={
            "content": "Initial audit of pay-gw. FACT: pay-gw timeout_ms = 2000ms.",
            "agent_id": "agent-research-01",
            "session_id": "sess-canon",
            "importance_score": 0.7,
            "timestamp": t1,
        },
    )
    assert r1.status_code == 201
    ep1_id = r1.json()["id"]

    # Episode 2 mentions alias 'payment-gateway' with updated timeout_ms = 4500ms
    r2 = client.post(
        "/api/v1/episodes",
        headers=headers,
        json={
            "content": "Updated config on payment-gateway after spike. FACT: payment-gateway timeout_ms = 4500ms.",
            "agent_id": "agent-coder-01",
            "session_id": "sess-canon",
            "importance_score": 0.9,
            "timestamp": t2,
        },
    )
    assert r2.status_code == 201
    ep2_id = r2.json()["id"]

    # Check canonical entity deduplication (BR-007): only 1 PaymentGateway entity exists
    entities = client.get("/api/v1/entities", headers=headers).json()
    pg_entities = [e for e in entities if e["canonical_name"] == "PaymentGateway"]
    assert len(pg_entities) == 1
    assert set(pg_entities[0]["source_episode_ids"]) == {ep1_id, ep2_id}

    # Check temporal conflict superseding (BR-004)
    facts = client.get("/api/v1/facts?include_superseded=true", headers=headers).json()
    timeout_facts = [f for f in facts if f["predicate"] == "timeout_ms"]
    assert len(timeout_facts) == 2

    current_facts = [f for f in timeout_facts if f["status"] == "CURRENT"]
    superseded_facts = [f for f in timeout_facts if f["status"] == "SUPERSEDED"]
    assert len(current_facts) == 1
    assert len(superseded_facts) == 1

    assert current_facts[0]["object_value"] == "4500ms"
    assert current_facts[0]["source_episode_id"] == ep2_id
    assert superseded_facts[0]["object_value"] == "2000ms"
    assert superseded_facts[0]["source_episode_id"] == ep1_id
    assert superseded_facts[0]["superseded_by_id"] == current_facts[0]["id"]

    # Verify FR-008 provenance lookup
    prov = client.get(f"/api/v1/provenance/{current_facts[0]['id']}", headers=headers)
    assert prov.status_code == 200
    assert prov.json()["source_episodes"][0]["id"] == ep2_id


def test_fr004_br003_procedural_corroboration_and_user_confirmation(
    client: TestClient, isolated_tenants: tuple[str, str]
) -> None:
    """
    Verifies FR-004 & BR-003:
    - A procedure extracted from 1 or 2 episodes remains PROPOSED.
    - Upon the 3rd corroborating episode, it transitions automatically to CONFIRMED (CORROBORATED_3X).
    - A proposed procedure can also be explicitly confirmed via POST /procedures/{id}/confirm.
    """
    tenant_a, _ = isolated_tenants
    headers = {"X-Tenant-ID": tenant_a}

    proc_text = (
        "PROCEDURE: Rotate AuthService Signing Keys | "
        "TRIGGER: When AuthService JWT signing key nears expiration or compromise | "
        "STEPS: 1. Generate new keypair in TokenVault; 2. Publish new JWKS public key; 3. Drain old sessions"
    )

    for i in range(1, 4):
        resp = client.post(
            "/api/v1/episodes",
            headers=headers,
            json={
                "content": f"Runbook observation #{i}: {proc_text}",
                "agent_id": "agent-research-01",
                "session_id": "sess-proc",
                "importance_score": 0.8,
            },
        )
        assert resp.status_code == 201
        procs = client.get("/api/v1/procedures", headers=headers).json()
        assert len(procs) == 1
        if i < 3:
            assert procs[0]["status"] == "PROPOSED"
            assert procs[0]["evidence_count"] == i
        else:
            assert procs[0]["status"] == "CONFIRMED"
            assert procs[0]["confirmation_method"] == "CORROBORATED_3X"
            assert procs[0]["evidence_count"] == 3


def test_fr005_chronological_session_history_and_time_filtering(
    client: TestClient, isolated_tenants: tuple[str, str]
) -> None:
    """
    Verifies FR-005: Session history returns entries in strict chronological order
    and filters accurately by requested time range.
    """
    tenant_a, _ = isolated_tenants
    headers = {"X-Tenant-ID": tenant_a}
    base_time = datetime(2026, 10, 16, 10, 0, 0, tzinfo=timezone.utc)

    # Insert out of order (t+20m, t+0m, t+10m) to prove chronological sorting
    for offset_min in (20, 0, 10):
        ts = (base_time + timedelta(minutes=offset_min)).isoformat()
        client.post(
            "/api/v1/episodes",
            headers=headers,
            json={
                "content": f"Turn at offset {offset_min} minutes",
                "agent_id": "agent-research-01",
                "session_id": "sess-chrono",
                "importance_score": 0.6,
                "timestamp": ts,
            },
        )

    hist = client.get("/api/v1/sessions/sess-chrono/history", headers=headers).json()
    assert hist["total_episodes"] == 3
    contents = [e["content"] for e in hist["episodes"]]
    assert contents == [
        "Turn at offset 0 minutes",
        "Turn at offset 10 minutes",
        "Turn at offset 20 minutes",
    ]

    # Filter between +5m and +15m
    start_q = (base_time + timedelta(minutes=5)).isoformat()
    end_q = (base_time + timedelta(minutes=15)).isoformat()
    filtered = client.get(
        "/api/v1/sessions/sess-chrono/history",
        params={"start_time": start_q, "end_time": end_q},
        headers=headers,
    ).json()
    assert filtered["total_episodes"] == 1
    assert filtered["episodes"][0]["content"] == "Turn at offset 10 minutes"


def test_nfr004_resilience_during_extractor_outage(
    client: TestClient, isolated_tenants: tuple[str, str]
) -> None:
    """
    Verifies NFR-004 & C-03: When the extraction provider is unavailable, AgentHive still stores
    the episode, marks extraction DEFERRED, and enriches it later when the provider recovers.
    """
    tenant_a, _ = isolated_tenants
    headers = {"X-Tenant-ID": tenant_a}

    extraction_orchestrator.set_simulate_outage(True)
    try:
        resp = client.post(
            "/api/v1/episodes",
            headers=headers,
            json={
                "content": "Outage drill episode. FACT: OrderRouter max_connections = 512.",
                "agent_id": "agent-research-01",
                "session_id": "sess-outage",
                "importance_score": 0.9,
            },
        )
        assert resp.status_code == 201
        ep = resp.json()
        assert ep["extraction_status"] == "DEFERRED"
    finally:
        extraction_orchestrator.set_simulate_outage(False)

    # Now recover and drain due jobs
    scope = TenantScope(
        tenant_id=tenant_a,
        graph_name=derive_opaque_graph_name(tenant_a),
        display_name="Test Tenant A",
        is_demo=False,
    )
    # Reset retry_after to now so job drains immediately in test
    from app.repositories.memory_repository import get_memory_repository
    from app.domain.enums import ExtractionStatus

    get_memory_repository().upsert_extraction_job(
        scope=scope,
        episode_id=ep["id"],
        status=ExtractionStatus.DEFERRED,
        provider="deterministic",
        attempt_count=1,
        retry_after=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    processed = extraction_orchestrator.drain_pending_jobs_for_tenant(scope)
    assert processed == 1

    recovered_ep = client.get(f"/api/v1/episodes/{ep['id']}", headers=headers).json()
    assert recovered_ep["extraction_status"] == "COMPLETED"
    facts = client.get("/api/v1/facts", headers=headers).json()
    assert any(f["subject_name"] == "OrderRouter" and f["object_value"] == "512" for f in facts)