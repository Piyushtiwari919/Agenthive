import React from "react";
import { Filter, RefreshCw } from "lucide-react";
import type { MemoryTier } from "../api/types";

interface GraphFilterBarProps {
  selectedTier: MemoryTier | "ALL";
  onSelectTier: (tier: MemoryTier | "ALL") => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onRefresh: () => void;
  totalNodes: number;
  totalEdges: number;
}

export const GraphFilterBar: React.FC<GraphFilterBarProps> = ({
  selectedTier,
  onSelectTier,
  searchQuery,
  onSearchChange,
  onRefresh,
  totalNodes,
  totalEdges,
}) => {
  const tiers: Array<{ id: MemoryTier | "ALL"; label: string }> = [
    { id: "ALL", label: "All Tiers" },
    { id: "EPISODIC", label: "Episodic" },
    { id: "SEMANTIC", label: "Semantic" },
    { id: "PROCEDURAL", label: "Procedural" },
    { id: "COORDINATION", label: "Agents & Handoffs" },
  ];

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl bg-[#0b1021] border border-slate-800">
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="text-xs text-slate-400 flex items-center gap-1 mr-1">
          <Filter className="w-3.5 h-3.5 text-indigo-400" />
          Tier Filter:
        </span>
        {tiers.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => onSelectTier(t.id)}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
              selectedTier === t.id
                ? "bg-indigo-600 text-white"
                : "bg-slate-900 text-slate-300 hover:bg-slate-800"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="flex items-center gap-2.5">
        <input
          type="text"
          placeholder="Filter graph nodes..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="bg-[#060913] border border-slate-700 rounded-lg px-2.5 py-1 text-xs text-white focus:outline-none focus:border-cyan-400"
        />
        <span className="text-xs text-slate-400 font-mono">
          {totalNodes} nodes • {totalEdges} edges
        </span>
        <button
          type="button"
          onClick={onRefresh}
          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-200"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh Graph
        </button>
      </div>
    </div>
  );
};