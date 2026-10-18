import React, { useCallback, useEffect, useState } from "react";
import { BookOpen, CheckCircle2, ExternalLink, Play, Square } from "lucide-react";
import { apiClient } from "../api/client";
import type { AgentRecord, ProcedureRecord } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";
import { useToast } from "../components/ToastProvider";

interface ProceduralMemoryPageProps {
  tenantId: string;
  onRefreshGraph: () => Promise<void>;
  onOpenProvenance: (targetId: string, label?: string) => void;
}

export const ProceduralMemoryPage: React.FC<ProceduralMemoryPageProps> = ({
  tenantId,
  onRefreshGraph,
  onOpenProvenance,
}) => {
  const { notify } = useToast();
  const [procedures, setProcedures] = useState<ProcedureRecord[]>([]);
  const [agents, setAgents] = useState<AgentRecord[]>([]);

  const loadProcedures = useCallback(async () => {
    try {
      const [procList, agentList] = await Promise.all([
        apiClient.listProcedures(tenantId),
        apiClient.listAgents(tenantId),
      ]);
      setProcedures(procList);
      setAgents(agentList);
    } catch (err) {
      notify("error", "Failed to load procedures", (err as Error).message);
    }
  }, [tenantId, notify]);

  useEffect(() => {
    setProcedures([]);
    void loadProcedures();
  }, [loadProcedures]);

  const handleConfirm = async (proc: ProcedureRecord) => {
    try {
      await apiClient.confirmProcedure(tenantId, proc.id);
      notify("success", "Procedure Confirmed", `${proc.name} marked CONFIRMED (USER_CONFIRMED).`);
      await loadProcedures();
      await onRefreshGraph();
    } catch (err) {
      notify("error", "Confirmation Failed", (err as Error).message);
    }
  };

  const handleExecuteOrStop = async (proc: ProcedureRecord) => {
    const defaultAgent = agents[0]?.id || "agent-alpha-coder";
    try {
      if (proc.is_currently_active) {
        await apiClient.completeProcedure(tenantId, proc.id, {
          agent_id: defaultAgent,
          final_status: "COMPLETED",
          result_summary: "Procedure execution completed cleanly.",
        });
        notify("info", "Procedure Execution Stopped", `Active glow cleared for ${proc.name}.`);
      } else {
        await apiClient.executeProcedure(tenantId, proc.id, {
          agent_id: defaultAgent,
          task_title: `Execute Runbook: ${proc.name}`,
        });
        notify(
          "success",
          "Procedure Active (Graph Glowing)",
          `${proc.name} is now executing on task for ${defaultAgent}.`
        );
      }
      await loadProcedures();
      await onRefreshGraph();
    } catch (err) {
      notify("error", "Execution Toggle Failed", (err as Error).message);
    }
  };

  return (
    <div className="space-y-5">
      <div className="p-4 rounded-xl bg-[#0b1021] border border-slate-800">
        <h1 className="text-lg font-bold text-white flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-emerald-400" />
          Procedural Memory Store & Live Execution Control (FR-004 / BR-003)
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Procedures require $\ge 3$ corroborating episodes or explicit user confirmation to become <code className="text-emerald-300">CONFIRMED</code>. Starting a task using a procedure pulses the procedural node on the Memory Graph.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {procedures.map((proc) => (
          <div
            key={proc.id}
            className={`p-4 rounded-xl bg-[#0b1021] border space-y-3 ${
              proc.is_currently_active
                ? "procedure-node-active-glow"
                : "border-slate-800"
            }`}
          >
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <div>
                <h2 className="text-sm font-bold text-white">{proc.name}</h2>
                <span className="text-[11px] font-mono text-slate-400">
                  ID: {proc.id} • Basis: {proc.confirmation_method} ({proc.evidence_count} episode(s))
                </span>
              </div>
              <StatusBadge status={proc.is_currently_active ? "IN_PROGRESS" : proc.status} />
            </div>

            <div className="p-2.5 rounded-lg bg-[#060913] border border-slate-800 text-xs">
              <span className="text-slate-400 font-semibold">Trigger Condition: </span>
              <span className="text-cyan-200">{proc.trigger_text}</span>
            </div>

            <div className="space-y-1 text-xs">
              <div className="text-slate-400 font-semibold">Ordered Actionable Steps:</div>
              <ol className="list-decimal list-inside space-y-1 text-slate-200 bg-[#060913] p-3 rounded-lg border border-slate-800">
                {proc.steps.map((step, i) => (
                  <li key={i}>{step}</li>
                ))}
              </ol>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 pt-2">
              <button
                type="button"
                onClick={() => onOpenProvenance(proc.id, proc.name)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-cyan-300 inline-flex items-center gap-1.5"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                Source Episodes ({proc.source_episode_ids.length})
              </button>

              <div className="flex items-center gap-2">
                {proc.status === "PROPOSED" && (
                  <button
                    type="button"
                    onClick={() => void handleConfirm(proc)}
                    className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white inline-flex items-center gap-1"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Confirm Procedure
                  </button>
                )}

                <button
                  type="button"
                  onClick={() => void handleExecuteOrStop(proc)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 ${
                    proc.is_currently_active
                      ? "bg-rose-600 hover:bg-rose-500 text-white"
                      : "bg-indigo-600 hover:bg-indigo-500 text-white"
                  }`}
                >
                  {proc.is_currently_active ? (
                    <>
                      <Square className="w-3.5 h-3.5" />
                      Stop Task Execution
                    </>
                  ) : (
                    <>
                      <Play className="w-3.5 h-3.5" />
                      Execute Task (Glow)
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};