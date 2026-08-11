"""Persisted, independently invokable evolution stages.

The stage runner is deliberately generic.  Subject adapters provide the same
role objects as the original cycle; this module owns persistence, ordering,
identity, and the integrity boundary.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel

from evogen.adapters.protocols import (
    CandidateBuilder,
    CandidateReviewer,
    EnvironmentInvestigator,
    ExperimentEvaluator,
    GenerationMaterializer,
    SubjectRunner,
)
from evogen.core.enums import CandidateStatus, GateVerdict, IssueStatus, ResolutionKind, StageName
from evogen.core.ids import new_id, sha256_bytes, stable_digest
from evogen.core.models import (
    ArtifactRef,
    CandidateManifest,
    CapabilityIssue,
    CapabilityManifest,
    CapabilitySpec,
    CycleManifest,
    CycleResult,
    DistilledTrace,
    EvolutionPlan,
    ExperimentResult,
    GenerationManifest,
    IngestResult,
    InvestigationReport,
    ProbeRequiredResult,
    ReviewReport,
    RunRecord,
    StagePointer,
    StageReceipt,
    TrajectoryEvent,
)
from evogen.evolution.diagnosis import EvidenceFirstDiagnostician
from evogen.evolution.selection import RetentionPolicy
from evogen.evolution.specification import CapabilityArchitect
from evogen.reporting import write_cycle_report
from evogen.storage.artifacts import ArtifactStore
from evogen.storage.ledger import Ledger
from evogen.trace.distill import TraceDistiller


class StageIntegrityError(RuntimeError):
    """Base class for actionable manifest, receipt, and artifact failures."""


class ManifestIntegrityError(StageIntegrityError):
    pass


class StageOrderError(StageIntegrityError):
    pass


class StageConflictError(StageIntegrityError):
    pass


class StageArtifactError(StageIntegrityError):
    pass


class ProbeRequiredError(StageIntegrityError):
    """Typed fail-closed result when a permanent stage receives BUILD_PROBE."""

    def __init__(self, result: ProbeRequiredResult) -> None:
        self.result = result
        super().__init__(result.message)


_OUTPUT_MODELS: dict[StageName, type[BaseModel]] = {
    StageName.INGEST: IngestResult,
    StageName.DISTILL: DistilledTrace,
    StageName.DIAGNOSE: CapabilityIssue,
    StageName.INVESTIGATE: InvestigationReport,
    StageName.SPECIFY: CapabilitySpec,
    StageName.BUILD: CandidateManifest,
    StageName.REVIEW: ReviewReport,
    StageName.EVALUATE: ExperimentResult,
    StageName.SELECT: CycleResult,
}


class EvolutionStageOrchestrator:
    """One generic dispatcher for all nine persisted stage invocations."""

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
        baseline: GenerationManifest,
        plan: EvolutionPlan,
        subject_plugin_name: str = "unknown",
        subject_plugin_api_version: str = "1.0",
        subject_plugin_source: str = "unknown",
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
        self.baseline = baseline
        self.plan = plan
        self.subject_plugin_name = subject_plugin_name
        self.subject_plugin_api_version = subject_plugin_api_version
        self.subject_plugin_source = subject_plugin_source
        self.diagnostician = diagnostician or EvidenceFirstDiagnostician()
        self.architect = architect or CapabilityArchitect()
        self.retention_policy = retention_policy or RetentionPolicy()
        self.stage_directory = self.workspace / "stages"
        self.manifest_pointer = self.workspace / "cycle-manifest.pointer.json"
        self.manifest_digest, self.manifest = self._load_or_create_manifest()
        self.baseline, self.plan = self._load_canonical_bootstrap()

    @property
    def stage_order(self) -> tuple[StageName, ...]:
        return StageName.ordered()

    def run(self, *, until: StageName | str | None = None) -> BaseModel:
        target = StageName(until) if until is not None else StageName.SELECT
        for stage in self.stage_order:
            result = self.invoke(stage)
            if stage == target:
                return result
        return self.invoke(StageName.SELECT)

    def invoke(self, stage: StageName | str) -> BaseModel:
        requested = StageName(stage)
        index = self.stage_order.index(requested)
        if index and not self._pointer_exists(self.stage_order[index - 1]):
            raise StageOrderError(
                f"Cannot invoke {requested.value}: prerequisite "
                f"{self.stage_order[index - 1].value} has no completed pointer"
            )
        existing = self._read_completed(requested)
        if existing is not None:
            return existing
        if index and self._read_completed(self.stage_order[index - 1]) is None:
            raise StageOrderError(f"Missing completed prerequisite for {requested.value}")

        inputs = self._inputs(requested)
        output = self._dispatch(requested, inputs)
        expected = _OUTPUT_MODELS[requested]
        if not isinstance(output, expected):
            raise StageIntegrityError(
                f"Stage {requested.value} returned {type(output).__name__}; "
                f"expected {expected.__name__}"
            )
        self._validate_stage_output(requested, output, inputs)
        output_ref = self.artifacts.put_model(output)
        prior = self._prior_receipt_digest(requested)
        receipt = StageReceipt(
            receipt_version="1.0",
            receipt_id=new_id("receipt"),
            cycle_id=self.manifest.cycle_id,
            manifest_digest=self.manifest_digest,
            stage=requested,
            subject=self.manifest.subject,
            subject_generation_fingerprint=self.manifest.subject_generation_fingerprint,
            input_refs=inputs,
            output_ref=output_ref,
            prior_receipt_digest=prior,
        )
        receipt_ref = self.artifacts.put_model(receipt)
        pointer = StagePointer(
            pointer_version="1.0",
            cycle_id=self.manifest.cycle_id,
            stage=requested,
            receipt_digest=receipt_ref.digest,
        )
        pointer_path = self._pointer_path(requested)
        if pointer_path.exists():
            raise StageConflictError(f"Stage pointer appeared during {requested.value}")
        self.artifacts.write_pointer(pointer_path, pointer)
        return output

    def completed_stage(self, stage: StageName | str) -> BaseModel:
        """Read one completed stage through all manifest and receipt checks."""
        selected = StageName(stage)
        result = self._read_completed(selected)
        if result is None:
            raise StageOrderError(f"Stage {selected.value} has not completed")
        return result

    def stage_status(self) -> tuple[tuple[StageName, ...], StageName | None]:
        """Return validated completion state without executing or publishing stages."""
        completed: list[StageName] = []
        for index, stage in enumerate(self.stage_order):
            if self._pointer_exists(stage):
                if self._read_completed(stage) is None:
                    raise StageArtifactError(f"Unreadable completed stage {stage.value}")
                completed.append(stage)
            elif any(self._pointer_exists(later) for later in self.stage_order[index + 1 :]):
                raise StageOrderError(f"Later stage pointer exists without {stage.value}")
            else:
                break
        next_stage = (
            self.stage_order[len(completed)]
            if len(completed) < len(self.stage_order)
            else None
        )
        return tuple(completed), next_stage

    def _validate_stage_output(
        self,
        stage: StageName,
        output: BaseModel,
        inputs: dict[str, ArtifactRef],
    ) -> None:
        """Validate semantic links for both publication and replay."""
        if stage == StageName.INGEST:
            ingest = cast(IngestResult, output)
            if (
                ingest.cycle_id != self.manifest.cycle_id
                or ingest.subject != self.manifest.subject
                or ingest.generation_id != self.baseline.generation_id
                or ingest.baseline_ref != self.manifest.baseline_ref
                or ingest.plan_ref != self.manifest.plan_ref
            ):
                raise StageIntegrityError("Ingest output identity or canonical refs mismatch")
            if len(ingest.run_refs) != len(ingest.runs):
                raise StageIntegrityError("Ingest run refs do not match run records")
            run_ids: set[str] = set()
            runs_by_id: dict[str, RunRecord] = {}
            observed_scenarios: list[str] = []
            for reference, record in zip(ingest.run_refs, ingest.runs, strict=True):
                persisted = self.artifacts.read_model(reference, RunRecord)
                if (
                    persisted != record
                    or record.run_id in run_ids
                    or record.generation_id != self.baseline.generation_id
                ):
                    raise StageIntegrityError(f"Ingest run ref mismatch for {record.run_id}")
                run_ids.add(record.run_id)
                runs_by_id[record.run_id] = record
                observed_scenarios.append(record.scenario_id)
            if observed_scenarios != self.plan.diagnostic_scenarios:
                raise StageIntegrityError("Ingest runs do not match diagnostic scenario order")
            event_ids: set[str] = set()
            previous_sequences: dict[str, int] = {}
            for reference in ingest.event_refs:
                event = self.artifacts.read_model(reference, TrajectoryEvent)
                event_record = runs_by_id.get(event.run_id)
                if (
                    event_record is None
                    or event.generation_id != event_record.generation_id
                    or event.generation_id != self.baseline.generation_id
                    or event.scenario_id != event_record.scenario_id
                    or event.event_id in event_ids
                    or (
                        event.run_id in previous_sequences
                        and event.sequence <= previous_sequences[event.run_id]
                    )
                ):
                    raise StageIntegrityError("Ingest event refs do not match run records")
                event_ids.add(event.event_id)
                previous_sequences[event.run_id] = event.sequence
            capability = self.artifacts.read_model(ingest.capability_ref, CapabilityManifest)
            if (
                capability.generation_id != self.baseline.generation_id
                or ingest.capability_ref.digest != self.baseline.capability_manifest_digest
            ):
                raise StageIntegrityError("Ingest capability manifest is not canonical")
            return
        if stage == StageName.DISTILL:
            ingest = self._read_input(inputs, "ingest", IngestResult)
            self._validate_ingest(ingest)
            recomputed = self._distill_from_cas(ingest)
            if cast(DistilledTrace, output) != recomputed:
                raise StageIntegrityError("Distilled output differs from persisted CAS evidence")
            return
        if stage == StageName.DIAGNOSE:
            self._validate_issue(cast(CapabilityIssue, output))
            return
        if stage == StageName.INVESTIGATE:
            issue = self._read_input(inputs, "diagnose", CapabilityIssue)
            investigation = cast(InvestigationReport, output)
            if investigation.issue_id != issue.issue_id:
                raise StageIntegrityError("Investigation issue link mismatch")
            return
        if stage == StageName.SPECIFY:
            issue = self._read_input(inputs, "diagnose", CapabilityIssue)
            specification = cast(CapabilitySpec, output)
            if (
                specification.issue_id != issue.issue_id
                or specification.parent_generation != self.baseline.generation_id
            ):
                raise StageIntegrityError("Specification issue or parent link mismatch")
            return
        if stage == StageName.BUILD:
            issue = self._read_input(inputs, "diagnose", CapabilityIssue)
            specification = self._read_input(inputs, "specify", CapabilitySpec)
            candidate = cast(CandidateManifest, output)
            self._validate_candidate(candidate)
            if (
                candidate.issue_id != issue.issue_id
                or candidate.spec_id != specification.spec_id
                or candidate.artifact_digests.get("issue_object") != inputs["diagnose"].digest
                or candidate.artifact_digests.get("specification_object")
                != inputs["specify"].digest
            ):
                raise StageIntegrityError("Candidate issue, spec, or artifact link mismatch")
            self._verify_candidate_files(candidate)
            return
        if stage == StageName.REVIEW:
            candidate = self._read_input(inputs, "build", CandidateManifest)
            if cast(ReviewReport, output).candidate_id != candidate.candidate_id:
                raise StageIntegrityError("Review candidate link mismatch")
            return
        if stage == StageName.EVALUATE:
            candidate = self._read_input(inputs, "build", CandidateManifest)
            review = self._read_input(inputs, "review", ReviewReport)
            experiment = cast(ExperimentResult, output)
            if (
                experiment.candidate_id != candidate.candidate_id
                or experiment.baseline_generation != self.baseline.generation_id
                or experiment.review_passed != review.passed
            ):
                raise StageIntegrityError("Experiment candidate or baseline link mismatch")
            return
        if stage == StageName.SELECT:
            result = cast(CycleResult, output)
            ingest = self._read_input(inputs, "ingest", IngestResult)
            issue = self._read_input(inputs, "diagnose", CapabilityIssue)
            investigation = self._read_input(inputs, "investigate", InvestigationReport)
            specification = self._read_input(inputs, "specify", CapabilitySpec)
            candidate = self._read_input(inputs, "build", CandidateManifest)
            review = self._read_input(inputs, "review", ReviewReport)
            experiment = self._read_input(inputs, "evaluate", ExperimentResult)
            expected_candidate = result.candidate.model_copy(
                update={
                    "status": candidate.status,
                    "artifact_digests": candidate.artifact_digests,
                }
            )
            expected_issue = result.issue.model_copy(update={"status": issue.status})
            if (
                result.baseline_generation != self.baseline
                or result.diagnostic_runs != ingest.runs
                or expected_issue != issue
                or result.investigation != investigation
                or result.specification != specification
                or expected_candidate != candidate
                or result.review != review
                or result.experiment != experiment
                or result.decision.candidate_id != result.candidate.candidate_id
                or result.candidate.artifact_digests.get("review_object")
                != inputs["review"].digest
                or result.candidate.artifact_digests.get("experiment_object")
                != inputs["evaluate"].digest
            ):
                raise StageIntegrityError("Cycle result contains inconsistent stage links")
            if result.retained_generation is not None:
                if (
                    result.decision.retained_generation_id
                    != result.retained_generation.generation_id
                    or result.retained_generation.parent_generation_id
                    != self.baseline.generation_id
                ):
                    raise StageIntegrityError("Retained generation link mismatch")
            elif result.decision.verdict == GateVerdict.RETAIN:
                raise StageIntegrityError("Retain decision has no retained generation")
            elif result.decision.retained_generation_id is not None:
                raise StageIntegrityError("Non-retain decision names a retained generation")
            self._verify_candidate_files(result.candidate)
            return
        raise AssertionError(stage)

    def _dispatch(self, stage: StageName, inputs: dict[str, ArtifactRef]) -> BaseModel:
        if stage == StageName.INGEST:
            return self._ingest()
        if stage == StageName.DISTILL:
            ingest = self._read_input(inputs, "ingest", IngestResult)
            self._validate_ingest(ingest)
            return self._distill(ingest)
        if stage == StageName.DIAGNOSE:
            distilled = self._read_input(inputs, "distill", DistilledTrace)
            if distilled.generation_id != self.baseline.generation_id:
                raise StageIntegrityError("Distilled trace generation does not match manifest")
            issue = self.diagnostician.diagnose(distilled)
            self.ledger.add_issue(issue)
            return issue
        if stage == StageName.INVESTIGATE:
            issue = self._read_input(inputs, "diagnose", CapabilityIssue)
            self._validate_issue(issue)
            return self.investigator.investigate(issue)
        if stage == StageName.SPECIFY:
            issue = self._read_input(inputs, "diagnose", CapabilityIssue)
            investigation = self._read_input(inputs, "investigate", InvestigationReport)
            self._validate_issue(issue)
            if investigation.issue_id != issue.issue_id:
                raise StageIntegrityError("Investigation does not belong to diagnosed issue")
            if issue.proposed_resolution == ResolutionKind.BUILD_PROBE:
                raise ProbeRequiredError(
                    ProbeRequiredResult(
                        issue_id=issue.issue_id,
                        message=(
                            "Issue requires a first-class evidence probe; permanent capability "
                            "architecture is not permitted."
                        ),
                    )
                )
            specification = self.architect.specify(
                issue=issue,
                investigation=investigation,
                revealing_cases=self.plan.revealing_cases,
                structural_variants=self.plan.structural_variants,
                regression_suites=self.plan.regression_suites,
                long_horizon_suites=self.plan.long_horizon_suites,
            )
            self.ledger.add_issue(issue.model_copy(update={"status": IssueStatus.SPECIFIED}))
            return specification
        if stage == StageName.BUILD:
            issue = self._read_input(inputs, "diagnose", CapabilityIssue)
            spec = self._read_input(inputs, "specify", CapabilitySpec)
            self._validate_issue(issue)
            if (
                spec.issue_id != issue.issue_id
                or spec.parent_generation != self.baseline.generation_id
            ):
                raise StageIntegrityError("Capability specification links do not match cycle")
            candidate = self.builder.build(
                parent=self.baseline,
                issue=issue,
                specification=spec,
                candidate_root=self.workspace / "candidates",
            )
            file_digests = self._candidate_file_digests(candidate)
            persisted_candidate = candidate.model_copy(
                update={
                    "file_digests": file_digests,
                    "artifact_digests": {
                        **candidate.artifact_digests,
                        "issue_object": inputs["diagnose"].digest,
                        "specification_object": inputs["specify"].digest,
                    },
                }
            )
            self.ledger.add_candidate(persisted_candidate)
            return persisted_candidate
        if stage == StageName.REVIEW:
            candidate = self._read_input(inputs, "build", CandidateManifest)
            self._validate_candidate(candidate)
            self._verify_candidate_files(candidate)
            review = self.reviewer.review(
                candidate,
                forbidden_literals=self.plan.forbidden_literals,
            )
            self.ledger.add_candidate(
                candidate.model_copy(update={"status": CandidateStatus.REVIEWED})
            )
            return review
        if stage == StageName.EVALUATE:
            candidate = self._read_input(inputs, "build", CandidateManifest)
            review = self._read_input(inputs, "review", ReviewReport)
            self._validate_candidate(candidate)
            if review.candidate_id != candidate.candidate_id:
                raise StageIntegrityError("Review does not belong to candidate")
            self._verify_candidate_files(candidate)
            result = self.evaluator.evaluate(
                baseline=self.baseline,
                candidate=candidate,
                trace_directory=self.workspace / "traces" / "evaluation",
                review_passed=review.passed,
            )
            self.ledger.add_experiment(result)
            self.ledger.add_candidate(
                candidate.model_copy(update={"status": CandidateStatus.EVALUATED})
            )
            return result
        if stage == StageName.SELECT:
            candidate = self._read_input(inputs, "build", CandidateManifest)
            review = self._read_input(inputs, "review", ReviewReport)
            experiment = self._read_input(inputs, "evaluate", ExperimentResult)
            self._validate_candidate(candidate)
            if (
                review.candidate_id != candidate.candidate_id
                or experiment.candidate_id != candidate.candidate_id
            ):
                raise StageIntegrityError("Selection inputs refer to different candidates")
            self._verify_candidate_files(candidate)
            decision = self.retention_policy.decide(experiment)
            retained: GenerationManifest | None = None
            final_candidate = candidate.model_copy(
                update={
                    "artifact_digests": {
                        **candidate.artifact_digests,
                        "review_object": inputs["review"].digest,
                        "experiment_object": inputs["evaluate"].digest,
                    }
                }
            )
            final_issue = self._read_input(inputs, "diagnose", CapabilityIssue)
            if decision.verdict == GateVerdict.RETAIN:
                retained = self.materializer.materialize(
                    baseline=self.baseline,
                    candidate=final_candidate,
                    experiment=experiment,
                    decision=decision,
                )
                decision = decision.model_copy(
                    update={"retained_generation_id": retained.generation_id}
                )
                final_candidate = final_candidate.model_copy(
                    update={"status": CandidateStatus.RETAINED}
                )
                final_issue = final_issue.model_copy(update={"status": IssueStatus.RESOLVED})
                self.ledger.add_generation(retained)
                self.ledger.add_lineage(
                    parent_generation_id=self.baseline.generation_id,
                    child_generation_id=retained.generation_id,
                    candidate_id=final_candidate.candidate_id,
                    decision=decision,
                )
            else:
                final_candidate = final_candidate.model_copy(
                    update={"status": CandidateStatus.REJECTED}
                )
            self.ledger.add_candidate(final_candidate)
            self.ledger.add_issue(final_issue)
            self.ledger.add_decision(decision)
            cycle_result = CycleResult(
                workspace=str(self.workspace),
                baseline_generation=self.baseline,
                diagnostic_runs=self._read_input(inputs, "ingest", IngestResult).runs,
                issue=final_issue,
                investigation=self._read_input(inputs, "investigate", InvestigationReport),
                specification=self._read_input(inputs, "specify", CapabilitySpec),
                candidate=final_candidate,
                review=review,
                experiment=experiment,
                decision=decision,
                retained_generation=retained,
            )
            (self.workspace / "cycle-result.json").write_text(
                cycle_result.model_dump_json(indent=2), encoding="utf-8"
            )
            write_cycle_report(cycle_result, self.workspace / "report.md")
            return cycle_result
        raise AssertionError(stage)

    def _ingest(self) -> IngestResult:
        self.ledger.add_generation(self.baseline)
        capability = self.runner.capability_manifest(self.baseline)
        capability_ref = self.artifacts.put_model(capability)
        baseline_ref = self._ref_for_model(self.baseline)
        plan_ref = self._ref_for_model(self.plan)
        runs: list[RunRecord] = []
        run_refs: list[ArtifactRef] = []
        event_refs: list[ArtifactRef] = []
        for scenario_id in self.plan.diagnostic_scenarios:
            record, events = self.runner.run(
                generation=self.baseline,
                scenario_id=scenario_id,
                trace_directory=self.workspace / "traces" / "diagnostic",
            )
            self.ledger.add_run(record, events)
            runs.append(record)
            run_refs.append(self.artifacts.put_model(record))
            event_refs.extend(self.artifacts.put_model(event) for event in events)
        return IngestResult(
            cycle_id=self.manifest.cycle_id,
            subject=self.manifest.subject,
            generation_id=self.baseline.generation_id,
            baseline_ref=baseline_ref,
            plan_ref=plan_ref,
            capability_ref=capability_ref,
            run_refs=run_refs,
            event_refs=event_refs,
            runs=runs,
        )

    def _distill(self, ingest: IngestResult) -> DistilledTrace:
        for record in ingest.runs:
            raw_path = record.metadata.get("trace_path")
            if not isinstance(raw_path, str):
                raise StageArtifactError(f"Run {record.run_id} has no trace_path metadata")
            path = Path(raw_path)
            if not path.exists() or sha256_bytes(path.read_bytes()) != record.trace_digest:
                raise StageArtifactError(f"Trace digest mismatch for run {record.run_id}")
        return self._distill_from_cas(ingest)

    def _distill_from_cas(self, ingest: IngestResult) -> DistilledTrace:
        events: list[TrajectoryEvent] = []
        for reference in ingest.event_refs:
            events.append(self.artifacts.read_model(reference, TrajectoryEvent))
        capabilities = self.artifacts.read_model(ingest.capability_ref, CapabilityManifest)
        return TraceDistiller().distill(
            generation_id=ingest.generation_id,
            events=events,
            capabilities=capabilities,
        )

    def _validate_ingest(self, ingest: IngestResult) -> None:
        baseline = self.artifacts.read_model(ingest.baseline_ref, GenerationManifest)
        plan = self.artifacts.read_model(ingest.plan_ref, EvolutionPlan)
        if baseline.generation_id != self.baseline.generation_id:
            raise StageIntegrityError("Ingest baseline does not match cycle manifest")
        if stable_digest(plan.model_dump(mode="json")) != self.manifest.plan_digest:
            raise ManifestIntegrityError("Persisted plan artifact differs from cycle manifest")
        if ingest.generation_id != self.baseline.generation_id:
            raise StageIntegrityError("Ingest generation does not match baseline")

    def _validate_issue(self, issue: CapabilityIssue) -> None:
        if issue.subject_generation != self.baseline.generation_id:
            raise StageIntegrityError("Issue subject generation does not match cycle")

    def _validate_candidate(self, candidate: CandidateManifest) -> None:
        if candidate.parent_generation != self.baseline.generation_id:
            raise StageIntegrityError("Candidate parent generation does not match cycle")

    def _inputs(self, stage: StageName) -> dict[str, ArtifactRef]:
        refs: dict[str, ArtifactRef] = {}
        if stage == StageName.INGEST:
            return refs
        previous_stage = self.stage_order[self.stage_order.index(stage) - 1]
        previous = self._read_receipt(previous_stage)
        self._read_receipt_output(previous_stage, previous)
        refs[previous.stage.value] = previous.output_ref
        if stage in {StageName.SPECIFY, StageName.BUILD, StageName.SELECT}:
            receipt = self._read_receipt(StageName.DIAGNOSE)
            self._read_receipt_output(StageName.DIAGNOSE, receipt)
            refs["diagnose"] = receipt.output_ref
        if stage in {StageName.BUILD, StageName.SELECT}:
            refs["investigate"] = self._read_receipt(StageName.INVESTIGATE).output_ref
        if stage == StageName.SELECT:
            receipt = self._read_receipt(StageName.INGEST)
            self._read_receipt_output(StageName.INGEST, receipt)
            refs["ingest"] = receipt.output_ref
        if stage in {StageName.BUILD, StageName.SELECT}:
            receipt = self._read_receipt(StageName.SPECIFY)
            self._read_receipt_output(StageName.SPECIFY, receipt)
            refs["specify"] = receipt.output_ref
        if stage in {StageName.REVIEW, StageName.EVALUATE, StageName.SELECT}:
            receipt = self._read_receipt(StageName.BUILD)
            self._read_receipt_output(StageName.BUILD, receipt)
            refs["build"] = receipt.output_ref
        if stage in {StageName.EVALUATE, StageName.SELECT}:
            receipt = self._read_receipt(StageName.REVIEW)
            self._read_receipt_output(StageName.REVIEW, receipt)
            refs["review"] = receipt.output_ref
        if stage == StageName.SELECT:
            receipt = self._read_receipt(StageName.EVALUATE)
            self._read_receipt_output(StageName.EVALUATE, receipt)
            refs["evaluate"] = receipt.output_ref
        return refs

    def _read_receipt_output(self, stage: StageName, receipt: StageReceipt) -> BaseModel:
        return self.artifacts.read_model(receipt.output_ref, _OUTPUT_MODELS[stage])

    def _read_completed(self, stage: StageName) -> BaseModel | None:
        path = self._pointer_path(stage)
        if not path.exists():
            return None
        pointer = self._read_pointer(path, expected_stage=stage)
        receipt = self._read_receipt(stage, pointer.receipt_digest)
        expected_inputs = self._inputs(stage)
        if receipt.input_refs != expected_inputs:
            raise StageIntegrityError(f"Receipt input references changed for {stage.value}")
        if stage in {StageName.REVIEW, StageName.EVALUATE, StageName.SELECT}:
            candidate = self._read_input(expected_inputs, "build", CandidateManifest)
            self._verify_candidate_files(candidate)
        output_type = _OUTPUT_MODELS[stage]
        output = self.artifacts.read_model(receipt.output_ref, output_type)
        self._validate_stage_output(stage, output, expected_inputs)
        return output

    def _read_receipt(
        self,
        stage: StageName,
        digest: str | None = None,
        _seen: set[str] | None = None,
    ) -> StageReceipt:
        seen = _seen or set()
        if digest is None:
            pointer = self._read_pointer(self._pointer_path(stage), expected_stage=stage)
            digest = pointer.receipt_digest
        if digest in seen:
            raise StageIntegrityError("Receipt chain contains a cycle")
        seen.add(digest)
        reference = ArtifactRef(digest=digest, model="StageReceipt")
        receipt = self.artifacts.read_model(reference, StageReceipt)
        if (
            receipt.stage != stage
            or receipt.cycle_id != self.manifest.cycle_id
            or receipt.subject != self.manifest.subject
            or receipt.manifest_digest != self.manifest_digest
        ):
            raise StageIntegrityError(f"Receipt identity mismatch for {stage.value}")
        if receipt.subject_generation_fingerprint != self.manifest.subject_generation_fingerprint:
            raise ManifestIntegrityError(
                f"Receipt generation fingerprint mismatch for {stage.value}"
            )
        index = self.stage_order.index(stage)
        expected_prior = None
        if index:
            prior_stage = self.stage_order[index - 1]
            prior_pointer = self._read_pointer(
                self._pointer_path(prior_stage), expected_stage=prior_stage
            )
            expected_prior = prior_pointer.receipt_digest
        if receipt.prior_receipt_digest != expected_prior:
            raise StageIntegrityError(f"Receipt hash chain mismatch for {stage.value}")
        self._read_receipt_output(stage, receipt)
        if index:
            self._read_receipt(self.stage_order[index - 1], expected_prior, seen)
        return receipt

    def _prior_receipt_digest(self, stage: StageName) -> str | None:
        index = self.stage_order.index(stage)
        if index == 0:
            return None
        prior_stage = self.stage_order[index - 1]
        pointer = self._read_pointer(
            self._pointer_path(prior_stage), expected_stage=prior_stage
        )
        return pointer.receipt_digest

    def _pointer_path(self, stage: StageName) -> Path:
        return self.stage_directory / f"{stage.value}.pointer.json"

    def _pointer_exists(self, stage: StageName) -> bool:
        return self._pointer_path(stage).exists()

    def _read_pointer(
        self,
        path: Path,
        *,
        expected_stage: StageName | None = None,
    ) -> StagePointer:
        try:
            pointer = self.artifacts.read_pointer(path, StagePointer)
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            raise StageArtifactError(f"Invalid stage pointer {path}: {exc}") from exc
        if pointer.cycle_id != self.manifest.cycle_id:
            raise StageConflictError(f"Pointer cycle identity mismatch for {path.name}")
        if expected_stage is not None and pointer.stage != expected_stage:
            raise StageConflictError(
                f"Pointer stage mismatch for {path.name}: {pointer.stage.value}"
            )
        return pointer

    def _ref_for_model(self, model: BaseModel) -> ArtifactRef:
        return self.artifacts.put_model(model)

    def _candidate_file_digests(self, candidate: CandidateManifest) -> dict[str, str]:
        root = Path(candidate.workspace_path).resolve()
        result: dict[str, str] = {}
        for relative in candidate.changed_files:
            path = (root / relative).resolve()
            if root not in path.parents or not path.is_file():
                raise StageArtifactError(f"Candidate changed file is missing: {relative}")
            result[relative] = sha256_bytes(path.read_bytes())
        return result

    def _verify_candidate_files(self, candidate: CandidateManifest) -> None:
        if set(candidate.file_digests) != set(candidate.changed_files):
            raise StageArtifactError("Candidate changed-file digest map is incomplete")
        actual = self._candidate_file_digests(candidate)
        if actual != candidate.file_digests:
            raise StageArtifactError(
                f"Candidate changed-file bytes differ after build: {sorted(actual)}"
            )

    def _load_or_create_manifest(self) -> tuple[str, CycleManifest]:
        fingerprint = stable_digest(
            {
                "generation_id": self.baseline.generation_id,
                "subject": self.baseline.subject,
                "source_ref": self.baseline.source_ref,
                "capability_manifest_digest": self.baseline.capability_manifest_digest,
                "artifact_digests": self.baseline.artifact_digests,
                "models": self.baseline.models,
                "prompts": self.baseline.prompts,
                "config": self.baseline.config,
                "metadata": self.baseline.metadata,
            }
        )
        if self.manifest_pointer.exists():
            try:
                pointer = json.loads(self.manifest_pointer.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ManifestIntegrityError(
                    f"Invalid cycle manifest pointer {self.manifest_pointer}: {exc}"
                ) from exc
            digest = pointer.get("digest")
            if not isinstance(digest, str):
                raise ManifestIntegrityError("Manifest pointer has no digest")
            manifest = self.artifacts.read_model(
                ArtifactRef(digest=digest, model="CycleManifest"), CycleManifest
            )
            mismatches = {
                "subject": (manifest.subject, self.subject_plugin_name),
                "api_version": (
                    manifest.subject_plugin_api_version,
                    self.subject_plugin_api_version,
                ),
                "plugin_source": (manifest.subject_plugin_source, self.subject_plugin_source),
                "generation": (manifest.subject_generation_fingerprint, fingerprint),
                "plan": (
                    manifest.plan_digest,
                    stable_digest(self.plan.model_dump(mode="json")),
                ),
            }
            changed = [name for name, (old, new) in mismatches.items() if old != new]
            if changed:
                raise ManifestIntegrityError(
                    "Workspace bootstrap differs from persisted cycle manifest: "
                    + ", ".join(changed)
                )
            return digest, manifest
        baseline_ref = self._ref_for_model(self.baseline)
        plan_ref = self._ref_for_model(self.plan)
        manifest = CycleManifest(
            manifest_version="1.0",
            cycle_id=new_id("cycle"),
            subject=self.subject_plugin_name,
            subject_plugin_api_version=self.subject_plugin_api_version,
            subject_plugin_source=self.subject_plugin_source,
            baseline_generation_id=self.baseline.generation_id,
            subject_generation_fingerprint=fingerprint,
            plan_digest=plan_ref.digest,
            baseline_ref=baseline_ref,
            plan_ref=plan_ref,
            stage_order=StageName.ordered(),
        )
        reference = self.artifacts.put_model(manifest)
        self.manifest_pointer.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.manifest_pointer.with_name(f".{self.manifest_pointer.name}.tmp")
        temporary.write_text(
            json.dumps({"digest": reference.digest}, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.manifest_pointer)
        return reference.digest, manifest

    def _load_canonical_bootstrap(self) -> tuple[GenerationManifest, EvolutionPlan]:
        baseline = self.artifacts.read_model(self.manifest.baseline_ref, GenerationManifest)
        plan = self.artifacts.read_model(self.manifest.plan_ref, EvolutionPlan)
        if baseline.generation_id != self.manifest.baseline_generation_id:
            raise ManifestIntegrityError("Manifest baseline reference has the wrong generation")
        if baseline.subject != self.manifest.subject:
            raise ManifestIntegrityError("Manifest baseline reference has the wrong subject")
        if stable_digest(plan.model_dump(mode="json")) != self.manifest.plan_digest:
            raise ManifestIntegrityError("Manifest plan reference failed digest validation")
        return baseline, plan

    def _read_input(self, inputs: dict[str, ArtifactRef], name: str, model: type[Any]) -> Any:
        reference = inputs.get(name)
        if reference is None:
            raise StageOrderError(f"Missing stage input {name}")
        return self.artifacts.read_model(reference, model)
