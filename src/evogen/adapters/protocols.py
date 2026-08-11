from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from evogen.core.models import (
    ArtifactRef,
    CandidateManifest,
    CapabilityIssue,
    CapabilityManifest,
    CapabilitySpec,
    DistilledTrace,
    EvaluationOutcome,
    EvaluationSuiteManifest,
    ExperimentResult,
    GateDecision,
    GenerationManifest,
    InvestigationReport,
    ProbeBuildOutput,
    ProbeCandidateManifest,
    ProbeEvaluation,
    ProbeEvidenceTarget,
    ProbePlan,
    ProbeReviewReport,
    ReviewReport,
    RunRecord,
    TrajectoryEvent,
)


@runtime_checkable
class SubjectRunner(Protocol):
    def run(
        self,
        *,
        generation: GenerationManifest,
        scenario_id: str,
        seed: int = 0,
        trace_directory: Path,
    ) -> tuple[RunRecord, list[TrajectoryEvent]]: ...

    def capability_manifest(self, generation: GenerationManifest) -> CapabilityManifest: ...


@runtime_checkable
class EnvironmentInvestigator(Protocol):
    def investigate(self, issue: CapabilityIssue) -> InvestigationReport: ...


@runtime_checkable
class CandidateBuilder(Protocol):
    def build(
        self,
        *,
        parent: GenerationManifest,
        issue: CapabilityIssue,
        specification: CapabilitySpec,
        candidate_root: Path,
    ) -> CandidateManifest: ...


@runtime_checkable
class ExperimentEvaluator(Protocol):
    def evaluate(
        self,
        *,
        baseline: GenerationManifest,
        candidate: CandidateManifest,
        evaluation_suite: EvaluationSuiteManifest,
        trace_directory: Path,
        review_passed: bool,
    ) -> EvaluationOutcome: ...


@runtime_checkable
class CandidateReviewer(Protocol):
    def review(
        self,
        candidate: CandidateManifest,
        *,
        forbidden_literals: list[str] | None = None,
    ) -> ReviewReport: ...


@runtime_checkable
class TraceAnalyst(Protocol):
    def distill(
        self,
        *,
        generation_id: str,
        events: list[TrajectoryEvent],
        capabilities: CapabilityManifest,
    ) -> DistilledTrace: ...


@runtime_checkable
class Diagnostician(Protocol):
    def diagnose(self, trace: DistilledTrace) -> CapabilityIssue: ...


@runtime_checkable
class CapabilityArchitectRole(Protocol):
    def specify(
        self,
        *,
        issue: CapabilityIssue,
        investigation: InvestigationReport,
        revealing_cases: list[str],
        structural_variants: list[str],
        regression_suites: list[str],
        long_horizon_suites: list[str],
    ) -> CapabilitySpec: ...


@runtime_checkable
class ReleaseRecommender(Protocol):
    def recommend(self, result: ExperimentResult) -> GateDecision: ...


@runtime_checkable
class GenerationMaterializer(Protocol):
    def materialize(
        self,
        *,
        baseline: GenerationManifest,
        candidate: CandidateManifest,
        experiment: ExperimentResult,
        decision: GateDecision,
    ) -> GenerationManifest: ...


@runtime_checkable
class SubjectDoctor(Protocol):
    """Minimal generic diagnostic boundary reserved for a later goal."""

    def check(self) -> None: ...


@runtime_checkable
class ProbePlanner(Protocol):
    def plan(
        self,
        *,
        issue: CapabilityIssue,
        investigation: InvestigationReport,
        parent: GenerationManifest,
        probe_id: str,
        evidence_target: ProbeEvidenceTarget | None = None,
        initial_observation: dict[str, Any] | None = None,
        investigation_ref: ArtifactRef | None = None,
        capability_manifest_ref: ArtifactRef | None = None,
    ) -> ProbePlan: ...


@runtime_checkable
class ProbeBuilder(Protocol):
    def build(self, *, plan: ProbePlan) -> ProbeBuildOutput: ...


@runtime_checkable
class ProbeReviewer(Protocol):
    def review(
        self,
        *,
        plan: ProbePlan,
        candidate: ProbeCandidateManifest,
    ) -> ProbeReviewReport: ...


@runtime_checkable
class ProbeEvaluator(Protocol):
    def evaluate(
        self,
        *,
        plan: ProbePlan,
        candidate: ProbeCandidateManifest,
        review: ProbeReviewReport,
    ) -> ProbeEvaluation: ...


@dataclass(frozen=True)
class ProbeRoleBundle:
    planner: ProbePlanner
    builder: ProbeBuilder
    reviewer: ProbeReviewer
    evaluator: ProbeEvaluator
