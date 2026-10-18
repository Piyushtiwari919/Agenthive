import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "apps" / "api"))

from app.services.benchmark_service import get_benchmark_service  # noqa: E402


def main() -> None:
    print("Running 10-Case Adversarial Cross-Tenant Leakage Probe Suite (FR-014 / K-06)...")
    report = get_benchmark_service().run_isolation_probe()
    print(json.dumps(report.model_dump(mode="json"), indent=2))
    print(
        f"\nResult: {report.passed_cases}/{report.total_cases} cases passed "
        f"({report.pass_rate_percent}%) — Zero Leakage Verified: {report.zero_leakage_verified}"
    )
    if not report.zero_leakage_verified:
        sys.exit(1)


if __name__ == "__main__":
    main()