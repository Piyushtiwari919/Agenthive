# AgentHive Implementation Plan & Traceability Matrix
**Hackathon:** Graph Hacks 2026 — Track 02: Agent Memory and Coordination
**Primary Database:** FalkorDB (Load-Bearing Graph Database — Constraint C-01)

## 1. Phased Execution & Stop/Go Gates
* **Phase 0 (M0 Foundation):** FalkorDB container & persistent volume, tenant control graph (`ah_control`), opaque per-tenant graph provisioning (`ah_tenant_<hash>`), `/api/v1/health` and `/api/v1/ready` with fail-closed HTTP 503 when FalkorDB is unreachable.
* **Phase 1 (M1 Memory Engine & Isolation):** Episodic capture (`FR-001`), restart persistence (`FR-002`), semantic extraction & entity canonicalization (`FR-003`, `BR-007`), temporal fact superseding (`BR-004`), procedural memory & 3-episode corroboration/user confirmation (`FR-004`, `BR-003`), chronological session history (`FR-005`), resilient extraction queue (`NFR-004`), and 10-case adversarial tenant isolation suite (`FR-013`, `FR-014`).
* **Phase 2 (M2 Context Assembly & Provenance):** Unified 4-part context assembly (`FR-006`), hybrid graph + lexical relevance ranking with importance tie-breaking (`FR-007`), 2-click source episode provenance (`FR-008`), 25-entity answer key & 10-query golden evaluation (`K-03`).
* **Phase 3 (M3 Coordination & Shared Task State):** Agent registry (`FR-009`), same-tenant handoffs (`FR-010`, `FR-011`, `BR-006`), <5s shared task state + SSE stream (`FR-012`), 20 scripted handoff scenarios (`K-02`).
* **Phase 4 (M4 MCP Interoperability):** Official Python MCP stdio server (`app/mcp_server.py`) sharing the domain layer, verified with an end-to-end external MCP client test (`C-02`).
* **Phase 5 (M5 Graph-First Dashboard):** React + TypeScript + Tailwind + React Flow UI with 3-tier graph visualization, genuine backend-driven active procedure glow, tenant switcher (`FR-015`, `FR-016`), and benchmark runner.
* **Phase 6 (M6 Reliability, Load Probe & Submission):** 50-reader / 10-writer 60s concurrency probe (`FR-017`, `NFR-001`, `NFR-002`), restart verification script, complete docs, and 3-minute demo script.