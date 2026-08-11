from __future__ import annotations

from pathlib import Path

from evogen.adapters.subjects import (
    SubjectFactoryContext,
    _prepare_workspace,
    compose_subject,
    load_subject_plugin,
)
from evogen.core.ids import new_id
from evogen.core.models import (
    CandidateManifest,
    CapabilityManifest,
    CycleResult,
    ExperimentResult,
    GateDecision,
    GenerationManifest,
)
from evogen.storage.artifacts import ArtifactStore
from evogen.storage.ledger import Ledger

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
        self.plugin = load_subject_plugin("microworld")
        self.context = SubjectFactoryContext(
            workspace=self.workspace,
            artifacts=self.artifacts,
            ledger=self.ledger,
        )
        self.composition = compose_subject(self.plugin, context=self.context)
        self.runner = self.composition.runner

    @classmethod
    def prepare(cls, workspace: Path, *, clean: bool = False) -> MicroworldEvolutionCycle:
        resolved = _prepare_workspace(workspace, clean=clean)
        return cls(resolved)

    def run(self) -> CycleResult:
        return self.composition.orchestrator.run(
            baseline=self.composition.bootstrap.baseline,
            plan=self.composition.bootstrap.plan,
        )

    def _baseline_generation(self) -> GenerationManifest:
        return self.composition.bootstrap.baseline
