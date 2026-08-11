"""Separate, persisted evidence-probe lifecycle.

The probe plane has its own CAS, receipts, workspace and ledger transitions. It
accepts canonical permanent inputs by reference, but can never create a
GenerationManifest or enter the permanent capability path.
"""

from __future__ import annotations

import ast
import base64
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel

from evogen.adapters.protocols import (
    ProbeBuilder,
    ProbeEvaluator,
    ProbePlanner,
    ProbeReviewer,
    SubjectRunner,
)
from evogen.core.enums import Completeness, ProbeDispositionKind, ProbeStageName, ResolutionKind
from evogen.core.ids import sha256_bytes, stable_json_bytes
from evogen.core.models import (
    ArtifactRef,
    CapabilityIssue,
    CapabilityManifest,
    GenerationManifest,
    InvestigationReport,
    ProbeBuildOutput,
    ProbeCandidateManifest,
    ProbeDispatchEvidence,
    ProbeDisposition,
    ProbeEvaluation,
    ProbeFilePayload,
    ProbeManifest,
    ProbeObservationEvidence,
    ProbePlan,
    ProbeResult,
    ProbeReviewReport,
    ProbeStagePointer,
    ProbeStageReceipt,
)
from evogen.storage.artifacts import ArtifactStore
from evogen.storage.ledger import Ledger


class ProbeIntegrityError(RuntimeError):
    pass


class ProbePathError(ProbeIntegrityError):
    pass


class ProbePlanningError(ProbeIntegrityError):
    pass


_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_PROBE_ID = re.compile(r"^[A-Za-z0-9_-]+$")
_OUTPUT_MODELS: dict[ProbeStageName, type[BaseModel]] = {
    ProbeStageName.PLAN: ProbePlan,
    ProbeStageName.BUILD: ProbeCandidateManifest,
    ProbeStageName.REVIEW: ProbeReviewReport,
    ProbeStageName.EVALUATE: ProbeEvaluation,
    ProbeStageName.DISPOSE: ProbeDisposition,
}


def _digest(value: Any) -> str:
    return sha256_bytes(stable_json_bytes(value))


def _stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}-{_digest(value)[:24]}"


def validate_probe_id(value: str) -> str:
    if (
        not value
        or value in {".", ".."}
        or not _PROBE_ID.fullmatch(value)
        or "/" in value
        or "\\" in value
    ):
        raise ProbePathError(f"Invalid single-component probe id: {value!r}")
    return value


def _reject_symlink_components(path: Path) -> None:
    for component in (path, *path.parents):
        if component.is_symlink():
            raise ProbePathError(f"Symlinked probe path component: {component}")


def _require_digest(value: str, label: str) -> None:
    if not _DIGEST.fullmatch(value):
        raise ProbeIntegrityError(f"{label} is not a canonical SHA-256 digest")


class ProbeOrchestrator:
    def __init__(
        self,
        *,
        workspace: Path,
        artifacts: ArtifactStore,
        ledger: Ledger,
        baseline_ref: ArtifactRef,
        issue_ref: ArtifactRef,
        investigation_ref: ArtifactRef,
        capability_manifest_ref: ArtifactRef,
        probe_id: str,
        initial_observation: dict[str, Any] | None = None,
        runner: SubjectRunner,
        planner: ProbePlanner,
        builder: ProbeBuilder,
        reviewer: ProbeReviewer,
        evaluator: ProbeEvaluator,
    ) -> None:
        validate_probe_id(probe_id)
        _reject_symlink_components(workspace)
        self.workspace = workspace.absolute()
        self.probes_root = self.workspace / "probes"
        _reject_symlink_components(self.probes_root)
        self.probe_id = probe_id
        self.probe_workspace = self.probes_root / probe_id
        _reject_symlink_components(self.probe_workspace)
        self.permanent_artifacts = artifacts
        self.probe_artifacts = ArtifactStore(self.probes_root / "artifacts")
        self.ledger = ledger
        self.runner = runner
        self.baseline_ref = baseline_ref
        self.issue_ref = issue_ref
        self.investigation_ref = investigation_ref
        self.capability_manifest_ref = capability_manifest_ref
        self.initial_observation = initial_observation
        self.baseline = self._canonical(baseline_ref, GenerationManifest, "baseline")
        self.issue = self._canonical(issue_ref, CapabilityIssue, "issue")
        self.investigation = self._canonical(
            investigation_ref, InvestigationReport, "investigation"
        )
        self.capability_manifest = self._canonical(
            capability_manifest_ref, CapabilityManifest, "capability manifest"
        )
        self._validate_canonical_inputs()
        self.planner = planner
        self.builder = builder
        self.reviewer = reviewer
        self.evaluator = evaluator
        if len({id(builder), id(reviewer), id(evaluator)}) != 3:
            raise ProbeIntegrityError(
                "Probe builder, reviewer, and evaluator must be distinct authorities"
            )
        self.manifest_pointer = self.probe_workspace / "probe-manifest.pointer.json"
        self.manifest_digest, self.manifest = self._load_or_create_manifest()

    def _canonical(self, ref: ArtifactRef, model: type[Any], label: str) -> Any:
        if ref.model != model.__name__:
            raise ProbeIntegrityError(f"{label} reference declares {ref.model}")
        _require_digest(ref.digest, label)
        try:
            return self.permanent_artifacts.read_model(ref, model)
        except Exception as exc:
            raise ProbeIntegrityError(f"{label} failed canonical CAS validation") from exc

    def _validate_canonical_inputs(self) -> None:
        if self.capability_manifest_ref.digest != self.baseline.capability_manifest_digest:
            raise ProbeIntegrityError("Capability ref does not match baseline canonical digest")
        if self.issue.subject_generation != self.baseline.generation_id:
            raise ProbeIntegrityError("Issue does not belong to baseline generation")
        if self.investigation.issue_id != self.issue.issue_id:
            raise ProbeIntegrityError("Investigation does not belong to issue")
        if self.capability_manifest.generation_id != self.baseline.generation_id:
            raise ProbeIntegrityError("Capability manifest does not belong to baseline")

    @property
    def stage_order(self) -> tuple[ProbeStageName, ...]:
        return ProbeStageName.ordered()

    def run(self, *, until: ProbeStageName | str | None = None) -> ProbeResult | BaseModel:
        target = ProbeStageName(until) if until is not None else ProbeStageName.DISPOSE
        for stage in self.stage_order:
            output = self.invoke(stage)
            if stage == target:
                return self.result() if stage == ProbeStageName.DISPOSE else output
        return self.result()

    def invoke(self, stage: ProbeStageName | str) -> BaseModel:
        selected = ProbeStageName(stage)
        index = self.stage_order.index(selected)
        if index and not self._stage_pointer_exists(self.stage_order[index - 1]):
            raise ProbeIntegrityError(f"Missing completed prerequisite for {selected.value}")
        existing = self._read_completed(selected)
        if existing is not None:
            return existing
        output = self._dispatch(selected, self._inputs(selected))
        expected = _OUTPUT_MODELS[selected]
        if not isinstance(output, expected):
            raise ProbeIntegrityError(f"Wrong output type for {selected.value}")
        self._validate_output(selected, output)
        output_ref = self.probe_artifacts.put_model(output)
        inputs = self._inputs(selected)
        prior = self._prior_receipt_digest(selected)
        receipt = ProbeStageReceipt(
            receipt_version="1.0",
            receipt_id=self._receipt_id(selected, inputs, output_ref, prior),
            probe_id=self.manifest.probe_id,
            manifest_digest=self.manifest_digest,
            stage=selected,
            subject=self.manifest.subject,
            input_refs=inputs,
            output_ref=output_ref,
            prior_receipt_digest=prior,
        )
        receipt_ref = self.probe_artifacts.put_model(receipt)
        pointer = ProbeStagePointer(
            pointer_version="1.0",
            probe_id=self.manifest.probe_id,
            stage=selected,
            receipt_digest=receipt_ref.digest,
        )
        pointer_path = self._pointer_path(selected)
        _reject_symlink_components(pointer_path)
        if pointer_path.exists():
            raise ProbeIntegrityError("Probe pointer appeared during publication")
        self.probe_artifacts.write_pointer(pointer_path, pointer)
        return output

    def completed_stage(self, stage: ProbeStageName | str) -> BaseModel:
        result = self._read_completed(ProbeStageName(stage))
        if result is None:
            raise ProbeIntegrityError(f"Probe stage {stage} is incomplete")
        return result

    def stage_status(self) -> tuple[tuple[ProbeStageName, ...], ProbeStageName | None]:
        completed: list[ProbeStageName] = []
        for index, stage in enumerate(self.stage_order):
            if self._stage_pointer_exists(stage):
                self.completed_stage(stage)
                completed.append(stage)
            elif any(self._stage_pointer_exists(later) for later in self.stage_order[index + 1 :]):
                raise ProbeIntegrityError("Later probe pointer exists without prerequisite")
            else:
                break
        return (
            tuple(completed),
            self.stage_order[len(completed)] if len(completed) < len(self.stage_order) else None,
        )

    def result(self) -> ProbeResult:
        return ProbeResult(
            workspace=str(self.probe_workspace),
            manifest=self.manifest,
            plan=cast(ProbePlan, self.completed_stage(ProbeStageName.PLAN)),
            candidate=cast(ProbeCandidateManifest, self.completed_stage(ProbeStageName.BUILD)),
            review=cast(ProbeReviewReport, self.completed_stage(ProbeStageName.REVIEW)),
            evaluation=cast(ProbeEvaluation, self.completed_stage(ProbeStageName.EVALUATE)),
            disposition=cast(ProbeDisposition, self.completed_stage(ProbeStageName.DISPOSE)),
        )

    def _dispatch(self, stage: ProbeStageName, inputs: dict[str, ArtifactRef]) -> BaseModel:
        if stage == ProbeStageName.PLAN:
            plan = self.planner.plan(
                issue=self.issue,
                investigation=self.investigation,
                parent=self.baseline,
                probe_id=self.manifest.probe_id,
                initial_observation=self.initial_observation,
                investigation_ref=self.investigation_ref,
                capability_manifest_ref=self.capability_manifest_ref,
            )
            if plan.probe_id != self.probe_id:
                raise ProbeIntegrityError("Planner changed probe identity")
            initial_ref = ArtifactRef(
                digest=self.probe_artifacts.put_json(plan.initial_observation),
                model="InitialObservation",
            )
            plan = plan.model_copy(
                update={
                    "initial_observation_ref": initial_ref,
                    "investigation_ref": self.investigation_ref,
                    "capability_manifest_ref": self.capability_manifest_ref,
                    "baseline_capability_manifest_digest": self.capability_manifest_ref.digest,
                }
            )
            self.ledger.add_probe_plan(plan)
            return plan
        plan = cast(ProbePlan, self._read_input(inputs, "plan", ProbePlan))
        if stage == ProbeStageName.BUILD:
            candidate_root = self.probe_workspace / "candidates"
            _reject_symlink_components(candidate_root)
            candidate_directory = candidate_root / plan.probe_id
            _reject_symlink_components(candidate_directory)
            try:
                draft = self.builder.build(plan=plan)
                candidate = self._materialize_candidate(plan, draft, candidate_directory)
            except ProbeIntegrityError:
                raise
            except Exception as exc:
                raise ProbeIntegrityError("Probe builder failed") from exc
            candidate = candidate.model_copy(
                update={
                    "created_at": self.manifest.created_at,
                    "candidate_id": _stable_id(
                        "probe-candidate",
                        {"probe": plan.probe_id, "source": candidate.source_digest},
                    ),
                }
            )
            self._validate_candidate(candidate, plan)
            self._verify_candidate_files(candidate, plan)
            self.ledger.add_probe_candidate(candidate)
            return candidate
        candidate = cast(
            ProbeCandidateManifest, self._read_input(inputs, "candidate", ProbeCandidateManifest)
        )
        self._verify_candidate_files(candidate, plan)
        if stage == ProbeStageName.REVIEW:
            review = self.reviewer.review(plan=plan, candidate=candidate)
            review = review.model_copy(
                update={"review_id": _stable_id("probe-review", candidate.source_digest)}
            )
            self.ledger.add_probe_review(review)
            return review
        review = cast(ProbeReviewReport, self._read_input(inputs, "review", ProbeReviewReport))
        if stage == ProbeStageName.EVALUATE:
            before = self._capability_proof()
            try:
                evaluation = self.evaluator.evaluate(plan=plan, candidate=candidate, review=review)
            except Exception as exc:
                evaluation = ProbeEvaluation(
                    evaluation_id="pending",
                    candidate_id=candidate.candidate_id,
                    probe_id=plan.probe_id,
                    named_uncertainty=plan.evidence_target.named_uncertainty,
                    initial_observation_ref=cast(ArtifactRef, plan.initial_observation_ref),
                    dispatch_evidence_ref=None,
                    later_observation_ref=None,
                    completeness=Completeness.UNKNOWN,
                    initial_capability_manifest_ref=before[0],
                    initial_capability_manifest_digest=before[1],
                    initial_capability_manifest_bytes_digest=before[1],
                    final_capability_manifest_ref=before[0],
                    final_capability_manifest_digest=before[1],
                    final_capability_manifest_bytes_digest=before[1],
                    notes=[f"Probe evaluator failed: {type(exc).__name__}: {exc}"],
                )
            after = self._capability_proof()
            evaluation = self._persist_evidence(evaluation, plan, before, after)
            evaluation = evaluation.model_copy(
                update={"evaluation_id": self._evaluation_id(candidate, evaluation)}
            )
            self.ledger.add_probe_evaluation(evaluation)
            return evaluation
        evaluation = cast(ProbeEvaluation, self._read_input(inputs, "evaluation", ProbeEvaluation))
        disposition = self._disposition(plan, candidate, review, evaluation)
        self.ledger.add_probe_disposition(disposition)
        return disposition

    def _materialize_candidate(
        self, plan: ProbePlan, draft: ProbeBuildOutput, root: Path
    ) -> ProbeCandidateManifest:
        """Publish only validated in-memory files into the assigned root."""
        payloads: dict[str, ProbeFilePayload] = {}
        allowed = set(plan.permissions.allowed_paths)
        for payload in draft.files:
            relative = Path(payload.path)
            if (
                not payload.path
                or relative.is_absolute()
                or len(relative.parts) != 1
                or relative.name in {"environment.py", "evaluator.py", "scenarios.py"}
                or payload.path not in allowed
                or payload.path in payloads
            ):
                raise ProbePathError("Probe builder returned an undeclared or unsafe file")
            payloads[payload.path] = payload
        if "probe.py" not in payloads:
            raise ProbePathError("Probe builder did not provide probe.py")
        declared_bytes = sum(len(payload.content.encode("utf-8")) for payload in payloads.values())
        if plan.permissions.max_bytes <= 0 or declared_bytes > plan.permissions.max_bytes:
            raise ProbePathError("Candidate source exceeds declared byte budget")
        _reject_symlink_components(root)
        root.mkdir(parents=True, exist_ok=True)
        _reject_symlink_components(root)
        for existing in root.iterdir():
            if existing.is_symlink() or not existing.is_file():
                raise ProbePathError("Candidate root contains a directory or symlink")
            if existing.name not in payloads:
                raise ProbePathError("Probe builder returned an incomplete or extra file tree")
        for path, payload in payloads.items():
            target = root / path
            _reject_symlink_components(target)
            target.write_text(payload.content, encoding="utf-8")
        actual: dict[str, str] = {}
        total = 0
        for existing in root.iterdir():
            if existing.is_symlink() or not existing.is_file() or existing.name not in payloads:
                raise ProbePathError("Candidate root contains an undeclared tree entry")
            data = existing.read_bytes()
            actual[existing.name] = sha256_bytes(data)
            total += len(data)
        if set(actual) != set(payloads):
            raise ProbePathError("Candidate file set differs from builder declaration")
        if plan.permissions.max_bytes <= 0 or total > plan.permissions.max_bytes:
            raise ProbePathError("Candidate source exceeds declared byte budget")
        source_digest = actual.get("probe.py")
        if source_digest is None:
            raise ProbePathError("Probe builder did not provide probe.py")
        return ProbeCandidateManifest(
            candidate_id="pending",
            probe_id=plan.probe_id,
            parent_generation=plan.parent_generation,
            issue_id=plan.issue_id,
            workspace_path=str(root),
            source_digest=source_digest,
            artifact_digests={"source": source_digest},
            changed_files=sorted(actual),
            file_digests=actual,
            metadata=draft.metadata,
        )

    @staticmethod
    def _evaluation_id(candidate: ProbeCandidateManifest, evaluation: ProbeEvaluation) -> str:
        seed = evaluation.model_dump(mode="json")
        seed.pop("evaluation_id", None)
        return _stable_id(
            "probe-evaluation",
            {"candidate": candidate.candidate_id, "evaluation": seed},
        )

    def _persist_evidence(
        self,
        evaluation: ProbeEvaluation,
        plan: ProbePlan,
        before: tuple[ArtifactRef, str],
        after: tuple[ArtifactRef, str],
    ) -> ProbeEvaluation:
        if evaluation.dispatch_evidence is not None:
            dispatch_ref = self.probe_artifacts.put_model(evaluation.dispatch_evidence)
        else:
            dispatch_ref = None
        if evaluation.later_observation is not None:
            later_ref = self.probe_artifacts.put_model(evaluation.later_observation)
        else:
            later_ref = None
        return evaluation.model_copy(
            update={
                "initial_observation_ref": plan.initial_observation_ref,
                "dispatch_evidence_ref": dispatch_ref,
                "later_observation_ref": later_ref,
                "initial_capability_manifest_ref": before[0],
                "initial_capability_manifest_digest": before[1],
                "initial_capability_manifest_bytes_digest": before[1],
                "final_capability_manifest_ref": after[0],
                "final_capability_manifest_digest": after[1],
                "final_capability_manifest_bytes_digest": after[1],
                "capability_manifest_unchanged": before[1] == after[1],
            }
        )

    def _capability_proof(self) -> tuple[ArtifactRef, str]:
        try:
            canonical = self.permanent_artifacts.read_bytes(self.capability_manifest_ref.digest)
        except Exception as exc:
            raise ProbeIntegrityError(
                "Capability manifest failed canonical CAS validation"
            ) from exc
        canonical_digest = sha256_bytes(canonical)
        actual = self.runner.capability_manifest(self.baseline)
        actual_bytes = stable_json_bytes(actual.model_dump(mode="json"))
        actual_digest = sha256_bytes(actual_bytes)
        if canonical_digest != actual_digest:
            raise ProbeIntegrityError("Runner capability manifest differs from permanent CAS")
        return self.capability_manifest_ref, canonical_digest

    def _disposition(
        self,
        plan: ProbePlan,
        candidate: ProbeCandidateManifest,
        review: ProbeReviewReport,
        evaluation: ProbeEvaluation,
    ) -> ProbeDisposition:
        if not review.passed:
            kind = ProbeDispositionKind.REJECTED
            reason = "Independent review rejected the probe."
        else:
            dispatch = self._evidence(evaluation.dispatch_evidence_ref, ProbeDispatchEvidence)
            later = self._evidence(evaluation.later_observation_ref, ProbeObservationEvidence)
            resolved = (
                evaluation.completeness == Completeness.COMPLETE
                and dispatch is not None
                and dispatch.completeness == Completeness.COMPLETE
                and dispatch.accepted
                and dispatch.changed
                and self._receipt_matches_dispatch(dispatch)
                and dispatch.steps <= plan.permissions.max_steps
                and dispatch.operation in plan.permissions.allowed_operations
                and dispatch.effect in plan.permissions.allowed_effects
                and self._target_was_observed(plan.initial_observation, dispatch.target_id)
                and later is not None
                and later.completeness == Completeness.COMPLETE
                and later.container_id == dispatch.target_id
                and later.inspected
                and bool(later.exposed_item_ids)
                and self._observation_matches_later(later)
                and evaluation.capability_manifest_unchanged
            )
            kind = ProbeDispositionKind.RESOLVED if resolved else ProbeDispositionKind.INCONCLUSIVE
            reason = (
                "Accepted changed receipt and complete later observation resolved uncertainty."
                if resolved
                else "Evidence was refused, missing, incomplete, or contradictory."
            )
        return ProbeDisposition(
            disposition_id=_stable_id(
                "probe-disposition", {"candidate": candidate.candidate_id, "kind": kind.value}
            ),
            candidate_id=candidate.candidate_id,
            probe_id=plan.probe_id,
            named_uncertainty=plan.evidence_target.named_uncertainty,
            disposition=kind,
            rationale=reason,
        )

    def _evidence(self, ref: ArtifactRef | None, model: type[Any]) -> Any | None:
        if ref is None:
            return None
        try:
            return self.probe_artifacts.read_model(ref, model)
        except (FileNotFoundError, RuntimeError, TypeError, ValueError) as exc:
            raise ProbeIntegrityError("Probe evidence failed CAS validation") from exc

    @staticmethod
    def _receipt_matches_dispatch(dispatch: ProbeDispatchEvidence) -> bool:
        receipt = dispatch.receipt
        return (
            isinstance(receipt.get("accepted"), bool)
            and isinstance(receipt.get("changed"), bool)
            and receipt["accepted"] == dispatch.accepted
            and receipt["changed"] == dispatch.changed
        )

    @staticmethod
    def _observation_matches_later(observation: ProbeObservationEvidence) -> bool:
        payload = observation.observation
        containers = payload.get("visible_containers") if isinstance(payload, dict) else None
        if not isinstance(containers, list) or not containers:
            return False
        matching = [
            item
            for item in containers
            if isinstance(item, dict) and item.get("container_id") == observation.container_id
        ]
        if len(matching) != 1:
            return False
        container = matching[0]
        revealed = container.get("revealed_items")
        if not isinstance(revealed, list):
            return False
        item_ids = [
            item.get("item_id") for item in revealed if isinstance(item, dict)
        ]
        return (
            container.get("inspected") == observation.inspected
            and item_ids == observation.exposed_item_ids
        )

    @staticmethod
    def _target_was_observed(observation: dict[str, Any], target_id: str) -> bool:
        containers = observation.get("visible_containers")
        if not isinstance(containers, list) or not containers:
            return False
        return any(
            isinstance(item, dict)
            and item.get("container_id") == target_id
            and item.get("opaque") is True
            and item.get("inspected") is False
            for item in containers
        )

    def _inputs(self, stage: ProbeStageName) -> dict[str, ArtifactRef]:
        if stage == ProbeStageName.PLAN:
            return {
                "baseline": self.manifest.baseline_ref,
                "issue": self.manifest.issue_ref,
                "investigation": self.manifest.investigation_ref,
                "capability": self.manifest.capability_manifest_ref,
            }
        refs = {"plan": self._read_receipt(ProbeStageName.PLAN).output_ref}
        if stage in {ProbeStageName.REVIEW, ProbeStageName.EVALUATE, ProbeStageName.DISPOSE}:
            refs["candidate"] = self._read_receipt(ProbeStageName.BUILD).output_ref
        if stage in {ProbeStageName.EVALUATE, ProbeStageName.DISPOSE}:
            refs["review"] = self._read_receipt(ProbeStageName.REVIEW).output_ref
        if stage == ProbeStageName.DISPOSE:
            refs["evaluation"] = self._read_receipt(ProbeStageName.EVALUATE).output_ref
        return refs

    def _read_input(self, inputs: dict[str, ArtifactRef], name: str, model: type[Any]) -> Any:
        ref = inputs.get(name)
        if ref is None:
            raise ProbeIntegrityError(f"Missing probe input {name}")
        try:
            return self.probe_artifacts.read_model(ref, model)
        except (FileNotFoundError, RuntimeError, TypeError, ValueError) as exc:
            raise ProbeIntegrityError(f"Probe input {name} failed CAS validation") from exc

    def _read_completed(self, stage: ProbeStageName) -> BaseModel | None:
        path = self._pointer_path(stage)
        _reject_symlink_components(path)
        if not path.exists():
            return None
        pointer = self._read_stage_pointer(stage)
        if pointer.probe_id != self.manifest.probe_id or pointer.stage != stage:
            raise ProbeIntegrityError("Probe pointer identity mismatch")
        receipt = self._read_receipt(stage, pointer.receipt_digest)
        if receipt.input_refs != self._inputs(stage):
            raise ProbeIntegrityError("Probe receipt inputs changed")
        try:
            output = self.probe_artifacts.read_model(receipt.output_ref, _OUTPUT_MODELS[stage])
        except (FileNotFoundError, RuntimeError, TypeError, ValueError) as exc:
            raise ProbeIntegrityError(f"Probe {stage.value} output failed CAS validation") from exc
        self._validate_output(stage, output)
        return output

    def _read_stage_pointer(self, stage: ProbeStageName) -> ProbeStagePointer:
        path = self._pointer_path(stage)
        _reject_symlink_components(path)
        try:
            return self.probe_artifacts.read_pointer(path, ProbeStagePointer)
        except Exception as exc:
            raise ProbeIntegrityError(f"Probe {stage.value} pointer failed validation") from exc

    def _validate_output(self, stage: ProbeStageName, output: BaseModel) -> None:
        if stage == ProbeStageName.PLAN:
            plan = cast(ProbePlan, output)
            self._validate_plan_semantics(plan)
            if (
                plan.probe_id != self.probe_id
                or plan.subject != self.baseline.subject
                or plan.parent_generation != self.baseline.generation_id
                or plan.issue_id != self.issue.issue_id
                or plan.investigation_ref != self.investigation_ref
                or plan.capability_manifest_ref != self.capability_manifest_ref
                or plan.baseline_capability_manifest_digest != self.capability_manifest_ref.digest
                or plan.initial_observation_ref is None
                or plan.initial_observation_ref.model != "InitialObservation"
            ):
                raise ProbeIntegrityError("Probe plan semantic links changed")
            try:
                initial_observation = self.probe_artifacts.read_json(
                    plan.initial_observation_ref.digest
                )
            except Exception as exc:
                raise ProbeIntegrityError(
                    "Initial observation ref failed CAS validation"
                ) from exc
            if initial_observation != plan.initial_observation:
                raise ProbeIntegrityError("Initial observation ref bytes changed")
            try:
                replayed = self.planner.plan(
                    issue=self.issue,
                    investigation=self.investigation,
                    parent=self.baseline,
                    probe_id=self.probe_id,
                    initial_observation=plan.initial_observation,
                    investigation_ref=self.investigation_ref,
                    capability_manifest_ref=self.capability_manifest_ref,
                ).model_copy(update={"initial_observation_ref": plan.initial_observation_ref})
            except Exception as exc:
                raise ProbeIntegrityError("Probe plan could not be independently replayed") from exc
            if replayed != plan:
                raise ProbeIntegrityError("Probe plan replay differs from persisted plan")
            return
        plan = cast(ProbePlan, self.completed_stage(ProbeStageName.PLAN))
        candidate = (
            cast(ProbeCandidateManifest, self.completed_stage(ProbeStageName.BUILD))
            if stage != ProbeStageName.BUILD
            else None
        )
        if stage == ProbeStageName.BUILD:
            self._validate_candidate(cast(ProbeCandidateManifest, output), plan)
            self._verify_candidate_files(cast(ProbeCandidateManifest, output), plan)
        elif stage == ProbeStageName.REVIEW:
            review = cast(ProbeReviewReport, output)
            if (
                candidate is None
                or review.candidate_id != candidate.candidate_id
                or review.probe_id != plan.probe_id
                or review.review_id != _stable_id("probe-review", candidate.source_digest)
            ):
                raise ProbeIntegrityError("Review semantic links changed")
            if review.passed != (all(review.checks.values()) and not review.findings):
                raise ProbeIntegrityError("Review verdict is inconsistent with findings")
            if review.reviewed_files != candidate.changed_files:
                raise ProbeIntegrityError("Review file scope changed")
            recomputed = self.reviewer.review(plan=plan, candidate=candidate)
            if (
                review.passed != recomputed.passed
                or review.checks != recomputed.checks
                or review.findings != recomputed.findings
                or review.reviewed_files != recomputed.reviewed_files
            ):
                raise ProbeIntegrityError("Review artifact is not independently reproducible")
        elif stage == ProbeStageName.EVALUATE:
            self._validate_evaluation(
                cast(ProbeEvaluation, output), plan, cast(ProbeCandidateManifest, candidate)
            )
        else:
            disposition = cast(ProbeDisposition, output)
            review = cast(ProbeReviewReport, self.completed_stage(ProbeStageName.REVIEW))
            evaluation = cast(ProbeEvaluation, self.completed_stage(ProbeStageName.EVALUATE))
            expected = self._disposition(
                plan, cast(ProbeCandidateManifest, candidate), review, evaluation
            )
            if disposition != expected:
                raise ProbeIntegrityError("Disposition is not derived from review/evidence")

    def _validate_plan_semantics(self, plan: ProbePlan) -> None:
        if self.issue.proposed_resolution != ResolutionKind.BUILD_PROBE:
            raise ProbeIntegrityError("Probe plan is not rooted in BUILD_PROBE")
        if plan.fixture_id not in self.issue.acceptance_hints.get("revealing_cases", []):
            raise ProbeIntegrityError("Probe fixture is not a named revealing case")
        if self.issue.required_effect is None:
            raise ProbeIntegrityError("Probe issue has no required effect")
        matching = [
            operation
            for operation in self.investigation.candidate_operations
            if self.issue.required_effect in operation.semantic_effects
        ]
        if len(matching) != 1:
            raise ProbeIntegrityError("Probe investigation has no unique exact operation")
        operation = matching[0]
        if (
            plan.permissions.allowed_operations != [operation.name]
            or set(plan.permissions.allowed_effects) != set(operation.semantic_effects)
        ):
            raise ProbeIntegrityError("Probe permissions are not investigation-derived")

    def _validate_evaluation(
        self, evaluation: ProbeEvaluation, plan: ProbePlan, candidate: ProbeCandidateManifest
    ) -> None:
        """Replay the trusted adapter boundary without elevating persisted evidence.

        In G05 the subject evaluator is trusted to obtain a later world observation
        independently of the dispatch receipt. Persisted artifact replay detects
        tampering; evaluator provenance and frozen authority are deferred to G06/G07.
        """
        canonical_ref, canonical_digest = self._capability_proof()
        if (
            evaluation.probe_id != plan.probe_id
            or evaluation.candidate_id != candidate.candidate_id
            or evaluation.named_uncertainty != plan.evidence_target.named_uncertainty
            or evaluation.initial_observation_ref != plan.initial_observation_ref
            or evaluation.initial_capability_manifest_ref != canonical_ref
            or evaluation.final_capability_manifest_ref != canonical_ref
            or evaluation.initial_capability_manifest_digest != canonical_digest
            or evaluation.final_capability_manifest_digest != canonical_digest
            or evaluation.initial_capability_manifest_bytes_digest
            != canonical_digest
            or evaluation.final_capability_manifest_bytes_digest
            != canonical_digest
            or evaluation.capability_manifest_unchanged is not True
            or evaluation.evaluation_id != self._evaluation_id(candidate, evaluation)
        ):
            raise ProbeIntegrityError("Capability proof or evaluation links changed")
        # Replay the subject evaluator as an independent verification boundary. The
        # persisted CAS/evaluation pair is never authoritative merely because the
        # adapter supplied matching evidence; coordinated forged CAS is rejected when
        # the adapter's deterministic fresh-world result differs.
        review = cast(ProbeReviewReport, self.completed_stage(ProbeStageName.REVIEW))
        try:
            replayed = self.evaluator.evaluate(
                plan=plan,
                candidate=candidate,
                review=review,
            )
        except Exception:
            if (
                evaluation.completeness != Completeness.UNKNOWN
                or evaluation.dispatch_evidence is not None
                or evaluation.later_observation is not None
            ):
                raise ProbeIntegrityError(
                    "Evaluation failure replay disagrees with evidence"
                ) from None
        else:
            if (
                replayed.completeness != evaluation.completeness
                or replayed.dispatch_evidence != evaluation.dispatch_evidence
                or replayed.later_observation != evaluation.later_observation
            ):
                raise ProbeIntegrityError("Evaluation evidence failed independent replay")
        if evaluation.dispatch_evidence_ref is not None:
            dispatch = self._evidence(evaluation.dispatch_evidence_ref, ProbeDispatchEvidence)
            if dispatch != evaluation.dispatch_evidence:
                raise ProbeIntegrityError("Dispatch evidence embedded bytes changed")
        elif evaluation.dispatch_evidence is not None:
            raise ProbeIntegrityError("Dispatch evidence is missing its CAS ref")
        if evaluation.later_observation_ref is not None:
            later = self._evidence(evaluation.later_observation_ref, ProbeObservationEvidence)
            if later != evaluation.later_observation:
                raise ProbeIntegrityError("Later observation embedded bytes changed")
        elif evaluation.later_observation is not None:
            raise ProbeIntegrityError("Later observation is missing its CAS ref")

    def _read_receipt(self, stage: ProbeStageName, digest: str | None = None) -> ProbeStageReceipt:
        if digest is None:
            digest = self._read_stage_pointer(stage).receipt_digest
        try:
            receipt = self.probe_artifacts.read_model(
                ArtifactRef(digest=digest, model="ProbeStageReceipt"), ProbeStageReceipt
            )
        except (FileNotFoundError, RuntimeError, TypeError, ValueError) as exc:
            raise ProbeIntegrityError("Probe receipt failed CAS validation") from exc
        if (
            receipt.stage != stage
            or receipt.probe_id != self.probe_id
            or receipt.manifest_digest != self.manifest_digest
            or receipt.subject != self.manifest.subject
        ):
            raise ProbeIntegrityError("Receipt identity changed")
        expected_id = self._receipt_id(
            stage,
            receipt.input_refs,
            receipt.output_ref,
            receipt.prior_receipt_digest,
        )
        if receipt.receipt_id != expected_id:
            raise ProbeIntegrityError("Receipt deterministic identity changed")
        index = self.stage_order.index(stage)
        expected = None
        if index:
            expected = self._read_stage_pointer(self.stage_order[index - 1]).receipt_digest
            self._read_receipt(self.stage_order[index - 1], expected)
        if receipt.prior_receipt_digest != expected:
            raise ProbeIntegrityError("Receipt chain changed")
        return receipt

    def _prior_receipt_digest(self, stage: ProbeStageName) -> str | None:
        index = self.stage_order.index(stage)
        if not index:
            return None
        return self._read_stage_pointer(self.stage_order[index - 1]).receipt_digest

    def _receipt_id(
        self,
        stage: ProbeStageName,
        inputs: dict[str, ArtifactRef],
        output_ref: ArtifactRef,
        prior: str | None,
    ) -> str:
        return _stable_id(
            "probe-receipt",
            {
                "probe": self.manifest.probe_id,
                "stage": stage.value,
                "manifest": self.manifest_digest,
                "inputs": inputs,
                "output": output_ref,
                "prior": prior,
            },
        )

    def _pointer_path(self, stage: ProbeStageName) -> Path:
        return self.probe_workspace / "stages" / f"{stage.value}.pointer.json"

    def _stage_pointer_exists(self, stage: ProbeStageName) -> bool:
        path = self._pointer_path(stage)
        _reject_symlink_components(path)
        return path.exists()

    def _load_or_create_manifest(self) -> tuple[str, ProbeManifest]:
        _reject_symlink_components(self.manifest_pointer)
        if self.manifest_pointer.exists():
            try:
                data = json.loads(self.manifest_pointer.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise ProbeIntegrityError("Probe manifest pointer is invalid") from exc
            if not isinstance(data, dict):
                raise ProbeIntegrityError("Probe manifest pointer is invalid")
            digest = data.get("digest")
            if not isinstance(digest, str):
                raise ProbeIntegrityError("Manifest pointer has no digest")
            try:
                manifest = self.probe_artifacts.read_model(
                    ArtifactRef(digest=digest, model="ProbeManifest"), ProbeManifest
                )
            except (FileNotFoundError, RuntimeError, TypeError, ValueError) as exc:
                raise ProbeIntegrityError("Probe manifest failed CAS validation") from exc
            expected = {
                "probe_id": self.probe_id,
                "subject": self.baseline.subject,
                "baseline_generation_id": self.baseline.generation_id,
                "baseline_ref": self.baseline_ref,
                "issue_ref": self.issue_ref,
                "investigation_ref": self.investigation_ref,
                "capability_manifest_ref": self.capability_manifest_ref,
            }
            for name, value in expected.items():
                if getattr(manifest, name) != value:
                    raise ProbeIntegrityError(f"Manifest {name} changed on reload")
            if manifest.baseline_capability_manifest_digest != self.capability_manifest_ref.digest:
                raise ProbeIntegrityError("Manifest capability digest changed on reload")
            return digest, manifest
        manifest = ProbeManifest(
            manifest_version="1.0",
            probe_id=self.probe_id,
            subject=self.baseline.subject,
            baseline_generation_id=self.baseline.generation_id,
            baseline_ref=self.baseline_ref,
            issue_ref=self.issue_ref,
            investigation_ref=self.investigation_ref,
            capability_manifest_ref=self.capability_manifest_ref,
            baseline_capability_manifest_digest=self.capability_manifest_ref.digest,
            stage_order=ProbeStageName.ordered(),
        )
        digest = self.probe_artifacts.put_model(manifest).digest
        self.probe_workspace.mkdir(parents=True, exist_ok=True)
        self.manifest_pointer.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.manifest_pointer.with_name(f".{self.manifest_pointer.name}.tmp")
        temporary.write_text(
            json.dumps({"digest": digest}, sort_keys=True) + "\n", encoding="utf-8"
        )
        temporary.replace(self.manifest_pointer)
        return digest, manifest

    def _validate_candidate(self, candidate: ProbeCandidateManifest, plan: ProbePlan) -> None:
        if (
            candidate.kind != "probe"
            or candidate.probe_id != plan.probe_id
            or candidate.issue_id != plan.issue_id
            or candidate.parent_generation != plan.parent_generation
            or Path(candidate.workspace_path) != self.probe_workspace / "candidates" / plan.probe_id
        ):
            raise ProbePathError("Probe candidate identity/root changed")
        expected_id = _stable_id(
            "probe-candidate",
            {"probe": plan.probe_id, "source": candidate.source_digest},
        )
        if candidate.candidate_id != expected_id:
            raise ProbeIntegrityError("Candidate deterministic identity changed")

    def _verify_candidate_files(self, candidate: ProbeCandidateManifest, plan: ProbePlan) -> None:
        root = Path(candidate.workspace_path)
        _reject_symlink_components(root)
        expected = self.probe_workspace / "candidates" / plan.probe_id
        if root != expected or not root.is_dir():
            raise ProbePathError("Candidate root is not orchestrator-assigned")
        allowed = set(plan.permissions.allowed_paths)
        if len(candidate.changed_files) != len(set(candidate.changed_files)):
            raise ProbePathError("Candidate changed files contain duplicates")
        if not set(candidate.changed_files).issubset(allowed):
            raise ProbePathError("Candidate changed files exceed declared permissions")
        if set(candidate.file_digests) != set(candidate.changed_files):
            raise ProbePathError("Candidate file digest map is incomplete")
        entries = list(root.iterdir())
        if any(entry.is_symlink() or not entry.is_file() for entry in entries):
            raise ProbePathError("Candidate root contains a directory or symlink")
        if {entry.name for entry in entries} != set(candidate.changed_files):
            raise ProbePathError("Candidate tree differs from declared files")
        total = 0
        source_digest: str | None = None
        for entry in entries:
            relative = entry.name
            path = Path(relative)
            if path.is_absolute() or ".." in path.parts or path == Path(""):
                raise ProbePathError("Candidate path escapes root")
            if path.name in {"environment.py", "evaluator.py", "scenarios.py"}:
                raise ProbePathError("Protected subject/evaluator file in probe candidate")
            target = root / path
            _reject_symlink_components(target)
            if not target.is_file() or target.resolve().parent != root.resolve():
                raise ProbePathError("Candidate file escapes root")
            data = target.read_bytes()
            total += len(data)
            if relative == "probe.py":
                source_digest = sha256_bytes(data)
            if sha256_bytes(data) != candidate.file_digests[relative]:
                raise ProbePathError("Candidate file digest changed")
        if source_digest is None or source_digest != candidate.source_digest:
            raise ProbePathError("Candidate source digest changed")
        if candidate.artifact_digests.get("source") != candidate.source_digest:
            raise ProbePathError("Candidate source artifact digest changed")
        if plan.permissions.max_bytes <= 0 or total > plan.permissions.max_bytes:
            raise ProbePathError("Candidate source exceeds declared byte budget")


_SAFE_NODES = {
    ast.Module,
    ast.FunctionDef,
    ast.arguments,
    ast.arg,
    ast.Return,
    ast.Assign,
    ast.Name,
    ast.Load,
    ast.Store,
    ast.Constant,
    ast.Subscript,
    ast.Load,
    ast.List,
    ast.ListComp,
    ast.comprehension,
    ast.If,
    ast.Compare,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.Eq,
    ast.Not,
    ast.UnaryOp,
    ast.NotEq,
    ast.Call,
    ast.Dict,
    ast.BinOp,
    ast.Add,
    ast.Index,
    ast.Expr,
    ast.Raise,
    ast.Gt,
    ast.GtE,
}


def validate_probe_source(
    source: str,
    *,
    allowed_operations: list[str],
    allowed_effects: list[str] | None = None,
) -> list[str]:
    findings: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"syntax error: {exc}"]
    for node in ast.walk(tree):
        if type(node) not in _SAFE_NODES:
            findings.append(f"forbidden syntax: {type(node).__name__}")
        if isinstance(
            node, (ast.Import, ast.ImportFrom, ast.Attribute, ast.While, ast.For, ast.With, ast.Try)
        ):
            findings.append("imports, attributes, and unbounded control flow are forbidden")
        if isinstance(node, ast.Name) and (
            node.id.startswith("__") or node.id in {"open", "exec", "eval", "compile", "__import__"}
        ):
            findings.append(f"forbidden name: {node.id}")
        if isinstance(node, ast.Dict):
            keys = [item.value for item in node.keys if isinstance(item, ast.Constant)]
            if "operation" in keys:
                for key, value in zip(node.keys, node.values, strict=True):
                    if isinstance(key, ast.Constant) and key.value == "operation":
                        if (
                            not isinstance(value, ast.Constant)
                            or value.value not in allowed_operations
                        ):
                            findings.append("undeclared operation literal")
            if "effect" in keys and allowed_effects is not None:
                for key, value in zip(node.keys, node.values, strict=True):
                    if isinstance(key, ast.Constant) and key.value == "effect":
                        if (
                            not isinstance(value, ast.Constant)
                            or value.value not in allowed_effects
                        ):
                            findings.append("undeclared effect literal")
    return sorted(set(findings))


def execute_probe_source(
    source: str,
    observation: dict[str, Any],
    timeout_seconds: float,
    *,
    allowed_operations: list[str] | None = None,
    allowed_effects: list[str] | None = None,
) -> dict[str, Any]:
    findings = validate_probe_source(
        source,
        allowed_operations=allowed_operations or [],
        allowed_effects=allowed_effects,
    )
    if findings:
        raise ProbeIntegrityError("Probe source failed static validation: " + "; ".join(findings))
    encoded = base64.b64encode(source.encode()).decode()
    wrapper = (
        "import base64,json,sys; "
        "src=base64.b64decode(sys.argv[1]).decode(); "
        "ns={}; exec(compile(src,'probe.py','exec'), "
        "{'__builtins__': {'len':len, 'ValueError':ValueError}}, ns); "
        "print(json.dumps(ns['derive_action'](json.loads(sys.stdin.read()))))"
    )
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-c", wrapper, encoded],
            input=json.dumps(observation),
            text=True,
            capture_output=True,
            timeout=max(timeout_seconds, 0.01),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProbeIntegrityError("Probe execution timed out") from exc
    if completed.returncode != 0:
        raise ProbeIntegrityError("Probe subprocess failed")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ProbeIntegrityError("Probe returned non-JSON action") from exc
    if not isinstance(result, dict):
        raise ProbeIntegrityError("Probe action is not an object")
    return result


def static_probe_source_checks(
    source: str,
    *,
    forbidden_literals: list[str] | None = None,
    allowed_operations: list[str] | None = None,
    allowed_effects: list[str] | None = None,
) -> list[str]:
    findings = validate_probe_source(
        source,
        allowed_operations=allowed_operations or [],
        allowed_effects=allowed_effects,
    )
    for literal in forbidden_literals or []:
        if literal and literal in source:
            findings.append(f"forbidden literal: {literal}")
    return sorted(set(findings))
