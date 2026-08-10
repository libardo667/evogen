from __future__ import annotations

from pathlib import Path

from evogen.adapters.protocols import (
    CandidateBuilder,
    CandidateReviewer,
    EnvironmentInvestigator,
    ExperimentEvaluator,
    GenerationMaterializer,
    SubjectRunner,
)
from evogen.core.enums import CandidateStatus, GateVerdict, IssueStatus
from evogen.core.models import (
    CycleResult,
    EvolutionPlan,
    GenerationManifest,
)
from evogen.evolution.diagnosis import EvidenceFirstDiagnostician
from evogen.evolution.selection import RetentionPolicy
from evogen.evolution.specification import CapabilityArchitect
from evogen.reporting import write_cycle_report
from evogen.storage.artifacts import ArtifactStore
from evogen.storage.ledger import Ledger
from evogen.trace.distill import TraceDistiller


class EvolutionOrchestrator:
    """Generic, artifact-mediated outer loop.

    Domain adapters own scenario execution, environment research, implementation,
    evaluation, and retained-generation materialization. The orchestrator owns the
    evidence order, status transitions, immutable artifacts, and lineage decision.
    """

    def __init__(
        self,
        *,
        workspace: Path,
        artifacts: ArtifactStore,
        ledger: Ledger,
        runner: SubjectRunner,
        investigator: EnvironmentInvestigator,
        builder: CandidateBuilder,
        reviewer: CandidateReviewer,
        evaluator: ExperimentEvaluator,
        materializer: GenerationMaterializer,
        diagnostician: EvidenceFirstDiagnostician | None = None,
        architect: CapabilityArchitect | None = None,
        retention_policy: RetentionPolicy | None = None,
    ) -> None:
        self.workspace = workspace.resolve()
        self.artifacts = artifacts
        self.ledger = ledger
        self.runner = runner
        self.investigator = investigator
        self.builder = builder
        self.reviewer = reviewer
        self.evaluator = evaluator
        self.materializer = materializer
        self.diagnostician = diagnostician or EvidenceFirstDiagnostician()
        self.architect = architect or CapabilityArchitect()
        self.retention_policy = retention_policy or RetentionPolicy()

    def run(
        self,
        *,
        baseline: GenerationManifest,
        plan: EvolutionPlan,
    ) -> CycleResult:
        self.ledger.add_generation(baseline)

        diagnostic_runs = []
        diagnostic_events = []
        for scenario_id in plan.diagnostic_scenarios:
            record, events = self.runner.run(
                generation=baseline,
                scenario_id=scenario_id,
                trace_directory=self.workspace / "traces" / "diagnostic",
            )
            self.ledger.add_run(record, events)
            diagnostic_runs.append(record)
            diagnostic_events.extend(events)

        capabilities = self.runner.capability_manifest(baseline)
        distilled = TraceDistiller().distill(
            generation_id=baseline.generation_id,
            events=diagnostic_events,
            capabilities=capabilities,
        )
        issue = self.diagnostician.diagnose(distilled)
        self.ledger.add_issue(issue)
        issue_digest = self.artifacts.put_json(issue.model_dump(mode="json"))

        investigation = self.investigator.investigate(issue)
        investigation_digest = self.artifacts.put_json(
            investigation.model_dump(mode="json")
        )
        specification = self.architect.specify(
            issue=issue,
            investigation=investigation,
            revealing_cases=plan.revealing_cases,
            structural_variants=plan.structural_variants,
            regression_suites=plan.regression_suites,
            long_horizon_suites=plan.long_horizon_suites,
        )
        specification_digest = self.artifacts.put_json(
            specification.model_dump(mode="json")
        )
        issue = issue.model_copy(update={"status": IssueStatus.SPECIFIED})
        self.ledger.add_issue(issue)

        candidate = self.builder.build(
            parent=baseline,
            issue=issue,
            specification=specification,
            candidate_root=self.workspace / "candidates",
        )
        candidate = candidate.model_copy(
            update={
                "artifact_digests": {
                    **candidate.artifact_digests,
                    "issue_object": issue_digest,
                    "investigation_object": investigation_digest,
                    "specification_object": specification_digest,
                }
            }
        )
        self.ledger.add_candidate(candidate)

        review = self.reviewer.review(
            candidate,
            forbidden_literals=plan.forbidden_literals,
        )
        review_digest = self.artifacts.put_json(review.model_dump(mode="json"))
        candidate = candidate.model_copy(update={"status": CandidateStatus.REVIEWED})
        self.ledger.add_candidate(candidate)

        experiment = self.evaluator.evaluate(
            baseline=baseline,
            candidate=candidate,
            trace_directory=self.workspace / "traces" / "evaluation",
            review_passed=review.passed,
        )
        self.ledger.add_experiment(experiment)
        experiment_digest = self.artifacts.put_json(experiment.model_dump(mode="json"))
        candidate = candidate.model_copy(
            update={
                "status": CandidateStatus.EVALUATED,
                "artifact_digests": {
                    **candidate.artifact_digests,
                    "review_object": review_digest,
                    "experiment_object": experiment_digest,
                },
            }
        )
        self.ledger.add_candidate(candidate)

        decision = self.retention_policy.decide(experiment)
        retained_generation = None
        if decision.verdict == GateVerdict.RETAIN:
            retained_generation = self.materializer.materialize(
                baseline=baseline,
                candidate=candidate,
                experiment=experiment,
                decision=decision,
            )
            decision = decision.model_copy(
                update={"retained_generation_id": retained_generation.generation_id}
            )
            candidate = candidate.model_copy(update={"status": CandidateStatus.RETAINED})
            issue = issue.model_copy(update={"status": IssueStatus.RESOLVED})
            self.ledger.add_generation(retained_generation)
            self.ledger.add_candidate(candidate)
            self.ledger.add_issue(issue)
            self.ledger.add_lineage(
                parent_generation_id=baseline.generation_id,
                child_generation_id=retained_generation.generation_id,
                candidate_id=candidate.candidate_id,
                decision=decision,
            )
        else:
            candidate = candidate.model_copy(update={"status": CandidateStatus.REJECTED})
            self.ledger.add_candidate(candidate)
        self.ledger.add_decision(decision)

        result = CycleResult(
            workspace=str(self.workspace),
            baseline_generation=baseline,
            diagnostic_runs=diagnostic_runs,
            issue=issue,
            investigation=investigation,
            specification=specification,
            candidate=candidate,
            review=review,
            experiment=experiment,
            decision=decision,
            retained_generation=retained_generation,
        )
        (self.workspace / "cycle-result.json").write_text(
            result.model_dump_json(indent=2), encoding="utf-8"
        )
        write_cycle_report(result, self.workspace / "report.md")
        return result
