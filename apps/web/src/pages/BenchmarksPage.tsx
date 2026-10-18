import React, { useState } from "react";
import { CheckCircle2, Play, ShieldAlert, Sparkles, Zap } from "lucide-react";
import { apiClient } from "../api/client";
import type {
  HandoffSuiteReport,
  IsolationProbeReport,
  RetrievalEvaluationReport,
} from "../api/types";
import { StatusBadge } from "../components/StatusBadge";
import { useToast } from "../components/ToastProvider";

export const BenchmarksPage: React.FC = () => {
  const { notify } = useToast();
  const [isolationReport, setIsolationReport] = useState<IsolationProbeReport | null>(null);
  const [handoffReport, setHandoffReport] = useState<HandoffSuiteReport | null>(null);
  const [retrievalReport, setRetrievalReport] = useState<RetrievalEvaluationReport | null>(null);
  const [runningSuite, setRunningSuite] = useState<string | null>(null);
  const [outageSimulated, setOutageSimulated] = useState<boolean>(false);

  const handleRunIsolation = async () => {
    setRunningSuite("isolation");
    try {
      const rep = await apiClient.runIsolationProbe();
      setIsolationReport(rep);
      notify(
        "success",
        "10-Case Isolation Probe Complete",
        `${rep.passed_cases}/${rep.total_cases} passed (${rep.pass_rate_percent}%)`
      );
    } catch (err) {
      notify("error", "Isolation Probe Failed", (err as Error).message);
    } finally {
      setRunningSuite(null);
    }
  };

  const handleRunHandoffSuite = async () => {
    setRunningSuite("handoff");
    try {
      const rep = await apiClient.runHandoffSuite();
      setHandoffReport(rep);
      notify(
        "success",
        "20-Scenario Handoff Suite Complete",
        `${rep.valid_delivered_count}/${rep.valid_scenarios_count} valid delivered`
      );
    } catch (err) {
      notify("error", "Handoff Suite Failed", (err as Error).message);
    } finally {
      setRunningSuite(null);
    }
  };

  const handleRunRetrievalEval = async () => {
    setRunningSuite("retrieval");
    try {
      const rep = await apiClient.runRetrievalEvaluation();
      setRetrievalReport(rep);
      notify(
        "success",
        "Golden Retrieval Evaluation Complete",
        `Top-3 Precision: ${rep.top3_precision_percent}% | Entity Coverage: ${rep.entity_coverage_percent}%`
      );
    } catch (err) {
      notify("error", "Retrieval Evaluation Failed", (err as Error).message);
    } finally {
      setRunningSuite(null);
    }
  };

  const handleToggleOutage = async () => {
    try {
      const res = await apiClient.toggleExtractorOutage(!outageSimulated);
      setOutageSimulated(res.simulate_outage);
      notify(
        res.simulate_outage ? "info" : "success",
        res.simulate_outage
          ? "Simulated LLM Outage ENABLED (NFR-004)"
          : "Extractor Provider Restored",
        res.simulate_outage
          ? "New episodes will persist safely with DEFERRED status."
          : "Deferred extraction jobs will now drain automatically."
      );
    } catch (err) {
      notify("error", "Failed to toggle outage state", (err as Error).message);
    }
  };

  return (
    <div className="space-y-5">
      <div className="p-4 rounded-xl bg-[#0b1021] border border-slate-800 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-bold text-white flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-cyan-400" />
            Live Judge Verification & Acceptance Benchmarks (Track 02)
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Execute the BRD acceptance suites directly against FalkorDB. Unexecuted suites display &ldquo;NOT RUN&rdquo; until triggered.
          </p>
        </div>

        <button
          type="button"
          onClick={() => void handleToggleOutage()}
          className={`px-3.5 py-2 rounded-lg text-xs font-semibold border ${
            outageSimulated
              ? "bg-amber-950 border-amber-500 text-amber-200"
              : "bg-slate-900 border-slate-700 text-slate-300 hover:text-white"
          }`}
        >
          {outageSimulated
            ? "Disable Simulated Extractor Outage (NFR-004)"
            : "Simulate LLM Extractor Outage Drill (NFR-004)"}
        </button>
      </div>

      {/* Three Interactive Benchmark Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* 1. 10-Case Adversarial Isolation Probe */}
        <div className="p-4 rounded-xl bg-[#0b1021] border border-slate-800 space-y-3 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-cyan-300">FR-014 / NFR-005 / K-06</span>
              <StatusBadge
                status={
                  isolationReport
                    ? isolationReport.zero_leakage_verified
                      ? "COMPLETED"
                      : "FAILED"
                    : "NOT_RUN"
                }
              />
            </div>
            <h2 className="text-sm font-bold text-white">
              10-Case Cross-Tenant Leakage Probe
            </h2>
            <p className="text-xs text-slate-400">
              Probes direct ID guesses, provenance links, session history, context assembly, graph subgraphs, and cross-tenant handoffs.
            </p>
            {isolationReport && (
              <div className="p-3 rounded-lg bg-[#060913] border border-slate-800 text-xs space-y-1">
                <div className="font-bold text-emerald-300">
                  Pass Rate: {isolationReport.passed_cases}/{isolationReport.total_cases} ({isolationReport.pass_rate_percent}%)
                </div>
                <div className="max-h-48 overflow-y-auto space-y-1 pt-1">
                  {isolationReport.cases.map((c) => (
                    <div key={c.case_id} className="flex items-center justify-between text-[11px]">
                      <span className="truncate pr-2">
                        {c.case_id}: {c.name}
                      </span>
                      <span className="font-mono text-emerald-400 shrink-0">{c.actual}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
          <button
            type="button"
            disabled={runningSuite !== null}
            onClick={() => void handleRunIsolation()}
            className="w-full py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-xs font-semibold text-white inline-flex items-center justify-center gap-1.5"
          >
            <Play className="w-3.5 h-3.5" />
            {runningSuite === "isolation" ? "Running 10-Case Probe..." : "Run 10-Case Isolation Probe"}
          </button>
        </div>

        {/* 2. 20-Scenario Agent Handoff Suite */}
        <div className="p-4 rounded-xl bg-[#0b1021] border border-slate-800 space-y-3 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-cyan-300">FR-011 / OBJ-02 / K-02</span>
              <StatusBadge
                status={
                  handoffReport
                    ? handoffReport.target_met
                      ? "COMPLETED"
                      : "FAILED"
                    : "NOT_RUN"
                }
              />
            </div>
            <h2 className="text-sm font-bold text-white">
              20-Scenario Agent Handoff Suite
            </h2>
            <p className="text-xs text-slate-400">
              Executes 18 valid same-tenant handoffs and 2 invalid/cross-tenant handoffs, verifying context delivery (&ge;90% target).
            </p>
            {handoffReport && (
              <div className="p-3 rounded-lg bg-[#060913] border border-slate-800 text-xs space-y-1">
                <div className="font-bold text-emerald-300">
                  Valid Delivered: {handoffReport.valid_delivered_count}/{handoffReport.valid_scenarios_count} | Invalid Rejected: {handoffReport.invalid_rejected_count}/{handoffReport.invalid_scenarios_count}
                </div>
                <div className="max-h-48 overflow-y-auto space-y-1 pt-1">
                  {handoffReport.cases.map((c) => (
                    <div key={c.case_id} className="flex items-center justify-between text-[11px]">
                      <span className="truncate pr-2">
                        {c.case_id}: {c.name}
                      </span>
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
          <button
            type="button"
            disabled={runningSuite !== null}
            onClick={() => void handleRunHandoffSuite()}
            className="w-full py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-xs font-semibold text-white inline-flex items-center justify-center gap-1.5"
          >
            <Zap className="w-3.5 h-3.5" />
            {runningSuite === "handoff" ? "Running 20 Scenarios..." : "Run 20-Scenario Handoff Suite"}
          </button>
        </div>

        {/* 3. 25-Entity & 10-Query Golden Retrieval Evaluation */}
        <div className="p-4 rounded-xl bg-[#0b1021] border border-slate-800 space-y-3 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-cyan-300">FR-003 / FR-007 / K-03</span>
              <StatusBadge
                status={
                  retrievalReport
                    ? retrievalReport.entity_target_met && retrievalReport.precision_target_met
                      ? "COMPLETED"
                      : "FAILED"
                    : "NOT_RUN"
                }
              />
            </div>
            <h2 className="text-sm font-bold text-white">
              25-Entity & 10-Query Golden Evaluation
            </h2>
            <p className="text-xs text-slate-400">
              Measures canonical entity extraction coverage (&ge;70% target), top-3 retrieval precision (&ge;80% target), and p95 latency (&lt;2000ms).
            </p>
            {retrievalReport && (
              <div className="p-3 rounded-lg bg-[#060913] border border-slate-800 text-xs space-y-1.5">
                <div className="flex justify-between">
                  <span>25-Entity Coverage:</span>
                  <strong className="text-emerald-300 font-mono">
                    {retrievalReport.entity_key_extracted}/{retrievalReport.entity_key_total} ({retrievalReport.entity_coverage_percent}%)
                  </strong>
                </div>
                <div className="flex justify-between">
                  <span>Golden Top-3 Precision:</span>
                  <strong className="text-emerald-300 font-mono">
                    {retrievalReport.top3_precision_percent}%
                  </strong>
                </div>
                <div className="flex justify-between">
                  <span>Context Assembly p95:</span>
                  <strong className="text-cyan-300 font-mono">
                    {retrievalReport.context_p95_ms} ms
                  </strong>
                </div>
              </div>
            )}
          </div>
          <button
            type="button"
            disabled={runningSuite !== null}
            onClick={() => void handleRunRetrievalEval()}
            className="w-full py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-xs font-semibold text-white inline-flex items-center justify-center gap-1.5"
          >
            <Sparkles className="w-3.5 h-3.5" />
            {runningSuite === "retrieval" ? "Evaluating Golden Set..." : "Run Golden Set Evaluation"}
          </button>
        </div>
      </div>
    </div>
  );
};