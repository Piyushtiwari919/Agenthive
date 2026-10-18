from datetime import datetime
from typing import Any, Dict, List
from pydantic import BaseModel


class ProbeCaseResult(BaseModel):
    case_id: str
    name: str
    passed: bool
    expected: str
    actual: str
    duration_ms: float


class IsolationProbeReport(BaseModel):
    suite_name: str = "10-Case Cross-Tenant Leakage Probe Suite (FR-014)"
    executed_at: datetime
    total_cases: int
    passed_cases: int
    pass_rate_percent: float
    zero_leakage_verified: bool
    cases: List[ProbeCaseResult]


class HandoffSuiteReport(BaseModel):
    suite_name: str = "20-Scenario Agent Handoff Verification Suite (FR-011 / K-02)"
    executed_at: datetime
    total_scenarios: int
    valid_scenarios_count: int
    valid_delivered_count: int
    invalid_scenarios_count: int
    invalid_rejected_count: int
    delivery_success_rate_percent: float
    target_met: bool
    cases: List[ProbeCaseResult]


class RetrievalEvaluationReport(BaseModel):
    executed_at: datetime
    tenant_id: str
    entity_key_total: int
    entity_key_extracted: int
    entity_coverage_percent: float
    entity_target_met: bool
    golden_queries_total: int
    top3_precision_percent: float
    precision_target_met: bool
    context_p95_ms: float
    query_details: List[Dict[str, Any]]