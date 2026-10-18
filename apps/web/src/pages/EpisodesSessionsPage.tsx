import React, { useCallback, useEffect, useState } from "react";
import { Clock, MessageSquare, Plus, Send } from "lucide-react";
import { apiClient } from "../api/client";
import type { EpisodeRecord, SessionSummary } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";
import { useToast } from "../components/ToastProvider";

interface EpisodesSessionsPageProps {
  tenantId: string;
  onRefreshGraph: () => Promise<void>;
}

export const EpisodesSessionsPage: React.FC<EpisodesSessionsPageProps> = ({
  tenantId,
  onRefreshGraph,
}) => {
  const { notify } = useToast();
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string>("");
  const [episodes, setEpisodes] = useState<EpisodeRecord[]>([]);
  const [startTimeFilter, setStartTimeFilter] = useState<string>("");
  const [endTimeFilter, setEndTimeFilter] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);

  // New Episode Form
  const [newContent, setNewContent] = useState<string>("");
  const [newAgentId, setNewAgentId] = useState<string>("agent-alpha-research");
  const [newSessionId, setNewSessionId] = useState<string>("sess-live-demo");
  const [newImportance, setNewImportance] = useState<number>(0.85);

  const loadSessionsAndEpisodes = useCallback(async () => {
    setLoading(true);
    try {
      const sessList = await apiClient.listSessions(tenantId);
      setSessions(sessList);
      if (selectedSessionId) {
        const hist = await apiClient.getSessionHistory(
          tenantId,
          selectedSessionId,
          startTimeFilter ? new Date(startTimeFilter).toISOString() : undefined,
          endTimeFilter ? new Date(endTimeFilter).toISOString() : undefined
        );
        setEpisodes(hist.episodes);
      } else {
        const epList = await apiClient.listEpisodes(tenantId);
        setEpisodes(epList);
      }
    } catch (err) {
      notify("error", "Failed to load episodes", (err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [tenantId, selectedSessionId, startTimeFilter, endTimeFilter, notify]);

  useEffect(() => {
    setSelectedSessionId("");
    setEpisodes([]);
  }, [tenantId]);

  useEffect(() => {
    void loadSessionsAndEpisodes();
  }, [loadSessionsAndEpisodes]);

  const handleRecordEpisode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newContent.trim()) return;
    try {
      const created = await apiClient.createEpisode(tenantId, {
        content: newContent.trim(),
        agent_id: newAgentId.trim(),
        session_id: newSessionId.trim(),
        importance_score: newImportance,
      });
      notify(
        "success",
        `Episode ${created.id} Persisted`,
        `Extraction Status: ${created.extraction_status}`
      );
      setNewContent("");
      await loadSessionsAndEpisodes();
      await onRefreshGraph();
    } catch (err) {
      notify("error", "Failed to record episode", (err as Error).message);
    }
  };

  return (
    <div className="space-y-5">
      {/* Capture New Episode Form (FR-001) */}
      <form
        onSubmit={handleRecordEpisode}
        className="p-4 rounded-xl bg-[#0b1021] border border-slate-800 space-y-3"
      >
        <h2 className="text-sm font-bold text-white flex items-center gap-2">
          <Plus className="w-4 h-4 text-indigo-400" />
          Capture New Episodic Interaction (FR-001)
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Acting Agent ID</label>
            <input
              type="text"
              required
              value={newAgentId}
              onChange={(e) => setNewAgentId(e.target.value)}
              className="w-full bg-[#060913] border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white font-mono"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Session Identifier</label>
            <input
              type="text"
              required
              value={newSessionId}
              onChange={(e) => setNewSessionId(e.target.value)}
              className="w-full bg-[#060913] border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white font-mono"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">
              Importance Score ({newImportance.toFixed(2)})
            </label>
            <input
              type="range"
              min="0.1"
              max="1.0"
              step="0.05"
              value={newImportance}
              onChange={(e) => setNewImportance(parseFloat(e.target.value))}
              className="w-full mt-2"
            />
          </div>
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            required
            placeholder="e.g. Investigated PaymentGateway spike. FACT: PaymentGateway timeout_ms = 5000ms."
            value={newContent}
            onChange={(e) => setNewContent(e.target.value)}
            className="flex-1 bg-[#060913] border border-slate-700 rounded-lg px-3 py-2 text-xs text-white"
          />
          <button
            type="submit"
            className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white inline-flex items-center gap-1.5"
          >
            <Send className="w-3.5 h-3.5" />
            Persist Episode
          </button>
        </div>
      </form>

      {/* Sessions Sidebar + Chronological History (FR-005) */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-[#0b1021] border border-slate-800 space-y-2">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Tenant Sessions ({sessions.length})
          </h3>
          <button
            type="button"
            onClick={() => setSelectedSessionId("")}
            className={`w-full text-left px-3 py-2 rounded-lg text-xs font-medium ${
              selectedSessionId === ""
                ? "bg-indigo-600 text-white"
                : "bg-slate-900 text-slate-300 hover:bg-slate-800"
            }`}
          >
            All Recent Episodes
          </button>
          <div className="space-y-1.5 max-h-[420px] overflow-y-auto pt-1">
            {sessions.map((s) => (
              <button
                key={s.session_id}
                type="button"
                onClick={() => setSelectedSessionId(s.session_id)}
                className={`w-full text-left p-2.5 rounded-lg border text-xs transition-colors ${
                  selectedSessionId === s.session_id
                    ? "bg-indigo-950/90 border-indigo-500 text-white"
                    : "bg-[#060913] border-slate-800 text-slate-300 hover:border-slate-700"
                }`}
              >
                <div className="font-mono font-semibold text-cyan-300 truncate">{s.session_id}</div>
                <div className="truncate text-slate-300 mt-0.5">{s.title}</div>
                <div className="text-[10px] text-slate-400 mt-1">
                  {s.episode_count} turns • {new Date(s.last_activity_at).toLocaleTimeString()}
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="lg:col-span-3 p-4 rounded-xl bg-[#0b1021] border border-slate-800 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-cyan-400" />
              {selectedSessionId
                ? `Chronological Session History: ${selectedSessionId} (FR-005)`
                : `Tenant Episode Log (${episodes.length})`}
            </h3>
            {selectedSessionId && (
              <div className="flex items-center gap-2 text-xs">
                <input
                  type="datetime-local"
                  value={startTimeFilter}
                  onChange={(e) => setStartTimeFilter(e.target.value)}
                  className="bg-[#060913] border border-slate-700 rounded px-2 py-1 text-xs text-slate-200"
                />
                <span className="text-slate-500">to</span>
                <input
                  type="datetime-local"
                  value={endTimeFilter}
                  onChange={(e) => setEndTimeFilter(e.target.value)}
                  className="bg-[#060913] border border-slate-700 rounded px-2 py-1 text-xs text-slate-200"
                />
              </div>
            )}
          </div>

          {loading ? (
            <div className="p-8 text-center text-xs text-slate-400">Loading episodes...</div>
          ) : episodes.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-400">
              No episodes found for this filter.
            </div>
          ) : (
            <div className="space-y-2.5 max-h-[520px] overflow-y-auto pr-1">
              {episodes.map((ep) => (
                <div
                  key={ep.id}
                  className="p-3.5 rounded-xl bg-[#060913] border border-slate-800 space-y-2 text-xs"
                >
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-semibold text-cyan-300">{ep.id}</span>
                      <span className="text-slate-400">•</span>
                      <span className="font-mono text-indigo-300">{ep.agent_id}</span>
                      <span className="text-slate-400">•</span>
                      <span className="font-mono text-slate-400">{ep.session_id}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-emerald-300">
                        Importance: {ep.importance_score.toFixed(2)}
                      </span>
                      <StatusBadge status={ep.extraction_status} />
                    </div>
                  </div>
                  <p className="text-slate-100 leading-relaxed">{ep.content}</p>
                  <div className="flex items-center gap-2 text-[11px] text-slate-400">
                    <Clock className="w-3 h-3" />
                    <span>{new Date(ep.timestamp).toISOString()}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};