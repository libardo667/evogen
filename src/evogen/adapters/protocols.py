from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from evogen.core.models import (
    CandidateManifest,
    CapabilityIssue,
    CapabilityManifest,
    CapabilitySpec,
    ExperimentResult,
    GateDecision,
    GenerationManifest,
    InvestigationReport,
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
        trace_directory: Path,
        review_passed: bool,
    ) -> ExperimentResult: ...


@runtime_checkable
class CandidateReviewer(Protocol):
    def review(
        self,
        candidate: CandidateManifest,
        *,
        forbidden_literals: list[str] | None = None,
    ) -> ReviewReport: ...


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
