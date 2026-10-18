import React, { useEffect, useState } from "react";
import { Clock, FileText, ShieldCheck, User, X } from "lucide-react";
import { apiClient } from "../api/client";
import type { ProvenanceResponse } from "../api/types";
import { StatusBadge } from "./StatusBadge";

interface ProvenanceDrawerProps {
  tenantId: string;
  targetId: string | null;
  targetLabel?: string;
  onClose: () => void;
}

export const ProvenanceDrawer: React.FC<ProvenanceDrawerProps> = ({
  tenantId,
  targetId,
  targetLabel,
  onClose,
}) => {
  const [data, setData] = useState<ProvenanceResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!targetId) {
      setData(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);

    apiClient
      .getProvenance(tenantId, targetId)
      .then((res) => {
        if (!cancelled) {
          setData(res);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message || "Failed to load source episode provenance.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [tenantId, targetId]);

  if (!targetId) return null;

  return (
    <div
      role="dialog"
      aria-label="Source Episode Provenance Inspector"
      className="fixed inset-y-0 right-0 z-50 w-full max-w-lg bg-[#0b1021] border-l border-slate-800 shadow-2xl flex flex-col"
    >
      <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-[#060913]">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-cyan-400" />
          <div>
            <h2 className="text-sm font-bold text-white">
              Source Episode Provenance (FR-008 / BR-002)
            </h2>
            <p className="text-xs text-slate-400 font-mono">
              Target: {targetLabel || targetId} ({targetId})
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          aria-label="Close provenance drawer"
          className="p-1.5 rounded-lg bg-slate-800/80 text-slate-300 hover:text-white"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {loading && (
          <div className="p-6 text-center text-sm text-slate-400">
            Traversing FalkorDB provenance edges for {targetId}...
          </div>
        )}

        {error && (
          <div className="p-4 rounded-lg bg-rose-950/60 border border-rose-700 text-rose-200 text-xs">
            {error}
          </div>
        )}

        {!loading && !error && data && (
          <>
            <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800 text-xs flex items-center justify-between">
              <span className="text-slate-400">
                Record Type: <strong className="text-white">{data.target_type}</strong>
              </span>
              <span className="text-slate-400">
                Tenant Scope: <strong className="text-cyan-300 font-mono">{data.tenant_id}</strong>
              </span>
              <span className="text-slate-400">
                Evidence Episodes: <strong className="text-emerald-300">{data.source_episodes.length}</strong>
              </span>
            </div>

            {data.source_episodes.map((ep) => (
              <div
                key={ep.id}
                className="p-4 rounded-xl bg-slate-900/70 border border-indigo-500/30 space-y-3"
              >
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <span className="font-mono text-xs text-cyan-300 font-semibold flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5" />
                    {ep.id}
                  </span>
                  <StatusBadge status={ep.extraction_status} />
                </div>

                <p className="text-sm text-slate-100 leading-relaxed bg-[#060913] p-3 rounded-lg border border-slate-800">
                  {ep.content}
                </p>

                <div className="grid grid-cols-2 gap-2 text-xs text-slate-400 pt-1">
                  <div className="flex items-center gap-1.5">
                    <User className="w-3.5 h-3.5 text-indigo-400" />
                    <span>Actor: {ep.agent_name} ({ep.agent_id})</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-indigo-400" />
                    <span>{new Date(ep.timestamp).toLocaleString()}</span>
                  </div>
                  <div>
                    Session: <span className="font-mono text-slate-200">{ep.session_id}</span>
                  </div>
                  <div>
                    Importance: <span className="font-mono text-emerald-300">{ep.importance_score.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
};