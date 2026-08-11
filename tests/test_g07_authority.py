from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from evogen.core.enums import GateVerdict
from evogen.core.ids import sha256_bytes
from evogen.core.models import (
    ArtifactRef,
    CandidateManifest,
    EvaluationAuthoritySnapshot,
    EvaluationCase,
    EvaluationOutcome,
    EvaluationSuiteManifest,
    ExperimentResult,
    MetricVector,
    ProtectedPathHash,
    ReviewReport,
    SubjectMetricVector,
)
from evogen.demo.microworld.cycle import MicroworldEvolutionCycle
from evogen.evolution.selection import RetentionPolicy
from evogen.evolution.stages import ManifestIntegrityError, StageIntegrityError


def _case(scenario_id: str, category: str) -> EvaluationCase:
    return EvaluationCase(
        scenario_id=scenario_id,
        category=category,
        seeds=[7, 11],
        repeat_count=2,
        per_run_wall_clock_ceiling_seconds=0.5,
    )


def _suite() -> EvaluationSuiteManifest:
    source = ArtifactRef(digest="a" * 64, model="SourceArtifact")
    return EvaluationSuiteManifest(
        suite_id="suite-test-v1",
        revealing_cases=[_case("r", "revealing")],
        structural_variants=[_case("v", "variant")],
        regression_suites=[_case("g", "regression")],
        long_horizon_suites=[_case("h", "long_horizon")],
        total_wall_clock_ceiling_seconds=10.0,
        evaluator_version="test-evaluator-v1",
        evaluator=source,
        evaluator_protected_path="fixture",
        environment_artifacts={"fixture": source},
        protected_paths=[
            ProtectedPathHash(
                logical_name="fixture",
                absolute_path="/tmp/g07-fixture.py",
                    sha256="a" * 64,
            )
        ],
        subject_metric_namespace="test.subject",
        candidate_tests_authoritative=False,
    )


def test_suite_expansion_contract_is_strict_and_ordered() -> None:
    suite = _suite()
    assert suite.subject_metric_namespace == "test.subject"
    assert suite.revealing_cases[0].seeds == [7, 11]
    assert suite.revealing_cases[0].repeat_count == 2
    assert suite.candidate_tests_authoritative is False

    with pytest.raises(ValueError, match="category"):
        EvaluationSuiteManifest(
            **{
                **suite.model_dump(),
                "structural_variants": [
                    _case("wrong", "revealing").model_dump()
                ],
            }
        )


def test_suite_rejects_duplicate_case_ids_and_invalid_limits() -> None:
    suite = _suite()
    with pytest.raises(ValueError, match="scenario IDs"):
        EvaluationSuiteManifest(
            **{
                **suite.model_dump(),
                "structural_variants": [_case("r", "variant").model_dump()],
            }
        )
    with pytest.raises(ValueError):
        EvaluationCase(
            scenario_id="bad",
            category="revealing",
            seeds=[],
            repeat_count=0,
            per_run_wall_clock_ceiling_seconds=0,
        )
    with pytest.raises(ValueError):
        EvaluationSuiteManifest(
            **{
                **suite.model_dump(),
                "candidate_tests_authoritative": True,
            }
        )
    with pytest.raises(ValueError, match="evaluator_protected_path"):
        EvaluationSuiteManifest(
            **{
                **suite.model_dump(),
                "evaluator_protected_path": "missing",
            }
        )


def test_experiment_subject_metric_namespaces_must_be_symmetric() -> None:
    metric = MetricVector(
        revealing_success_rate=1,
        variant_success_rate=1,
        regression_success_rate=1,
        long_horizon_success_rate=1,
        intervention_count=0,
        invalid_action_count=0,
        blocked_run_count=0,
        average_steps=0,
    )
    now = datetime.now(UTC)
    with pytest.raises(ValueError, match="symmetric"):
        EvaluationOutcome(
            experiment_id="e",
            candidate_id="c",
            baseline_generation="g",
            started_at=now,
            finished_at=now,
            baseline_results=[],
            candidate_results=[],
            baseline_metrics=metric,
            candidate_metrics=metric,
            prediction_matched=True,
            review_passed=True,
            baseline_subject_metrics=[
                SubjectMetricVector(namespace="subject", metrics={"runs": 1})
            ],
            candidate_subject_metrics=[
                SubjectMetricVector(namespace="other", metrics={"runs": 1})
            ],
        )


def test_authority_snapshot_keeps_suite_identity_and_hash_map() -> None:
    suite = _suite()
    snapshot = EvaluationAuthoritySnapshot(
        suite_ref=ArtifactRef(
            digest="c" * 64,
            model="EvaluationSuiteManifest",
        ),
        suite_id=suite.suite_id,
        evaluator_version=suite.evaluator_version,
        protected_path_digests={"fixture": "a" * 64},
    )
    assert snapshot.protected_path_digests == {"fixture": "a" * 64}


def test_unchanged_evaluation_persists_canonical_authority_snapshots(
    tmp_path: Path,
) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "workspace", clean=True)
    stages = cycle.composition.orchestrator.stages
    result = stages.run(until="evaluate")
    assert isinstance(result, ExperimentResult)
    assert result.evaluation_suite_ref == stages.evaluation_suite_ref
    assert result.pre_authority_snapshot is not None
    assert result.post_authority_snapshot is not None
    expected = {
        item.logical_name: item.sha256
        for item in cycle.composition.bootstrap.evaluation_suite.protected_paths
    }
    for snapshot in (result.pre_authority_snapshot, result.post_authority_snapshot):
        assert snapshot.suite_ref == stages.evaluation_suite_ref
        assert snapshot.suite_id == stages.evaluation_suite.suite_id
        assert snapshot.evaluator_version == stages.evaluation_suite.evaluator_version
        assert snapshot.protected_path_digests == expected
    assert result.pre_authority_snapshot.protected_path_digests == (
        result.post_authority_snapshot.protected_path_digests
    )
    assert len(result.baseline_results) == len(result.candidate_results) == 7


@pytest.mark.parametrize("tamper", ["missing", "wrong_seed", "reordered"])
def test_noncanonical_result_coordinates_are_rejected(
    tmp_path: Path,
    tamper: str,
) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / tamper, clean=True)
    stages = cycle.composition.orchestrator.stages
    stages.run(until="review")

    class CoordinateTamperingEvaluator:
        def __init__(self, delegate: object) -> None:
            self.delegate = delegate

        def evaluate(self, **kwargs: object) -> ExperimentResult:
            result = self.delegate.evaluate(**kwargs)  # type: ignore[attr-defined]
            candidate_results = list(result.candidate_results)
            if tamper == "missing":
                candidate_results.pop()
            elif tamper == "wrong_seed":
                candidate_results[0] = candidate_results[0].model_copy(
                    update={"seed": 99}
                )
            else:
                candidate_results.reverse()
            return result.model_copy(update={"candidate_results": candidate_results})

    stages.evaluator = CoordinateTamperingEvaluator(  # type: ignore[assignment]
        stages.evaluator
    )
    with pytest.raises(StageIntegrityError, match="suite expansion"):
        stages.invoke("evaluate")
    assert not (cycle.workspace / "stages" / "evaluate.pointer.json").exists()
    with sqlite3.connect(cycle.workspace / "evogen.sqlite3") as connection:
        assert connection.execute("SELECT COUNT(*) FROM experiments").fetchone() == (0,)


@pytest.mark.parametrize(
    "tamper",
    [
        "inflated_metrics",
        "reused_run_id",
        "stale_timestamp",
        "inner_timestamps",
        "inflated_elapsed",
    ],
)
def test_run_evidence_and_metrics_are_root_validated(tmp_path: Path, tamper: str) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / tamper, clean=True)
    stages = cycle.composition.orchestrator.stages
    stages.run(until="review")

    class EvidenceTamperingEvaluator:
        def __init__(self, delegate: object) -> None:
            self.delegate = delegate

        def evaluate(self, **kwargs: object) -> EvaluationOutcome:
            result = self.delegate.evaluate(**kwargs)  # type: ignore[attr-defined]
            if tamper == "reused_run_id":
                candidate_results = list(result.candidate_results)
                candidate_results[0] = candidate_results[0].model_copy(
                    update={"run_id": result.baseline_results[0].run_id}
                )
                return result.model_copy(update={"candidate_results": candidate_results})
            if tamper == "stale_timestamp":
                return result.model_copy(
                    update={"started_at": datetime(2000, 1, 1, tzinfo=UTC)}
                )
            if tamper == "inner_timestamps":
                now = datetime.now(UTC)
                return result.model_copy(
                    update={"started_at": now, "finished_at": now}
                )
            if tamper == "inflated_elapsed":
                candidate_results = list(result.candidate_results)
                candidate_results[0] = candidate_results[0].model_copy(
                    update={"elapsed_seconds": 9999.0}
                )
                return result.model_copy(update={"candidate_results": candidate_results})
            inflated = result.candidate_metrics.model_copy(
                update={"average_steps": result.candidate_metrics.average_steps + 1.0}
            )
            return result.model_copy(update={"candidate_metrics": inflated})

    stages.evaluator = EvidenceTamperingEvaluator(stages.evaluator)  # type: ignore[assignment]
    with pytest.raises(
        StageIntegrityError, match="(run ID|metrics|timestamps|window|wall-clock)"
    ):
        stages.invoke("evaluate")
    assert not (cycle.workspace / "stages" / "evaluate.pointer.json").exists()
    with sqlite3.connect(cycle.workspace / "evogen.sqlite3") as connection:
        assert connection.execute("SELECT COUNT(*) FROM experiments").fetchone() == (0,)


def test_runtime_created_candidate_file_is_rejected(tmp_path: Path) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "workspace", clean=True)
    stages = cycle.composition.orchestrator.stages
    stages.run(until="review")

    class RuntimeFileEvaluator:
        def __init__(self, delegate: object) -> None:
            self.delegate = delegate

        def evaluate(self, **kwargs: object) -> EvaluationOutcome:
            result = self.delegate.evaluate(**kwargs)  # type: ignore[attr-defined]
            candidate = kwargs["candidate"]
            Path(candidate.workspace_path, "runtime-created.txt").write_text(
                "unlisted", encoding="utf-8"
            )
            return result

    stages.evaluator = RuntimeFileEvaluator(stages.evaluator)  # type: ignore[assignment]
    with pytest.raises(StageIntegrityError, match="workspace"):
        stages.invoke("evaluate")
    assert not (cycle.workspace / "stages" / "evaluate.pointer.json").exists()


def test_runtime_suite_cas_corruption_is_rejected_before_publication(tmp_path: Path) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "workspace", clean=True)
    stages = cycle.composition.orchestrator.stages
    stages.run(until="review")
    artifact_path = cycle.artifacts.path_for(stages.evaluation_suite.evaluator.digest)
    original = artifact_path.read_bytes()

    class CorruptingEvaluator:
        def __init__(self, delegate: object) -> None:
            self.delegate = delegate

        def evaluate(self, **kwargs: object) -> EvaluationOutcome:
            result = self.delegate.evaluate(**kwargs)  # type: ignore[attr-defined]
            artifact_path.write_bytes(b"corrupt during evaluation")
            return result

    stages.evaluator = CorruptingEvaluator(stages.evaluator)  # type: ignore[assignment]
    try:
        with pytest.raises(StageIntegrityError, match="authority"):
            stages.invoke("evaluate")
        assert not (cycle.workspace / "stages" / "evaluate.pointer.json").exists()
        with sqlite3.connect(cycle.workspace / "evogen.sqlite3") as connection:
            assert connection.execute("SELECT COUNT(*) FROM experiments").fetchone() == (0,)
    finally:
        artifact_path.write_bytes(original)


@pytest.mark.parametrize("logical_name", ["scenarios.py", "evaluator.py"])
def test_candidate_authority_edit_is_rejected_before_experiment_publication(
    tmp_path: Path, logical_name: str
) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "workspace", clean=True)
    stages = cycle.composition.orchestrator.stages
    protected = next(
        Path(item.absolute_path)
        for item in cycle.composition.bootstrap.evaluation_suite.protected_paths
        if item.logical_name == logical_name
    )
    original = protected.read_bytes()

    class MutatingCandidateBuilder:
        def __init__(self, delegate: object) -> None:
            self.delegate = delegate

        def build(self, **kwargs: object) -> CandidateManifest:
            candidate = self.delegate.build(**kwargs)  # type: ignore[attr-defined]
            plugin = Path(candidate.workspace_path) / candidate.changed_files[0]
            plugin.write_text(
                plugin.read_text(encoding="utf-8")
                + "\nfrom pathlib import Path as _AuthorityPath\n"
                + f"_authority = _AuthorityPath({str(protected)!r})\n"
                + "_authority.write_text("
                + "_authority.read_text(encoding='utf-8') + '\\n# candidate edit\\n', "
                + "encoding='utf-8')\n",
                encoding="utf-8",
            )
            digest = sha256_bytes(plugin.read_bytes())
            return candidate.model_copy(
                update={
                    "source_digest": digest,
                    "artifact_digests": {
                        **candidate.artifact_digests,
                        "plugin": digest,
                    },
                }
            )

    stages.builder = MutatingCandidateBuilder(stages.builder)  # type: ignore[assignment]
    try:
        with pytest.raises(StageIntegrityError, match="authority"):
            stages.run(until="evaluate")
        candidate = stages.completed_stage("build")
        assert isinstance(candidate, CandidateManifest)
        review = stages.completed_stage("review")
        assert isinstance(review, ReviewReport)
        assert review.passed is True
        candidate_runs = cycle.ledger.list_runs(candidate.candidate_id)
        assert len(candidate_runs) == 7
        assert all(run.success for run in candidate_runs)
        assert not (cycle.workspace / "stages" / "evaluate.pointer.json").exists()
        with sqlite3.connect(cycle.workspace / "evogen.sqlite3") as connection:
            assert connection.execute("SELECT COUNT(*) FROM experiments").fetchone() == (0,)
            assert connection.execute("SELECT COUNT(*) FROM decisions").fetchone() == (0,)
            assert connection.execute("SELECT COUNT(*) FROM lineage").fetchone() == (0,)
            assert connection.execute(
                "SELECT status FROM candidates WHERE candidate_id=?",
                (candidate.candidate_id,),
            ).fetchone() == ("reviewed",)
        assert not (cycle.workspace / "cycle-result.json").exists()
    finally:
        protected.write_bytes(original)


def test_completed_evaluation_refuses_protected_authority_drift(tmp_path: Path) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "workspace", clean=True)
    stages = cycle.composition.orchestrator.stages
    stages.run(until="evaluate")
    protected = next(
        Path(item.absolute_path)
        for item in cycle.composition.bootstrap.evaluation_suite.protected_paths
        if item.logical_name == "scenarios.py"
    )
    original = protected.read_bytes()
    protected.write_bytes(original + b"\n# stale held-out authority\n")
    try:
        with pytest.raises(StageIntegrityError, match="authority"):
            stages.completed_stage("evaluate")
    finally:
        protected.write_bytes(original)


def test_candidate_test_claims_cannot_override_generic_retention_metrics() -> None:
    baseline = MetricVector(
        revealing_success_rate=0,
        variant_success_rate=0,
        regression_success_rate=1,
        long_horizon_success_rate=0,
        intervention_count=0,
        invalid_action_count=0,
        blocked_run_count=1,
        average_steps=1,
    )
    candidate = baseline.model_copy(
        update={
            "revealing_success_rate": 1,
            "variant_success_rate": 1,
            "regression_success_rate": 0.5,
            "long_horizon_success_rate": 1,
        }
    )
    now = datetime.now(UTC)
    result = ExperimentResult(
        experiment_id="candidate-test-claim",
        candidate_id="candidate",
        baseline_generation="baseline",
        started_at=now,
        finished_at=now,
        baseline_results=[],
        candidate_results=[],
        baseline_metrics=baseline,
        candidate_metrics=candidate,
        prediction_matched=True,
        review_passed=True,
        evaluation_suite_ref=ArtifactRef(digest="a" * 64, model="EvaluationSuiteManifest"),
        pre_authority_snapshot=EvaluationAuthoritySnapshot(
            suite_ref=ArtifactRef(digest="a" * 64, model="EvaluationSuiteManifest"),
            suite_id="suite",
            evaluator_version="v1",
            protected_path_digests={},
        ),
        post_authority_snapshot=EvaluationAuthoritySnapshot(
            suite_ref=ArtifactRef(digest="a" * 64, model="EvaluationSuiteManifest"),
            suite_id="suite",
            evaluator_version="v1",
            protected_path_digests={},
        ),
        baseline_subject_metrics=[
            SubjectMetricVector(namespace="microworld", metrics={"tests_passed": False})
        ],
        candidate_subject_metrics=[
            SubjectMetricVector(namespace="microworld", metrics={"tests_passed": True})
        ],
        notes=["Candidate-authored tests report a perfect score."],
    )

    decision = RetentionPolicy().decide(result)
    assert decision.verdict == GateVerdict.REJECT
    assert "regressions_all_pass" in decision.failed_rules


def test_suite_artifact_corruption_is_rejected(tmp_path: Path) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "workspace", clean=True)
    stages = cycle.composition.orchestrator.stages
    stages.run(until="evaluate")
    digest = cycle.composition.bootstrap.evaluation_suite.evaluator.digest
    artifact_path = cycle.artifacts.path_for(digest)
    original = artifact_path.read_bytes()
    artifact_path.unlink()
    try:
        with pytest.raises(ManifestIntegrityError, match="artifact"):
            stages.completed_stage("evaluate")
    finally:
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_bytes(original)
