from __future__ import annotations

from datetime import UTC, datetime

from evogen.core.enums import GateVerdict
from evogen.core.models import (
    ArtifactRef,
    EvaluationAuthoritySnapshot,
    ExperimentResult,
    MetricVector,
    SubjectMetricVector,
)
from evogen.evolution.selection import RetentionPolicy


def metrics(**updates):
    values = {
        "revealing_success_rate": 1.0,
        "variant_success_rate": 1.0,
        "regression_success_rate": 1.0,
        "long_horizon_success_rate": 1.0,
        "intervention_count": 0,
        "invalid_action_count": 0,
        "blocked_run_count": 0,
        "average_steps": 1.0,
        "new_high_severity_issues": 0,
    }
    values.update(updates)
    return MetricVector(**values)


def experiment(candidate_metrics: MetricVector) -> ExperimentResult:
    now = datetime.now(UTC)
    return ExperimentResult(
        experiment_id="experiment-1",
        candidate_id="candidate-1",
        baseline_generation="generation-1",
        started_at=now,
        finished_at=now,
        baseline_results=[],
        candidate_results=[],
        baseline_metrics=metrics(
            revealing_success_rate=0.0,
            variant_success_rate=0.0,
            long_horizon_success_rate=0.0,
            blocked_run_count=3,
        ),
        candidate_metrics=candidate_metrics,
        prediction_matched=True,
        review_passed=True,
        baseline_subject_metrics=[SubjectMetricVector(namespace="test", metrics={})],
        candidate_subject_metrics=[SubjectMetricVector(namespace="test", metrics={})],
        evaluation_suite_ref=ArtifactRef(digest="a" * 64, model="EvaluationSuiteManifest"),
        pre_authority_snapshot=EvaluationAuthoritySnapshot(
            suite_ref=ArtifactRef(digest="a" * 64, model="EvaluationSuiteManifest"),
            suite_id="suite", evaluator_version="v1", protected_path_digests={}
        ),
        post_authority_snapshot=EvaluationAuthoritySnapshot(
            suite_ref=ArtifactRef(digest="a" * 64, model="EvaluationSuiteManifest"),
            suite_id="suite", evaluator_version="v1", protected_path_digests={}
        ),
    )


def test_regression_failure_rejects_candidate():
    decision = RetentionPolicy().decide(
        experiment(metrics(regression_success_rate=0.5))
    )
    assert decision.verdict == GateVerdict.REJECT
    assert "regressions_all_pass" in decision.failed_rules


def test_missing_long_horizon_evidence_requests_revision():
    decision = RetentionPolicy().decide(
        experiment(metrics(long_horizon_success_rate=0.0))
    )
    assert decision.verdict == GateVerdict.REVISE
    assert "long_horizon_all_pass" in decision.failed_rules
