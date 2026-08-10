from __future__ import annotations

from pathlib import Path

from evogen.core.models import CycleResult


def render_cycle_markdown(result: CycleResult) -> str:
    baseline = result.experiment.baseline_metrics
    candidate = result.experiment.candidate_metrics
    findings = (
        "\n".join(
            f"- **{finding.severity.value} / {finding.code}:** {finding.message}"
            for finding in result.review.findings
        )
        or "- No blocking review findings."
    )
    rules = "\n".join(f"- ✓ `{rule}`" for rule in result.decision.passed_rules)
    failed = "\n".join(f"- ✗ `{rule}`" for rule in result.decision.failed_rules)
    retained = (
        result.retained_generation.generation_id
        if result.retained_generation is not None
        else "not retained"
    )
    candidate_operations = "\n".join(
        f"- `{operation.name}` — {operation.description}"
        for operation in result.investigation.candidate_operations
    )
    evaluation_rows = "\n".join(
        [
            "| Revealing success | "
            f"{baseline.revealing_success_rate:.0%} | "
            f"{candidate.revealing_success_rate:.0%} |",
            "| Variant success | "
            f"{baseline.variant_success_rate:.0%} | "
            f"{candidate.variant_success_rate:.0%} |",
            "| Regression success | "
            f"{baseline.regression_success_rate:.0%} | "
            f"{candidate.regression_success_rate:.0%} |",
            "| Long-horizon success | "
            f"{baseline.long_horizon_success_rate:.0%} | "
            f"{candidate.long_horizon_success_rate:.0%} |",
            f"| Blocked runs | {baseline.blocked_run_count} | {candidate.blocked_run_count} |",
            "| Invalid actions | "
            f"{baseline.invalid_action_count} | {candidate.invalid_action_count} |",
            f"| Interventions | {baseline.intervention_count} | "
            f"{candidate.intervention_count} |",
            f"| Average steps | {baseline.average_steps:.2f} | "
            f"{candidate.average_steps:.2f} |",
        ]
    )
    return f"""# EvoGen evolution-cycle report

## Outcome

- Verdict: **{result.decision.verdict.value}**
- Parent generation: `{result.baseline_generation.generation_id}`
- Candidate: `{result.candidate.candidate_id}`
- Resulting generation: `{retained}`
- Capability: `{result.specification.capability_name}`

{result.decision.rationale}

## Evidence-backed issue

**{result.issue.title}**

{result.issue.symptom_summary}

- Failure layer: `{result.issue.classification.primary.value}`
- Confidence: `{result.issue.classification.confidence:.2f}`
- Required effect: `{result.issue.required_effect}`
- Proposed resolution: `{result.issue.proposed_resolution.value}`
- Supporting events: {len(result.issue.supporting_evidence)}

Prediction:

> {result.issue.prediction}

## Investigation

{result.investigation.conclusion}

Candidate environment operations:

{candidate_operations}

## Candidate review

- Passed: `{str(result.review.passed).lower()}`
- Changed files: {', '.join(f'`{path}`' for path in result.candidate.changed_files)}

{findings}

## Evaluation

| Metric | Baseline | Candidate |
| --- | ---: | ---: |
{evaluation_rows}

Prediction matched: `{str(result.experiment.prediction_matched).lower()}`

## Retention gate

Passed:

{rules or '- None'}

Failed:

{failed or '- None'}

## Reproduce

From the repository root:

```bash
uv run --frozen --extra dev python scripts/verify.py
```

The full JSON result is stored beside this report, while raw JSONL trajectories,
content-addressed artifacts, candidate source, and SQLite lineage remain under the
workspace directory.
"""


def write_cycle_report(result: CycleResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_cycle_markdown(result), encoding="utf-8")
