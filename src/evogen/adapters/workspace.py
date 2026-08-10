from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path


class GitWorkspaceError(RuntimeError):
    pass


class GitWorkspaceAdapter:
    """Create isolated candidate worktrees without granting deployment authority."""

    def __init__(self, repository: Path, worktree_root: Path) -> None:
        self.repository = repository.resolve()
        self.worktree_root = worktree_root.resolve()
        if not (self.repository / ".git").exists():
            raise GitWorkspaceError(f"Not a Git repository: {self.repository}")
        self.worktree_root.mkdir(parents=True, exist_ok=True)

    def create(self, *, candidate_id: str, base_ref: str) -> Path:
        destination = self.worktree_root / candidate_id
        if destination.exists():
            raise GitWorkspaceError(f"Candidate worktree already exists: {destination}")
        branch = f"evogen/{candidate_id}"
        self._run(
            ["git", "worktree", "add", "-b", branch, str(destination), base_ref],
            cwd=self.repository,
        )
        return destination

    def remove(self, path: Path, *, force: bool = False) -> None:
        arguments = ["git", "worktree", "remove"]
        if force:
            arguments.append("--force")
        arguments.append(str(path.resolve()))
        self._run(arguments, cwd=self.repository)

    def diff(self, path: Path) -> str:
        return self._run(["git", "diff", "--no-ext-diff", "--binary"], cwd=path)

    def changed_files(self, path: Path) -> list[str]:
        output = self._run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=path
        )
        files: list[str] = []
        for line in output.splitlines():
            if len(line) >= 4:
                files.append(line[3:])
        return files

    def run_checks(
        self,
        path: Path,
        commands: Sequence[Sequence[str]],
    ) -> list[tuple[tuple[str, ...], bool, str]]:
        results: list[tuple[tuple[str, ...], bool, str]] = []
        for command in commands:
            try:
                output = self._run(list(command), cwd=path)
            except GitWorkspaceError as exc:
                results.append((tuple(command), False, str(exc)))
                break
            results.append((tuple(command), True, output))
        return results

    @staticmethod
    def _run(arguments: list[str], *, cwd: Path) -> str:
        completed = subprocess.run(
            arguments,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise GitWorkspaceError(
                f"Command failed ({completed.returncode}): {' '.join(arguments)}\n"
                f"stdout:\n{completed.stdout}\n"
                f"stderr:\n{completed.stderr}"
            )
        return completed.stdout
