"""Typed, replaceable external reasoning roles.

These adapters contain no subject ontology.  They only assemble typed packets,
invoke the shared retained executor, and enforce links owned by the evolution
stage that called them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from evogen.core.enums import AgentRole
from evogen.core.ids import new_id, sha256_bytes, stable_digest
from evogen.core.models import (
    CandidateManifest,
    CapabilityIssue,
    CapabilityManifest,
    CapabilitySpec,
    DistilledTrace,
    ExperimentResult,
    GateDecision,
    InvestigationReport,
    ReviewReport,
    RoleRequest,
    TrajectoryEvent,
)

from .agents import RoleInvoker


def _request(
    role: AgentRole,
    objective: str,
    inputs: dict[str, Any],
    output_model: type[Any],
    constraints: list[str] | None = None,
) -> RoleRequest:
    return RoleRequest(
        request_id=new_id("role-request"),
        role=role,
        objective=objective,
        input_artifacts=inputs,
        output_contract=output_model.model_json_schema(),
        constraints=constraints or [],
    )


class TraceAnalystAdapter:
    def __init__(self, invoker: RoleInvoker[DistilledTrace]) -> None:
        self.invoker = invoker

    def distill(
        self,
        *,
        generation_id: str,
        events: list[TrajectoryEvent],
        capabilities: CapabilityManifest,
    ) -> DistilledTrace:
        request = _request(
            AgentRole.TRACE_ANALYST,
            "Distill trajectory events into evidence-linked failure signatures.",
            {
                "generation_id": generation_id,
                "events": [event.model_dump(mode="json") for event in events],
                "capabilities": capabilities.model_dump(mode="json"),
            },
            DistilledTrace,
        )
        return self.invoker.invoke(
            request,
            DistilledTrace,
            semantic_validator=lambda value: _require(
                value.generation_id == generation_id,
                "distilled trace generation link mismatch",
            ),
        )


class DiagnosticianAdapter:
    def __init__(self, invoker: RoleInvoker[CapabilityIssue]) -> None:
        self.invoker = invoker

    def diagnose(self, trace: DistilledTrace) -> CapabilityIssue:
        request = _request(
            AgentRole.DIAGNOSTICIAN,
            "Diagnose one distilled trace conservatively; preserve unknowns.",
            {"trace": trace.model_dump(mode="json")},
            CapabilityIssue,
        )
        return self.invoker.invoke(
            request,
            CapabilityIssue,
            semantic_validator=lambda value: _require(
                value.subject_generation == trace.generation_id,
                "diagnosis subject generation link mismatch",
            ),
        )


class InvestigatorAdapter:
    def __init__(self, invoker: RoleInvoker[InvestigationReport]) -> None:
        self.invoker = invoker

    def investigate(self, issue: CapabilityIssue) -> InvestigationReport:
        request = _request(
            AgentRole.INVESTIGATOR,
            "Investigate the environment for operations matching this issue.",
            {"issue": issue.model_dump(mode="json")},
            InvestigationReport,
        )
        return self.invoker.invoke(
            request,
            InvestigationReport,
            semantic_validator=lambda value: _require(
                value.issue_id == issue.issue_id,
                "investigation issue link mismatch",
            ),
        )


class CapabilityArchitectAdapter:
    def __init__(self, invoker: RoleInvoker[CapabilitySpec]) -> None:
        self.invoker = invoker

    def specify(
        self,
        *,
        issue: CapabilityIssue,
        investigation: InvestigationReport,
        revealing_cases: list[str],
        structural_variants: list[str],
        regression_suites: list[str],
        long_horizon_suites: list[str],
    ) -> CapabilitySpec:
        request = _request(
            AgentRole.CAPABILITY_ARCHITECT,
            "Architect an implementable capability contract from issue and evidence.",
            {
                "issue": issue.model_dump(mode="json"),
                "investigation": investigation.model_dump(mode="json"),
                "revealing_cases": revealing_cases,
                "structural_variants": structural_variants,
                "regression_suites": regression_suites,
                "long_horizon_suites": long_horizon_suites,
            },
            CapabilitySpec,
        )
        return self.invoker.invoke(
            request,
            CapabilitySpec,
            semantic_validator=lambda value: _require(
                value.issue_id == issue.issue_id
                and value.parent_generation == issue.subject_generation,
                "capability specification issue or parent link mismatch",
            ),
        )


class AdversarialReviewerAdapter:
    def __init__(self, invoker: RoleInvoker[ReviewReport]) -> None:
        self.invoker = invoker

    def review(
        self,
        candidate: CandidateManifest,
        *,
        forbidden_literals: list[str] | None = None,
    ) -> ReviewReport:
        files = _candidate_files(candidate)
        safe_candidate = candidate.model_dump(mode="json")
        safe_candidate.pop("workspace_path", None)
        request = _request(
            AgentRole.ADVERSARIAL_REVIEWER,
            "Review candidate source against its capability contract and forbidden literals.",
            {
                "candidate": safe_candidate,
                "declared_files": files,
                "forbidden_literals": list(forbidden_literals or []),
            },
            ReviewReport,
        )
        return self.invoker.invoke(
            request,
            ReviewReport,
            semantic_validator=lambda value: _require(
                value.candidate_id == candidate.candidate_id,
                "review candidate link mismatch",
            ),
        )


class ReleaseStewardAdapter:
    def __init__(self, invoker: RoleInvoker[GateDecision]) -> None:
        self.invoker = invoker

    def recommend(self, result: ExperimentResult) -> GateDecision:
        request = _request(
            AgentRole.RELEASE_STEWARD,
            "Recommend a release disposition from the complete experiment evidence.",
            {"experiment": result.model_dump(mode="json")},
            GateDecision,
        )
        return self.invoker.invoke(
            request,
            GateDecision,
            semantic_validator=lambda value: _require(
                value.candidate_id == result.candidate_id,
                "release recommendation candidate link mismatch",
            ),
        )


def _candidate_files(candidate: CandidateManifest) -> list[dict[str, str]]:
    root = Path(candidate.workspace_path).resolve()
    files: list[dict[str, str]] = []
    actual_digests: dict[str, str] = {}
    for relative in sorted(candidate.changed_files):
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"Candidate declares unsafe file path {relative!r}")
        full = (root / path).resolve()
        if root not in full.parents:
            raise ValueError(f"Candidate file escapes workspace: {relative!r}")
        content = full.read_bytes()
        digest = sha256_bytes(content)
        declared = candidate.file_digests.get(relative)
        if declared is not None and declared != digest:
            raise ValueError(f"Candidate file digest mismatch: {relative!r}")
        files.append({"path": relative, "content": content.decode("utf-8"), "digest": digest})
        actual_digests[relative] = digest
    if stable_digest(actual_digests) != candidate.source_digest:
        raise ValueError("Candidate source digest does not match declared file bytes")
    return files


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


# Stable descriptive names for plugin authors and compatibility with callers
# that prefer “external” terminology.
ExternalTraceAnalyst = TraceAnalystAdapter
ExternalDiagnostician = DiagnosticianAdapter
ExternalInvestigator = InvestigatorAdapter
ExternalCapabilityArchitect = CapabilityArchitectAdapter
ExternalAdversarialReviewer = AdversarialReviewerAdapter
ExternalReleaseSteward = ReleaseStewardAdapter
