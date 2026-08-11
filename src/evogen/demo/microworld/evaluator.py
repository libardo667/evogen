from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from evogen.core.ids import new_id, stable_digest
from evogen.core.models import (
    CandidateManifest,
    EvaluationCase,
    EvaluationOutcome,
    EvaluationSuiteManifest,
    GenerationManifest,
    MetricVector,
    ScenarioResult,
    SubjectMetricVector,
)
from evogen.storage.ledger import Ledger

from .subject import MicroworldRunner


class MicroworldEvaluator:
    def __init__(self, *, runner: MicroworldRunner, ledger: Ledger | None = None) -> None:
        self.runner = runner
        self.ledger = ledger

    def evaluate(
        self,
        *,
        baseline: GenerationManifest,
        candidate: CandidateManifest,
        evaluation_suite: EvaluationSuiteManifest,
        trace_directory: Path,
        review_passed: bool,
    ) -> EvaluationOutcome:
        started = datetime.now(UTC)
        evaluation_started = perf_counter()
        candidate_generation = GenerationManifest(
            generation_id=candidate.candidate_id,
            parent_generation_id=baseline.generation_id,
            subject=baseline.subject,
            source_ref=f"candidate:{candidate.source_digest}",
            capability_manifest_digest="transient",
            artifact_digests=candidate.artifact_digests,
            models=baseline.models,
            prompts=baseline.prompts,
            config={
                **baseline.config,
                "plugin_root": str(Path(candidate.workspace_path) / "plugins"),
            },
            metadata={"transient_candidate": True},
        )
        candidate_manifest = self.runner.capability_manifest(candidate_generation)
        candidate_generation = candidate_generation.model_copy(
            update={
                "capability_manifest_digest": stable_digest(
                    candidate_manifest.model_dump(mode="json")
                )
            }
        )

        baseline_results = self._run_suite(
            generation=baseline,
            evaluation_suite=evaluation_suite,
            evaluation_started=evaluation_started,
            trace_directory=trace_directory / "baseline",
        )
        candidate_results = self._run_suite(
            generation=candidate_generation,
            evaluation_suite=evaluation_suite,
            evaluation_started=evaluation_started,
            trace_directory=trace_directory / "candidate",
        )
        baseline_metrics = _metrics(baseline_results)
        candidate_metrics = _metrics(candidate_results)
        prediction_matched = (
            candidate_metrics.revealing_success_rate == 1.0
            and candidate_metrics.revealing_success_rate
            > baseline_metrics.revealing_success_rate
            and candidate_metrics.variant_success_rate
            > baseline_metrics.variant_success_rate
        )
        return EvaluationOutcome(
            experiment_id=new_id("experiment"),
            candidate_id=candidate.candidate_id,
            baseline_generation=baseline.generation_id,
            started_at=started,
            finished_at=datetime.now(UTC),
            baseline_results=baseline_results,
            candidate_results=candidate_results,
            baseline_metrics=baseline_metrics,
            candidate_metrics=candidate_metrics,
            prediction_matched=prediction_matched,
            review_passed=review_passed,
            baseline_subject_metrics=[_subject_metrics(baseline_results, evaluation_suite)],
            candidate_subject_metrics=[_subject_metrics(candidate_results, evaluation_suite)],
            notes=[
                "Every scenario was rerun from a fresh deterministic world.",
                "Baseline and candidate used the same executor policy and evaluator.",
                "The candidate changed only the isolated capability plugin directory.",
            ],
        )

    def _run_suite(
        self,
        *,
        generation: GenerationManifest,
        evaluation_suite: EvaluationSuiteManifest,
        evaluation_started: float,
        trace_directory: Path,
    ) -> list[ScenarioResult]:
        results: list[ScenarioResult] = []
        for case in _suite_cases(evaluation_suite):
            for seed in case.seeds:
                for repeat_index in range(case.repeat_count):
                    run_started = perf_counter()
                    record, events = self.runner.run(
                        generation=generation,
                        scenario_id=case.scenario_id,
                        seed=seed,
                        trace_directory=trace_directory,
                    )
                    elapsed = perf_counter() - run_started
                    if elapsed > case.per_run_wall_clock_ceiling_seconds:
                        raise TimeoutError(
                            f"Evaluation case {case.scenario_id} exceeded its wall-clock ceiling"
                        )
                    if self.ledger is not None:
                        self.ledger.add_run(record, events)
                    results.append(
                        ScenarioResult(
                            scenario_id=case.scenario_id,
                            category=case.category,
                            seed=seed,
                            repeat_index=repeat_index,
                            elapsed_seconds=elapsed,
                            success=record.success,
                            steps=record.steps,
                            interventions=record.interventions,
                            invalid_actions=record.invalid_actions,
                            blocked=record.termination == "goal_blocked",
                            termination=record.termination,
                            run_id=record.run_id,
                            trace_digest=record.trace_digest,
                        )
                    )
                    if (
                        perf_counter() - evaluation_started
                        > evaluation_suite.total_wall_clock_ceiling_seconds
                    ):
                        raise TimeoutError("Evaluation suite exceeded its total wall-clock ceiling")
        return results


def _suite_cases(suite: EvaluationSuiteManifest) -> Iterator[EvaluationCase]:
    yield from suite.revealing_cases
    yield from suite.structural_variants
    yield from suite.regression_suites
    yield from suite.long_horizon_suites


def _subject_metrics(
    results: list[ScenarioResult], suite: EvaluationSuiteManifest
) -> SubjectMetricVector:
    return SubjectMetricVector(
        namespace=suite.subject_metric_namespace,
        metrics={
            "evaluated_runs": len(results),
            "successful_runs": sum(result.success for result in results),
        },
    )


def _metrics(results: list[ScenarioResult]) -> MetricVector:
    def rate(category: str) -> float:
        selected = [result for result in results if result.category == category]
        if not selected:
            return 1.0
        return sum(result.success for result in selected) / len(selected)

    return MetricVector(
        revealing_success_rate=rate("revealing"),
        variant_success_rate=rate("variant"),
        regression_success_rate=rate("regression"),
        long_horizon_success_rate=rate("long_horizon"),
        intervention_count=sum(result.interventions for result in results),
        invalid_action_count=sum(result.invalid_actions for result in results),
        blocked_run_count=sum(result.blocked for result in results),
        average_steps=(
            sum(result.steps for result in results) / len(results) if results else 0.0
        ),
        new_high_severity_issues=0,
    )
