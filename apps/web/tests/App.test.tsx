import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "../src/App";
import { apiClient } from "../src/api/client";

vi.mock("../src/api/client", () => ({
  API_BASE_URL: "http://localhost:8000/api/v1",
  apiClient: {
    getReadyStatus: vi.fn(),
    listTenants: vi.fn(),
    getSubgraph: vi.fn(),
    getProvenance: vi.fn(),
    listAgents: vi.fn(),
    assembleContext: vi.fn(),
    listProcedures: vi.fn(),
    confirmProcedure: vi.fn(),
    executeProcedure: vi.fn(),
    completeProcedure: vi.fn(),
    listHandoffs: vi.fn(),
    listTasks: vi.fn(),
    seedDemoDataset: vi.fn(),
    runIsolationProbe: vi.fn(),
    runHandoffSuite: vi.fn(),
    runRetrievalEvaluation: vi.fn(),
    toggleExtractorOutage: vi.fn(),
  },
}));

describe("AgentHive Phase 5 Dashboard & Tenant Isolation UI", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(apiClient.getReadyStatus).mockResolvedValue({
      status: "ready",
      database: "falkordb",
      database_connected: true,
      environment: "demo",
      extraction_provider: "deterministic",
      timestamp: new Date().toISOString(),
    });

    vi.mocked(apiClient.listTenants).mockResolvedValue([
      {
        tenant_id: "alpha-eng",
        display_name: "Tenant A — Alpha Core Engineering",
        graph_name: "ah_tenant_alpha",
        is_demo: true,
        created_at: new Date().toISOString(),
      },
      {
        tenant_id: "beta-sec",
        display_name: "Tenant B — Beta Cloud Security",
        graph_name: "ah_tenant_beta",
        is_demo: true,
        created_at: new Date().toISOString(),
      },
    ]);

    vi.mocked(apiClient.getSubgraph).mockImplementation(
      async (tenantId: string) => ({
        tenant_id: tenantId,
        metrics: {
          tenant_id: tenantId,
          episode_count: tenantId === "alpha-eng" ? 85 : 35,
          session_count: 10,
          entity_count: tenantId === "alpha-eng" ? 25 : 5,
          current_fact_count: 30,
          superseded_fact_count: 2,
          confirmed_procedure_count: 8,
          proposed_procedure_count: 2,
          registered_agent_count: 3,
          pending_handoff_count: 3,
          active_task_count: tenantId === "alpha-eng" ? 1 : 0,
          pending_extraction_jobs: 0,
        },
        active_procedures:
          tenantId === "alpha-eng"
            ? [
                {
                  procedure_id: "proc_alpha_1",
                  procedure_name: "Mitigate PaymentGateway Timeout Spike",
                  task_id: "task_1",
                  task_title: "Execute Mitigation",
                  task_status: "IN_PROGRESS",
                  agent_id: "agent-alpha-coder",
                },
              ]
            : [],
        nodes: [
          {
            id: `proc_${tenantId}_1`,
            label:
              tenantId === "alpha-eng"
                ? "Mitigate PaymentGateway Timeout Spike"
                : "Quarantine Malicious ASN",
            node_type: "Procedure",
            tier: "PROCEDURAL",
            tenant_id: tenantId,
            status: "CONFIRMED",
            is_glowing: tenantId === "alpha-eng",
            properties: { trigger_text: "When spike occurs" },
          },
        ],
        edges: [],
      }),
    );
  });

  it("renders database-derived metrics, active procedure glow banner & graph node, and switches tenant cleanly (FR-015, FR-016)", async () => {
    render(<App />);

    // Verify Tenant A metrics, active procedure header banner, and glowing graph node appear
    await waitFor(() => {
      expect(screen.getByText("85")).toBeInTheDocument();
      expect(
        screen.getAllByText(/Mitigate PaymentGateway Timeout Spike/i).length,
      ).toBeGreaterThanOrEqual(2);
      expect(screen.getByText("ACTIVE EXECUTION")).toBeInTheDocument();
    });

    // Switch to Tenant B (beta-sec) and verify prior tenant state clears and reloads Tenant B
    const select = screen.getByLabelText("Select Active Tenant Scope");
    fireEvent.change(select, { target: { value: "beta-sec" } });

    await waitFor(() => {
      expect(apiClient.getSubgraph).toHaveBeenCalledWith("beta-sec", 45);
      expect(screen.getByText("35")).toBeInTheDocument();
      expect(screen.getByText("Quarantine Malicious ASN")).toBeInTheDocument();
      expect(screen.queryByText("ACTIVE EXECUTION")).not.toBeInTheDocument();
    });
  });

  it("navigates to Benchmarks view and shows NOT_RUN until suites are executed", async () => {
    render(<App />);

    const benchBtn = await screen.findByText("Benchmarks & Isolation");
    fireEvent.click(benchBtn);

    expect(screen.getAllByText("NOT_RUN").length).toBeGreaterThanOrEqual(3);
  });
});
