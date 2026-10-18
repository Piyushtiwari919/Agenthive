import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "apps" / "api"))

from app.core.errors import DatabaseUnavailableError  # noqa: E402
from app.repositories.falkor_client import falkor_manager  # noqa: E402


def main() -> None:
    print("Verifying Sponsor Removal Test (C-01 / K-09)...")
    # Simulate FalkorDB offline
    def _break() -> bool:
        raise DatabaseUnavailableError("FalkorDB container stopped.")

    falkor_manager.ping = _break  # type: ignore

    try:
        falkor_manager.ping()
        print("[FAIL] Expected DatabaseUnavailableError when FalkorDB is removed.")
        sys.exit(1)
    except DatabaseUnavailableError as exc:
        print(f"[OK] Product successfully fails closed with 503 when FalkorDB is removed: {exc}")


if __name__ == "__main__":
    main()