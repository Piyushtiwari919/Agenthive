import React from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { BookOpen, Cpu, FileText, GitFork, Layers, Sparkles } from "lucide-react";

export interface CustomGraphNodeData extends Record<string, unknown> {
  label: string;
  nodeType: string;
  tier: string;
  status?: string;
  isGlowing: boolean;
}

export const AgentHiveGraphNode: React.FC<NodeProps> = ({ data }) => {
  const nodeData = data as unknown as CustomGraphNodeData;
  const { label, nodeType, tier, status, isGlowing } = nodeData;

  let borderClass = "border-slate-700 bg-[#0b1021]/95";
  let badgeClass = "bg-slate-800 text-slate-300";
  let IconComponent = Layers;

  if (tier === "EPISODIC") {
    borderClass = "border-indigo-500/60 bg-indigo-950/50";
    badgeClass = "bg-indigo-900/80 text-indigo-200";
    IconComponent = FileText;
  } else if (tier === "SEMANTIC") {
    borderClass = "border-violet-500/60 bg-violet-950/50";
    badgeClass = "bg-violet-900/80 text-violet-200";
    IconComponent = Layers;
  } else if (tier === "PROCEDURAL") {
    borderClass =
      status === "CONFIRMED"
        ? "border-emerald-500/80 bg-emerald-950/50"
        : "border-amber-500/70 bg-amber-950/50";
    badgeClass =
      status === "CONFIRMED"
        ? "bg-emerald-900/80 text-emerald-200"
        : "bg-amber-900/80 text-amber-200";
    IconComponent = BookOpen;
  } else if (tier === "COORDINATION") {
    borderClass = "border-cyan-500/60 bg-cyan-950/40";
    badgeClass = "bg-cyan-900/80 text-cyan-200";
    IconComponent = nodeType === "Agent" ? Cpu : GitFork;
  }

  return (
    <div
      className={`px-3 py-2 rounded-xl border shadow-lg min-w-[165px] max-w-[230px] transition-all ${borderClass} ${
        isGlowing ? "procedure-node-active-glow" : ""
      }`}
    >
      <Handle type="target" position={Position.Top} className="!bg-slate-400 !w-2 !h-2" />
      <div className="flex items-center justify-between gap-1.5 mb-1">
        <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono uppercase ${badgeClass}`}>
          <IconComponent className="w-3 h-3" />
          {nodeType}
        </span>
        {status && (
          <span className="text-[10px] font-mono text-slate-300 px-1.5 py-0.5 rounded bg-black/40">
            {status}
          </span>
        )}
      </div>
      <div className="text-xs font-semibold text-white truncate" title={label}>
        {label}
      </div>
      {isGlowing && (
        <div className="mt-1.5 flex items-center gap-1 text-[10px] font-semibold text-cyan-300">
          <Sparkles className="w-3 h-3" />
          ACTIVE EXECUTION
        </div>
      )}
      <Handle type="source" position={Position.Bottom} className="!bg-slate-400 !w-2 !h-2" />
    </div>
  );
};