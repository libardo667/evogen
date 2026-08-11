"""The microworld's implementation of EvoGen's generic subject contract."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from evogen.adapters.protocols import (
    CandidateBuilder,
    CandidateReviewer,
    EnvironmentInvestigator,
    ExperimentEvaluator,
    GenerationMaterializer,
    SubjectRunner,
)
from evogen.adapters.subjects import (
    SUBJECT_PLUGIN_API_VERSION,
    SubjectBootstrap,
    SubjectDoctor,
    SubjectFactoryContext,
    SubjectPlugin,
)
from evogen.core.models import EvolutionPlan, GenerationManifest
from evogen.evolution.review import PythonCandidateReviewer

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


class MicroworldDoctor:
    """Placeholder for the later generic conformance/doctor goal."""

    def check(self) -> None:
        return None


def build_runner(context: SubjectFactoryContext) -> MicroworldRunner:
    del context
    return MicroworldRunner()


def build_investigator(context: SubjectFactoryContext) -> MicroworldInvestigator:
    del context
    return MicroworldInvestigator()


def build_builder(context: SubjectFactoryContext) -> ReferenceMicroworldBuilder:
    del context
    return ReferenceMicroworldBuilder()


def build_reviewer(context: SubjectFactoryContext) -> PythonCandidateReviewer:
    del context
    return PythonCandidateReviewer()


def _runner_from_context(context: SubjectFactoryContext) -> MicroworldRunner:
    runner = context.runner
    if not isinstance(runner, MicroworldRunner):
        raise RuntimeError("Microworld factories require the shared MicroworldRunner instance.")
    return runner


def build_evaluator(context: SubjectFactoryContext) -> MicroworldEvaluator:
    return MicroworldEvaluator(runner=_runner_from_context(context), ledger=context.ledger)


def build_materializer(context: SubjectFactoryContext) -> GenerationMaterializer:
    # Import lazily so loading this subject entry point does not import its
    # composition wrapper before the generic loader has created the context.
    from .cycle import MicroworldGenerationMaterializer

    return MicroworldGenerationMaterializer(
        runner=_runner_from_context(context),
        artifacts=context.artifacts,
    )


def build_doctor(context: SubjectFactoryContext) -> MicroworldDoctor:
    del context
    return MicroworldDoctor()


def build_bootstrap(context: SubjectFactoryContext) -> SubjectBootstrap:
    """Create microworld-only baseline/plan values in generic core types."""

    runner = _runner_from_context(context)
    plugin_root = context.workspace / "subjects" / "microworld" / "genesis" / "plugins"
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
    manifest = runner.capability_manifest(provisional)
    digest = context.artifacts.put_json(manifest.model_dump(mode="json"))
    baseline = provisional.model_copy(
        update={
            "capability_manifest_digest": digest,
            "artifact_digests": {"capability_manifest": digest},
        }
    )
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
    return SubjectBootstrap(baseline=baseline, plan=plan)


@dataclass(frozen=True)
class MicroworldSubjectPlugin:
    """Concrete metadata payload for the bundled deterministic subject."""

    name: str = "microworld"
    api_version: str = SUBJECT_PLUGIN_API_VERSION
    runner_factory: Callable[[SubjectFactoryContext], SubjectRunner] = build_runner
    investigator_factory: Callable[
        [SubjectFactoryContext], EnvironmentInvestigator
    ] = build_investigator
    builder_factory: Callable[[SubjectFactoryContext], CandidateBuilder] = build_builder
    reviewer_factory: Callable[[SubjectFactoryContext], CandidateReviewer] = build_reviewer
    evaluator_factory: Callable[[SubjectFactoryContext], ExperimentEvaluator] = build_evaluator
    materializer_factory: Callable[
        [SubjectFactoryContext], GenerationMaterializer
    ] = build_materializer
    doctor_factory: Callable[[SubjectFactoryContext], SubjectDoctor] = build_doctor
    bootstrap_factory: Callable[[SubjectFactoryContext], SubjectBootstrap] = build_bootstrap


subject_plugin: SubjectPlugin = MicroworldSubjectPlugin()


def build_subject_plugin() -> SubjectPlugin:
    """Entry-point factory used by the installed ``evogen.subjects`` group."""

    return subject_plugin


__all__ = [
    "MicroworldDoctor",
    "MicroworldSubjectPlugin",
    "build_subject_plugin",
    "subject_plugin",
]
