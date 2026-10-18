from typing import Any, Dict, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.domain.benchmarks import (
    HandoffSuiteReport,
    IsolationProbeReport,
    RetrievalEvaluationReport,
)
from app.services.benchmark_service import get_benchmark_service
from app.workers.extraction_worker import extraction_orchestrator

router = APIRouter(prefix="/diagnostics", tags=["Diagnostics, Seeding & Benchmarks"])


class OutageToggleRequest(BaseModel):
    simulate_outage: Optional[bool] = None

class LoadProbeRequest(BaseModel):
    duration_sec: int = Field(default=15, ge=5, le=120)

@router.post("/load-probe")
def run_load_probe(req: LoadProbeRequest) -> Dict[str, Any]:
    """
    Executes high-concurrency load probe (50 readers + 10 writers per tenant) (FR-017, NFR-002).
    """
    return get_benchmark_service().run_load_probe(duration_sec=req.duration_sec)

@router.post("/seed")
def seed_demo_data() -> Dict[str, Any]:
    """
    Idempotently seeds the 120-episode synthetic demonstration dataset across alpha-eng and beta-sec (C-07).
    """
    return get_benchmark_service().seed_demo_dataset()


@router.post("/isolation-probe", response_model=IsolationProbeReport)
def run_isolation_probe() -> IsolationProbeReport:
    """
    Executes the 10-case adversarial cross-tenant leakage probe suite on demand (FR-014, K-06).
    """
    return get_benchmark_service().run_isolation_probe()


@router.post("/handoff-suite", response_model=HandoffSuiteReport)
def run_handoff_suite() -> HandoffSuiteReport:
    """
    Executes the 20 scripted handoff scenarios and verifies >=90% valid delivery (FR-011, K-02).
    """
    return get_benchmark_service().run_handoff_suite()


@router.post("/retrieval-eval", response_model=RetrievalEvaluationReport)
def run_retrieval_evaluation() -> RetrievalEvaluationReport:
    """
    Evaluates the 25-entity answer key (FR-003) and 10-query golden set top-3 precision (FR-007, K-03).
    """
    return get_benchmark_service().evaluate_retrieval()


@router.post("/extractor-outage")
def toggle_extractor_outage(req: OutageToggleRequest) -> Dict[str, Any]:
    """
    Toggles simulated LLM extractor outage for live NFR-004 resilience demonstrations.
    """
    extraction_orchestrator.set_simulate_outage(req.simulate_outage)
    return {
        "simulate_outage": extraction_orchestrator.is_outage_simulated(),
        "active_provider": extraction_orchestrator.get_active_provider().provider_name,
    }