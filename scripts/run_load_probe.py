import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "apps" / "api"))

from app.services.benchmark_service import get_benchmark_service  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="AgentHive High-Concurrency Load Probe")
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Duration in seconds (default 60s per NFR-002)",
    )
    args = parser.parse_args()

    print(f"Running high-concurrency load probe for {args.duration}s (50 readers + 10 writers per tenant)...")
    report = get_benchmark_service().run_load_probe(duration_sec=args.duration)
    print(json.dumps(report, indent=2))

    print(
        f"\n[Result] Total Requests: {report['total_requests']} | Errors: {report['total_errors']} "
        f"({report['error_rate_percent']}%) — Target <5%: {report['error_rate_target_met']}\n"
        f"Write p95: {report['write_latency_ms']['p95']} ms (Target <200ms: {report['write_latency_ms']['target_p95_met']})\n"
        f"Context Assembly p95: {report['context_assembly_latency_ms']['p95']} ms (Target <2000ms: {report['context_assembly_latency_ms']['target_p95_met']})"
    )
    if not (report["error_rate_target_met"] and report["write_latency_ms"]["target_p95_met"] and report["context_assembly_latency_ms"]["target_p95_met"]):
        sys.exit(1)


if __name__ == "__main__":
    main()