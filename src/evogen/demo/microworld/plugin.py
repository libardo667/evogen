"""The microworld's implementation of EvoGen's generic subject contract."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from evogen.adapters.protocols import (
    CandidateBuilder,
    CandidateReviewer,
    EnvironmentInvestigator,
    ExperimentEvaluator,
    GenerationMaterializer,
    ProbeRoleBundle,
    SubjectRunner,
)
from evogen.adapters.subjects import (
    SUBJECT_PLUGIN_API_VERSION,
    SubjectBootstrap,
    SubjectDoctor,
    SubjectFactoryContext,
    SubjectPlugin,
)
from evogen.core.ids import sha256_bytes
from evogen.core.models import (
    ArtifactRef,
    EvaluationCase,
    EvaluationCategory,
    EvaluationSuiteManifest,
    EvolutionPlan,
    GenerationManifest,
    ProtectedPathHash,
)
from evogen.evolution.review import PythonCandidateReviewer

from .builder import ReferenceMicroworldBuilder
from .evaluator import MicroworldEvaluator
from .investigator import MicroworldInvestigator
from .scenarios import (
    DIAGNOSTIC_SCENARIOS,
    EVALUATION_SCENARIOS,
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


def build_probe_roles(context: SubjectFactoryContext) -> ProbeRoleBundle:
    """Provide typed generic probe roles through the public subject boundary."""
    from .probe import (
        MicroworldProbeBuilder,
        MicroworldProbeEvaluator,
        MicroworldProbePlanner,
        MicroworldProbeReviewer,
    )

    runner = _runner_from_context(context)
    if context.bootstrap is None:
        raise RuntimeError("Probe roles require the composed subject bootstrap")
    return ProbeRoleBundle(
        planner=MicroworldProbePlanner(
            runner=runner,
            trace_directory=context.workspace / "probes" / "baseline-traces",
        ),
        builder=MicroworldProbeBuilder(),
        reviewer=MicroworldProbeReviewer(),
        evaluator=MicroworldProbeEvaluator(
            runner=runner,
            baseline=context.bootstrap.baseline,
        ),
    )


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
    protected_scenarios = list(
        dict.fromkeys([*DIAGNOSTIC_SCENARIOS, *EVALUATION_SCENARIOS])
    )
    forbidden_literals = [
        *protected_scenarios,
        *[
            get_scenario(identifier).target_item_id
            for identifier in protected_scenarios
        ],
    ]
    plan = EvolutionPlan(
        diagnostic_scenarios=DIAGNOSTIC_SCENARIOS,
        revealing_cases=REVEALING_CASES,
        structural_variants=STRUCTURAL_VARIANTS,
        regression_suites=REGRESSION_SUITES,
        long_horizon_suites=LONG_HORIZON_SUITES,
        forbidden_literals=forbidden_literals,
    )
    suite = _build_evaluation_suite(context)
    return SubjectBootstrap(baseline=baseline, plan=plan, evaluation_suite=suite)


def _source_path(module: ModuleType) -> Path:
    source = inspect.getsourcefile(module)
    if source is None:
        raise RuntimeError(f"Cannot locate source for {module!r}")
    path = Path(source).resolve()
    if not path.is_file() or not path.is_absolute():
        raise RuntimeError(f"Subject authority source is not an absolute file: {path}")
    return path


def _build_evaluation_suite(context: SubjectFactoryContext) -> EvaluationSuiteManifest:
    from . import environment, evaluator, scenarios, subject

    source_modules = {
        "evaluator.py": evaluator,
        "scenarios.py": scenarios,
        "environment.py": environment,
        "subject.py": subject,
    }
    refs = {
        name: ArtifactRef(
            digest=context.artifacts.put_bytes(_source_path(module).read_bytes()),
            model="SourceArtifact",
        )
        for name, module in source_modules.items()
    }
    refs["scenario_specs.json"] = ArtifactRef(
        digest=context.artifacts.put_json(
            {
                identifier: spec.model_dump(mode="json")
                for identifier, spec in scenarios.SCENARIOS.items()
            }
        ),
        model="SourceArtifact",
    )
    refs["environment_operations.json"] = ArtifactRef(
        digest=context.artifacts.put_json(
            [operation.model_dump(mode="json") for operation in environment.ENVIRONMENT_OPERATIONS]
        ),
        model="SourceArtifact",
    )
    cases: dict[EvaluationCategory, list[str]] = {
        "revealing": REVEALING_CASES,
        "variant": STRUCTURAL_VARIANTS,
        "regression": REGRESSION_SUITES,
        "long_horizon": LONG_HORIZON_SUITES,
    }
    built: dict[str, list[EvaluationCase]] = {}
    for category, scenario_ids in cases.items():
        for scenario_id in scenario_ids:
            if get_scenario(scenario_id).category != category:
                raise RuntimeError(
                    f"Scenario {scenario_id!r} category differs from evaluation suite"
                )
        built[category] = [
            EvaluationCase(
                scenario_id=scenario_id,
                category=category,
                seeds=[0],
                repeat_count=1,
                per_run_wall_clock_ceiling_seconds=10.0,
            )
            for scenario_id in scenario_ids
        ]
    protected = [
        ProtectedPathHash(
            logical_name=name,
            absolute_path=str(_source_path(module)),
            sha256=sha256_bytes(_source_path(module).read_bytes()),
        )
        for name, module in source_modules.items()
    ]
    return EvaluationSuiteManifest(
        suite_id="microworld-suite-v1",
        revealing_cases=built["revealing"],
        structural_variants=built["variant"],
        regression_suites=built["regression"],
        long_horizon_suites=built["long_horizon"],
        total_wall_clock_ceiling_seconds=120.0,
        evaluator_version="microworld-evaluator-1",
        evaluator=refs["evaluator.py"],
        evaluator_protected_path="evaluator.py",
        environment_artifacts=refs,
        protected_paths=protected,
        subject_metric_namespace="microworld",
        candidate_tests_authoritative=False,
    )


@dataclass(frozen=True)
class MicroworldSubjectPlugin:
    """Concrete metadata payload for the bundled deterministic subject."""

    name: str = "microworld"
    api_version: str = SUBJECT_PLUGIN_API_VERSION
    runner_factory: Callable[[SubjectFactoryContext], SubjectRunner] = build_runner
    investigator_factory: Callable[[SubjectFactoryContext], EnvironmentInvestigator] = (
        build_investigator
    )
    builder_factory: Callable[[SubjectFactoryContext], CandidateBuilder] = build_builder
    reviewer_factory: Callable[[SubjectFactoryContext], CandidateReviewer] = build_reviewer
    evaluator_factory: Callable[[SubjectFactoryContext], ExperimentEvaluator] = build_evaluator
    materializer_factory: Callable[[SubjectFactoryContext], GenerationMaterializer] = (
        build_materializer
    )
    doctor_factory: Callable[[SubjectFactoryContext], SubjectDoctor] = build_doctor
    bootstrap_factory: Callable[[SubjectFactoryContext], SubjectBootstrap] = build_bootstrap
    probe_roles_factory: Callable[[SubjectFactoryContext], ProbeRoleBundle] = build_probe_roles


subject_plugin: SubjectPlugin = MicroworldSubjectPlugin()


def build_subject_plugin() -> SubjectPlugin:
    """Entry-point factory used by the installed ``evogen.subjects`` group."""

    return subject_plugin


__all__ = [
    "MicroworldDoctor",
    "MicroworldSubjectPlugin",
    "build_subject_plugin",
    "build_probe_roles",
    "subject_plugin",
]
