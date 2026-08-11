"""Microworld implementation of the generic probe roles."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from evogen.core.enums import Completeness, EventKind, ResolutionKind, Severity
from evogen.core.ids import stable_digest
from evogen.core.models import (
    ArtifactRef,
    CapabilityIssue,
    GenerationManifest,
    InvestigationReport,
    ProbeBuildOutput,
    ProbeCandidateManifest,
    ProbeDispatchEvidence,
    ProbeEvaluation,
    ProbeEvidenceTarget,
    ProbeFilePayload,
    ProbeObservationEvidence,
    ProbePermissions,
    ProbePlan,
    ProbeReviewReport,
    ReviewFinding,
)
from evogen.evolution.probes import (
    ProbePlanningError,
    execute_probe_source,
    static_probe_source_checks,
)

from .environment import MicroWorld
from .scenarios import get_scenario
from .subject import MicroworldRunner


class MicroworldProbePlanner:
    def __init__(self, *, runner: MicroworldRunner, trace_directory: Path) -> None:
        self.runner = runner
        self.trace_directory = trace_directory

    def plan(
        self,
        *,
        issue: CapabilityIssue,
        investigation: InvestigationReport,
        parent: GenerationManifest,
        probe_id: str,
        evidence_target: ProbeEvidenceTarget | None = None,
        initial_observation: dict[str, Any] | None = None,
        investigation_ref: ArtifactRef | None = None,
        capability_manifest_ref: ArtifactRef | None = None,
    ) -> ProbePlan:
        if issue.proposed_resolution != ResolutionKind.BUILD_PROBE:
            raise ProbePlanningError("Only BUILD_PROBE issues may enter the probe planner")
        if investigation_ref is None or capability_manifest_ref is None:
            raise ProbePlanningError(
                "Probe planning requires canonical investigation and capability refs"
            )
        if issue.required_effect is None:
            raise ProbePlanningError("Probe issue has no required effect")
        exact = [
            operation
            for operation in investigation.candidate_operations
            if issue.required_effect in operation.semantic_effects
        ]
        if len(exact) != 1:
            raise ProbePlanningError("Investigation has no unique exact operation/effect")
        fixture_ids = issue.acceptance_hints.get("revealing_cases", [])
        if len(fixture_ids) != 1:
            raise ProbePlanningError("Issue does not name exactly one probe fixture")
        fixture_id = fixture_ids[0]
        if initial_observation is None:
            record, events = self.runner.run(
                generation=parent,
                scenario_id=fixture_id,
                trace_directory=self.trace_directory,
            )
            del record
            observations = [event for event in events if event.kind == EventKind.OBSERVATION]
            if not observations:
                raise ProbePlanningError("Probe fixture produced no initial observation")
            observation = observations[0].payload
        else:
            observation = initial_observation
        target = evidence_target or ProbeEvidenceTarget(
            named_uncertainty=(
                f"Whether {exact[0].name} can produce {issue.required_effect} "
                "when bound to an observed opaque container."
            ),
            hypotheses=[
                "The declared operation is accepted for an observed opaque container.",
                "A later independent snapshot exposes the same container contents.",
            ],
            required_later_observations=[
                "accepted and changed execution receipt",
                "complete later observation of the bound container",
            ],
            prohibited_inferences=["dispatch acceptance alone proves a world effect"],
        )
        forbidden = [fixture_id]
        target_value = observation.get("target_item_id")
        if isinstance(target_value, str):
            forbidden.append(target_value)
        for container in observation.get("visible_containers", []):
            if isinstance(container, dict):
                for key in ("container_id", "name"):
                    value = container.get(key)
                    if isinstance(value, str):
                        forbidden.append(value)
        return ProbePlan(
            probe_id=probe_id,
            issue_id=issue.issue_id,
            parent_generation=parent.generation_id,
            subject=parent.subject,
            investigation_ref=investigation_ref,
            capability_manifest_ref=capability_manifest_ref,
            baseline_capability_manifest_digest=capability_manifest_ref.digest,
            fixture_id=fixture_id,
            evidence_target=target,
            permissions=ProbePermissions(
                allowed_operations=[exact[0].name],
                allowed_effects=list(exact[0].semantic_effects),
                allowed_paths=["probe.py"],
                max_steps=1,
                max_bytes=4096,
                max_duration_seconds=1.0,
            ),
            initial_observation=observation,
            metadata={"forbidden_literals": forbidden},
        )


class MicroworldProbeBuilder:
    def build(self, *, plan: ProbePlan) -> ProbeBuildOutput:
        if (
            len(plan.permissions.allowed_operations) != 1
            or len(plan.permissions.allowed_effects) != 1
        ):
            raise ProbePlanningError("Microworld probes require one declared operation and effect")
        operation = repr(plan.permissions.allowed_operations[0])
        effect = repr(plan.permissions.allowed_effects[0])
        source = f'''"""Observation-bound disposable probe."""

def derive_action(initial_observation):
    containers = initial_observation["visible_containers"]
    opaque = [item for item in containers if item["opaque"] and not item["inspected"]]
    if len(opaque) != 1:
        raise ValueError("Expected one observed opaque container")
    container = opaque[0]
    return {{
        "operation": {operation},
        "effect": {effect},
        "container_id": container["container_id"],
    }}
'''
        return ProbeBuildOutput(files=[ProbeFilePayload(path="probe.py", content=source)])


class MicroworldProbeReviewer:
    def review(self, *, plan: ProbePlan, candidate: ProbeCandidateManifest) -> ProbeReviewReport:
        root = Path(candidate.workspace_path)
        findings: list[ReviewFinding] = []
        checks = {
            "isolated_root": root.name == plan.probe_id and root.parent.name == "candidates",
            "changed_file_scope": set(candidate.changed_files).issubset(
                set(plan.permissions.allowed_paths)
            ),
        }
        try:
            source = (root / "probe.py").read_text(encoding="utf-8")
        except OSError as exc:
            source = ""
            findings.append(
                ReviewFinding(
                    severity=Severity.CRITICAL,
                    code="missing_source",
                    message=str(exc),
                    file="probe.py",
                )
            )
        for message in static_probe_source_checks(
            source,
            forbidden_literals=cast_forbidden(plan),
            allowed_operations=plan.permissions.allowed_operations,
            allowed_effects=plan.permissions.allowed_effects,
        ):
            findings.append(
                ReviewFinding(
                    severity=Severity.HIGH,
                    code="static",
                    message=message,
                    file="probe.py",
                )
            )
        checks["static_source"] = not any(item.code == "static" for item in findings)
        checks["byte_budget"] = len(source.encode("utf-8")) <= plan.permissions.max_bytes
        return ProbeReviewReport(
            review_id="pending",
            candidate_id=candidate.candidate_id,
            probe_id=plan.probe_id,
            passed=all(checks.values()) and not findings,
            checks=checks,
            findings=findings,
            reviewed_files=list(candidate.changed_files),
        )


def cast_forbidden(plan: ProbePlan) -> list[str]:
    value = plan.metadata.get("forbidden_literals", [])
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


class MicroworldProbeEvaluator:
    def __init__(self, *, runner: MicroworldRunner, baseline: GenerationManifest) -> None:
        self.runner = runner
        self.baseline = baseline

    def evaluate(
        self,
        *,
        plan: ProbePlan,
        candidate: ProbeCandidateManifest,
        review: ProbeReviewReport,
    ) -> ProbeEvaluation:
        digest = stable_digest(
            self.runner.capability_manifest(self.baseline).model_dump(mode="json")
        )
        ref = ArtifactRef(digest=digest, model="CapabilityManifest")
        base: dict[str, Any] = dict(
            evaluation_id="pending",
            candidate_id=candidate.candidate_id,
            probe_id=plan.probe_id,
            named_uncertainty=plan.evidence_target.named_uncertainty,
            initial_observation_ref=cast(ArtifactRef, plan.initial_observation_ref),
            dispatch_evidence_ref=None,
            later_observation_ref=None,
            initial_capability_manifest_ref=ref,
            initial_capability_manifest_digest=digest,
            initial_capability_manifest_bytes_digest=digest,
            final_capability_manifest_ref=ref,
            final_capability_manifest_digest=digest,
            final_capability_manifest_bytes_digest=digest,
        )
        if not review.passed:
            return ProbeEvaluation(
                completeness=Completeness.UNKNOWN,
                notes=["Review denied execution."],
                **base,
            )
        source = (Path(candidate.workspace_path) / "probe.py").read_text(encoding="utf-8")
        try:
            action = execute_probe_source(
                source,
                plan.initial_observation,
                plan.permissions.max_duration_seconds,
                allowed_operations=plan.permissions.allowed_operations,
                allowed_effects=plan.permissions.allowed_effects,
            )
        except Exception as exc:
            return ProbeEvaluation(
                completeness=Completeness.UNKNOWN,
                notes=[f"Probe execution failed: {exc}"],
                **base,
            )
        operation = action.get("operation")
        effect = action.get("effect")
        target_id = action.get("container_id")
        observed = [
            item
            for item in plan.initial_observation.get("visible_containers", [])
            if item.get("opaque") and not item.get("inspected")
        ]
        if (
            not isinstance(operation, str)
            or not isinstance(effect, str)
            or not isinstance(target_id, str)
            or operation != "inspect_container"
            or effect != "reveal_contents"
            or operation not in plan.permissions.allowed_operations
            or effect not in plan.permissions.allowed_effects
            or target_id not in {item.get("container_id") for item in observed}
        ):
            return ProbeEvaluation(
                completeness=Completeness.UNKNOWN,
                notes=["Action was undeclared or unbound."],
                **base,
            )
        world = MicroWorld(get_scenario(plan.fixture_id))
        receipt = world.inspect_container(target_id)
        dispatch = ProbeDispatchEvidence(
            operation=operation,
            effect=effect,
            target_id=target_id,
            accepted=receipt.accepted,
            changed=receipt.changed,
            steps=1,
            receipt=receipt.model_dump(mode="json"),
            completeness=Completeness.COMPLETE,
        )
        later = world.snapshot().model_dump(mode="json")
        container = next(
            item for item in later["visible_containers"] if item["container_id"] == target_id
        )
        observation = ProbeObservationEvidence(
            container_id=target_id,
            inspected=bool(container["inspected"]),
            exposed_item_ids=[item["item_id"] for item in container["revealed_items"]],
            observation=later,
            completeness=Completeness.COMPLETE,
        )
        return ProbeEvaluation(
            dispatch_evidence=dispatch,
            later_observation=observation,
            completeness=Completeness.COMPLETE,
            **base,
        )


__all__ = [
    "MicroworldProbeBuilder",
    "MicroworldProbeEvaluator",
    "MicroworldProbePlanner",
    "MicroworldProbeReviewer",
]
