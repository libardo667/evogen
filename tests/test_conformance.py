from __future__ import annotations

import ast
import shutil
import sqlite3
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from evogen.adapters import conformance
from evogen.adapters.conformance import BOUNDARIES, run_subject_conformance
from evogen.adapters.subjects import (
    SubjectBootstrap,
    SubjectFactoryContext,
    compose_subject,
    load_subject_plugin,
)
from evogen.cli import app
from evogen.core.enums import Completeness
from evogen.core.ids import sha256_bytes, stable_json_bytes
from evogen.core.models import (
    BoundedCollection,
    SubjectCheck,
    SubjectConformanceReport,
    SubjectDiagnostic,
)
from evogen.storage.artifacts import ArtifactStore
from evogen.storage.ledger import Ledger

ROOT = Path(__file__).parents[1]


def test_microworld_positive_report_exercises_all_seven_boundaries() -> None:
    report = run_subject_conformance("microworld")
    assert report.status == "pass"
    assert report.passed is True
    assert [check.boundary_id for check in report.checks] == list(BOUNDARIES)
    assert all(check.status == "pass" and check.evidence for check in report.checks)
    assert report.diagnostics.completeness == Completeness.COMPLETE
    assert report.diagnostics.items == []


def test_public_doctor_does_not_publish_cycle_or_stage_authority(tmp_path: Path) -> None:
    workspace = tmp_path / "new-doctor"
    report = run_subject_conformance("microworld", workspace=workspace)
    assert report.status == "pass"
    assert not any(
        (workspace / name).exists()
        for name in (
            "cycle-result.json",
            "report.md",
            "cycle-manifest.pointer.json",
            "lineage.pointer.json",
        )
    )
    ledger = Ledger(workspace / "evogen.sqlite3", read_only=True)
    assert ledger.list_generations() == []
    assert ledger.lineage_rows() == []


@pytest.mark.parametrize(
    "failure,blocked",
    [
        ("_generation_check", set(BOUNDARIES[1:])),
        ("_capability_check", set(BOUNDARIES[2:])),
        ("_trajectory_check", set(BOUNDARIES[3:])),
        ("_builder_check", {"evaluation_symmetry", "retained_generation_materialization"}),
        ("_evaluation_check", {"retained_generation_materialization"}),
    ],
)
def test_failed_prerequisites_block_dependent_boundaries(
    monkeypatch: pytest.MonkeyPatch, failure: str, blocked: set[str]
) -> None:
    def fail(*args: object, **kwargs: object):
        raise RuntimeError(f"malicious {failure}")

    monkeypatch.setattr(conformance, failure, fail)
    report = run_subject_conformance("microworld")
    by_boundary = {check.boundary_id: check for check in report.checks}
    boundary_name = {
        "_generation_check": "generation_manifest",
        "_capability_check": "capability_manifest",
        "_trajectory_check": "trajectory_ordering",
        "_builder_check": "candidate_workspace_isolation",
        "_evaluation_check": "evaluation_symmetry",
    }[failure]
    assert by_boundary[boundary_name].status == "fail"
    for boundary in blocked:
        assert by_boundary[boundary].status == "blocked"
        assert by_boundary[boundary].blocked_dependency


def test_loading_failure_uses_report_shape_and_blocks_remaining(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(name: str):
        raise conformance.SubjectPluginError(
            "missing", boundary_id="discovery", code="subject_not_found"
        )

    monkeypatch.setattr(conformance, "load_subject_plugin", fail)
    report = run_subject_conformance("missing")
    assert report.status == "fail"
    assert report.checks[0].boundary_id == "discovery"
    assert report.checks[0].evidence["code"] == "subject_not_found"
    assert all(check.status == "blocked" for check in report.checks[1:])


def test_nonempty_or_incomplete_doctor_diagnostics_fail_report() -> None:
    check = SubjectCheck(
        boundary_id="generation_manifest",
        status="pass",
        message="ok",
        evidence={"verified": True},
    )
    for diagnostics in (
        BoundedCollection(
            items=[SubjectDiagnostic(code="warning", message="evidence")],
            completeness=Completeness.COMPLETE,
            known_total=1,
        ),
        BoundedCollection(items=[], completeness=Completeness.UNKNOWN),
        BoundedCollection(items=[], completeness=Completeness.MISSING),
        BoundedCollection(
            items=[SubjectDiagnostic(code="partial", message="evidence")],
            completeness=Completeness.TRUNCATED,
            known_total=2,
        ),
    ):
        report = SubjectConformanceReport(
            subject="fake", api_version="1.1", checks=[check], diagnostics=diagnostics
        )
        assert report.status == "fail"
        assert report.passed is False


def test_cli_json_and_human_exit_and_markup_safety() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["subject", "doctor", "missing", "--json"])
    assert result.exit_code == 1
    assert '"status": "fail"' in result.stdout
    human = runner.invoke(app, ["subject", "doctor", "missing"])
    assert human.exit_code == 1
    assert "[subject_not_found]" in human.stdout


def test_cli_list_is_metadata_only() -> None:
    result = CliRunner().invoke(app, ["subject", "list", "--json"])
    assert result.exit_code == 0
    assert '"name": "microworld"' in result.stdout


def test_explicit_workspace_safety_refuses_existing_unrecognized_directory(tmp_path: Path) -> None:
    unsafe = tmp_path / "unsafe"
    unsafe.mkdir()
    marker = unsafe / "keep.txt"
    marker.write_text("keep", encoding="utf-8")
    report = run_subject_conformance("microworld", workspace=unsafe)
    assert report.status == "fail"
    assert report.checks[0].boundary_id == "workspace"
    assert marker.read_text(encoding="utf-8") == "keep"


def test_public_doctor_refuses_existing_evolution_workspace_and_symlink_without_writes(
    tmp_path: Path,
) -> None:
    existing = tmp_path / "existing"
    existing.mkdir()
    (existing / "evogen.sqlite3").write_bytes(b"sentinel")
    before = sorted((path.relative_to(existing), path.read_bytes()) for path in existing.rglob("*"))
    report = run_subject_conformance("microworld", workspace=existing)
    assert report.checks[0].boundary_id == "workspace"
    assert report.checks[0].evidence["code"] == "workspace_not_new"
    after = sorted((path.relative_to(existing), path.read_bytes()) for path in existing.rglob("*"))
    assert before == after

    target = tmp_path / "target"
    link = tmp_path / "doctor-link"
    link.symlink_to(target, target_is_directory=True)
    report = run_subject_conformance("microworld", workspace=link)
    assert report.checks[0].evidence["code"] == "workspace_symlink"
    assert not target.exists()

    parent_target = tmp_path / "parent-target"
    parent_target.mkdir()
    parent_link = tmp_path / "parent-link"
    parent_link.symlink_to(parent_target, target_is_directory=True)
    nested = parent_link / "nested"
    report = run_subject_conformance("microworld", workspace=nested)
    assert report.checks[0].evidence["code"] == "workspace_ancestor_symlink"
    assert not (parent_target / "nested").exists()


def test_cli_unexpected_doctor_exception_uses_typed_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "evogen.cli.run_subject_conformance",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("outer failure")),
    )
    runner = CliRunner()
    json_result = runner.invoke(app, ["subject", "doctor", "microworld", "--json"])
    assert json_result.exit_code == 1
    assert '"status": "fail"' in json_result.stdout
    assert '"code": "subject_doctor_error"' in json_result.stdout
    human_result = runner.invoke(app, ["subject", "doctor", "microworld"])
    assert human_result.exit_code == 1
    assert "subject_doctor_error" in human_result.stdout


def _public_plugin(monkeypatch: pytest.MonkeyPatch, **updates: object) -> object:
    plugin = load_subject_plugin("microworld")
    hostile = replace(plugin, **updates)
    monkeypatch.setattr(conformance, "load_subject_plugin", lambda name: hostile)
    return hostile


def test_public_requested_scenario_forgery_fails_trajectory_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = load_subject_plugin("microworld")

    def runner_factory(context):
        runner = base.runner_factory(context)
        original = runner.run

        def hostile(**kwargs):
            return original(**{**kwargs, "scenario_id": "diagnostic:opaque-container"})

        runner.run = hostile
        return runner

    _public_plugin(monkeypatch, runner_factory=runner_factory)
    report = run_subject_conformance("microworld")
    by_boundary = {check.boundary_id: check for check in report.checks}
    assert by_boundary["trajectory_ordering"].status == "fail"
    assert by_boundary["trajectory_ordering"].evidence["code"] == "trajectory_ordering_error"
    assert by_boundary["scenario_isolation"].status == "blocked"


def test_public_generation_wrong_typed_capability_generation_fails_generation_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = load_subject_plugin("microworld")

    def bootstrap_factory(context):
        bootstrap = base.bootstrap_factory(context)
        manifest = base.runner_factory(context).capability_manifest(bootstrap.baseline)
        wrong = manifest.model_copy(update={"generation_id": "forged-generation"})
        digest = context.artifacts.put_json(wrong.model_dump(mode="json"))
        baseline = bootstrap.baseline.model_copy(
            update={
                "capability_manifest_digest": digest,
                "artifact_digests": {
                    **bootstrap.baseline.artifact_digests,
                    "capability_manifest": digest,
                },
            }
        )
        return SubjectBootstrap(
            baseline=baseline,
            plan=bootstrap.plan,
            evaluation_suite=bootstrap.evaluation_suite,
        )

    _public_plugin(monkeypatch, bootstrap_factory=bootstrap_factory)
    report = run_subject_conformance("microworld")
    by_boundary = {check.boundary_id: check for check in report.checks}
    assert by_boundary["generation_manifest"].status == "fail"
    assert by_boundary["generation_manifest"].evidence["code"] == "generation_manifest_error"
    assert all(by_boundary[name].status == "blocked" for name in BOUNDARIES[1:])


def test_public_capability_instability_fails_capability_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = load_subject_plugin("microworld")
    calls = 0

    def runner_factory(context):
        nonlocal calls
        runner = base.runner_factory(context)
        original = runner.capability_manifest

        def hostile(generation):
            nonlocal calls
            calls += 1
            manifest = original(generation)
            return (
                manifest.model_copy(update={"generation_id": "forged-generation"})
                if calls >= 2
                else manifest
            )

        runner.capability_manifest = hostile
        return runner

    _public_plugin(monkeypatch, runner_factory=runner_factory)
    report = run_subject_conformance("microworld")
    by_boundary = {check.boundary_id: check for check in report.checks}
    assert by_boundary["capability_manifest"].status == "fail"
    assert by_boundary["capability_manifest"].evidence["code"] == "capability_manifest_error"
    assert all(by_boundary[name].status == "blocked" for name in BOUNDARIES[2:])


def test_public_isolation_disk_divergence_fails_isolation_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = load_subject_plugin("microworld")
    calls = 0
    counts = {"builder": 0, "evaluator": 0, "materializer": 0}

    def runner_factory(context):
        nonlocal calls
        runner = base.runner_factory(context)
        original = runner.run

        def hostile(**kwargs):
            nonlocal calls
            calls += 1
            record, events = original(**kwargs)
            if calls == 4:
                path = Path(record.metadata["trace_path"])
                forged_events = [
                    events[0].model_copy(update={"payload": {**events[0].payload, "forged": True}}),
                    *events[1:],
                ]
                path.write_text(
                    "\n".join(event.model_dump_json() for event in forged_events) + "\n",
                    encoding="utf-8",
                )
            return record, events

        runner.run = hostile
        return runner

    def builder_factory(context):
        builder = base.builder_factory(context)
        original = builder.build

        def counted(**kwargs):
            counts["builder"] += 1
            return original(**kwargs)

        builder.build = counted
        return builder

    def evaluator_factory(context):
        evaluator = base.evaluator_factory(context)
        original = evaluator.evaluate

        def counted(**kwargs):
            counts["evaluator"] += 1
            return original(**kwargs)

        evaluator.evaluate = counted
        return evaluator

    def materializer_factory(context):
        materializer = base.materializer_factory(context)
        original = materializer.materialize

        def counted(**kwargs):
            counts["materializer"] += 1
            return original(**kwargs)

        materializer.materialize = counted
        return materializer

    _public_plugin(
        monkeypatch,
        runner_factory=runner_factory,
        builder_factory=builder_factory,
        evaluator_factory=evaluator_factory,
        materializer_factory=materializer_factory,
    )
    report = run_subject_conformance("microworld")
    by_boundary = {check.boundary_id: check for check in report.checks}
    assert by_boundary["scenario_isolation"].status == "fail"
    assert by_boundary["candidate_workspace_isolation"].status == "blocked"
    assert by_boundary["evaluation_symmetry"].status == "blocked"
    assert by_boundary["retained_generation_materialization"].status == "blocked"
    assert counts == {"builder": 0, "evaluator": 0, "materializer": 0}


def test_public_candidate_valid_post_build_mutation_fails_candidate_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = load_subject_plugin("microworld")

    def builder_factory(context):
        builder = base.builder_factory(context)
        original = builder.build

        def hostile(**kwargs):
            candidate = original(**kwargs)
            path = Path(candidate.workspace_path) / candidate.changed_files[0]
            path.write_text(path.read_text(encoding="utf-8") + "\n# forged\n", encoding="utf-8")
            return candidate

        builder.build = hostile
        return builder

    _public_plugin(monkeypatch, builder_factory=builder_factory)
    report = run_subject_conformance("microworld")
    by_boundary = {check.boundary_id: check for check in report.checks}
    assert by_boundary["candidate_workspace_isolation"].status == "fail"
    assert by_boundary["evaluation_symmetry"].status == "blocked"


def test_public_evaluator_identity_forgery_fails_evaluation_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = load_subject_plugin("microworld")

    def evaluator_factory(context):
        evaluator = base.evaluator_factory(context)
        original = evaluator.evaluate

        def hostile(**kwargs):
            outcome = original(**kwargs)
            return outcome.model_copy(update={"candidate_id": "forged-candidate"})

        evaluator.evaluate = hostile
        return evaluator

    _public_plugin(monkeypatch, evaluator_factory=evaluator_factory)
    report = run_subject_conformance("microworld")
    by_boundary = {check.boundary_id: check for check in report.checks}
    assert by_boundary["evaluation_symmetry"].status == "fail"
    assert by_boundary["retained_generation_materialization"].status == "blocked"


@pytest.mark.parametrize("forgery", ["inverted_window", "zero_elapsed", "total_ceiling"])
def test_public_evaluation_time_forgery_fails_evaluation_boundary(
    monkeypatch: pytest.MonkeyPatch, forgery: str
) -> None:
    base = load_subject_plugin("microworld")

    def evaluator_factory(context):
        evaluator = base.evaluator_factory(context)
        original = evaluator.evaluate

        def hostile(**kwargs):
            outcome = original(**kwargs)
            if forgery == "inverted_window":
                outcome = outcome.model_copy(
                    update={"started_at": outcome.finished_at + timedelta(seconds=1)}
                )
            elif forgery == "zero_elapsed":
                outcome = outcome.model_copy(
                    update={
                        "baseline_results": [
                            result.model_copy(update={"elapsed_seconds": 0.0})
                            for result in outcome.baseline_results
                        ],
                        "candidate_results": [
                            result.model_copy(update={"elapsed_seconds": 0.0})
                            for result in outcome.candidate_results
                        ],
                    }
                )
            else:
                context.bootstrap.evaluation_suite.total_wall_clock_ceiling_seconds = 0.000001
            return outcome

        evaluator.evaluate = hostile
        return evaluator

    _public_plugin(monkeypatch, evaluator_factory=evaluator_factory)
    report = run_subject_conformance("microworld")
    by_boundary = {check.boundary_id: check for check in report.checks}
    assert by_boundary["evaluation_symmetry"].status == "fail"
    assert by_boundary["retained_generation_materialization"].status == "blocked"


def test_public_symmetric_forged_subject_metric_namespace_fails_evaluation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = load_subject_plugin("microworld")

    def evaluator_factory(context):
        evaluator = base.evaluator_factory(context)
        original = evaluator.evaluate

        def hostile(**kwargs):
            outcome = original(**kwargs)
            forged = [
                metric.model_copy(update={"namespace": "forged"})
                for metric in outcome.baseline_subject_metrics
            ]
            return outcome.model_copy(
                update={
                    "baseline_subject_metrics": forged,
                    "candidate_subject_metrics": [
                        metric.model_copy(update={"namespace": "forged"})
                        for metric in outcome.candidate_subject_metrics
                    ],
                }
            )

        evaluator.evaluate = hostile
        return evaluator

    _public_plugin(monkeypatch, evaluator_factory=evaluator_factory)
    report = run_subject_conformance("microworld")
    by_boundary = {check.boundary_id: check for check in report.checks}
    assert by_boundary["evaluation_symmetry"].status == "fail"
    assert by_boundary["retained_generation_materialization"].status == "blocked"


def test_public_materializer_authority_mutation_fails_materialization_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = load_subject_plugin("microworld")

    def materializer_factory(context):
        materializer = base.materializer_factory(context)
        original = materializer.materialize
        suite = context.bootstrap.evaluation_suite
        protected = suite.protected_paths[0]
        fixture_path = context.workspace / "authority-fixture" / Path(protected.absolute_path).name
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_bytes = Path(protected.absolute_path).read_bytes()
        fixture_path.write_bytes(fixture_bytes)
        fixture_digest = sha256_bytes(fixture_bytes)
        context.artifacts.put_bytes(fixture_bytes)
        protected_copy = protected.model_copy(
            update={"absolute_path": str(fixture_path), "sha256": fixture_digest}
        )
        protected_paths = [
            protected_copy if item.logical_name == protected.logical_name else item
            for item in suite.protected_paths
        ]
        environment_artifacts = {
            name: (
                reference.model_copy(update={"digest": fixture_digest})
                if name == protected.logical_name
                else reference
            )
            for name, reference in suite.environment_artifacts.items()
        }
        evaluator_ref = (
            suite.evaluator.model_copy(update={"digest": fixture_digest})
            if suite.evaluator_protected_path == protected.logical_name
            else suite.evaluator
        )
        updated_suite = suite.model_copy(
            update={
                "protected_paths": protected_paths,
                "environment_artifacts": environment_artifacts,
                "evaluator": evaluator_ref,
            }
        )
        object.__setattr__(context.bootstrap, "evaluation_suite", updated_suite)

        def hostile(**kwargs):
            fixture_path.write_bytes(fixture_path.read_bytes() + b" forged")
            return original(**kwargs)

        materializer.materialize = hostile
        return materializer

    _public_plugin(monkeypatch, materializer_factory=materializer_factory)
    report = run_subject_conformance("microworld")
    by_boundary = {check.boundary_id: check for check in report.checks}
    assert by_boundary["retained_generation_materialization"].status == "fail"


def test_generic_conformance_has_no_domain_imports_or_literals() -> None:
    path = ROOT / "src" / "evogen" / "adapters" / "conformance.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    source = path.read_text(encoding="utf-8").lower()
    assert not any(word in source for word in ("kenshi", "openttd", "microworld"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all("evogen.demo" not in alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            assert "evogen.demo" not in (node.module or "")


def _composition(tmp_path: Path):
    workspace = tmp_path / "subject"
    return compose_subject(
        load_subject_plugin("microworld"),
        context=SubjectFactoryContext(
            workspace=workspace,
            artifacts=ArtifactStore(workspace / "artifacts"),
            ledger=Ledger(workspace / "evogen.sqlite3"),
        ),
        publish_cycle_manifest=False,
    )


def test_generation_rejects_wrong_model_and_wrong_generation_cas(tmp_path: Path) -> None:
    composition = _composition(tmp_path)
    baseline = composition.bootstrap.baseline
    path = composition.context.artifacts.path_for(baseline.capability_manifest_digest)
    original = path.read_bytes()
    path.write_bytes(stable_json_bytes({"wrong": "model"}))
    with pytest.raises(ValueError, match="wrong model"):
        conformance._generation_check(composition)
    path.write_bytes(original)
    manifest = composition.runner.capability_manifest(baseline).model_copy(
        update={"generation_id": "wrong-generation"}
    )
    wrong_digest = composition.context.artifacts.put_json(manifest.model_dump(mode="json"))
    wrong_baseline = baseline.model_copy(
        update={
            "capability_manifest_digest": wrong_digest,
            "artifact_digests": {
                **baseline.artifact_digests,
                "capability_manifest": wrong_digest,
            },
        }
    )
    object.__setattr__(composition.bootstrap, "baseline", wrong_baseline)
    with pytest.raises(ValueError, match="generation identity"):
        conformance._generation_check(composition)


def test_trajectory_rejects_outside_and_symlink_trace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    composition = _composition(tmp_path)
    original_run = composition.runner.run
    outside = tmp_path / "outside.jsonl"

    def outside_run(**kwargs):
        record, events = original_run(**kwargs)
        path = Path(record.metadata["trace_path"])
        outside.write_bytes(path.read_bytes())
        return record.model_copy(
            update={"metadata": {**record.metadata, "trace_path": str(outside)}}
        ), events

    monkeypatch.setattr(composition.runner, "run", outside_run)
    with pytest.raises(ValueError, match="regular-file trace"):
        conformance._trajectory_check(composition, {})

    monkeypatch.undo()
    original_run = composition.runner.run

    def symlink_run(**kwargs):
        record, events = original_run(**kwargs)
        path = Path(record.metadata["trace_path"])
        target = path.with_suffix(".real")
        path.rename(target)
        path.symlink_to(target)
        return record, events

    monkeypatch.setattr(composition.runner, "run", symlink_run)
    with pytest.raises(ValueError, match="regular-file trace"):
        conformance._trajectory_check(composition, {})


def test_candidate_sibling_and_post_build_mutations_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    composition = _composition(tmp_path)
    original_build = composition.builder.build

    def sibling_build(**kwargs):
        candidate = original_build(**kwargs)
        Path(kwargs["candidate_root"], "sibling.txt").write_text("forged", encoding="utf-8")
        return candidate

    monkeypatch.setattr(composition.builder, "build", sibling_build)
    with pytest.raises(ValueError, match="sibling"):
        conformance._builder_check(composition, {})
    shutil.rmtree(composition.context.workspace / "candidates")

    monkeypatch.undo()
    state: dict[str, object] = {}
    assert conformance._builder_check(composition, state).status == "pass"
    original_review = composition.reviewer.review

    def mutating_review(candidate, **kwargs):
        review = original_review(candidate, **kwargs)
        path = Path(candidate.workspace_path, "plugins", "inspect_container.py")
        path.write_text(path.read_text(encoding="utf-8") + "\n# forged\n", encoding="utf-8")
        return review

    monkeypatch.setattr(composition.reviewer, "review", mutating_review)
    with pytest.raises(ValueError, match="candidate workspace"):
        conformance._evaluation_check(composition, state)


def test_materializer_protected_authority_mutation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    composition = _composition(tmp_path)
    state: dict[str, object] = {}
    assert conformance._builder_check(composition, state).status == "pass"
    assert conformance._evaluation_check(composition, state).status == "pass"
    original_materialize = composition.materializer.materialize
    protected = Path(composition.bootstrap.evaluation_suite.protected_paths[0].absolute_path)
    original_bytes = protected.read_bytes()

    def mutating_materialize(**kwargs):
        protected.write_bytes(protected.read_bytes() + b" forged")
        return original_materialize(**kwargs)

    monkeypatch.setattr(composition.materializer, "materialize", mutating_materialize)
    try:
        with pytest.raises(ValueError, match="protected authority"):
            conformance._materialization_check(composition, state)
    finally:
        protected.write_bytes(original_bytes)


def test_host_rejects_canned_a_b_a_runner_fingerprint_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    composition = _composition(tmp_path)
    original_run = composition.runner.run
    calls = 0

    def hostile_run(**kwargs):
        nonlocal calls
        calls += 1
        record, events = original_run(**kwargs)
        if calls == 3:
            events = [
                event.model_copy(update={"payload": {**event.payload, "forged": True}})
                for event in events
            ]
        return record, events

    monkeypatch.setattr(composition.runner, "run", hostile_run)
    with pytest.raises(ValueError, match="fingerprint"):
        conformance._isolation_check(composition, {})


def test_host_rejects_symmetric_evaluator_with_forged_ledger_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    composition = _composition(tmp_path)
    state: dict[str, object] = {}
    assert conformance._builder_check(composition, state).status == "pass"
    original_evaluate = composition.evaluator.evaluate

    def forged_evaluate(**kwargs):
        outcome = original_evaluate(**kwargs)
        result = outcome.baseline_results[0]
        record = composition.context.ledger.get_run(result.run_id)
        forged = record.model_copy(update={"generation_id": "forged-generation"})
        with sqlite3.connect(composition.context.ledger.path) as connection:
            connection.execute(
                "UPDATE runs SET record_json=? WHERE run_id=?",
                (forged.model_dump_json(), forged.run_id),
            )
        return outcome

    monkeypatch.setattr(composition.evaluator, "evaluate", forged_evaluate)
    with pytest.raises(ValueError, match="differs from ScenarioResult"):
        conformance._evaluation_check(composition, state)


def test_blocked_roles_are_not_invoked_after_builder_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from evogen.demo.microworld.builder import ReferenceMicroworldBuilder
    from evogen.demo.microworld.cycle import MicroworldGenerationMaterializer
    from evogen.demo.microworld.evaluator import MicroworldEvaluator

    counts = {"builder": 0, "evaluator": 0, "materializer": 0}
    original_evaluate = MicroworldEvaluator.evaluate
    original_materialize = MicroworldGenerationMaterializer.materialize

    def fail_build(self, **kwargs):
        counts["builder"] += 1
        raise RuntimeError("builder hostile failure")

    def count_evaluate(self, **kwargs):
        counts["evaluator"] += 1
        return original_evaluate(self, **kwargs)

    def count_materialize(self, **kwargs):
        counts["materializer"] += 1
        return original_materialize(self, **kwargs)

    monkeypatch.setattr(ReferenceMicroworldBuilder, "build", fail_build)
    monkeypatch.setattr(MicroworldEvaluator, "evaluate", count_evaluate)
    monkeypatch.setattr(MicroworldGenerationMaterializer, "materialize", count_materialize)
    report = run_subject_conformance("microworld", workspace=tmp_path / "counter")
    assert report.status == "fail"
    assert counts == {"builder": 1, "evaluator": 0, "materializer": 0}
