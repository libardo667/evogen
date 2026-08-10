from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path, PurePosixPath

from evogen.core.enums import AgentRole
from evogen.core.ids import new_id, sha256_bytes, stable_digest
from evogen.core.models import (
    CandidateManifest,
    CapabilityIssue,
    CapabilitySpec,
    GenerationManifest,
    PatchSet,
    RoleRequest,
)

from .agents import RoleBackend

WorkspaceSeeder = Callable[[GenerationManifest, Path], None]


class CandidateBuildError(RuntimeError):
    pass


def empty_workspace_seeder(parent: GenerationManifest, destination: Path) -> None:
    del parent
    destination.mkdir(parents=True, exist_ok=False)


def copy_workspace_seeder(source: Path) -> WorkspaceSeeder:
    source = source.resolve()

    def seed(parent: GenerationManifest, destination: Path) -> None:
        del parent
        shutil.copytree(
            source,
            destination,
            ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", ".pytest_cache"),
        )

    return seed


class RoleBackedDirectoryBuilder:
    """Turn one role-isolated coding-agent response into an auditable candidate.

    The backend cannot choose where files land. It returns a PatchSet; this class
    validates relative paths, file counts, byte limits, and writes only inside an
    isolated candidate directory seeded by the caller.
    """

    def __init__(
        self,
        *,
        backend: RoleBackend,
        seed_workspace: WorkspaceSeeder = empty_workspace_seeder,
        max_files: int = 100,
        max_total_bytes: int = 2_000_000,
    ) -> None:
        self.backend = backend
        self.seed_workspace = seed_workspace
        self.max_files = max_files
        self.max_total_bytes = max_total_bytes

    def build(
        self,
        *,
        parent: GenerationManifest,
        issue: CapabilityIssue,
        specification: CapabilitySpec,
        candidate_root: Path,
    ) -> CandidateManifest:
        candidate_id = new_id("candidate")
        workspace = candidate_root / candidate_id
        workspace.parent.mkdir(parents=True, exist_ok=True)
        self.seed_workspace(parent, workspace)
        if not workspace.is_dir():
            raise CandidateBuildError("Workspace seeder did not create a directory")

        packet_root = workspace / ".evogen-input"
        packet_root.mkdir(parents=True, exist_ok=False)
        input_paths = {
            "parent_generation": packet_root / "parent-generation.json",
            "capability_issue": packet_root / "capability-issue.json",
            "capability_spec": packet_root / "capability-spec.json",
        }
        input_paths["parent_generation"].write_text(
            parent.model_dump_json(indent=2), encoding="utf-8"
        )
        input_paths["capability_issue"].write_text(
            issue.model_dump_json(indent=2), encoding="utf-8"
        )
        input_paths["capability_spec"].write_text(
            specification.model_dump_json(indent=2), encoding="utf-8"
        )
        request = RoleRequest(
            request_id=new_id("role-request"),
            role=AgentRole.IMPLEMENTER,
            objective=(
                "Implement the frozen capability specification in the seeded candidate "
                "workspace. Return only a PatchSet; do not edit the evaluator, revealing "
                "scenarios, or input artifacts."
            ),
            input_artifacts={
                name: str(path.resolve()) for name, path in input_paths.items()
            },
            output_contract=PatchSet.model_json_schema(),
            constraints=[
                f"Write at most {self.max_files} files.",
                f"Return at most {self.max_total_bytes} UTF-8 bytes.",
                "All paths must be relative and may not traverse upward.",
                "Do not write under .evogen-input.",
                *specification.non_goals,
                *specification.implementation_constraints,
            ],
        )
        response = self.backend.run(request)
        if not response.success:
            raise CandidateBuildError(
                "Implementer role failed: " + "; ".join(response.notes or ["unknown failure"])
            )
        try:
            patch_set = PatchSet.model_validate(response.output)
        except ValueError as exc:
            raise CandidateBuildError(f"Implementer returned an invalid PatchSet: {exc}") from exc
        if not patch_set.files:
            raise CandidateBuildError("Implementer returned an empty PatchSet")
        if len(patch_set.files) > self.max_files:
            raise CandidateBuildError(
                f"PatchSet contains {len(patch_set.files)} files; limit is {self.max_files}"
            )

        total_bytes = sum(len(file.content.encode("utf-8")) for file in patch_set.files)
        if total_bytes > self.max_total_bytes:
            raise CandidateBuildError(
                f"PatchSet contains {total_bytes} bytes; limit is {self.max_total_bytes}"
            )

        changed_files: list[str] = []
        file_digests: dict[str, str] = {}
        seen: set[str] = set()
        for file in patch_set.files:
            relative = _validate_relative_path(file.path)
            normalized = relative.as_posix()
            if normalized in seen:
                raise CandidateBuildError(f"PatchSet repeats path {normalized!r}")
            seen.add(normalized)
            destination = workspace.joinpath(*relative.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(file.content, encoding="utf-8")
            changed_files.append(normalized)
            file_digests[normalized] = sha256_bytes(file.content.encode("utf-8"))

        transcript = packet_root / "implementer-response.json"
        transcript.write_text(response.model_dump_json(indent=2), encoding="utf-8")
        source_digest = stable_digest(file_digests)
        return CandidateManifest(
            candidate_id=candidate_id,
            parent_generation=parent.generation_id,
            issue_id=issue.issue_id,
            spec_id=specification.spec_id,
            workspace_path=str(workspace),
            source_digest=source_digest,
            artifact_digests={
                "patch_set": stable_digest(patch_set.model_dump(mode="json")),
                "implementer_response": sha256_bytes(transcript.read_bytes()),
                **{f"file:{path}": digest for path, digest in file_digests.items()},
            },
            changed_files=sorted(changed_files),
            claimed_capabilities=patch_set.claimed_capabilities,
            metadata={
                "builder": type(self).__name__,
                "implementation_summary": patch_set.summary,
                "role_request_id": request.request_id,
                "role_response_id": response.response_id,
            },
        )


def _validate_relative_path(raw: str) -> PurePosixPath:
    if "\\" in raw:
        raise CandidateBuildError(f"Patch path must use POSIX separators: {raw!r}")
    path = PurePosixPath(raw)
    if path.is_absolute() or not path.parts:
        raise CandidateBuildError(f"Patch path must be a non-empty relative path: {raw!r}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise CandidateBuildError(f"Patch path may not traverse or contain empty parts: {raw!r}")
    if path.parts[0] == ".evogen-input":
        raise CandidateBuildError("PatchSet may not modify EvoGen input artifacts")
    return path
