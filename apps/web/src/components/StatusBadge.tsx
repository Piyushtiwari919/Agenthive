import React from "react";
import {
  AlertTriangle,
  Archive,
  CheckCircle2,
  Clock,
  Sparkles,
  XCircle,
} from "lucide-react";

interface StatusBadgeProps {
  status: string;
  size?: "sm" | "md";
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = "sm" }) => {
  const normalized = (status || "UNKNOWN").toUpperCase();
  const baseClasses =
    size === "sm"
      ? "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border"
      : "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border";

  switch (normalized) {
    case "CONFIRMED":
    case "COMPLETED":
    case "CURRENT":
    case "ACTIVE":
    case "READY":
      return (
        <span className={`${baseClasses} bg-emerald-950/70 text-emerald-300 border-emerald-700/60`}>
          <CheckCircle2 className="w-3 h-3 shrink-0" />
          {normalized}
        </span>
      );
    case "PROPOSED":
    case "PENDING":
    case "ACCEPTED":
      return (
        <span className={`${baseClasses} bg-amber-950/70 text-amber-300 border-amber-700/60`}>
          <Clock className="w-3 h-3 shrink-0" />
          {normalized}
        </span>
      );
    case "IN_PROGRESS":
      return (
        <span className={`${baseClasses} bg-cyan-950/80 text-cyan-200 border-cyan-500/70`}>
          <Sparkles className="w-3 h-3 shrink-0" />
          {normalized}
        </span>
      );
    case "SUPERSEDED":
    case "ARCHIVED":
    case "IDLE":
      return (
        <span className={`${baseClasses} bg-slate-800/80 text-slate-300 border-slate-600/60`}>
          <Archive className="w-3 h-3 shrink-0" />
          {normalized}
        </span>
      );
    case "DEFERRED":
      return (
        <span className={`${baseClasses} bg-violet-950/80 text-violet-300 border-violet-700/60`}>
          <AlertTriangle className="w-3 h-3 shrink-0" />
          {normalized}
        </span>
      );
    case "FAILED":
    case "CANCELLED":
    case "OFFLINE":
      return (
        <span className={`${baseClasses} bg-rose-950/80 text-rose-300 border-rose-700/60`}>
          <XCircle className="w-3 h-3 shrink-0" />
          {normalized}
        </span>
      );
    default:
      return (
        <span className={`${baseClasses} bg-indigo-950/70 text-indigo-200 border-indigo-700/60`}>
          {normalized}
        </span>
      );
  }
};