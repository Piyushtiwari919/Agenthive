# AgentHive — Persistent Multi-Agent Memory and Coordination Platform on FalkorDB
**Graph Hacks 2026 — Track 02: Agent Memory and Coordination**

---

## 1. Executive Summary & Problem Solved
AI agents suffer from **Agent Amnesia**: context evaporates when conversation windows close, findings by research agents remain invisible to coding agents, and corrected mistakes repeat daily. **AgentHive** eliminates this re-explanation tax by delivering:
1. **Three-Tier Persistent Memory:** Episodic (`what happened`), Semantic (`what is known`), and Procedural (`how to do it`).
2. **Structured Handoffs:** Agents transfer tasks, summaries, and state payload to other registered agents in the same tenant.
3. **Strict Tenant Isolation:** Graph-per-tenant architecture enforced at the database boundary and proven via adversarial probes.
4. **FalkorDB Centrality:** FalkorDB is the load-bearing primary database—the product fails closed (HTTP `503`) if FalkorDB is removed (Constraint C-01 / K-09).

---

## 2. Architecture & Graph Data Model
* **Backend:** Python 3.12, FastAPI, Pydantic v2, official FalkorDB Python client, and official Python MCP SDK (`FastMCP`).
* **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, and React Flow.
* **Graph Model:** Isolated FalkorDB graph per tenant (`ah_tenant_<hash>`) containing `Session`, `Episode`, `Entity`, `Fact`, `Procedure`, `Agent`, `Task`, `Handoff`, and `ExtractionJob` nodes.

```mermaid
flowchart TB
    UI["React + TypeScript + React Flow UI"] --> FastAPI["FastAPI + SSE Stream (/api/v1)"]
    MCP["External MCP Client"] --> MCPServer["Official Python MCP Server (stdio)"]
    FastAPI --> Services["Domain Services"]
    MCPServer --> Services
    Services --> FalkorRepo["FalkorDB Repository Layer"]
    FalkorRepo --> TenantGraph[("FalkorDB Tenant Graph: ah_tenant_<hash>")]