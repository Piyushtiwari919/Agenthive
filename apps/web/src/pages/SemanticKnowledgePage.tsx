import React, { useEffect, useState } from "react";
import { ExternalLink, Layers, ShieldCheck } from "lucide-react";
import { apiClient } from "../api/client";
import type { EntityRecord, FactRecord } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";

interface SemanticKnowledgePageProps {
  tenantId: string;
  onOpenProvenance: (targetId: string, label?: string) => void;
}

export const SemanticKnowledgePage: React.FC<SemanticKnowledgePageProps> = ({
  tenantId,
  onOpenProvenance,
}) => {
  const [entities, setEntities] = useState<EntityRecord[]>([]);
  const [facts, setFacts] = useState<FactRecord[]>([]);
  const [selectedEntityId, setSelectedEntityId] = useState<string>("");
  const [includeSuperseded, setIncludeSuperseded] = useState<boolean>(true);
  const [search, setSearch] = useState<string>("");

  useEffect(() => {
    setSelectedEntityId("");
    setEntities([]);
    setFacts([]);
  }, [tenantId]);

  useEffect(() => {
    apiClient
      .listEntities(tenantId, search || undefined)
      .then(setEntities)
      .catch(() => setEntities([]));
  }, [tenantId, search]);

  useEffect(() => {
    apiClient
      .listFacts(tenantId, selectedEntityId || undefined, includeSuperseded)
      .then(setFacts)
      .catch(() => setFacts([]));
  }, [tenantId, selectedEntityId, includeSuperseded]);

  return (
    <div className="space-y-5">
      <div className="p-4 rounded-xl bg-[#0b1021] border border-slate-800 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-bold text-white flex items-center gap-2">
            <Layers className="w-5 h-5 text-violet-400" />
            Semantic Knowledge Store: Canonical Entities & Temporal Facts (FR-003 / BR-004 / BR-007)
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Repeated entity aliases resolve to one canonical Entity record. Conflicting facts use timestamp precedence while retaining superseded values.
          </p>
        </div>

        <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
          <input
            type="checkbox"
            checked={includeSuperseded}
            onChange={(e) => setIncludeSuperseded(e.target.checked)}
            className="rounded border-slate-700"
          />
          Show Superseded Facts (Audit Trail)
        </label>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Canonical Entities List */}
        <div className="p-4 rounded-xl bg-[#0b1021] border border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white">
              Canonical Entities ({entities.length})
            </h2>
            {selectedEntityId && (
              <button
                type="button"
                onClick={() => setSelectedEntityId("")}
                className="text-xs text-cyan-300 hover:underline"
              >
                Show All
              </button>
            )}
          </div>
          <input
            type="text"
            placeholder="Search canonical name or alias..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-[#060913] border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white"
          />

          <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
            {entities.map((ent) => (
              <div
                key={ent.id}
                onClick={() => setSelectedEntityId(ent.id === selectedEntityId ? "" : ent.id)}
                className={`p-3 rounded-lg border cursor-pointer transition-colors text-xs space-y-1.5 ${
                  selectedEntityId === ent.id
                    ? "bg-violet-950/80 border-violet-500 text-white"
                    : "bg-[#060913] border-slate-800 hover:border-slate-700"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-sm text-white">{ent.canonical_name}</span>
                  <span className="px-2 py-0.5 rounded bg-slate-800 text-violet-300 font-mono text-[10px]">
                    {ent.entity_type}
                  </span>
                </div>
                <div className="text-[11px] text-slate-400">
                  Aliases: <span className="font-mono text-slate-300">{ent.aliases.join(", ")}</span>
                </div>
                <div className="flex items-center justify-between pt-1">
                  <span className="text-[10px] text-slate-400 font-mono">
                    {ent.source_episode_ids.length} source episode(s)
                  </span>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onOpenProvenance(ent.id, ent.canonical_name);
                    }}
                    className="text-[11px] text-cyan-300 hover:underline inline-flex items-center gap-1"
                  >
                    <ExternalLink className="w-3 h-3" />
                    Provenance
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Extracted Facts & Conflict History */}
        <div className="lg:col-span-2 p-4 rounded-xl bg-[#0b1021] border border-slate-800 space-y-3">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-cyan-400" />
            Semantic Facts & Temporal Precedence Ledger ({facts.length})
          </h2>

          <div className="space-y-2.5 max-h-[540px] overflow-y-auto pr-1">
            {facts.map((f) => (
              <div
                key={f.id}
                className={`p-3.5 rounded-xl border text-xs flex flex-wrap items-center justify-between gap-3 ${
                  f.status === "SUPERSEDED"
                    ? "bg-slate-900/40 border-slate-800 opacity-75"
                    : "bg-[#060913] border-slate-800"
                }`}
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-bold text-white text-sm">{f.subject_name}</span>
                    <span className="font-mono text-indigo-300">.{f.predicate}</span>
                    <span className="text-slate-400">=</span>
                    <span className="font-mono font-bold text-cyan-300 text-sm">
                      {f.object_value}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 flex flex-wrap items-center gap-3">
                    <span>Observed: {new Date(f.observed_at).toLocaleString()}</span>
                    <span>
                      Source Episode: <strong className="font-mono text-slate-200">{f.source_episode_id}</strong>
                    </span>
                    {f.superseded_by_id && (
                      <span className="text-amber-300 font-mono">
                        Superseded by: {f.superseded_by_id}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <StatusBadge status={f.status} />
                  <button
                    type="button"
                    onClick={() => onOpenProvenance(f.id, `${f.subject_name}.${f.predicate}`)}
                    className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-indigo-600 text-white text-xs inline-flex items-center gap-1"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    Source Episode
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};