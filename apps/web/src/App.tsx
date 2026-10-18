import React, { useCallback, useEffect, useState } from "react";
import { apiClient } from "./api/client";
import type { GraphSubgraphResponse } from "./api/types";
import { LayoutShell, type NavTab } from "./components/LayoutShell";
import { ProvenanceDrawer } from "./components/ProvenanceDrawer";
import { ToastProvider } from "./components/ToastProvider";
import { useActivityStream } from "./hooks/useActivityStream";
import { TenantProvider, useTenantScope } from "./hooks/useTenantScope";
import { AgentsHandoffsPage } from "./pages/AgentsHandoffsPage";
import { BenchmarksPage } from "./pages/BenchmarksPage";
import { ContextPlaygroundPage } from "./pages/ContextPlaygroundPage";
import { EpisodesSessionsPage } from "./pages/EpisodesSessionsPage";
import { OverviewGraphPage } from "./pages/OverviewGraphPage";
import { ProceduralMemoryPage } from "./pages/ProceduralMemoryPage";
import { SemanticKnowledgePage } from "./pages/SemanticKnowledgePage";

const DashboardContent: React.FC = () => {
  const { tenantId, scopeEpoch } = useTenantScope();
  const [activeTab, setActiveTab] = useState<NavTab>("overview");
  const [dbReady, setDbReady] = useState<boolean>(true);
  const [subgraph, setSubgraph] = useState<GraphSubgraphResponse | null>(null);
  const [loadingGraph, setLoadingGraph] = useState<boolean>(false);

  // Provenance Drawer State (FR-008: <= 2 interactions from anywhere)
  const [provenanceTarget, setProvenanceTarget] = useState<{
    id: string;
    label?: string;
  } | null>(null);

  const fetchTenantSubgraph = useCallback(async () => {
    setLoadingGraph(true);
    try {
      const [readyRes, graphRes] = await Promise.all([
        apiClient.getReadyStatus(),
        apiClient.getSubgraph(tenantId, 45),
      ]);
      setDbReady(Boolean(readyRes.database_connected));
      setSubgraph(graphRes);
    } catch {
      setDbReady(false);
    } finally {
      setLoadingGraph(false);
    }
  }, [tenantId]);

  // Clear previous tenant state immediately on tenant switch (FR-016)
  useEffect(() => {
    setSubgraph(null);
    setProvenanceTarget(null);
    void fetchTenantSubgraph();
  }, [tenantId, scopeEpoch, fetchTenantSubgraph]);

  // Subscribe to SSE live events for <5s task updates and active procedure glow
  const { connected: sseConnected } = useActivityStream(tenantId, () => {
    void fetchTenantSubgraph();
  });

  const handleOpenProvenance = (targetId: string, label?: string) => {
    setProvenanceTarget({ id: targetId, label });
  };

  return (
    <LayoutShell
      activeTab={activeTab}
      onSelectTab={setActiveTab}
      dbReady={dbReady}
      sseConnected={sseConnected}
      activeProcedures={subgraph?.active_procedures || []}
    >
      {activeTab === "overview" && (
        <OverviewGraphPage
          tenantId={tenantId}
          subgraph={subgraph}
          loading={loadingGraph}
          onRefresh={fetchTenantSubgraph}
          onOpenProvenance={handleOpenProvenance}
        />
      )}

      {activeTab === "playground" && (
        <ContextPlaygroundPage
          tenantId={tenantId}
          onOpenProvenance={handleOpenProvenance}
        />
      )}

      {activeTab === "episodes" && (
        <EpisodesSessionsPage
          tenantId={tenantId}
          onRefreshGraph={fetchTenantSubgraph}
        />
      )}

      {activeTab === "semantic" && (
        <SemanticKnowledgePage
          tenantId={tenantId}
          onOpenProvenance={handleOpenProvenance}
        />
      )}

      {activeTab === "procedures" && (
        <ProceduralMemoryPage
          tenantId={tenantId}
          onRefreshGraph={fetchTenantSubgraph}
          onOpenProvenance={handleOpenProvenance}
        />
      )}

      {activeTab === "agents" && (
        <AgentsHandoffsPage
          tenantId={tenantId}
          onRefreshGraph={fetchTenantSubgraph}
        />
      )}

      {activeTab === "benchmarks" && <BenchmarksPage />}

      <ProvenanceDrawer
        tenantId={tenantId}
        targetId={provenanceTarget?.id || null}
        targetLabel={provenanceTarget?.label}
        onClose={() => setProvenanceTarget(null)}
      />
    </LayoutShell>
  );
};

export const App: React.FC = () => {
  return (
    <ToastProvider>
      <TenantProvider>
        <DashboardContent />
      </TenantProvider>
    </ToastProvider>
  );
};

export default App;