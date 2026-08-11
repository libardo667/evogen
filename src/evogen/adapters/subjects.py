"""Versioned subject contract, installed loading, and generic composition."""

from __future__ import annotations

import importlib.metadata
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

from evogen.core.enums import StageName
from evogen.core.ids import sha256_bytes
from evogen.core.models import CycleResult, EvolutionPlan, GenerationManifest
from evogen.evolution.orchestrator import EvolutionOrchestrator
from evogen.storage.artifacts import ArtifactStore
from evogen.storage.ledger import Ledger

from .protocols import (
    CandidateBuilder,
    CandidateReviewer,
    EnvironmentInvestigator,
    ExperimentEvaluator,
    GenerationMaterializer,
    ProbeBuilder,
    ProbeEvaluator,
    ProbePlanner,
    ProbeReviewer,
    ProbeRoleBundle,
    SubjectDoctor,
    SubjectRunner,
)

SUBJECT_PLUGIN_API_VERSION = "1.0"
SUBJECT_PLUGIN_ENTRY_POINT_GROUP = "evogen.subjects"


class SubjectPluginError(RuntimeError):
    pass


class SubjectPluginDiscoveryError(SubjectPluginError):
    pass


class SubjectPluginNotFoundError(SubjectPluginDiscoveryError):
    pass


class DuplicateSubjectPluginError(SubjectPluginDiscoveryError):
    pass


class SubjectPluginLoadError(SubjectPluginError):
    pass


class SubjectPluginShapeError(SubjectPluginError):
    pass


class SubjectPluginVersionError(SubjectPluginError):
    pass


class SubjectPluginFactoryError(SubjectPluginShapeError):
    pass


class SubjectBootstrapError(SubjectPluginError):
    pass


class SubjectWorkspaceError(SubjectPluginError):
    pass


class SubjectPlugin(Protocol):
    """Versioned subject contract; loader validation checks callability explicitly."""

    @property
    def name(self) -> str: ...

    @property
    def api_version(self) -> str: ...

    @property
    def runner_factory(self) -> Callable[[SubjectFactoryContext], SubjectRunner]: ...

    @property
    def investigator_factory(
        self,
    ) -> Callable[[SubjectFactoryContext], EnvironmentInvestigator]: ...

    @property
    def builder_factory(self) -> Callable[[SubjectFactoryContext], CandidateBuilder]: ...

    @property
    def reviewer_factory(self) -> Callable[[SubjectFactoryContext], CandidateReviewer]: ...

    @property
    def evaluator_factory(self) -> Callable[[SubjectFactoryContext], ExperimentEvaluator]: ...

    @property
    def materializer_factory(self) -> Callable[[SubjectFactoryContext], GenerationMaterializer]: ...

    @property
    def doctor_factory(self) -> Callable[[SubjectFactoryContext], SubjectDoctor]: ...

    @property
    def bootstrap_factory(self) -> Callable[[SubjectFactoryContext], SubjectBootstrap]: ...

    @property
    def probe_roles_factory(
        self,
    ) -> Callable[[SubjectFactoryContext], ProbeRoleBundle] | None: ...


@dataclass
class SubjectFactoryContext:
    workspace: Path
    artifacts: ArtifactStore
    ledger: Ledger
    runner: SubjectRunner | None = None
    bootstrap: SubjectBootstrap | None = None


@dataclass(frozen=True)
class SubjectBootstrap:
    baseline: GenerationManifest
    plan: EvolutionPlan


@dataclass(frozen=True)
class SubjectComposition:
    plugin: SubjectPlugin
    context: SubjectFactoryContext
    runner: SubjectRunner
    investigator: EnvironmentInvestigator
    builder: CandidateBuilder
    reviewer: CandidateReviewer
    evaluator: ExperimentEvaluator
    materializer: GenerationMaterializer
    doctor: SubjectDoctor
    bootstrap: SubjectBootstrap
    orchestrator: EvolutionOrchestrator
    probe_roles: ProbeRoleBundle | None


def _distribution_name(entry_point: importlib.metadata.EntryPoint) -> str:
    distribution = getattr(entry_point, "dist", None)
    name = getattr(distribution, "name", None) if distribution is not None else None
    return name if isinstance(name, str) and name else "<unknown distribution>"


def _entry_point_sort_key(entry_point: importlib.metadata.EntryPoint) -> tuple[str, str, str]:
    name = getattr(entry_point, "name", "")
    value = getattr(entry_point, "value", "")
    return (str(name), _distribution_name(entry_point), str(value))


def _installed_entry_points() -> list[importlib.metadata.EntryPoint]:
    try:
        selected = importlib.metadata.entry_points(group=SUBJECT_PLUGIN_ENTRY_POINT_GROUP)
        return sorted(list(selected), key=_entry_point_sort_key)
    except Exception as exc:
        raise SubjectPluginDiscoveryError(
            "Could not inspect installed subject entry-point metadata for "
            f"group {SUBJECT_PLUGIN_ENTRY_POINT_GROUP!r}: {exc}"
        ) from exc


def discover_subject_entry_points() -> tuple[importlib.metadata.EntryPoint, ...]:
    entries = _installed_entry_points()
    grouped: dict[str, list[importlib.metadata.EntryPoint]] = {}
    for entry_point in entries:
        name = getattr(entry_point, "name", None)
        if not isinstance(name, str) or not name.strip():
            raise SubjectPluginShapeError(
                "Subject entry point has a missing or empty name in distribution "
                f"{_distribution_name(entry_point)!r}."
            )
        grouped.setdefault(name, []).append(entry_point)

    duplicates = sorted(name for name, matches in grouped.items() if len(matches) > 1)
    if duplicates:
        details = "; ".join(
            f"{name!r}: "
            + ", ".join(
                f"{_distribution_name(entry_point)!r}={getattr(entry_point, 'value', '')!r}"
                for entry_point in grouped[name]
            )
            for name in duplicates
        )
        raise DuplicateSubjectPluginError(
            "Duplicate subject entry-point names in installed metadata: " + details
        )
    return tuple(entries)


def _entry_point_for(subject_name: str) -> importlib.metadata.EntryPoint:
    if not isinstance(subject_name, str) or not subject_name.strip():
        raise SubjectPluginNotFoundError(
            f"Subject plugin name must be a non-empty string; received {subject_name!r}."
        )
    entries = discover_subject_entry_points()
    match = next((entry for entry in entries if entry.name == subject_name), None)
    if match is None:
        available = ", ".join(entry.name for entry in entries) or "<none>"
        raise SubjectPluginNotFoundError(
            f"No installed subject plugin named {subject_name!r} in entry-point group "
            f"{SUBJECT_PLUGIN_ENTRY_POINT_GROUP!r}; available names: {available}."
        )
    return match


def validate_subject_plugin(
    plugin: object,
    *,
    expected_name: str | None = None,
) -> SubjectPlugin:
    try:
        raw_name = getattr(plugin, "name", None)
    except Exception as exc:
        raise SubjectPluginShapeError(
            "Loaded subject plugin has an unreadable identity name."
        ) from exc
    if not isinstance(raw_name, str) or not raw_name.strip():
        raise SubjectPluginShapeError(
            "Loaded subject plugin has a missing or empty string identity name."
        )
    if raw_name != raw_name.strip():
        raise SubjectPluginShapeError(
            f"Subject plugin identity {raw_name!r} must not contain surrounding whitespace."
        )
    name = raw_name
    if expected_name is not None and name != expected_name:
        raise SubjectPluginShapeError(
            f"Subject entry point {expected_name!r} loaded plugin identity {name!r}; names "
            "must match."
        )

    try:
        api_version = getattr(plugin, "api_version", None)
    except Exception as exc:
        raise SubjectPluginVersionError(
            f"Subject plugin {name!r} has an unreadable API version; supported version is "
            f"{SUBJECT_PLUGIN_API_VERSION!r}."
        ) from exc
    if not isinstance(api_version, str) or not api_version.strip():
        raise SubjectPluginVersionError(
            f"Subject plugin {name!r} is missing a non-empty API version; supported version "
            f"is {SUBJECT_PLUGIN_API_VERSION!r}."
        )
    if api_version != SUBJECT_PLUGIN_API_VERSION:
        raise SubjectPluginVersionError(
            f"Subject plugin {name!r} declares API version {api_version!r}; supported version "
            f"is {SUBJECT_PLUGIN_API_VERSION!r}."
        )

    factory_names = (
        "runner_factory",
        "investigator_factory",
        "builder_factory",
        "reviewer_factory",
        "evaluator_factory",
        "materializer_factory",
        "doctor_factory",
        "bootstrap_factory",
    )
    for factory_name in factory_names:
        try:
            factory = getattr(plugin, factory_name)
        except Exception as exc:
            raise SubjectPluginShapeError(
                f"Subject plugin {name!r} has no readable {factory_name!r} attribute."
            ) from exc
        if not callable(factory):
            raise SubjectPluginShapeError(
                f"Subject plugin {name!r} has a missing or non-callable {factory_name}."
            )
    optional_probe_factory = getattr(plugin, "probe_roles_factory", None)
    if optional_probe_factory is not None and not callable(optional_probe_factory):
        raise SubjectPluginShapeError(
            f"Subject plugin {name!r} has a non-callable probe_roles_factory."
        )
    return cast(SubjectPlugin, plugin)


def load_subject_plugin(subject_name: str) -> SubjectPlugin:
    entry_point = _entry_point_for(subject_name)
    distribution = _distribution_name(entry_point)
    try:
        loaded = entry_point.load()
    except Exception as exc:
        raise SubjectPluginLoadError(
            f"Failed to load subject plugin {subject_name!r} from distribution "
            f"{distribution!r}: {exc}"
        ) from exc
    if not callable(loaded):
        raise SubjectPluginShapeError(
            f"Entry point for subject {subject_name!r} from distribution {distribution!r} "
            "loaded a non-callable plugin factory."
        )
    try:
        plugin = loaded()
    except Exception as exc:
        raise SubjectPluginLoadError(
            f"Subject plugin factory for {subject_name!r} from distribution "
            f"{distribution!r} raised while creating the plugin: {exc}"
        ) from exc
    try:
        return validate_subject_plugin(plugin, expected_name=subject_name)
    except SubjectPluginError:
        raise
    except Exception as exc:
        raise SubjectPluginShapeError(
            f"Subject plugin {subject_name!r} from distribution {distribution!r} could not "
            f"be validated: {exc}"
        ) from exc


def _call_factory(
    plugin: SubjectPlugin,
    context: SubjectFactoryContext,
    factory_name: str,
    subject_name: str,
    failure: type[SubjectPluginError],
) -> object:
    try:
        factory = cast(
            Callable[[SubjectFactoryContext], object],
            getattr(plugin, factory_name),
        )
    except Exception as exc:
        raise SubjectPluginShapeError(
            f"Subject plugin {subject_name!r} has an unreadable {factory_name}."
        ) from exc
    try:
        return factory(context)
    except Exception as exc:
        raise failure(f"Subject plugin {subject_name!r} {factory_name} raised: {exc}") from exc


def _factory_result(
    plugin: SubjectPlugin,
    context: SubjectFactoryContext,
    factory_name: str,
    subject_name: str,
    expected_type: str,
    conforms: Callable[[object], bool],
) -> object:
    result = _call_factory(
        plugin,
        context,
        factory_name,
        subject_name,
        SubjectPluginFactoryError,
    )
    try:
        conforms_result = conforms(result)
    except Exception as exc:
        raise SubjectPluginFactoryError(
            f"Subject plugin {subject_name!r} {factory_name} returned an object that "
            f"could not be validated: {exc}"
        ) from exc
    if not conforms_result:
        raise SubjectPluginFactoryError(
            f"Subject plugin {subject_name!r} {factory_name} returned {type(result).__name__}; "
            f"expected an object implementing {expected_type}."
        )
    return result


def _check_runner_dependency(
    role: str,
    subject_name: str,
    behaviour: object,
    runner: SubjectRunner,
) -> None:
    try:
        dependency = getattr(behaviour, "runner", None)
    except Exception as exc:
        raise SubjectPluginFactoryError(
            f"Subject plugin {subject_name!r} {role} has an unreadable runner dependency."
        ) from exc
    if dependency is not None and dependency is not runner:
        raise SubjectPluginFactoryError(
            f"Subject plugin {subject_name!r} {role} is wired to a different runner instance."
        )


def _bootstrap_result(
    plugin: SubjectPlugin,
    context: SubjectFactoryContext,
    subject_name: str,
) -> SubjectBootstrap:
    result = _call_factory(
        plugin,
        context,
        "bootstrap_factory",
        subject_name,
        SubjectBootstrapError,
    )
    if not isinstance(result, SubjectBootstrap):
        raise SubjectBootstrapError(
            f"Subject plugin {subject_name!r} bootstrap_factory returned "
            f"{type(result).__name__}; expected SubjectBootstrap."
        )
    try:
        baseline = result.baseline
        plan = result.plan
    except Exception as exc:
        raise SubjectBootstrapError(
            f"Subject plugin {subject_name!r} bootstrap_factory returned a bootstrap "
            f"with unreadable fields: {exc}"
        ) from exc
    if not isinstance(baseline, GenerationManifest):
        raise SubjectBootstrapError(
            f"Subject plugin {subject_name!r} bootstrap_factory returned a bootstrap "
            "with an invalid baseline; expected GenerationManifest."
        )
    if not isinstance(plan, EvolutionPlan):
        raise SubjectBootstrapError(
            f"Subject plugin {subject_name!r} bootstrap_factory returned a bootstrap "
            "with an invalid plan; expected EvolutionPlan."
        )
    try:
        baseline_subject = baseline.subject
    except Exception as exc:
        raise SubjectBootstrapError(
            f"Subject plugin {subject_name!r} bootstrap baseline has an unreadable subject: {exc}"
        ) from exc
    if baseline_subject != subject_name:
        raise SubjectBootstrapError(
            f"Subject plugin {subject_name!r} bootstrap baseline subject "
            f"{baseline_subject!r} does not match plugin identity."
        )
    return result


def compose_subject(
    plugin: SubjectPlugin,
    *,
    context: SubjectFactoryContext,
) -> SubjectComposition:
    validated = validate_subject_plugin(plugin)
    subject_name = validated.name
    runner = cast(
        SubjectRunner,
        _factory_result(
            validated,
            context,
            "runner_factory",
            subject_name,
            "SubjectRunner",
            lambda value: isinstance(value, SubjectRunner),
        ),
    )
    context.runner = runner
    bootstrap = _bootstrap_result(validated, context, subject_name)
    context.bootstrap = bootstrap
    investigator = cast(
        EnvironmentInvestigator,
        _factory_result(
            validated,
            context,
            "investigator_factory",
            subject_name,
            "EnvironmentInvestigator",
            lambda value: isinstance(value, EnvironmentInvestigator),
        ),
    )
    builder = cast(
        CandidateBuilder,
        _factory_result(
            validated,
            context,
            "builder_factory",
            subject_name,
            "CandidateBuilder",
            lambda value: isinstance(value, CandidateBuilder),
        ),
    )
    reviewer = cast(
        CandidateReviewer,
        _factory_result(
            validated,
            context,
            "reviewer_factory",
            subject_name,
            "CandidateReviewer",
            lambda value: isinstance(value, CandidateReviewer),
        ),
    )
    evaluator = cast(
        ExperimentEvaluator,
        _factory_result(
            validated,
            context,
            "evaluator_factory",
            subject_name,
            "ExperimentEvaluator",
            lambda value: isinstance(value, ExperimentEvaluator),
        ),
    )
    _check_runner_dependency("evaluator_factory", subject_name, evaluator, runner)
    materializer = cast(
        GenerationMaterializer,
        _factory_result(
            validated,
            context,
            "materializer_factory",
            subject_name,
            "GenerationMaterializer",
            lambda value: isinstance(value, GenerationMaterializer),
        ),
    )
    _check_runner_dependency("materializer_factory", subject_name, materializer, runner)
    doctor = cast(
        SubjectDoctor,
        _factory_result(
            validated,
            context,
            "doctor_factory",
            subject_name,
            "SubjectDoctor",
            lambda value: isinstance(value, SubjectDoctor),
        ),
    )
    orchestrator = EvolutionOrchestrator(
        workspace=context.workspace,
        artifacts=context.artifacts,
        ledger=context.ledger,
        runner=runner,
        investigator=investigator,
        builder=builder,
        reviewer=reviewer,
        evaluator=evaluator,
        materializer=materializer,
        baseline=bootstrap.baseline,
        plan=bootstrap.plan,
        subject_plugin_name=subject_name,
        subject_plugin_api_version=validated.api_version,
        subject_plugin_source=_plugin_source_identity(validated),
    )
    probe_roles: ProbeRoleBundle | None = None
    probe_factory = getattr(validated, "probe_roles_factory", None)
    if probe_factory is not None:
        result = _call_factory(
            validated,
            context,
            "probe_roles_factory",
            subject_name,
            SubjectPluginFactoryError,
        )
        if not isinstance(result, ProbeRoleBundle):
            raise SubjectPluginFactoryError(
                f"Subject plugin {subject_name!r} probe_roles_factory returned "
                f"{type(result).__name__}; expected ProbeRoleBundle."
            )
        for name, role, expected in (
            ("planner", result.planner, ProbePlanner),
            ("builder", result.builder, ProbeBuilder),
            ("reviewer", result.reviewer, ProbeReviewer),
            ("evaluator", result.evaluator, ProbeEvaluator),
        ):
            if not isinstance(role, expected):
                raise SubjectPluginFactoryError(
                    f"Subject plugin {subject_name!r} probe role {name!r} does not "
                    f"implement {expected.__name__}."
                )
        if len({id(result.builder), id(result.reviewer), id(result.evaluator)}) != 3:
            raise SubjectPluginFactoryError(
                f"Subject plugin {subject_name!r} probe builder, reviewer, and "
                "evaluator must be distinct authorities."
            )
        probe_roles = result
    return SubjectComposition(
        plugin=validated,
        context=context,
        runner=runner,
        investigator=investigator,
        builder=builder,
        reviewer=reviewer,
        evaluator=evaluator,
        materializer=materializer,
        doctor=doctor,
        bootstrap=bootstrap,
        orchestrator=orchestrator,
        probe_roles=probe_roles,
    )


def _plugin_source_identity(plugin: SubjectPlugin) -> str:
    module_name = plugin.__class__.__module__
    module = sys.modules.get(module_name)
    source_path = getattr(module, "__file__", None)
    if isinstance(source_path, str):
        path = Path(source_path)
        if path.is_file():
            return f"{module_name}:{sha256_bytes(path.read_bytes())}"
    return f"{module_name}:{plugin.__class__.__qualname__}"


def _is_recognizable_workspace(path: Path) -> bool:
    if path == (Path.cwd() / ".evogen-demo").resolve():
        return True
    return (
        (path / "evogen.sqlite3").is_file()
        and (path / "artifacts").is_dir()
        and any(
            (path / marker).exists()
            for marker in ("traces", "subjects", "candidates", "cycle-result.json", "report.md")
        )
    )


def _contains_git_repository(path: Path) -> bool:
    for ancestor in (path, *path.parents):
        marker = ancestor / ".git"
        if marker.is_file():
            return True
        if marker.is_dir() and ancestor == path:
            return True
        if marker.is_dir() and any((marker / name).exists() for name in ("HEAD", "config")):
            return True
    return False


def _prepare_workspace(workspace: Path, *, clean: bool) -> Path:
    resolved = workspace.resolve()
    if clean and resolved.exists():
        if resolved.is_file():
            raise SubjectWorkspaceError(
                f"Refusing to clean file path {resolved}; expected an EvoGen workspace directory."
            )
        if resolved == Path(resolved.anchor):
            raise SubjectWorkspaceError(f"Refusing to clean filesystem root {resolved}.")
        if resolved == Path.home():
            raise SubjectWorkspaceError(f"Refusing to clean user home directory {resolved}.")
        if resolved == Path.cwd().resolve():
            raise SubjectWorkspaceError(f"Refusing to clean current working directory {resolved}.")
        if resolved != (Path.cwd() / ".evogen-demo").resolve() and _contains_git_repository(
            resolved
        ):
            raise SubjectWorkspaceError(
                f"Refusing to clean repository path {resolved}; an ancestor contains .git."
            )
        if not _is_recognizable_workspace(resolved):
            raise SubjectWorkspaceError(
                f"Refusing to clean unrecognized existing directory {resolved}; "
                "expected an EvoGen ledger, artifacts, and workspace evidence."
            )
        try:
            shutil.rmtree(resolved)
        except OSError as exc:
            raise SubjectWorkspaceError(
                f"Could not clean EvoGen workspace {resolved}: {exc}"
            ) from exc
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def run_subject_cycle(
    subject_name: str,
    workspace: Path,
    *,
    clean: bool = False,
    until: StageName | str | None = None,
) -> CycleResult:
    plugin = load_subject_plugin(subject_name)
    resolved = _prepare_workspace(workspace, clean=clean)
    context = SubjectFactoryContext(
        workspace=resolved,
        artifacts=ArtifactStore(resolved / "artifacts"),
        ledger=Ledger(resolved / "evogen.sqlite3"),
    )
    composition = compose_subject(plugin, context=context)
    result = composition.orchestrator.stages.run(until=until)
    if not isinstance(result, CycleResult):
        raise SubjectWorkspaceError(
            f"run_subject_cycle requires select or no --until; received {type(result).__name__}"
        )
    return result


def run_subject_progress(
    subject_name: str,
    workspace: Path,
    *,
    clean: bool = False,
    until: StageName | str | None = None,
) -> object:
    """Run the same dispatcher, allowing a typed mid-cycle result."""
    plugin = load_subject_plugin(subject_name)
    resolved = _prepare_workspace(workspace, clean=clean)
    context = SubjectFactoryContext(
        workspace=resolved,
        artifacts=ArtifactStore(resolved / "artifacts"),
        ledger=Ledger(resolved / "evogen.sqlite3"),
    )
    composition = compose_subject(plugin, context=context)
    return composition.orchestrator.stages.run(until=until)


def run_subject_stage(
    subject_name: str,
    workspace: Path,
    stage: StageName | str,
    *,
    clean: bool = False,
) -> object:
    """Invoke exactly one persisted stage through the generic dispatcher."""
    plugin = load_subject_plugin(subject_name)
    resolved = _prepare_workspace(workspace, clean=clean)
    context = SubjectFactoryContext(
        workspace=resolved,
        artifacts=ArtifactStore(resolved / "artifacts"),
        ledger=Ledger(resolved / "evogen.sqlite3"),
    )
    composition = compose_subject(plugin, context=context)
    return composition.orchestrator.stages.invoke(stage)


def read_subject_stage(
    subject_name: str,
    workspace: Path,
    stage: StageName | str,
) -> object:
    """Read a completed stage without executing or publishing any stage."""
    plugin = load_subject_plugin(subject_name)
    resolved = workspace.resolve()
    if not resolved.exists():
        raise SubjectWorkspaceError(f"No EvoGen workspace at {resolved}")
    if (
        not (resolved / "artifacts").is_dir()
        or not (resolved / "evogen.sqlite3").is_file()
        or not (resolved / "cycle-manifest.pointer.json").is_file()
    ):
        raise SubjectWorkspaceError(f"Incomplete EvoGen workspace at {resolved}")
    context = SubjectFactoryContext(
        workspace=resolved,
        artifacts=ArtifactStore(resolved / "artifacts", read_only=True),
        ledger=Ledger(resolved / "evogen.sqlite3", read_only=True),
    )
    composition = compose_subject(plugin, context=context)
    return composition.orchestrator.stages.completed_stage(stage)


def read_subject_status(
    subject_name: str,
    workspace: Path,
) -> tuple[tuple[StageName, ...], StageName | None]:
    """Validate and report stage state without running a missing stage."""
    plugin = load_subject_plugin(subject_name)
    resolved = workspace.resolve()
    if not resolved.exists():
        raise SubjectWorkspaceError(f"No EvoGen workspace at {resolved}")
    if (
        not (resolved / "artifacts").is_dir()
        or not (resolved / "evogen.sqlite3").is_file()
        or not (resolved / "cycle-manifest.pointer.json").is_file()
    ):
        raise SubjectWorkspaceError(f"Incomplete EvoGen workspace at {resolved}")
    context = SubjectFactoryContext(
        workspace=resolved,
        artifacts=ArtifactStore(resolved / "artifacts", read_only=True),
        ledger=Ledger(resolved / "evogen.sqlite3", read_only=True),
    )
    composition = compose_subject(plugin, context=context)
    return composition.orchestrator.stages.stage_status()


__all__ = [
    "DuplicateSubjectPluginError",
    "SUBJECT_PLUGIN_API_VERSION",
    "SUBJECT_PLUGIN_ENTRY_POINT_GROUP",
    "SubjectBootstrap",
    "SubjectBootstrapError",
    "SubjectComposition",
    "SubjectDoctor",
    "SubjectFactoryContext",
    "SubjectPlugin",
    "SubjectPluginError",
    "SubjectPluginFactoryError",
    "SubjectPluginDiscoveryError",
    "SubjectPluginLoadError",
    "SubjectPluginNotFoundError",
    "SubjectPluginShapeError",
    "SubjectPluginVersionError",
    "compose_subject",
    "discover_subject_entry_points",
    "load_subject_plugin",
    "run_subject_cycle",
    "run_subject_progress",
    "run_subject_stage",
    "read_subject_stage",
    "read_subject_status",
    "SubjectWorkspaceError",
    "validate_subject_plugin",
]
