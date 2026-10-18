import React, { useCallback, useEffect, useState } from "react";
import { Check, Cpu, GitFork, Play, Plus } from "lucide-react";
import { apiClient } from "../api/client";
import type { AgentRecord, HandoffRecord, HandoffStatus, TaskRecord } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";
import { useToast } from "../components/ToastProvider";

interface AgentsHandoffsPageProps {
  tenantId: string;
  onRefreshGraph: () => Promise<void>;
}

export const AgentsHandoffsPage: React.FC<AgentsHandoffsPageProps> = ({
  tenantId,
  onRefreshGraph,
}) => {
  const { notify } = useToast();
  const [agents, setAgents] = useState<AgentRecord[]>([]);
  const [handoffs, setHandoffs] = useState<HandoffRecord[]>([]);
  const [tasks, setTasks] = useState<TaskRecord[]>([]);

  // Handoff creation form state
  const [originAgentId, setOriginAgentId] = useState<string>("");
  const [targetAgentId, setTargetAgentId] = useState<string>("");
  const [taskTitle, setTaskTitle] = useState<string>("");
  const [contextSummary, setContextSummary] = useState<string>("");
  const [stateJson, setStateJson] = useState<string>('{"service": "PaymentGateway", "timeout_ms": 4500}');

  const loadCoordinationData = useCallback(async () => {
    try {
      const [aList, hList, tList] = await Promise.all([
        apiClient.listAgents(tenantId),
        apiClient.listHandoffs(tenantId),
        apiClient.listTasks(tenantId),
      ]);
      setAgents(aList);
      setHandoffs(hList);
      setTasks(tList);
      if (aList.length >= 2) {
        setOriginAgentId((prev) => prev || aList[0].id);
        setTargetAgentId((prev) => prev || aList[1].id);
      }
    } catch (err) {
      notify("error", "Failed to load coordination state", (err as Error).message);
    }
  }, [tenantId, notify]);

  useEffect(() => {
    setOriginAgentId("");
    setTargetAgentId("");
    void loadCoordinationData();
  }, [loadCoordinationData]);

  const handleCreateHandoff = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const parsedPayload = JSON.parse(stateJson || "{}") as Record<string, unknown>;
      const created = await apiClient.createHandoff(tenantId, {
        origin_agent_id: originAgentId,
        target_agent_id: targetAgentId,
        task_title: taskTitle,
        context_summary: contextSummary,
        state_payload: parsedPayload,
      });
      notify(
        "success",
        "Structured Handoff Created (FR-010)",
        `Handoff ${created.id} queued for ${created.target_agent_id}`
      );
      setTaskTitle("");
      setContextSummary("");
      await loadCoordinationData();
      await onRefreshGraph();
    } catch (err) {
      notify("error", "Handoff Creation Failed", (err as Error).message);
    }
  };

  const handleTransitionHandoff = async (ho: HandoffRecord, nextStatus: HandoffStatus) => {
    try {
      await apiClient.updateHandoffStatus(tenantId, ho.id, {
        status: nextStatus,
        acting_agent_id: ho.target_agent_id,
        note: `Transitioned to ${nextStatus} via dashboard`,
      });
      notify("success", "Handoff & Shared Task Updated (FR-012)", `${ho.id} -> ${nextStatus}`);
      await loadCoordinationData();
      await onRefreshGraph();
    } catch (err) {
      notify("error", "Status Transition Failed", (err as Error).message);
    }
  };

  return (
    <div className="space-y-5">
      {/* Registered Agents Row (FR-009) */}
      <div className="p-4 rounded-xl bg-[#0b1021] border border-slate-800 space-y-3">
        <h1 className="text-base font-bold text-white flex items-center gap-2">
          <Cpu className="w-5 h-5 text-cyan-400" />
          Registered Tenant Agents ({agents.length}) — FR-009
        </h1>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {agents.map((ag) => (
            <div
              key={ag.id}
              className="p-3.5 rounded-xl bg-[#060913] border border-slate-800 space-y-2 text-xs"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-white text-sm">{ag.name}</span>
                <StatusBadge status={ag.status} />
              </div>
              <div className="font-mono text-cyan-300">{ag.id}</div>
              <div className="text-slate-400">Role: {ag.role}</div>
              <div className="flex flex-wrap gap-1 pt-1">
                {ag.capabilities.map((cap) => (
                  <span
                    key={cap}
                    className="px-2 py-0.5 rounded bg-indigo-950/80 text-indigo-200 border border-indigo-700/50 font-mono text-[10px]"
                  >
                    {cap}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Initiate Same-Tenant Handoff Form (FR-010, BR-006) */}
      <form
        onSubmit={handleCreateHandoff}
        className="p-4 rounded-xl bg-[#0b1021] border border-slate-800 space-y-3"
      >
        <h2 className="text-sm font-bold text-white flex items-center gap-2">
          <Plus className="w-4 h-4 text-indigo-400" />
          Initiate Structured Agent-to-Agent Handoff (FR-010 / BR-006)
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Origin Agent</label>
            <select
              value={originAgentId}
              onChange={(e) => setOriginAgentId(e.target.value)}
              className="w-full bg-[#060913] border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white font-mono"
            >
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.id} ({a.name})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Target Agent (Same Tenant)</label>
            <select
              value={targetAgentId}
              onChange={(e) => setTargetAgentId(e.target.value)}
              className="w-full bg-[#060913] border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-cyan-300 font-mono"
            >
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.id} ({a.name})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Task Title</label>
            <input
              type="text"
              required
              placeholder="e.g. Apply PaymentGateway timeout=4500ms patch"
              value={taskTitle}
              onChange={(e) => setTaskTitle(e.target.value)}
              className="w-full bg-[#060913] border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white"
            />
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Context Summary</label>
            <input
              type="text"
              required
              placeholder="Summary of findings and decisions for target agent..."
              value={contextSummary}
              onChange={(e) => setContextSummary(e.target.value)}
              className="w-full bg-[#060913] border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Structured State Payload (JSON)</label>
            <input
              type="text"
              required
              value={stateJson}
              onChange={(e) => setStateJson(e.target.value)}
              className="w-full bg-[#060913] border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-emerald-300 font-mono"
            />
          </div>
        </div>
        <button
          type="submit"
          className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white inline-flex items-center gap-1.5"
        >
          <GitFork className="w-3.5 h-3.5" />
          Dispatch Handoff
        </button>
      </form>

      {/* Handoffs Timeline & Shared Task State Board */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="p-4 rounded-xl bg-[#0b1021] border border-slate-800 space-y-3">
          <h2 className="text-sm font-bold text-white">
            Handoff Queue & Lifecycle ({handoffs.length}) — FR-011
          </h2>
          <div className="space-y-2.5 max-h-[460px] overflow-y-auto pr-1">
            {handoffs.map((ho) => (
              <div
                key={ho.id}
                className="p-3.5 rounded-xl bg-[#060913] border border-slate-800 space-y-2 text-xs"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-bold text-white">{ho.task_title}</span>
                  <StatusBadge status={ho.status} />
                </div>
                <div className="font-mono text-cyan-300 text-[11px]">
                  {ho.origin_agent_id} &rarr; {ho.target_agent_id} ({ho.id})
                </div>
                <p className="text-slate-300">{ho.context_summary}</p>
                <pre className="p-2 rounded bg-slate-900 font-mono text-[11px] text-emerald-300 overflow-x-auto">
                  {JSON.stringify(ho.state_payload, null, 2)}
                </pre>
                {ho.status !== "COMPLETED" && ho.status !== "CANCELLED" && (
                  <div className="flex items-center gap-2 pt-1">
                    {ho.status === "PENDING" && (
                      <button
                        type="button"
                        onClick={() => void handleTransitionHandoff(ho, "IN_PROGRESS")}
                        className="px-2.5 py-1 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-semibold inline-flex items-center gap-1"
                      >
                        <Play className="w-3 h-3" />
                        Accept & Start
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => void handleTransitionHandoff(ho, "COMPLETED")}
                      className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-semibold inline-flex items-center gap-1"
                    >
                      <Check className="w-3 h-3" />
                      Mark Completed
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="p-4 rounded-xl bg-[#0b1021] border border-slate-800 space-y-3">
          <h2 className="text-sm font-bold text-white">
            Shared Tenant Task State ({tasks.length}) — FR-012 (&lt;5s Sync)
          </h2>
          <div className="space-y-2.5 max-h-[460px] overflow-y-auto pr-1">
            {tasks.map((t) => (
              <div
                key={t.id}
                className="p-3.5 rounded-xl bg-[#060913] border border-slate-800 space-y-1.5 text-xs"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-bold text-white">{t.title}</span>
                  <StatusBadge status={t.status} />
                </div>
                <div className="text-slate-400 font-mono text-[11px]">
                  Task ID: {t.id} • Owner: <span className="text-cyan-300">{t.owner_agent_id}</span>
                </div>
                {t.active_procedure_id && (
                  <div className="text-cyan-300 font-mono text-[11px]">
                    Active Procedure: {t.active_procedure_id}
                  </div>
                )}
                {t.result_summary && <p className="text-slate-300">{t.result_summary}</p>}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};