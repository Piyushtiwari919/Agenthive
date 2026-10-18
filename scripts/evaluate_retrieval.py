import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "apps" / "api"))

from app.services.benchmark_service import get_benchmark_service  # noqa: E402


def main() -> None:
    print("Evaluating 25-Entity Answer Key (FR-003) & 10-Query Golden Set Top-3 Precision (FR-007 / K-03)...")
    report = get_benchmark_service().evaluate_retrieval()
    print(json.dumps(report.model_dump(mode="json"), indent=2))
    print(
        f"\nEntity Extraction Coverage: {report.entity_key_extracted}/{report.entity_key_total} "
        f"({report.entity_coverage_percent}% — Target >=70%: {report.entity_target_met})\n"
        f"Golden Top-3 Retrieval Precision: {report.top3_precision_percent}% "
        f"(Target >=80%: {report.precision_target_met})\n"
        f"Context Assembly p95 Latency: {report.context_p95_ms} ms (Target <2000 ms)"
    )
    if not (report.entity_target_met and report.precision_target_met):
        sys.exit(1)


if __name__ == "__main__":
    main()