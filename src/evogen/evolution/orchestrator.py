from __future__ import annotations

from pathlib import Path

from evogen.adapters.protocols import (
    CandidateBuilder,
    CandidateReviewer,
    CapabilityArchitectRole,
    Diagnostician,
    EnvironmentInvestigator,
    ExperimentEvaluator,
    GenerationMaterializer,
    ReleaseRecommender,
    SubjectRunner,
    TraceAnalyst,
)
from evogen.core.models import CycleResult, EvolutionPlan, GenerationManifest
from evogen.evolution.selection import RetentionPolicy
from evogen.storage.artifacts import ArtifactStore
from evogen.storage.ledger import Ledger

from .stages import EvolutionStageOrchestrator


class EvolutionOrchestrator:
    """Compatibility facade delegating entirely to persisted public stages."""

    def __init__(
        self,
        *,
        workspace: Path,
        artifacts: ArtifactStore,
        ledger: Ledger,
        runner: SubjectRunner,
        investigator: EnvironmentInvestigator,
        builder: CandidateBuilder,
        reviewer: CandidateReviewer,
        evaluator: ExperimentEvaluator,
        materializer: GenerationMaterializer,
        baseline: GenerationManifest,
        plan: EvolutionPlan,
        subject_plugin_name: str = "unknown",
        subject_plugin_api_version: str = "1.0",
        subject_plugin_source: str = "unknown",
        trace_analyst: TraceAnalyst | None = None,
        diagnostician: Diagnostician | None = None,
        architect: CapabilityArchitectRole | None = None,
        retention_policy: RetentionPolicy | None = None,
        release_recommender: ReleaseRecommender | None = None,
    ) -> None:
        self.stages = EvolutionStageOrchestrator(
            workspace=workspace,
            artifacts=artifacts,
            ledger=ledger,
            runner=runner,
            investigator=investigator,
            builder=builder,
            reviewer=reviewer,
            evaluator=evaluator,
            materializer=materializer,
            baseline=baseline,
            plan=plan,
            subject_plugin_name=subject_plugin_name,
            subject_plugin_api_version=subject_plugin_api_version,
            subject_plugin_source=subject_plugin_source,
            trace_analyst=trace_analyst,
            diagnostician=diagnostician,
            architect=architect,
            retention_policy=retention_policy,
            release_recommender=release_recommender,
        )

    def invoke(self, stage: str) -> object:
        return self.stages.invoke(stage)

    def run(self, *, until: str | None = None) -> CycleResult:
        result = self.stages.run(until=until)
        if not isinstance(result, CycleResult):
            raise RuntimeError(
                "EvolutionOrchestrator.run() requires the complete select stage; "
                f"received {type(result).__name__}"
            )
        return result
