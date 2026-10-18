import React, { useState } from "react";
import {
  Activity,
  BookOpen,
  BrainCircuit,
  Cpu,
  Database,
  GitFork,
  Layers,
  MessageSquare,
  Plus,
  Radio,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import type { ActiveProcedureExecution } from "../api/types";
import { useTenantScope } from "../hooks/useTenantScope";
import { useToast } from "./ToastProvider";

export type NavTab =
  | "overview"
  | "playground"
  | "episodes"
  | "semantic"
  | "procedures"
  | "agents"
  | "benchmarks";

interface LayoutShellProps {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  dbReady: boolean;
  sseConnected: boolean;
  activeProcedures: ActiveProcedureExecution[];
  children: React.ReactNode;
}

export const LayoutShell: React.FC<LayoutShellProps> = ({
  activeTab,
  onSelectTab,
  dbReady,
  sseConnected,
  activeProcedures,
  children,
}) => {
  const { tenantId, tenants, activeTenantInfo, switchTenant, provisionNewTenant } =
    useTenantScope();
  const { notify } = useToast();
  const [showNewTenantModal, setShowNewTenantModal] = useState(false);
  const [newTenantId, setNewTenantId] = useState("");
  const [newTenantName, setNewTenantName] = useState("");

  const navItems: Array<{ id: NavTab; label: string; icon: React.ReactNode }> = [
    { id: "overview", label: "Overview & Memory Graph", icon: <BrainCircuit className="w-4 h-4" /> },
    { id: "playground", label: "Context Playground", icon: <Sparkles className="w-4 h-4" /> },
    { id: "episodes", label: "Episodes & Sessions", icon: <MessageSquare className="w-4 h-4" /> },
    { id: "semantic", label: "Semantic Knowledge", icon: <Layers className="w-4 h-4" /> },
    { id: "procedures", label: "Procedural Memory", icon: <BookOpen className="w-4 h-4" /> },
    { id: "agents", label: "Agents & Handoffs", icon: <GitFork className="w-4 h-4" /> },
    { id: "benchmarks", label: "Benchmarks & Isolation", icon: <ShieldAlert className="w-4 h-4" /> },
  ];

  const handleCreateTenant = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTenantId.trim() || !newTenantName.trim()) return;
    try {
      const created = await provisionNewTenant({
        tenant_id: newTenantId.trim().toLowerCase(),
        display_name: newTenantName.trim(),
        description: "On-demand isolated tenant graph (FR-013)",
      });
      notify("success", "Isolated Tenant Provisioned", `Graph ${created.graph_name} is ready.`);
      setNewTenantId("");
      setNewTenantName("");
      setShowNewTenantModal(false);
    } catch (err) {
      notify("error", "Tenant Provisioning Failed", (err as Error).message);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#060913] text-slate-100">
      {/* Top Control Bar */}
      <header className="sticky top-0 z-30 border-b border-slate-800/90 bg-[#0b1021]/95 backdrop-blur-md px-4 py-3">
        <div className="max-w-[1600px] mx-auto flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Cpu className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-base tracking-tight text-white">AgentHive</span>
                <span className="text-[11px] font-mono uppercase px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-700/60">
                  Graph Hacks 2026 • Track 02
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Persistent Multi-Agent Memory & Coordination Platform on FalkorDB
              </p>
            </div>
          </div>

          {/* Active Procedure Execution Banner (Live Glow Indicator) */}
          {activeProcedures.length > 0 && (
            <div
              role="status"
              aria-live="polite"
              className="flex items-center gap-2.5 px-3.5 py-1.5 rounded-full bg-cyan-950/90 border border-cyan-400 text-cyan-100 text-xs shadow-lg shadow-cyan-500/20"
            >
              <Activity className="w-4 h-4 text-cyan-300 animate-pulse" />
              <span>
                <strong>Procedure Active:</strong> {activeProcedures[0].procedure_name} (Task:{" "}
                {activeProcedures[0].task_status})
              </span>
            </div>
          )}

          {/* Right Controls: FalkorDB Status + Tenant Switcher (FR-016) */}
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs">
              <Database
                className={`w-3.5 h-3.5 ${dbReady ? "text-emerald-400" : "text-rose-400"}`}
              />
              <span className="text-slate-300">FalkorDB:</span>
              <span className={dbReady ? "text-emerald-400 font-semibold" : "text-rose-400 font-semibold"}>
                {dbReady ? "ONLINE" : "UNAVAILABLE (503)"}
              </span>
              <span className="text-slate-600">|</span>
              <Radio
                className={`w-3.5 h-3.5 ${sseConnected ? "text-cyan-400" : "text-slate-500"}`}
              />
              <span className="text-slate-400">{sseConnected ? "SSE Live" : "Polling"}</span>
            </div>

            <div className="flex items-center gap-2 bg-slate-900/90 border border-indigo-500/40 rounded-lg px-2.5 py-1">
              <label htmlFor="tenant-switcher-select" className="text-xs text-slate-400 font-medium">
                Tenant Scope (Demo):
              </label>
              <select
                id="tenant-switcher-select"
                aria-label="Select Active Tenant Scope"
                value={tenantId}
                onChange={(e) => switchTenant(e.target.value)}
                className="bg-[#060913] text-xs font-mono text-cyan-300 border border-slate-700 rounded px-2 py-1 focus:outline-none focus:border-cyan-400"
              >
                {tenants.map((t) => (
                  <option key={t.tenant_id} value={t.tenant_id}>
                    {t.tenant_id} — {t.display_name}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => setShowNewTenantModal(true)}
                title="Provision isolated tenant graph (FR-013)"
                className="p-1 rounded bg-indigo-600/80 hover:bg-indigo-500 text-white text-xs flex items-center gap-1 px-2"
              >
                <Plus className="w-3.5 h-3.5" />
                New
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Layout Body */}
      <div className="flex-1 max-w-[1600px] w-full mx-auto flex flex-col lg:flex-row">
        {/* Left Navigation Sidebar */}
        <aside className="lg:w-64 shrink-0 border-b lg:border-b-0 lg:border-r border-slate-800/90 bg-[#0b1021]/60 p-3 flex flex-col justify-between">
          <nav aria-label="Main Navigation" className="flex lg:flex-col gap-1 overflow-x-auto">
            {navItems.map((item) => {
              const isSelected = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onSelectTab(item.id)}
                  className={`flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap ${
                    isSelected
                      ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/25"
                      : "text-slate-300 hover:bg-slate-800/70 hover:text-white"
                  }`}
                >
                  {item.icon}
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Active Tenant Boundary Card */}
          <div className="hidden lg:block mt-6 p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-xs space-y-1.5">
            <div className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">
              Isolated FalkorDB Graph Boundary
            </div>
            <div className="font-semibold text-white truncate">
              {activeTenantInfo?.display_name || tenantId}
            </div>
            <div className="font-mono text-[11px] text-cyan-300 truncate">
              Graph: {activeTenantInfo?.graph_name || `ah_tenant_${tenantId}`}
            </div>
            <p className="text-[11px] text-slate-400 leading-normal">
              Enforced at repository layer (BR-001). Zero cross-tenant reads permitted.
            </p>
          </div>
        </aside>

        {/* Active View Content */}
        <main className="flex-1 p-4 lg:p-6 overflow-x-hidden">{children}</main>
      </div>

      {/* Provision New Tenant Modal (FR-013) */}
      {showNewTenantModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <form
            onSubmit={handleCreateTenant}
            className="bg-[#0b1021] border border-slate-700 rounded-xl max-w-md w-full p-5 space-y-4 shadow-2xl"
          >
            <h3 className="text-base font-bold text-white">
              Provision Isolated Tenant Graph (FR-013)
            </h3>
            <p className="text-xs text-slate-400">
              Creates a brand-new, empty FalkorDB graph with opaque SHA-256 naming.
            </p>
            <div>
              <label className="block text-xs text-slate-300 mb-1">
                Tenant Slug (lowercase alphanumeric/hyphens)
              </label>
              <input
                type="text"
                required
                pattern="^[a-z0-9][a-z0-9_-]{1,62}$"
                placeholder="e.g. gamma-ml"
                value={newTenantId}
                onChange={(e) => setNewTenantId(e.target.value)}
                className="w-full bg-[#060913] border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-300 mb-1">Display Name</label>
              <input
                type="text"
                required
                placeholder="e.g. Tenant C — Gamma ML Platform"
                value={newTenantName}
                onChange={(e) => setNewTenantName(e.target.value)}
                className="w-full bg-[#060913] border border-slate-700 rounded-lg px-3 py-2 text-xs text-white"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowNewTenantModal(false)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 text-xs text-slate-300 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white"
              >
                Provision Tenant
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};