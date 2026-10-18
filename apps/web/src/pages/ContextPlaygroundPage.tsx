import React, { useEffect, useState } from "react";
import {
  BookOpen,
  Clock,
  ExternalLink,
  FileText,
  GitFork,
  Layers,
  Search,
  Sparkles,
} from "lucide-react";
import { apiClient } from "../api/client";
import type { AgentRecord, AssembledContextPackage } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";
import { useToast } from "../components/ToastProvider";

interface ContextPlaygroundPageProps {
  tenantId: string;
  onOpenProvenance: (targetId: string, label?: string) => void;
}

const SAMPLE_QUERIES: Record<string, string[]> = {
  "alpha-eng": [
    "PaymentGateway timeout_ms spike mitigation and CircuitBreaker pool configuration",
    "AuthService token_ttl_min signing key rotation and TokenVault JWKS rollover",
    "LedgerWorker reconciliation batch deadlock recovery and FalkorDB graph transaction retry",
  ],
  "beta-sec": [
    "SIEMIngestor credential stuffing burst against WAFGateway and CertManager rotation",
    "IAMController least-privilege policy and KMSRotator session keys",
  ],
};

export const ContextPlaygroundPage: React.FC<ContextPlaygroundPageProps> = ({
  tenantId,
  onOpenProvenance,
}) => {
  const { notify } = useToast();
  const [query, setQuery] = useState<string>("");
  const [agentId, setAgentId] = useState<string>("");
  const [agents, setAgents] = useState<AgentRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [pkg, setPkg] = useState<AssembledContextPackage | null>(null);

  useEffect(() => {
    setPkg(null);
    setQuery("");
    apiClient
      .listAgents(tenantId)
      .then((list) => {
        setAgents(list);
        if (list.length > 0) {
          const coder = list.find((a) => a.id.includes("coder") || a.id.includes("remediator"));
          setAgentId(coder ? coder.id : list[0].id);
        } else {
          setAgentId("");
        }
      })
      .catch(() => setAgents([]));
  }, [tenantId]);

  const handleAssemble = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    try {
      const result = await apiClient.assembleContext(tenantId, {
        query: query.trim(),
        agent_id: agentId || undefined,
        max_episodes: 5,
      });
      setPkg(result);
    } catch (err) {
      notify("error", "Context Assembly Failed", (err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const samples = SAMPLE_QUERIES[tenantId] || SAMPLE_QUERIES["alpha-eng"];

  return (
    <div className="space-y-5">
      <div className="p-4 rounded-xl bg-[#0b1021] border border-slate-800 space-y-4">
        <div>
          <h1 className="text-lg font-bold text-white flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-indigo-400" />
            Unified Four-Part Context Assembly Playground (FR-006 / FR-007)
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Issues a single request to <code className="text-cyan-300">POST /api/v1/context/assemble</code> returning ranked Episodic memories, Semantic Entities/Facts, Applicable Procedures, and Pending Handoffs with source provenance.
          </p>
        </div>

        <form onSubmit={handleAssemble} className="grid grid-cols-1 lg:grid-cols-4 gap-3">
          <div className="lg:col-span-2">
            <label className="block text-xs text-slate-300 mb-1">
              Task or Query Description
            </label>
            <input
              type="text"
              required
              placeholder="Enter agent task or technical query..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full bg-[#060913] border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-400"
            />
          </div>

          <div>
            <label className="block text-xs text-slate-300 mb-1">
              Requesting Agent (for Pending Handoffs)
            </label>
            <select
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
              className="w-full bg-[#060913] border border-slate-700 rounded-lg px-3 py-2 text-xs text-cyan-300 font-mono"
            >
              <option value="">All / Unspecified Agent</option>
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.id} ({a.name})
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-end">
            <button
              type="submit"
              disabled={loading}
              className="w-full inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-xs font-semibold text-white"
            >
              <Search className="w-4 h-4" />
              {loading ? "Assembling Context..." : "Assemble Unified Context"}
            </button>
          </div>
        </form>

        {/* Sample Queries */}
        <div className="flex items-center gap-2 flex-wrap pt-1">
          <span className="text-xs text-slate-400">Sample Queries:</span>
          {samples.map((sq, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => setQuery(sq)}
              className="text-xs px-2.5 py-1 rounded-full bg-slate-900 hover:bg-slate-800 text-indigo-300 border border-slate-700"
            >
              {sq.slice(0, 58)}...
            </button>
          ))}
        </div>
      </div>

      {/* Results Display */}
      {pkg && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 p-3 rounded-xl bg-slate-900/90 border border-indigo-500/30 text-xs">
            <div className="flex items-center gap-4">
              <span>
                Tenant: <strong className="text-cyan-300 font-mono">{pkg.tenant_id}</strong>
              </span>
              <span>
                Agent: <strong className="text-white font-mono">{pkg.requesting_agent_id || "any"}</strong>
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-emerald-950 text-emerald-300 border border-emerald-700/60 font-mono">
                <Clock className="w-3.5 h-3.5" />
                Assembled in {pkg.duration_ms} ms (Target &lt; 2000 ms)
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Group 1: Ranked Episodic Memories */}
            <div className="p-4 rounded-xl bg-[#0b1021] border border-slate-800 space-y-3">
              <h2 className="text-sm font-bold text-white flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-indigo-400" />
                  1. Ranked Episodic Memories ({pkg.episodes.length})
                </span>
                <span className="text-[11px] font-normal text-slate-400">
                  FR-007 Importance Tiebreaker
                </span>
              </h2>
              {pkg.episodes.length === 0 ? (
                <p className="text-xs text-slate-400">No matching episodes found.</p>
              ) : (
                pkg.episodes.map((item, i) => (
                  <div
                    key={item.episode.id}
                    className="p-3 rounded-lg bg-[#060913] border border-slate-800 space-y-2"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-mono text-indigo-300 font-semibold">
                        #{i + 1} • {item.episode.id} (Session: {item.episode.session_id})
                      </span>
                      <span className="font-mono text-emerald-300">
                        Score: {item.relevance_score.toFixed(2)} | Imp: {item.episode.importance_score.toFixed(2)}
                      </span>
                    </div>
                    <p className="text-xs text-slate-200 leading-relaxed">{item.episode.content}</p>
                    <div className="text-[11px] text-slate-400 font-mono bg-slate-900/80 px-2 py-1 rounded">
                      Why included: {item.trace.explanation}
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Group 2: Semantic Entities & Facts */}
            <div className="p-4 rounded-xl bg-[#0b1021] border border-slate-800 space-y-3">
              <h2 className="text-sm font-bold text-white flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Layers className="w-4 h-4 text-violet-400" />
                  2. Semantic Entities ({pkg.entities.length}) & Facts ({pkg.facts.length})
                </span>
                <span className="text-[11px] font-normal text-slate-400">FR-008 Provenance</span>
              </h2>
              <div className="flex flex-wrap gap-1.5">
                {pkg.entities.map((ent) => (
                  <button
                    key={ent.id}
                    type="button"
                    onClick={() => onOpenProvenance(ent.id, ent.canonical_name)}
                    className="px-2 py-1 rounded bg-violet-950/70 border border-violet-700/60 text-violet-200 text-xs font-mono hover:bg-violet-900"
                  >
                    {ent.canonical_name} ({ent.entity_type})
                  </button>
                ))}
              </div>
              <div className="space-y-2 max-h-80 overflow-y-auto">
                {pkg.facts.map((f) => (
                  <div
                    key={f.id}
                    className="p-2.5 rounded-lg bg-[#060913] border border-slate-800 flex items-center justify-between gap-2 text-xs"
                  >
                    <div>
                      <span className="font-semibold text-white">{f.subject_name}</span>
                      <span className="text-slate-400 font-mono">.{f.predicate} = </span>
                      <span className="text-cyan-300 font-mono font-semibold">{f.object_value}</span>
                      <div className="text-[11px] text-slate-400 mt-0.5">
                        Source Episode: <span className="font-mono">{f.source_episode_id}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <StatusBadge status={f.status} />
                      <button
                        type="button"
                        onClick={() => onOpenProvenance(f.id, `${f.subject_name}.${f.predicate}`)}
                        className="px-2 py-1 rounded bg-slate-800 hover:bg-indigo-600 text-white text-[11px] inline-flex items-center gap-1"
                      >
                        <ExternalLink className="w-3 h-3" />
                        Source
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Group 3: Applicable Procedures */}
            <div className="p-4 rounded-xl bg-[#0b1021] border border-slate-800 space-y-3">
              <h2 className="text-sm font-bold text-white flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <BookOpen className="w-4 h-4 text-emerald-400" />
                  3. Applicable Procedures ({pkg.procedures.length})
                </span>
                <span className="text-[11px] font-normal text-slate-400">FR-004 / BR-003</span>
              </h2>
              {pkg.procedures.length === 0 ? (
                <p className="text-xs text-slate-400">No trigger-matched procedures found.</p>
              ) : (
                pkg.procedures.map((proc) => (
                  <div
                    key={proc.id}
                    className="p-3 rounded-lg bg-[#060913] border border-slate-800 space-y-2 text-xs"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-bold text-white">{proc.name}</span>
                      <StatusBadge status={proc.status} />
                    </div>
                    <div className="text-slate-300">
                      <strong className="text-slate-400">Trigger:</strong> {proc.trigger_text}
                    </div>
                    <ol className="list-decimal list-inside space-y-1 text-slate-200 pl-1">
                      {proc.steps.map((s, idx) => (
                        <li key={idx}>{s}</li>
                      ))}
                    </ol>
                    <div className="flex items-center justify-between pt-1 text-[11px] text-slate-400">
                      <span>
                        Corroborating Episodes: <strong>{proc.evidence_count}</strong> ({proc.confirmation_method})
                      </span>
                      <button
                        type="button"
                        onClick={() => onOpenProvenance(proc.id, proc.name)}
                        className="text-cyan-300 hover:underline inline-flex items-center gap-1"
                      >
                        <ExternalLink className="w-3 h-3" />
                        Inspect Evidence ({proc.source_episode_ids.length})
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Group 4: Pending Handoffs */}
            <div className="p-4 rounded-xl bg-[#0b1021] border border-slate-800 space-y-3">
              <h2 className="text-sm font-bold text-white flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <GitFork className="w-4 h-4 text-cyan-400" />
                  4. Pending Agent Handoffs ({pkg.pending_handoffs.length})
                </span>
                <span className="text-[11px] font-normal text-slate-400">FR-010 / FR-011</span>
              </h2>
              {pkg.pending_handoffs.length === 0 ? (
                <p className="text-xs text-slate-400">
                  No pending handoffs queued for agent {pkg.requesting_agent_id || "any"}.
                </p>
              ) : (
                pkg.pending_handoffs.map((ho) => (
                  <div
                    key={ho.id}
                    className="p-3 rounded-lg bg-[#060913] border border-cyan-500/30 space-y-2 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-white">{ho.task_title}</span>
                      <StatusBadge status={ho.status} />
                    </div>
                    <div className="font-mono text-[11px] text-cyan-300">
                      {ho.origin_agent_id} &rarr; {ho.target_agent_id}
                    </div>
                    <p className="text-slate-300">{ho.context_summary}</p>
                    <pre className="p-2 rounded bg-slate-900 text-[11px] font-mono text-emerald-300 overflow-x-auto">
                      {JSON.stringify(ho.state_payload, null, 2)}
                    </pre>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};