from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from evogen.core.enums import CandidateStatus, GateVerdict, StageName
from evogen.core.ids import stable_digest
from evogen.core.models import (
    ArtifactRef,
    CandidateManifest,
    ExperimentResult,
    GateDecision,
    MetricVector,
    ReviewReport,
)
from evogen.evolution.selection import RetentionPolicy
from evogen.evolution.stages import EvolutionStageOrchestrator, StageIntegrityError


class _Authority:
    def __init__(
        self,
        authority_id: str | None = None,
        *,
        invoker_id: str | None = None,
        backend: object | None = None,
    ) -> None:
        self.authority_id = authority_id
        if invoker_id is not None or backend is not None:
            self.invoker = SimpleNamespace(authority_id=invoker_id, backend=backend)


def _authority_boundary(
    builder: object, reviewer: object, evaluator: object,
) -> EvolutionStageOrchestrator:
    stage = object.__new__(EvolutionStageOrchestrator)
    stage.builder = builder
    stage.reviewer = reviewer
    stage.evaluator = evaluator
    return stage


def test_builder_reviewer_evaluator_must_be_distinct_objects() -> None:
    shared = _Authority("builder")
    stage = _authority_boundary(shared, shared, _Authority("evaluator"))

    with pytest.raises(StageIntegrityError, match="distinct authorities"):
        stage._validate_authority_separation()


@pytest.mark.parametrize(
    ("builder", "reviewer", "evaluator"),
    [
        (_Authority("shared"), _Authority("shared"), _Authority("evaluator")),
        (
            _Authority(invoker_id="shared"),
            _Authority("shared"),
            _Authority("evaluator"),
        ),
        (
            _Authority("builder"),
            _Authority(invoker_id="shared"),
            _Authority("shared"),
        ),
    ],
)
def test_exposed_duplicate_authority_ids_are_rejected(
    builder: object, reviewer: object, evaluator: object,
) -> None:
    stage = _authority_boundary(builder, reviewer, evaluator)

    with pytest.raises(StageIntegrityError, match="shares authority_id"):
        stage._validate_authority_separation()


def test_distinct_role_ids_cannot_hide_a_shared_backend() -> None:
    shared_backend = object()
    stage = _authority_boundary(
        _Authority(invoker_id="builder", backend=shared_backend),
        _Authority(invoker_id="reviewer", backend=shared_backend),
        _Authority("evaluator"),
    )

    with pytest.raises(StageIntegrityError, match="shares role backend"):
        stage._validate_authority_separation()


def _candidate() -> CandidateManifest:
    return CandidateManifest(
        candidate_id="candidate-1",
        parent_generation="gen-1",
        issue_id="issue-1",
        spec_id="spec-1",
        workspace_path="/tmp/candidate-1",
        source_digest=stable_digest({"plugin.py": "a" * 64}),
        artifact_digests={},
        changed_files=["plugin.py"],
        file_digests={"plugin.py": "a" * 64},
        claimed_capabilities=[],
        status=CandidateStatus.EVALUATED,
    )


def _experiment(*, review_passed: bool, improved: bool) -> ExperimentResult:
    baseline = MetricVector(
        revealing_success_rate=1.0 if improved else 0.0,
        variant_success_rate=1.0 if improved else 0.0,
        regression_success_rate=1.0,
        long_horizon_success_rate=1.0,
        intervention_count=0,
        invalid_action_count=0,
        blocked_run_count=0,
        average_steps=1.0,
    )
    candidate = baseline.model_copy(
        update={
            "revealing_success_rate": 1.0,
            "variant_success_rate": 1.0,
        }
    )
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    return ExperimentResult(
        experiment_id="experiment-1",
        candidate_id="candidate-1",
        baseline_generation="gen-1",
        started_at=timestamp,
        finished_at=timestamp,
        baseline_results=[],
        candidate_results=[],
        baseline_metrics=baseline,
        candidate_metrics=candidate,
        prediction_matched=True,
        review_passed=review_passed,
    )


def _select_stage(
    *, experiment: ExperimentResult, recommendation: GateDecision,
) -> EvolutionStageOrchestrator:
    candidate = _candidate()
    review = ReviewReport(
        review_id="review-1",
        candidate_id=candidate.candidate_id,
        passed=experiment.review_passed,
        checks={},
    )
    stage = object.__new__(EvolutionStageOrchestrator)
    stage.release_recommender = SimpleNamespace(
        recommend=lambda _result: recommendation,
    )
    stage.retention_policy = RetentionPolicy()
    stage.builder = _Authority("builder")
    stage.reviewer = _Authority("reviewer")
    stage.evaluator = _Authority("evaluator")
    stage._read_input = lambda _inputs, key, _model: {
        "build": candidate,
        "review": review,
        "evaluate": experiment,
    }[key]
    stage._validate_candidate = lambda _candidate: None
    stage._verify_candidate_files = lambda _candidate: None
    stage._inputs_for_test = {
        key: ArtifactRef(digest=digest, model="Test")
        for key, digest in zip(
            ("build", "review", "evaluate"),
            ("a" * 64, "b" * 64, "c" * 64),
            strict=True,
        )
    }
    return stage


def _deterministic_decision(experiment: ExperimentResult) -> GateDecision:
    return RetentionPolicy().decide(experiment)


def _assert_recommendation_rejected(
    experiment: ExperimentResult,
    mutate: Callable[[GateDecision], GateDecision],
    *,
    match: str,
) -> None:
    deterministic = _deterministic_decision(experiment)
    recommendation = mutate(deterministic)
    stage = _select_stage(experiment=experiment, recommendation=recommendation)

    with pytest.raises(StageIntegrityError, match=match):
        stage._dispatch(StageName.SELECT, stage._inputs_for_test)


def test_release_recommendation_cannot_be_more_permissive_than_reject() -> None:
    experiment = _experiment(review_passed=False, improved=False)
    deterministic = _deterministic_decision(experiment)
    assert deterministic.verdict == GateVerdict.REJECT

    _assert_recommendation_rejected(
        experiment,
        lambda decision: decision.model_copy(update={"verdict": GateVerdict.REVISE}),
        match="cannot avoid deterministic rejection",
    )


def test_release_recommendation_cannot_be_more_permissive_than_revise() -> None:
    experiment = _experiment(review_passed=True, improved=True)
    deterministic = _deterministic_decision(experiment)
    assert deterministic.verdict == GateVerdict.REVISE

    _assert_recommendation_rejected(
        experiment,
        lambda decision: decision.model_copy(update={"verdict": GateVerdict.RETAIN}),
        match="cannot be more permissive than revise",
    )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda decision: decision.model_copy(
            update={"passed_rules": list(reversed(decision.passed_rules))}
        ),
        lambda decision: decision.model_copy(
            update={"passed_rules": [*decision.passed_rules, decision.passed_rules[0]]}
        ),
        lambda decision: decision.model_copy(
            update={"failed_rules": [*decision.failed_rules, "forged_rule"]}
        ),
        lambda decision: decision.model_copy(
            update={"failed_rules": ["forged_rule", *decision.failed_rules]}
        ),
    ],
)
def test_release_recommendation_cannot_rewrite_rule_evidence(
    mutate: Callable[[GateDecision], GateDecision],
) -> None:
    _assert_recommendation_rejected(
        _experiment(review_passed=True, improved=True),
        mutate,
        match="rule evidence differs",
    )


def test_release_recommendation_cannot_change_candidate_id() -> None:
    _assert_recommendation_rejected(
        _experiment(review_passed=False, improved=False),
        lambda decision: decision.model_copy(update={"candidate_id": "candidate-forged"}),
        match="candidate does not match",
    )


def test_release_recommendation_cannot_supply_retained_generation_id() -> None:
    _assert_recommendation_rejected(
        _experiment(review_passed=False, improved=False),
        lambda decision: decision.model_copy(
            update={
                "verdict": GateVerdict.RETAIN,
                "retained_generation_id": "generation-forged",
            }
        ),
        match="may not materialize or name a generation",
    )
