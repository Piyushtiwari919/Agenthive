import type {
  AgentRecord,
  AssembledContextPackage,
  EntityRecord,
  EpisodeRecord,
  FactRecord,
  GraphSubgraphResponse,
  HandoffRecord,
  HandoffStatus,
  HandoffSuiteReport,
  IsolationProbeReport,
  ProcedureRecord,
  ProvenanceResponse,
  RetrievalEvaluationReport,
  SessionHistoryResponse,
  SessionSummary,
  TaskRecord,
  TaskStatus,
  TenantInfo,
} from "./types";

const rawBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";
export const API_BASE_URL = rawBaseUrl.replace(/\/+$/, "");

export class ApiClientError extends Error {
  status: number;
  code: string;

  constructor(message: string, status: number, code = "API_ERROR") {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = code;
  }
}

async function requestJson<T>(
  path: string,
  options: RequestInit = {},
  tenantId?: string
): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  if (tenantId) {
    headers.set("X-Tenant-ID", tenantId);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errMsg = `HTTP ${response.status}: ${response.statusText}`;
    let errCode = "HTTP_ERROR";
    try {
      const body = await response.json();
      if (body?.error?.message) {
        errMsg = body.error.message;
        errCode = body.error.code || errCode;
      }
    } catch {
      // Fallback to status text
    }
    throw new ApiClientError(errMsg, response.status, errCode);
  }

  return (await response.json()) as T;
}

export const apiClient = {
  getReadyStatus: () =>
    requestJson<{
      status: string;
      database: string;
      database_connected: boolean;
      environment: string;
      extraction_provider: string;
      timestamp: string;
    }>("/ready"),

  listTenants: () => requestJson<TenantInfo[]>("/tenants"),

  createTenant: (payload: {
    tenant_id: string;
    display_name: string;
    description?: string;
    is_demo?: boolean;
  }) =>
    requestJson<TenantInfo>("/tenants", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getSubgraph: (tenantId: string, maxEpisodes = 45) =>
    requestJson<GraphSubgraphResponse>(
      `/graph/subgraph?max_episodes=${maxEpisodes}`,
      {},
      tenantId
    ),

  assembleContext: (
    tenantId: string,
    payload: {
      query: string;
      agent_id?: string;
      session_id?: string;
      max_episodes?: number;
      include_superseded_facts?: boolean;
      include_proposed_procedures?: boolean;
    }
  ) =>
    requestJson<AssembledContextPackage>(
      "/context/assemble",
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
      tenantId
    ),

  listEpisodes: (tenantId: string, sessionId?: string, includeArchived = false) => {
    const params = new URLSearchParams();
    if (sessionId) params.set("session_id", sessionId);
    if (includeArchived) params.set("include_archived", "true");
    params.set("limit", "150");
    return requestJson<EpisodeRecord[]>(`/episodes?${params.toString()}`, {}, tenantId);
  },

  createEpisode: (
    tenantId: string,
    payload: {
      content: string;
      agent_id: string;
      agent_name?: string;
      session_id: string;
      session_title?: string;
      importance_score: number;
    }
  ) =>
    requestJson<EpisodeRecord>(
      "/episodes",
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
      tenantId
    ),

  listSessions: (tenantId: string) =>
    requestJson<SessionSummary[]>("/sessions?limit=100", {}, tenantId),

  getSessionHistory: (
    tenantId: string,
    sessionId: string,
    startTimeIso?: string,
    endTimeIso?: string
  ) => {
    const params = new URLSearchParams();
    if (startTimeIso) params.set("start_time", startTimeIso);
    if (endTimeIso) params.set("end_time", endTimeIso);
    return requestJson<SessionHistoryResponse>(
      `/sessions/${encodeURIComponent(sessionId)}/history?${params.toString()}`,
      {},
      tenantId
    );
  },

  listEntities: (tenantId: string, search?: string) => {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    return requestJson<EntityRecord[]>(`/entities?${params.toString()}`, {}, tenantId);
  },

  listFacts: (tenantId: string, subjectEntityId?: string, includeSuperseded = true) => {
    const params = new URLSearchParams();
    if (subjectEntityId) params.set("subject_entity_id", subjectEntityId);
    params.set("include_superseded", String(includeSuperseded));
    return requestJson<FactRecord[]>(`/facts?${params.toString()}`, {}, tenantId);
  },

  getProvenance: (tenantId: string, targetId: string) =>
    requestJson<ProvenanceResponse>(
      `/provenance/${encodeURIComponent(targetId)}`,
      {},
      tenantId
    ),

  listProcedures: (tenantId: string) =>
    requestJson<ProcedureRecord[]>("/procedures", {}, tenantId),

  confirmProcedure: (tenantId: string, procedureId: string) =>
    requestJson<ProcedureRecord>(
      `/procedures/${encodeURIComponent(procedureId)}/confirm`,
      { method: "POST" },
      tenantId
    ),

  executeProcedure: (
    tenantId: string,
    procedureId: string,
    payload: { agent_id: string; task_title?: string }
  ) =>
    requestJson<{ procedure: ProcedureRecord; task: TaskRecord }>(
      `/procedures/${encodeURIComponent(procedureId)}/execute`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
      tenantId
    ),

  completeProcedure: (
    tenantId: string,
    procedureId: string,
    payload: { agent_id: string; final_status?: TaskStatus; result_summary?: string }
  ) =>
    requestJson<ProcedureRecord>(
      `/procedures/${encodeURIComponent(procedureId)}/complete`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
      tenantId
    ),

  listAgents: (tenantId: string) =>
    requestJson<AgentRecord[]>("/agents", {}, tenantId),

  registerAgent: (
    tenantId: string,
    payload: {
      agent_id?: string;
      name: string;
      role: string;
      capabilities: string[];
    }
  ) =>
    requestJson<AgentRecord>(
      "/agents",
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
      tenantId
    ),

  listHandoffs: (tenantId: string) =>
    requestJson<HandoffRecord[]>("/handoffs", {}, tenantId),

  createHandoff: (
    tenantId: string,
    payload: {
      origin_agent_id: string;
      target_agent_id: string;
      task_title: string;
      context_summary: string;
      state_payload: Record<string, unknown>;
      session_id?: string;
    }
  ) =>
    requestJson<HandoffRecord>(
      "/handoffs",
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
      tenantId
    ),

  updateHandoffStatus: (
    tenantId: string,
    handoffId: string,
    payload: { status: HandoffStatus; acting_agent_id: string; note?: string }
  ) =>
    requestJson<HandoffRecord>(
      `/handoffs/${encodeURIComponent(handoffId)}/status`,
      {
        method: "PATCH",
        body: JSON.stringify(payload),
      },
      tenantId
    ),

  listTasks: (tenantId: string) =>
    requestJson<TaskRecord[]>("/tasks", {}, tenantId),

  updateTaskStatus: (
    tenantId: string,
    taskId: string,
    payload: { status: TaskStatus; acting_agent_id: string; result_summary?: string }
  ) =>
    requestJson<TaskRecord>(
      `/tasks/${encodeURIComponent(taskId)}/status`,
      {
        method: "PATCH",
        body: JSON.stringify(payload),
      },
      tenantId
    ),

  seedDemoDataset: () =>
    requestJson<Record<string, unknown>>("/diagnostics/seed", { method: "POST" }),

  runIsolationProbe: () =>
    requestJson<IsolationProbeReport>("/diagnostics/isolation-probe", { method: "POST" }),

  runHandoffSuite: () =>
    requestJson<HandoffSuiteReport>("/diagnostics/handoff-suite", { method: "POST" }),

  runRetrievalEvaluation: () =>
    requestJson<RetrievalEvaluationReport>("/diagnostics/retrieval-eval", { method: "POST" }),

  toggleExtractorOutage: (simulateOutage: boolean) =>
    requestJson<{ simulate_outage: boolean; active_provider: string }>(
      "/diagnostics/extractor-outage",
      {
        method: "POST",
        body: JSON.stringify({ simulate_outage: simulateOutage }),
      }
    ),
};