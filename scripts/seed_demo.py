import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "apps" / "api"))

from app.services.benchmark_service import get_benchmark_service  # noqa: E402


def main() -> None:
    print("Seeding AgentHive deterministic corpus (120 episodes across alpha-eng & beta-sec)...")
    summary = get_benchmark_service().seed_demo_dataset()
    print(json.dumps(summary, indent=2))
    print(
        f"\n[OK] Seed complete in {summary['duration_ms']} ms — "
        f"Total Episodes: {summary['total_episodes']}"
    )


if __name__ == "__main__":
    main()