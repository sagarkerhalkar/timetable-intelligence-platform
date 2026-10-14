from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], cwd: Path) -> bool:
    print(f"\n> {' '.join(command)}")
    result = subprocess.run(command, cwd=cwd, check=False)
    return result.returncode == 0


def main() -> int:
    checks: list[tuple[list[str], Path]] = [
        ([sys.executable, "-m", "pytest", "--cov=app", "--cov-report=term-missing", "--cov-fail-under=80"], ROOT / "services/api"),
    ]
    npm = shutil.which("npm")
    if npm:
        web = ROOT / "apps/web"
        checks.extend(
            [
                ([npm, "run", "lint"], web),
                ([npm, "run", "typecheck"], web),
                ([npm, "test"], web),
                ([npm, "run", "build"], web),
            ]
        )
    else:
        print("npm is unavailable; frontend checks were skipped locally. CI will run them.")

    failures = [command for command, cwd in checks if not run(command, cwd)]
    if failures:
        print(f"\n{len(failures)} validation command(s) failed.")
        return 1
    print("\nAll available validation checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
