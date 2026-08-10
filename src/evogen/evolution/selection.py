from __future__ import annotations

from evogen.core.enums import GateVerdict
from evogen.core.ids import new_id
from evogen.core.models import ExperimentResult, GateDecision


class RetentionPolicy:
    """Deterministic gate: evidence, variants, regressions, and horizon all matter."""

    def decide(self, result: ExperimentResult) -> GateDecision:
        candidate = result.candidate_metrics
        baseline = result.baseline_metrics
        rules = {
            "static_review_passed": result.review_passed,
            "prediction_matched": result.prediction_matched,
            "revealing_cases_all_pass": candidate.revealing_success_rate == 1.0,
            "structural_variants_all_pass": candidate.variant_success_rate == 1.0,
            "regressions_all_pass": candidate.regression_success_rate == 1.0,
            "long_horizon_all_pass": candidate.long_horizon_success_rate == 1.0,
            "no_new_high_severity_issues": candidate.new_high_severity_issues == 0,
            "no_intervention_regression": (
                candidate.intervention_count <= baseline.intervention_count
            ),
            "no_invalid_action_regression": (
                candidate.invalid_action_count <= baseline.invalid_action_count
            ),
            "target_competence_improved": (
                candidate.revealing_success_rate > baseline.revealing_success_rate
                or candidate.variant_success_rate > baseline.variant_success_rate
            ),
        }
        passed = [name for name, value in rules.items() if value]
        failed = [name for name, value in rules.items() if not value]

        hard_failures = {
            "static_review_passed",
            "regressions_all_pass",
            "no_new_high_severity_issues",
        }
        if not failed:
            verdict = GateVerdict.RETAIN
            rationale = (
                "Candidate closed the revealing issue, generalized across variants, preserved "
                "regressions, survived the long-horizon suite, and matched its prediction."
            )
        elif hard_failures.intersection(failed):
            verdict = GateVerdict.REJECT
            rationale = (
                "Candidate failed a non-negotiable safety, review, or regression rule and is not "
                "eligible to become an ancestor."
            )
        else:
            verdict = GateVerdict.REVISE
            rationale = (
                "Candidate is directionally useful but lacks enough generalized evidence for "
                "retention. Revise the capability or its proof plan."
            )

        return GateDecision(
            decision_id=new_id("decision"),
            candidate_id=result.candidate_id,
            verdict=verdict,
            passed_rules=passed,
            failed_rules=failed,
            rationale=rationale,
        )
