from __future__ import annotations

import shutil
from pathlib import Path

from evogen.core.ids import new_id
from evogen.core.models import (
    CandidateManifest,
    CapabilityManifest,
    EvolutionPlan,
    ExperimentResult,
    GateDecision,
    GenerationManifest,
)
from evogen.evolution.orchestrator import EvolutionOrchestrator
from evogen.evolution.review import PythonCandidateReviewer
from evogen.storage.artifacts import ArtifactStore
from evogen.storage.ledger import Ledger

from .builder import ReferenceMicroworldBuilder
from .evaluator import MicroworldEvaluator
from .investigator import MicroworldInvestigator
from .scenarios import (
    DIAGNOSTIC_SCENARIOS,
    LONG_HORIZON_SUITES,
    REGRESSION_SUITES,
    REVEALING_CASES,
    STRUCTURAL_VARIANTS,
    get_scenario,
)
from .subject import MicroworldRunner


class MicroworldGenerationMaterializer:
    def __init__(
        self,
        *,
        runner: MicroworldRunner,
        artifacts: ArtifactStore,
    ) -> None:
        self.runner = runner
        self.artifacts = artifacts

    def materialize(
        self,
        *,
        baseline: GenerationManifest,
        candidate: CandidateManifest,
        experiment: ExperimentResult,
        decision: GateDecision,
    ) -> GenerationManifest:
        del decision
        generation_id = new_id("gen")
        provisional = GenerationManifest(
            generation_id=generation_id,
            parent_generation_id=baseline.generation_id,
            subject=baseline.subject,
            source_ref=f"candidate:{candidate.source_digest}",
            capability_manifest_digest="pending",
            artifact_digests={
                **candidate.artifact_digests,
                "experiment": candidate.artifact_digests["experiment_object"],
            },
            models=baseline.models,
            prompts=baseline.prompts,
            config={
                **baseline.config,
                "plugin_root": str(Path(candidate.workspace_path) / "plugins"),
            },
            metadata={
                "retained_from_candidate": candidate.candidate_id,
                "closed_issue": candidate.issue_id,
                "experiment_id": experiment.experiment_id,
            },
        )
        manifest: CapabilityManifest = self.runner.capability_manifest(provisional)
        digest = self.artifacts.put_json(manifest.model_dump(mode="json"))
        return provisional.model_copy(
            update={
                "capability_manifest_digest": digest,
                "artifact_digests": {
                    **provisional.artifact_digests,
                    "capability_manifest": digest,
                },
            }
        )


class MicroworldEvolutionCycle:
    """Adapter composition over EvoGen's generic outer-loop orchestrator."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()
        self.artifacts = ArtifactStore(self.workspace / "artifacts")
        self.ledger = Ledger(self.workspace / "evogen.sqlite3")
        self.runner = MicroworldRunner()

    @classmethod
    def prepare(cls, workspace: Path, *, clean: bool = False) -> "MicroworldEvolutionCycle":
        resolved = workspace.resolve()
        if clean and resolved.exists():
            shutil.rmtree(resolved)
        resolved.mkdir(parents=True, exist_ok=True)
        return cls(resolved)

    def run(self):
        baseline = self._baseline_generation()
        forbidden_literals = [
            *REVEALING_CASES,
            *STRUCTURAL_VARIANTS,
            *[get_scenario(identifier).target_item_id for identifier in REVEALING_CASES],
        ]
        plan = EvolutionPlan(
            diagnostic_scenarios=DIAGNOSTIC_SCENARIOS,
            revealing_cases=REVEALING_CASES,
            structural_variants=STRUCTURAL_VARIANTS,
            regression_suites=REGRESSION_SUITES,
            long_horizon_suites=LONG_HORIZON_SUITES,
            forbidden_literals=forbidden_literals,
        )
        orchestrator = EvolutionOrchestrator(
            workspace=self.workspace,
            artifacts=self.artifacts,
            ledger=self.ledger,
            runner=self.runner,
            investigator=MicroworldInvestigator(),
            builder=ReferenceMicroworldBuilder(),
            reviewer=PythonCandidateReviewer(),
            evaluator=MicroworldEvaluator(runner=self.runner, ledger=self.ledger),
            materializer=MicroworldGenerationMaterializer(
                runner=self.runner,
                artifacts=self.artifacts,
            ),
        )
        return orchestrator.run(baseline=baseline, plan=plan)

    def _baseline_generation(self) -> GenerationManifest:
        plugin_root = self.workspace / "subjects" / "microworld" / "genesis" / "plugins"
        plugin_root.mkdir(parents=True, exist_ok=True)
        generation_id = "gen-microworld-0001"
        provisional = GenerationManifest(
            generation_id=generation_id,
            subject="microworld",
            source_ref="builtin:microworld-baseline-v1",
            capability_manifest_digest="pending",
            config={"plugin_root": str(plugin_root)},
            metadata={
                "purpose": "intentionally impoverished baseline",
                "withheld_environment_operation": "inspect_container",
            },
        )
        manifest = self.runner.capability_manifest(provisional)
        digest = self.artifacts.put_json(manifest.model_dump(mode="json"))
        return provisional.model_copy(
            update={
                "capability_manifest_digest": digest,
                "artifact_digests": {"capability_manifest": digest},
            }
        )
