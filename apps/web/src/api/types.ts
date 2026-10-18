export type ExtractionStatus = "PENDING" | "COMPLETED" | "DEFERRED" | "FAILED";
export type FactStatus = "CURRENT" | "SUPERSEDED";
export type ProcedureStatus = "PROPOSED" | "CONFIRMED";
export type ConfirmationMethod = "UNCONFIRMED" | "CORROBORATED_3X" | "USER_CONFIRMED";
export type AgentStatus = "ACTIVE" | "IDLE" | "OFFLINE";
export type HandoffStatus = "PENDING" | "ACCEPTED" | "IN_PROGRESS" | "COMPLETED" | "FAILED" | "CANCELLED";
export type TaskStatus = "PENDING" | "IN_PROGRESS" | "COMPLETED" | "FAILED" | "CANCELLED";
export type MemoryTier = "EPISODIC" | "SEMANTIC" | "PROCEDURAL" | "COORDINATION";

export interface TenantInfo {
  tenant_id: string;
  display_name: string;
  description?: string | null;
  graph_name: string;
  is_demo: boolean;
  created_at: string;
}

export interface ProvenanceRef {
  episode_id: string;
  session_id: string;
  agent_id: string;
  timestamp: string;
  snippet: string;
}

export interface EpisodeRecord {
  id: string;
  tenant_id: string;
  content: string;
  agent_id: string;
  agent_name: string;
  session_id: string;
  timestamp: string;
  importance_score: number;
  extraction_status: ExtractionStatus;
  archived: boolean;
  idempotency_key?: string | null;
  created_at: string;
}

export interface SessionSummary {
  session_id: string;
  tenant_id: string;
  title: string;
  started_at: string;
  last_activity_at: string;
  episode_count: number;
}

export interface SessionHistoryResponse {
  tenant_id: string;
  session_id: string;
  start_time?: string | null;
  end_time?: string | null;
  total_episodes: number;
  episodes: EpisodeRecord[];
}

export interface EntityRecord {
  id: string;
  tenant_id: string;
  canonical_key: string;
  canonical_name: string;
  entity_type: string;
  aliases: string[];
  source_episode_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface FactRecord {
  id: string;
  tenant_id: string;
  subject_entity_id: string;
  subject_name: string;
  predicate: string;
  object_value: string;
  object_entity_id?: string | null;
  status: FactStatus;
  confidence: number;
  source_episode_id: string;
  observed_at: string;
  superseded_by_id?: string | null;
  provenance?: ProvenanceRef | null;
}

export interface ProcedureRecord {
  id: string;
  tenant_id: string;
  name: string;
  trigger_text: string;
  trigger_keywords: string[];
  steps: string[];
  status: ProcedureStatus;
  confirmation_method: ConfirmationMethod;
  evidence_count: number;
  source_episode_ids: string[];
  provenance_refs: ProvenanceRef[];
  active_task_id?: string | null;
  is_currently_active: boolean;
  last_executed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProvenanceResponse {
  target_id: string;
  target_type: string;
  tenant_id: string;
  source_episodes: EpisodeRecord[];
}

export interface RelevanceTrace {
  matched_terms: string[];
  lexical_score: number;
  graph_boost: number;
  importance_score: number;
  recency_score: number;
  final_score: number;
  explanation: string;
}

export interface RankedEpisode {
  episode: EpisodeRecord;
  relevance_score: number;
  trace: RelevanceTrace;
}

export interface HandoffRecord {
  id: string;
  tenant_id: string;
  task_id: string;
  task_title: string;
  origin_agent_id: string;
  target_agent_id: string;
  context_summary: string;
  state_payload: Record<string, unknown>;
  status: HandoffStatus;
  session_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AssembledContextPackage {
  tenant_id: string;
  query: string;
  requesting_agent_id?: string | null;
  assembled_at: string;
  duration_ms: number;
  episodes: RankedEpisode[];
  entities: EntityRecord[];
  facts: FactRecord[];
  procedures: ProcedureRecord[];
  pending_handoffs: HandoffRecord[];
}

export interface AgentRecord {
  id: string;
  tenant_id: string;
  name: string;
  role: string;
  capabilities: string[];
  status: AgentStatus;
  created_at: string;
}

export interface TaskRecord {
  id: string;
  tenant_id: string;
  title: string;
  status: TaskStatus;
  owner_agent_id: string;
  session_id?: string | null;
  active_procedure_id?: string | null;
  result_summary?: string | null;
  created_at: string;
  updated_at: string;
}

export interface GraphNodeDTO {
  id: string;
  label: string;
  node_type: string;
  tier: MemoryTier;
  tenant_id: string;
  status?: string | null;
  is_glowing: boolean;
  properties: Record<string, unknown>;
}

export interface GraphEdgeDTO {
  id: string;
  source: string;
  target: string;
  label: string;
  is_active_path: boolean;
}

export interface ActiveProcedureExecution {
  procedure_id: string;
  procedure_name: string;
  task_id: string;
  task_title: string;
  task_status: string;
  agent_id: string;
}

export interface OverviewMetricsDTO {
  tenant_id: string;
  episode_count: number;
  session_count: number;
  entity_count: number;
  current_fact_count: number;
  superseded_fact_count: number;
  confirmed_procedure_count: number;
  proposed_procedure_count: number;
  registered_agent_count: number;
  pending_handoff_count: number;
  active_task_count: number;
  pending_extraction_jobs: number;
}

export interface GraphSubgraphResponse {
  tenant_id: string;
  metrics: OverviewMetricsDTO;
  active_procedures: ActiveProcedureExecution[];
  nodes: GraphNodeDTO[];
  edges: GraphEdgeDTO[];
}

export interface ProbeCaseResult {
  case_id: string;
  name: string;
  passed: boolean;
  expected: string;
  actual: string;
  duration_ms: number;
}

export interface IsolationProbeReport {
  suite_name: string;
  executed_at: string;
  total_cases: number;
  passed_cases: number;
  pass_rate_percent: number;
  zero_leakage_verified: boolean;
  cases: ProbeCaseResult[];
}

export interface HandoffSuiteReport {
  suite_name: string;
  executed_at: string;
  total_scenarios: number;
  valid_scenarios_count: number;
  valid_delivered_count: number;
  invalid_scenarios_count: number;
  invalid_rejected_count: number;
  delivery_success_rate_percent: number;
  target_met: boolean;
  cases: ProbeCaseResult[];
}

export interface RetrievalEvaluationReport {
  executed_at: string;
  tenant_id: string;
  entity_key_total: number;
  entity_key_extracted: number;
  entity_coverage_percent: number;
  entity_target_met: boolean;
  golden_queries_total: number;
  top3_precision_percent: number;
  precision_target_met: boolean;
  context_p95_ms: number;
  query_details: Array<Record<string, unknown>>;
}