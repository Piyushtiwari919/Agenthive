import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "apps" / "api"))

from app.services.benchmark_service import get_benchmark_service  # noqa: E402


def main() -> None:
    print("Running 20-Scenario Agent Handoff Verification Suite (FR-011 / K-02)...")
    report = get_benchmark_service().run_handoff_suite()
    print(json.dumps(report.model_dump(mode="json"), indent=2))
    print(
        f"\nResult: {report.valid_delivered_count}/{report.valid_scenarios_count} valid handoffs delivered, "
        f"{report.invalid_rejected_count}/{report.invalid_scenarios_count} invalid handoffs rejected "
        f"(Overall Target Met: {report.target_met})"
    )
    if not report.target_met:
        sys.exit(1)


if __name__ == "__main__":
    main()