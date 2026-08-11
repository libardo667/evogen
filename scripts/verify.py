from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*arguments: str) -> None:
    print(f"\n==> {' '.join(arguments)}", flush=True)
    env = os.environ.copy()
    source = str(ROOT / "src")
    env["PYTHONPATH"] = (
        source if not env.get("PYTHONPATH") else source + os.pathsep + env["PYTHONPATH"]
    )
    env.setdefault("UV_CACHE_DIR", "/tmp/evogen-uv-cache")
    subprocess.run(arguments, cwd=ROOT, env=env, check=True)


def verify_wheel_entry_point(directory: Path) -> None:
    wheels = sorted(directory.glob("*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"Expected one wheel in {directory}, found {wheels}")
    with zipfile.ZipFile(wheels[0]) as archive:
        metadata_paths = [
            name for name in archive.namelist() if name.endswith(".dist-info/entry_points.txt")
        ]
        if len(metadata_paths) != 1:
            raise RuntimeError(
                f"Expected one entry_points.txt in {wheels[0]}, found {metadata_paths}"
            )
        metadata = archive.read(metadata_paths[0]).decode("utf-8")
    expected = (
        "[evogen.subjects]\n"
        "microworld = evogen.demo.microworld.plugin:build_subject_plugin"
    )
    if expected not in metadata:
        raise RuntimeError(
            "Wheel entry-point metadata does not contain the exact bundled microworld "
            f"registration:\n{metadata}"
        )


def main() -> None:
    run(sys.executable, "-m", "compileall", "-q", "src", "tests")
    run("ruff", "check", ".")
    run("mypy", "src")
    with tempfile.TemporaryDirectory(prefix="evogen-wheel-verify-") as directory:
        wheel_directory = Path(directory)
        run("uv", "build", "--wheel", "--out-dir", str(wheel_directory))
        verify_wheel_entry_point(wheel_directory)
    run(sys.executable, "-m", "pytest", "-q")
    with tempfile.TemporaryDirectory(prefix="evogen-verify-") as directory:
        workspace = Path(directory) / "workspace"
        run(
            sys.executable,
            "-m",
            "evogen",
            "demo",
            "--workspace",
            str(workspace),
            "--clean",
        )
    run("git", "diff", "--check")


if __name__ == "__main__":
    main()
