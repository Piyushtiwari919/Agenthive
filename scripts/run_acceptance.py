import subprocess
from pathlib import Path
import sys


def main() -> None:
    print("Running Master Acceptance Test Suite (FR-001..FR-017, NFR-001..008, C-01..02)...")
    res = subprocess.run(["pytest", "-v"], cwd=str(Path(__file__).resolve().parent.parent / "apps" / "api"))
    sys.exit(res.returncode)


if __name__ == "__main__":
    main()