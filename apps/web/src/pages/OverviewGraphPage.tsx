import React, { useState } from "react";
import {
  Activity,
  BookOpen,
  Database,
  ExternalLink,
  GitFork,
  Layers,
  MessageSquare,
  Play,
  Sparkles,
  Square,
} from "lucide-react";
import { apiClient } from "../api/client";
import type {
  GraphNodeDTO,
  GraphSubgraphResponse,
  MemoryTier,
} from "../api/types";
import { StatusBadge } from "../components/StatusBadge";
import { useToast } from "../components/ToastProvider";
import { GraphFilterBar } from "../graph/GraphFilterBar";
import { MemoryGraphCanvas } from "../graph/MemoryGraphCanvas";

interface OverviewGraphPageProps {
  tenantId: string;
  subgraph: GraphSubgraphResponse | null;
  loading: boolean;
  onRefresh: () => Promise<void>;
  onOpenProvenance: (targetId: string, label?: string) => void;
}

export const OverviewGraphPage: React.FC<OverviewGraphPageProps> = ({
  tenantId,
  subgraph,
  loading,
  onRefresh,
  onOpenProvenance,
}) => {
  const { notify } = useToast();
  const [selectedTier, setSelectedTier] = useState<MemoryTier | "ALL">("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedNode, setSelectedNode] = useState<GraphNodeDTO | null>(null);
  const [seeding, setSeeding] = useState<boolean>(false);

  const metrics = subgraph?.metrics;

  const handleSeedDemo = async () => {
    setSeeding(true);
    try {
      const res = await apiClient.seedDemoDataset();
      notify(
        "success",
        "120-Episode Synthetic Corpus Seeded",
        `Total Episodes: ${String(res.total_episodes ?? 120)}`
      );
      await onRefresh();
    } catch (err) {
      notify("error", "Seeding Failed", (err as Error).message);
    } finally {
      setSeeding(false);
    }
  };

  const handleToggleProcedureExecution = async (node: GraphNodeDTO) => {
    try {
      if (node.is_glowing) {
        await apiClient.completeProcedure(tenantId, node.id, {
          agent_id: "agent-alpha-coder",
          final_status: "COMPLETED",
          result_summary: "Completed from Graph Inspector",
        });
        notify("info", "Procedure Execution Completed", `Stopped active glow on ${node.label}`);
      } else {
        const agents = await apiClient.listAgents(tenantId);
        const defaultAgent = agents[0]?.id || "agent-alpha-coder";
        await apiClient.executeProcedure(tenantId, node.id, {
          agent_id: defaultAgent,
          task_title: `Executing ${node.label}`,
        });
        notify("success", "Procedure Active", `${node.label} is now actively executing.`);
      }
      await onRefresh();
    } catch (err) {
      notify("error", "Procedure Action Failed", (err as Error).message);
    }
  };

  return (
    <div className="space-y-5">
      {/* Hero Banner & Quick Seed Action */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl bg-gradient-to-r from-indigo-950/70 via-[#0b1021] to-cyan-950/50 border border-indigo-500/30">
        <div>
          <h1 className="text-lg font-bold text-white flex items-center gap-2">
            <Database className="w-5 h-5 text-cyan-400" />
            Live FalkorDB Three-Tier Memory Graph ({tenantId})
          </h1>
          <p className="text-xs text-slate-300 mt-0.5">
            Real-time graph records scoped to <span className="font-mono text-cyan-300">{tenantId}</span>. Click any Fact, Procedure, or Entity node to inspect source episode provenance in $\le 2$ clicks.
          </p>
        </div>
        <button
          type="button"
          disabled={seeding}
          onClick={handleSeedDemo}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30"
        >
          <Sparkles className="w-4 h-4" />
          {seeding ? "Seeding FalkorDB..." : "Seed 120-Episode Demo Corpus"}
        </button>
      </div>

      {/* Live Database-Derived Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3">
        <div className="p-3.5 rounded-xl bg-[#0b1021] border border-slate-800">
          <div className="text-xs text-slate-400 flex items-center justify-between">
            <span>Episodes</span>
            <MessageSquare className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-1">
            {metrics ? metrics.episode_count : "—"}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">
            Across {metrics ? metrics.session_count : 0} sessions
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-[#0b1021] border border-slate-800">
          <div className="text-xs text-slate-400 flex items-center justify-between">
            <span>Canonical Entities</span>
            <Layers className="w-4 h-4 text-violet-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-1">
            {metrics ? metrics.entity_count : "—"}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">Deduplicated (BR-007)</div>
        </div>

        <div className="p-3.5 rounded-xl bg-[#0b1021] border border-slate-800">
          <div className="text-xs text-slate-400 flex items-center justify-between">
            <span>Semantic Facts</span>
            <Database className="w-4 h-4 text-fuchsia-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-1">
            {metrics ? metrics.current_fact_count : "—"}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">
            +{metrics ? metrics.superseded_fact_count : 0} superseded retained
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-[#0b1021] border border-slate-800">
          <div className="text-xs text-slate-400 flex items-center justify-between">
            <span>Procedures</span>
            <BookOpen className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-1">
            {metrics ? metrics.confirmed_procedure_count : "—"}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">
            Confirmed • {metrics ? metrics.proposed_procedure_count : 0} proposed
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-[#0b1021] border border-slate-800">
          <div className="text-xs text-slate-400 flex items-center justify-between">
            <span>Registered Agents</span>
            <GitFork className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-1">
            {metrics ? metrics.registered_agent_count : "—"}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">
            {metrics ? metrics.pending_handoff_count : 0} pending handoffs
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-[#0b1021] border border-slate-800">
          <div className="text-xs text-slate-400 flex items-center justify-between">
            <span>Active Tasks</span>
            <Activity className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-1">
            {metrics ? metrics.active_task_count : "—"}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">
            {subgraph?.active_procedures.length || 0} glowing procedure(s)
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <GraphFilterBar
        selectedTier={selectedTier}
        onSelectTier={setSelectedTier}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onRefresh={() => void onRefresh()}
        totalNodes={subgraph?.nodes.length || 0}
        totalEdges={subgraph?.edges.length || 0}
      />

      {/* Graph Canvas + Node Inspector */}
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-4">
        <div className="xl:col-span-3">
          {loading && !subgraph ? (
            <div className="h-[560px] rounded-xl bg-[#0b1021] border border-slate-800 flex items-center justify-center text-sm text-slate-400">
              Querying FalkorDB tenant graph for {tenantId}...
            </div>
          ) : (
            <MemoryGraphCanvas
              nodes={subgraph?.nodes || []}
              edges={subgraph?.edges || []}
              selectedTier={selectedTier}
              searchQuery={searchQuery}
              onSelectNode={(n) => setSelectedNode(n)}
            />
          )}
        </div>

        {/* Right Node Details Panel */}
        <div className="p-4 rounded-xl bg-[#0b1021] border border-slate-800 flex flex-col justify-between space-y-4">
          {selectedNode ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono uppercase text-cyan-300">
                  {selectedNode.tier} • {selectedNode.node_type}
                </span>
                {selectedNode.status && <StatusBadge status={selectedNode.status} />}
              </div>
              <h3 className="text-sm font-bold text-white break-words">{selectedNode.label}</h3>
              <div className="text-xs font-mono text-slate-400">ID: {selectedNode.id}</div>

              <div className="p-3 rounded-lg bg-[#060913] border border-slate-800 text-xs space-y-1.5 max-h-64 overflow-y-auto">
                {Object.entries(selectedNode.properties).map(([k, v]) => (
                  <div key={k} className="break-words">
                    <span className="text-slate-400 font-mono">{k}: </span>
                    <span className="text-slate-200">
                      {typeof v === "object" ? JSON.stringify(v) : String(v)}
                    </span>
                  </div>
                ))}
              </div>

              <div className="space-y-2 pt-2">
                {["Fact", "Procedure", "Entity", "Episode"].includes(selectedNode.node_type) && (
                  <button
                    type="button"
                    onClick={() => onOpenProvenance(selectedNode.id, selectedNode.label)}
                    className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    Inspect Source Episode Provenance
                  </button>
                )}

                {selectedNode.node_type === "Procedure" && (
                  <button
                    type="button"
                    onClick={() => void handleToggleProcedureExecution(selectedNode)}
                    className={`w-full inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold ${
                      selectedNode.is_glowing
                        ? "bg-rose-600 hover:bg-rose-500 text-white"
                        : "bg-cyan-600 hover:bg-cyan-500 text-white"
                    }`}
                  >
                    {selectedNode.is_glowing ? (
                      <>
                        <Square className="w-3.5 h-3.5" />
                        Complete Task & Stop Glow
                      </>
                    ) : (
                      <>
                        <Play className="w-3.5 h-3.5" />
                        Execute Task with Procedure (Trigger Glow)
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div className="text-xs text-slate-400 space-y-2">
              <div className="font-semibold text-slate-200 text-sm">Graph Node Inspector</div>
              <p>
                Click any node in the FalkorDB canvas to inspect its properties, trace source
                episodes in 1 click (FR-008), or trigger live procedure execution.
              </p>
            </div>
          )}

          {/* Legend */}
          <div className="border-t border-slate-800 pt-3 space-y-1.5 text-[11px] text-slate-400">
            <div className="font-semibold text-slate-300">Memory Tier Legend</div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-indigo-500" />
              <span>Episodic (Conversations & Turns)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-violet-500" />
              <span>Semantic (Canonical Entities & Facts)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
              <span>Procedural (Confirmed / Proposed Runbooks)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" />
              <span>Coordination (Agents, Tasks & Handoffs)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};