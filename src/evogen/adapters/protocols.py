from __future__ import annotations

from pathlib import Path
from typing import Protocol

from evogen.core.models import (
    CapabilityIssue,
    CapabilityManifest,
    CapabilitySpec,
    CandidateManifest,
    ExperimentResult,
    GateDecision,
    GenerationManifest,
    InvestigationReport,
    ReviewReport,
    RunRecord,
    TrajectoryEvent,
)


class SubjectRunner(Protocol):
    def run(
        self,
        *,
        generation: GenerationManifest,
        scenario_id: str,
        trace_directory: Path,
    ) -> tuple[RunRecord, list[TrajectoryEvent]]: ...

    def capability_manifest(self, generation: GenerationManifest) -> CapabilityManifest: ...


class EnvironmentInvestigator(Protocol):
    def investigate(self, issue: CapabilityIssue) -> InvestigationReport: ...


class CandidateBuilder(Protocol):
    def build(
        self,
        *,
        parent: GenerationManifest,
        issue: CapabilityIssue,
        specification: CapabilitySpec,
        candidate_root: Path,
    ) -> CandidateManifest: ...


class ExperimentEvaluator(Protocol):
    def evaluate(
        self,
        *,
        baseline: GenerationManifest,
        candidate: CandidateManifest,
        trace_directory: Path,
        review_passed: bool,
    ) -> ExperimentResult: ...


class CandidateReviewer(Protocol):
    def review(
        self,
        candidate: CandidateManifest,
        *,
        forbidden_literals: list[str] | None = None,
    ) -> ReviewReport: ...


class GenerationMaterializer(Protocol):
    def materialize(
        self,
        *,
        baseline: GenerationManifest,
        candidate: CandidateManifest,
        experiment: ExperimentResult,
        decision: GateDecision,
    ) -> GenerationManifest: ...
