from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(*arguments: str) -> None:
    env = os.environ.copy()
    source = str(ROOT / "src")
    env["PYTHONPATH"] = (
        source if not env.get("PYTHONPATH") else source + os.pathsep + env["PYTHONPATH"]
    )
    subprocess.run(arguments, cwd=ROOT, env=env, check=True)


def main() -> None:
    run(sys.executable, "-m", "compileall", "-q", "src", "tests")
    run(sys.executable, "-m", "pytest", "-q")
    with tempfile.TemporaryDirectory(prefix="evogen-verify-") as directory:
        run(
            sys.executable,
            "-m",
            "evogen",
            "demo",
            "--workspace",
            directory,
            "--clean",
        )


if __name__ == "__main__":
    main()
