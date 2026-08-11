from __future__ import annotations

import ast
import importlib
import importlib.metadata
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from evogen.adapters.protocols import (
    CandidateBuilder,
    CandidateReviewer,
    EnvironmentInvestigator,
    ExperimentEvaluator,
    GenerationMaterializer,
    ProbeRoleBundle,
    SubjectDoctor,
    SubjectRunner,
)
from evogen.adapters.subjects import (
    DuplicateSubjectPluginError,
    SubjectBootstrap,
    SubjectBootstrapError,
    SubjectFactoryContext,
    SubjectPluginFactoryError,
    SubjectPluginLoadError,
    SubjectPluginNotFoundError,
    SubjectPluginShapeError,
    SubjectPluginVersionError,
    SubjectWorkspaceError,
    compose_subject,
    discover_subject_entry_points,
    load_subject_plugin,
    run_subject_cycle,
)
from evogen.cli import app
from evogen.core.ids import sha256_bytes
from evogen.core.models import (
    ArtifactRef,
    EvaluationCase,
    EvaluationSuiteManifest,
    EvolutionPlan,
    GenerationManifest,
    ProtectedPathHash,
)
from evogen.storage.artifacts import ArtifactStore
from evogen.storage.ledger import Ledger

ROOT = Path(__file__).resolve().parents[1]
runner = CliRunner()


class _EntryPoints(list):
    def select(self, *, group: str):
        raise AssertionError("current Python path should use entry_points(group=...)")


class _FakeEntryPoint:
    def __init__(self, name: str, value, *, distribution: str = "fake-subject") -> None:
        self.name = name
        self.value = f"fake:{name}"
        self.dist = SimpleNamespace(name=distribution)
        self._value = value

    def load(self):
        if isinstance(self._value, BaseException):
            raise self._value
        return self._value


class _Runner:
    def run(self, **kwargs):
        del kwargs
        return object(), []

    def capability_manifest(self, generation):
        del generation
        return object()


class _Investigator:
    def investigate(self, issue):
        del issue
        return object()


class _Builder:
    def build(self, **kwargs):
        del kwargs
        return object()


class _Reviewer:
    def review(self, candidate, **kwargs):
        del candidate, kwargs
        return object()


class _Evaluator:
    def __init__(self, runner) -> None:
        self.runner = runner

    def evaluate(self, **kwargs):
        del kwargs
        return object()


class _Materializer:
    def __init__(self, runner) -> None:
        self.runner = runner

    def materialize(self, **kwargs):
        del kwargs
        return object()


class _Doctor:
    def check(self) -> None:
        return None


def _bootstrap(
    context: SubjectFactoryContext,
    *,
    subject: str = "fake",
) -> SubjectBootstrap:
    authority_path = (context.workspace / "fake-evaluator.py").resolve()
    authority_path.write_bytes(b"# immutable fake evaluator authority\n")
    authority_digest = sha256_bytes(authority_path.read_bytes())
    source_ref = ArtifactRef(
        digest=context.artifacts.put_bytes(authority_path.read_bytes()),
        model="SourceArtifact",
    )
    case_ids = {
        "revealing": "fake-revealing",
        "variant": "fake-variant",
        "regression": "fake-regression",
        "long_horizon": "fake-long-horizon",
    }

    def evaluation_case(category: str) -> EvaluationCase:
        return EvaluationCase(
            scenario_id=case_ids[category],
            category=category,
            seeds=[0],
            repeat_count=1,
            per_run_wall_clock_ceiling_seconds=1.0,
        )

    evaluation_suite = EvaluationSuiteManifest(
        suite_id="fake-suite-v1",
        revealing_cases=[evaluation_case("revealing")],
        structural_variants=[evaluation_case("variant")],
        regression_suites=[evaluation_case("regression")],
        long_horizon_suites=[evaluation_case("long_horizon")],
        total_wall_clock_ceiling_seconds=10.0,
            evaluator_version="fake-evaluator-v1",
            evaluator=source_ref,
            evaluator_protected_path="fake-evaluator.py",
        environment_artifacts={"fake-evaluator.py": source_ref},
        protected_paths=[
            ProtectedPathHash(
                logical_name="fake-evaluator.py",
                absolute_path=str(authority_path),
                sha256=authority_digest,
            )
        ],
        subject_metric_namespace="fake",
        candidate_tests_authoritative=False,
    )
    return SubjectBootstrap(
        baseline=GenerationManifest(
            generation_id="gen-fake-0001",
            subject=subject,
            source_ref="test:fake",
            capability_manifest_digest="pending",
        ),
        plan=EvolutionPlan(
            diagnostic_scenarios=[],
            revealing_cases=[case_ids["revealing"]],
            structural_variants=[case_ids["variant"]],
            regression_suites=[case_ids["regression"]],
            long_horizon_suites=[case_ids["long_horizon"]],
        ),
        evaluation_suite=evaluation_suite,
    )


def _factories():
    return {
        "runner_factory": lambda context: _Runner(),
        "investigator_factory": lambda context: _Investigator(),
        "builder_factory": lambda context: _Builder(),
        "reviewer_factory": lambda context: _Reviewer(),
        "evaluator_factory": lambda context: _Evaluator(context.runner),
        "materializer_factory": lambda context: _Materializer(context.runner),
        "doctor_factory": lambda context: _Doctor(),
        "bootstrap_factory": lambda context: _bootstrap(context),
    }


def _plugin(*, name: str = "fake", api_version: str = "1.0", **overrides):
    values = {"name": name, "api_version": api_version, **_factories()}
    values.update(overrides)
    return SimpleNamespace(**values)


def _context(tmp_path: Path) -> SubjectFactoryContext:
    return SubjectFactoryContext(
        workspace=tmp_path,
        artifacts=ArtifactStore(tmp_path / "artifacts"),
        ledger=Ledger(tmp_path / "evogen.sqlite3"),
    )


def _metadata(entries):
    def entry_points(*, group: str):
        assert group == "evogen.subjects"
        return entries

    return entry_points


def test_installed_metadata_discovers_bundled_microworld() -> None:
    entries = discover_subject_entry_points()
    microworld = [entry for entry in entries if entry.name == "microworld"]
    assert len(microworld) == 1
    assert microworld[0].value == "evogen.demo.microworld.plugin:build_subject_plugin"
    assert microworld[0].dist is not None
    plugin = load_subject_plugin("microworld")
    assert plugin.name == "microworld"
    assert callable(plugin.bootstrap_factory)


def test_source_packaging_declares_the_subject_entry_point_group() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '[project.entry-points."evogen.subjects"]' in pyproject
    assert (
        'microworld = "evogen.demo.microworld.plugin:build_subject_plugin"' in pyproject
    )


def test_importable_subject_without_installed_metadata_is_not_discoverable(monkeypatch) -> None:
    monkeypatch.setattr(importlib.metadata, "entry_points", _metadata(_EntryPoints()))
    with pytest.raises(SubjectPluginNotFoundError, match="No installed subject plugin"):
        load_subject_plugin("microworld")


def test_empty_requested_name_is_rejected() -> None:
    with pytest.raises(SubjectPluginNotFoundError, match="non-empty string"):
        load_subject_plugin("")


def test_duplicate_entry_point_detail_order_is_deterministic(monkeypatch) -> None:
    entries = _EntryPoints(
        [
            _FakeEntryPoint("same", lambda: _plugin(), distribution="z-distribution"),
            _FakeEntryPoint("same", lambda: _plugin(), distribution="a-distribution"),
        ]
    )
    monkeypatch.setattr(importlib.metadata, "entry_points", _metadata(entries))
    with pytest.raises(DuplicateSubjectPluginError) as raised:
        load_subject_plugin("same")
    message = str(raised.value)
    assert message.index("a-distribution") < message.index("z-distribution")


def test_missing_entry_point_name_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(
        importlib.metadata,
        "entry_points",
        _metadata(_EntryPoints([_FakeEntryPoint("", lambda: _plugin())])),
    )
    with pytest.raises(SubjectPluginShapeError, match="missing or empty name"):
        discover_subject_entry_points()


def test_entry_point_load_exception_is_wrapped_with_context(monkeypatch) -> None:
    monkeypatch.setattr(
        importlib.metadata,
        "entry_points",
        _metadata(
            _EntryPoints(
                [_FakeEntryPoint("broken", RuntimeError("load boom"), distribution="dist-a")]
            )
        ),
    )
    with pytest.raises(SubjectPluginLoadError, match="broken.*dist-a.*load boom"):
        load_subject_plugin("broken")


def test_subject_plugin_factory_exception_is_wrapped_with_context(monkeypatch) -> None:
    def factory():
        raise RuntimeError("factory boom")

    monkeypatch.setattr(
        importlib.metadata,
        "entry_points",
        _metadata(_EntryPoints([_FakeEntryPoint("broken", factory, distribution="dist-c")])),
    )
    with pytest.raises(SubjectPluginLoadError, match="broken.*dist-c.*factory boom"):
        load_subject_plugin("broken")


@pytest.mark.parametrize(
    ("loaded", "error", "message"),
    [
        (object(), SubjectPluginShapeError, "non-callable plugin factory"),
        (lambda: _plugin(name="other"), SubjectPluginShapeError, "names must match"),
        (lambda: _plugin(api_version="9.0"), SubjectPluginVersionError, "supported version"),
    ],
)
def test_loaded_plugin_identity_and_version_fail_closed(
    monkeypatch,
    loaded,
    error,
    message,
) -> None:
    monkeypatch.setattr(
        importlib.metadata,
        "entry_points",
        _metadata(_EntryPoints([_FakeEntryPoint("fake", loaded, distribution="dist-b")])),
    )
    with pytest.raises(error, match=message):
        load_subject_plugin("fake")


@pytest.mark.parametrize(
    "factory_name",
    [
        "runner_factory",
        "investigator_factory",
        "builder_factory",
        "reviewer_factory",
        "evaluator_factory",
        "materializer_factory",
        "doctor_factory",
        "bootstrap_factory",
    ],
)
def test_all_factory_attributes_are_required_and_callable(monkeypatch, factory_name) -> None:
    missing = _plugin()
    delattr(missing, factory_name)
    noncallable = _plugin(**{factory_name: object()})
    for plugin in (missing, noncallable):
        monkeypatch.setattr(
            importlib.metadata,
            "entry_points",
            _metadata(_EntryPoints([_FakeEntryPoint("fake", lambda plugin=plugin: plugin)])),
        )
        with pytest.raises(SubjectPluginShapeError, match=factory_name):
            load_subject_plugin("fake")


@pytest.mark.parametrize(
    ("factory_name", "error"),
    [
        ("runner_factory", SubjectPluginFactoryError),
        ("investigator_factory", SubjectPluginFactoryError),
        ("builder_factory", SubjectPluginFactoryError),
        ("reviewer_factory", SubjectPluginFactoryError),
        ("evaluator_factory", SubjectPluginFactoryError),
        ("materializer_factory", SubjectPluginFactoryError),
        ("doctor_factory", SubjectPluginFactoryError),
        ("bootstrap_factory", SubjectBootstrapError),
    ],
)
def test_all_factories_raise_typed_errors(tmp_path, factory_name, error) -> None:
    def raising(context):
        del context
        raise RuntimeError("factory failure")

    plugin = _plugin(**{factory_name: raising})
    with pytest.raises(error, match=factory_name):
        compose_subject(plugin, context=_context(tmp_path))


@pytest.mark.parametrize(
    ("factory_name", "error"),
    [
        ("runner_factory", SubjectPluginFactoryError),
        ("investigator_factory", SubjectPluginFactoryError),
        ("builder_factory", SubjectPluginFactoryError),
        ("reviewer_factory", SubjectPluginFactoryError),
        ("evaluator_factory", SubjectPluginFactoryError),
        ("materializer_factory", SubjectPluginFactoryError),
        ("doctor_factory", SubjectPluginFactoryError),
        ("bootstrap_factory", SubjectBootstrapError),
    ],
)
def test_all_factories_return_typed_results(tmp_path, factory_name, error) -> None:
    plugin = _plugin(**{factory_name: lambda context: object()})
    with pytest.raises(error, match=factory_name):
        compose_subject(plugin, context=_context(tmp_path))


def test_bootstrap_subject_mismatch_is_rejected(tmp_path) -> None:
    plugin = _plugin(
        bootstrap_factory=lambda context: _bootstrap(context, subject="other")
    )
    with pytest.raises(SubjectBootstrapError, match="does not match plugin identity"):
        compose_subject(plugin, context=_context(tmp_path))


def test_all_factories_share_context_and_runner_identity(tmp_path) -> None:
    seen: list[int] = []
    factories = _factories()
    for factory_name, factory in factories.items():
        def wrapped(context, factory=factory):
            seen.append(id(context))
            return factory(context)

        factories[factory_name] = wrapped
    plugin = _plugin(**factories)
    context = _context(tmp_path)
    composition = compose_subject(plugin, context=context)

    assert len(seen) == 8
    assert set(seen) == {id(context)}
    assert composition.context is context
    assert composition.bootstrap.baseline.subject == "fake"
    assert context.runner is composition.runner
    assert composition.evaluator.runner is composition.runner
    assert composition.materializer.runner is composition.runner
    assert isinstance(composition.runner, SubjectRunner)
    assert isinstance(composition.investigator, EnvironmentInvestigator)
    assert isinstance(composition.builder, CandidateBuilder)
    assert isinstance(composition.reviewer, CandidateReviewer)
    assert isinstance(composition.evaluator, ExperimentEvaluator)
    assert isinstance(composition.materializer, GenerationMaterializer)
    assert isinstance(composition.doctor, SubjectDoctor)


def test_probe_roles_are_optional_but_microworld_exposes_typed_bundle(tmp_path) -> None:
    composition = compose_subject(_plugin(), context=_context(tmp_path / "optional"))
    assert composition.probe_roles is None
    microworld = load_subject_plugin("microworld")
    composed = compose_subject(microworld, context=_context(tmp_path / "microworld"))
    assert composed.probe_roles is not None
    assert all(
        role is not None
        for role in (
            composed.probe_roles.planner,
            composed.probe_roles.builder,
            composed.probe_roles.reviewer,
            composed.probe_roles.evaluator,
        )
    )


@pytest.mark.parametrize("factory", [lambda context: object(), object()])
def test_probe_factory_shape_and_failure_are_typed(tmp_path: Path, factory) -> None:
    plugin = _plugin(probe_roles_factory=factory)
    error = SubjectPluginShapeError if not callable(factory) else SubjectPluginFactoryError
    with pytest.raises(error, match="probe_roles_factory"):
        compose_subject(plugin, context=_context(tmp_path))


def test_probe_factory_exception_is_wrapped(tmp_path: Path) -> None:
    def raising(context):
        del context
        raise RuntimeError("probe factory boom")

    with pytest.raises(SubjectPluginFactoryError, match="probe_roles_factory.*probe factory boom"):
        compose_subject(
            _plugin(probe_roles_factory=raising),
            context=_context(tmp_path),
        )


class _ProbePlanner:
    def plan(self, **kwargs):
        del kwargs
        return object()


class _ProbeBuilder:
    def build(self, **kwargs):
        del kwargs
        return object()


class _ProbeReviewer:
    def review(self, **kwargs):
        del kwargs
        return object()


class _ProbeEvaluator:
    def evaluate(self, **kwargs):
        del kwargs
        return object()


@pytest.mark.parametrize("bad_role", ["planner", "builder", "reviewer", "evaluator"])
def test_each_probe_role_is_runtime_checked(tmp_path: Path, bad_role: str) -> None:
    roles = {
        "planner": _ProbePlanner(),
        "builder": _ProbeBuilder(),
        "reviewer": _ProbeReviewer(),
        "evaluator": _ProbeEvaluator(),
    }
    roles[bad_role] = object()
    plugin = _plugin(probe_roles_factory=lambda context: ProbeRoleBundle(**roles))
    with pytest.raises(SubjectPluginFactoryError, match=bad_role):
        compose_subject(plugin, context=_context(tmp_path))


def test_external_subject_is_discovered_from_real_metadata(tmp_path, monkeypatch) -> None:
    module = tmp_path / "external_subject.py"
    module.write_text(
        "from types import SimpleNamespace\n"
        "def build_subject_plugin():\n"
        "    f = lambda context: object()\n"
        "    return SimpleNamespace(\n"
        "        name='external', api_version='1.0', runner_factory=f,\n"
        "        investigator_factory=f, builder_factory=f, reviewer_factory=f,\n"
        "        evaluator_factory=f, materializer_factory=f, doctor_factory=f,\n"
        "        bootstrap_factory=f,\n"
        "    )\n",
        encoding="utf-8",
    )
    dist_info = tmp_path / "external_subject-1.0.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: external-subject\nVersion: 1.0\n"
    )
    (dist_info / "entry_points.txt").write_text(
        "[evogen.subjects]\nexternal = external_subject:build_subject_plugin\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()
    plugin = load_subject_plugin("external")
    assert plugin.name == "external"


def test_generic_source_has_no_microworld_imports() -> None:
    source_root = ROOT / "src" / "evogen"
    for path in source_root.rglob("*.py"):
        if "demo" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            assert all("evogen.demo.microworld" not in name for name in names), path


def test_existing_unmarked_workspace_is_not_deleted(tmp_path) -> None:
    unsafe = tmp_path / "unsafe"
    unsafe.mkdir()
    marker = unsafe / "keep.txt"
    marker.write_text("keep", encoding="utf-8")
    with pytest.raises(SubjectWorkspaceError, match="unrecognized existing directory"):
        run_subject_cycle("microworld", unsafe, clean=True)
    assert marker.exists()


@pytest.mark.parametrize("target", [Path("/"), Path.home(), Path.cwd(), ROOT])
def test_broad_workspace_targets_are_rejected(target: Path) -> None:
    with pytest.raises(SubjectWorkspaceError):
        run_subject_cycle("microworld", target, clean=True)


def test_existing_file_workspace_target_is_rejected(tmp_path) -> None:
    target = tmp_path / "workspace-file"
    target.write_text("keep", encoding="utf-8")
    with pytest.raises(SubjectWorkspaceError, match="file path"):
        run_subject_cycle("microworld", target, clean=True)
    assert target.read_text(encoding="utf-8") == "keep"


def test_existing_evolution_workspace_can_be_cleaned(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    first = run_subject_cycle("microworld", workspace)
    stale = workspace / "stale.txt"
    stale.write_text("remove", encoding="utf-8")
    second = run_subject_cycle("microworld", workspace, clean=True)
    assert first.experiment.baseline_metrics == second.experiment.baseline_metrics
    assert not stale.exists()
    assert (workspace / "cycle-result.json").exists()


def test_cli_demo_metrics_remain_exact(tmp_path) -> None:
    result = runner.invoke(
        app,
        ["demo", "--workspace", str(tmp_path / "cli"), "--clean", "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["experiment"]["baseline_metrics"] == {
        "revealing_success_rate": 0.0,
        "variant_success_rate": 0.0,
        "regression_success_rate": 1.0,
        "long_horizon_success_rate": 0.0,
        "intervention_count": 0,
        "invalid_action_count": 0,
        "blocked_run_count": 5,
        "average_steps": 1.1428571428571428,
        "new_high_severity_issues": 0,
    }
    assert payload["experiment"]["candidate_metrics"] == {
        "revealing_success_rate": 1.0,
        "variant_success_rate": 1.0,
        "regression_success_rate": 1.0,
        "long_horizon_success_rate": 1.0,
        "intervention_count": 0,
        "invalid_action_count": 0,
        "blocked_run_count": 0,
        "average_steps": 3.2857142857142856,
        "new_high_severity_issues": 0,
    }
    assert payload["decision"]["verdict"] == "retain"
