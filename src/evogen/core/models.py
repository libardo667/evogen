from __future__ import annotations

from datetime import UTC, datetime
from math import isfinite
from typing import Annotated, Any, Generic, Literal, TypeAlias, TypeVar

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

from .enums import (
    AgentRole,
    CandidateStatus,
    Completeness,
    EventKind,
    FailureLayer,
    GateVerdict,
    IssueStatus,
    ProbeDispositionKind,
    ProbeStageName,
    ProofClass,
    ResolutionKind,
    RoleOutcome,
    Severity,
    StageName,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


DigestStr = Annotated[str, Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")]
JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | list[object] | dict[str, object]


def _nonblank(value: str) -> str:
    if not value.strip():
        raise ValueError("value must be nonblank")
    return value


def _json_value(value: object) -> JsonValue:
    if isinstance(value, float) and not isfinite(value):
        raise ValueError("role input values cannot contain non-finite floats")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        return {key: _json_value(item) for key, item in value.items()}
    raise ValueError("role input values must be JSON values")


_ItemT = TypeVar("_ItemT")


class BoundedCollection(StrictModel, Generic[_ItemT]):
    """A collection whose absence semantics are explicit."""

    items: list[_ItemT]
    completeness: Completeness
    known_total: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_completeness(self) -> BoundedCollection[_ItemT]:
        if self.completeness == Completeness.COMPLETE:
            if self.known_total is None or self.known_total != len(self.items):
                raise ValueError("Complete collections require known_total equal to len(items)")
        elif self.completeness == Completeness.TRUNCATED:
            if self.known_total is not None and self.known_total <= len(self.items):
                raise ValueError(
                    "Truncated collections require known_total greater than retained items"
                )
        else:
            if self.items:
                raise ValueError("Missing or unknown collections cannot carry authoritative items")
            if self.known_total is not None:
                raise ValueError(
                    "Missing or unknown collections cannot claim an authoritative total"
                )
        return self


class EvidenceRef(StrictModel):
    run_id: str
    event_id: str
    note: str


class CapabilityDefinition(StrictModel):
    name: str
    purpose: str
    kind: str
    semantic_effects: list[str] = Field(default_factory=list)
    owner_component: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    applicability: str
    completion_evidence: list[str] = Field(default_factory=list)
    implementation_ref: str
    proof_class: ProofClass = ProofClass.PORTABLE
    introduced_generation: str
    limitations: list[str] = Field(default_factory=list)


class CapabilityManifest(StrictModel):
    generation_id: str
    capabilities: list[CapabilityDefinition]

    @property
    def names(self) -> set[str]:
        return {capability.name for capability in self.capabilities}

    def by_name(self, name: str) -> CapabilityDefinition | None:
        return next(
            (capability for capability in self.capabilities if capability.name == name),
            None,
        )


class GenerationManifest(StrictModel):
    generation_id: str
    parent_generation_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    subject: str
    source_ref: str
    capability_manifest_digest: str
    artifact_digests: dict[str, str] = Field(default_factory=dict)
    models: dict[str, str] = Field(default_factory=dict)
    prompts: dict[str, str] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunRecord(StrictModel):
    run_id: str
    generation_id: str
    scenario_id: str
    started_at: datetime
    finished_at: datetime
    success: bool
    termination: str
    trace_digest: str
    steps: int
    interventions: int = 0
    invalid_actions: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrajectoryEvent(StrictModel):
    envelope_version: Literal["1.0"]
    event_id: str
    run_id: str
    generation_id: str
    scenario_id: str
    sequence: StrictInt = Field(ge=0)
    recorded_at: datetime = Field(default_factory=utc_now)
    kind: EventKind
    world_revision: str | None = None
    source_event_type: str | None
    source_event_id: str | None
    source_sequence: StrictInt | None
    source_step_index: StrictInt | None
    source_world_revision: str | None
    payload: dict[str, Any] = Field(default_factory=dict)


class FailureSignature(StrictModel):
    code: str
    count: int = Field(ge=1)
    blocker_type: str | None = None
    required_effect: str | None = None
    offered_actions: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRef]
    facts: dict[str, Any] = Field(default_factory=dict)


class DistilledTrace(StrictModel):
    generation_id: str
    run_ids: list[str]
    scenario_ids: list[str]
    existing_capabilities: list[str]
    existing_semantic_effects: list[str]
    signatures: list[FailureSignature]
    event_count: int


class IssueClassification(StrictModel):
    primary: FailureLayer
    alternatives: list[FailureLayer] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str


class CapabilityIssue(StrictModel):
    issue_id: str
    subject_generation: str
    created_at: datetime = Field(default_factory=utc_now)
    status: IssueStatus = IssueStatus.OPEN
    title: str
    symptom_summary: str
    classification: IssueClassification
    supporting_evidence: list[EvidenceRef]
    contradicting_evidence: list[str] = Field(default_factory=list)
    known_unknowns: list[str] = Field(default_factory=list)
    required_effect: str | None = None
    blocker_type: str | None = None
    proposed_resolution: ResolutionKind
    prediction: str
    acceptance_hints: dict[str, list[str]] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EnvironmentOperation(StrictModel):
    name: str
    semantic_effects: list[str]
    description: str
    source_ref: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)


class InvestigationReport(StrictModel):
    report_id: str
    issue_id: str
    inspected_sources: list[str]
    candidate_operations: list[EnvironmentOperation]
    rejected_operations: list[str] = Field(default_factory=list)
    remaining_unknowns: list[str] = Field(default_factory=list)
    conclusion: str


class CapabilitySpec(StrictModel):
    spec_id: str
    issue_id: str
    parent_generation: str
    capability_name: str
    purpose: str
    semantic_effects: list[str]
    owner_component: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    applicability: str
    binding_rules: list[str]
    execution_route: str
    completion_evidence: list[str]
    non_goals: list[str]
    prediction: str
    revealing_cases: list[str]
    structural_variants: list[str]
    regression_suites: list[str]
    long_horizon_suites: list[str]
    implementation_constraints: list[str] = Field(default_factory=list)


class PatchFile(StrictModel):
    path: str
    content: str


class PatchSet(StrictModel):
    summary: str
    files: list[PatchFile]
    claimed_capabilities: list[str] = Field(default_factory=list)


class CandidateManifest(StrictModel):
    candidate_id: str
    parent_generation: str
    issue_id: str
    spec_id: str
    created_at: datetime = Field(default_factory=utc_now)
    status: CandidateStatus = CandidateStatus.CREATED
    workspace_path: str
    source_digest: str
    artifact_digests: dict[str, str]
    changed_files: list[str]
    claimed_capabilities: list[str]
    file_digests: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReviewFinding(StrictModel):
    severity: Severity
    code: str
    message: str
    file: str | None = None


class ReviewReport(StrictModel):
    review_id: str
    candidate_id: str
    passed: bool
    checks: dict[str, bool]
    findings: list[ReviewFinding] = Field(default_factory=list)
    reviewed_files: list[str] = Field(default_factory=list)


class ScenarioResult(StrictModel):
    scenario_id: str
    category: str
    success: bool
    steps: int
    interventions: int
    invalid_actions: int
    blocked: bool
    termination: str
    run_id: str
    trace_digest: str


class MetricVector(StrictModel):
    revealing_success_rate: float = Field(ge=0.0, le=1.0)
    variant_success_rate: float = Field(ge=0.0, le=1.0)
    regression_success_rate: float = Field(ge=0.0, le=1.0)
    long_horizon_success_rate: float = Field(ge=0.0, le=1.0)
    intervention_count: int = Field(ge=0)
    invalid_action_count: int = Field(ge=0)
    blocked_run_count: int = Field(ge=0)
    average_steps: float = Field(ge=0.0)
    new_high_severity_issues: int = Field(default=0, ge=0)


class ExperimentResult(StrictModel):
    experiment_id: str
    candidate_id: str
    baseline_generation: str
    started_at: datetime
    finished_at: datetime
    baseline_results: list[ScenarioResult]
    candidate_results: list[ScenarioResult]
    baseline_metrics: MetricVector
    candidate_metrics: MetricVector
    prediction_matched: bool
    review_passed: bool
    notes: list[str] = Field(default_factory=list)


class GateDecision(StrictModel):
    decision_id: str
    candidate_id: str
    verdict: GateVerdict
    passed_rules: list[str]
    failed_rules: list[str]
    rationale: str
    retained_generation_id: str | None = None

    @model_validator(mode="after")
    def retained_generation_requires_retain(self) -> GateDecision:
        if self.retained_generation_id is not None and self.verdict != GateVerdict.RETAIN:
            raise ValueError("retained_generation_id is valid only for a retain verdict")
        return self


class ArtifactRef(StrictModel):
    """A typed reference to one immutable content-addressed artifact."""

    digest: DigestStr
    model: str

    @field_validator("model")
    @classmethod
    def validate_model_identity(cls, value: str) -> str:
        if (
            not value
            or not value[0].isalpha()
            or not all(character.isalnum() or character == "_" for character in value)
        ):
            raise ValueError("Artifact model identity must be a controlled identifier")
        return value


class RoleRequest(StrictModel):
    request_id: str
    role: AgentRole
    objective: str
    # Values are self-contained JSON, never paths that a child process can use
    # to obtain mutable workspace state.
    input_artifacts: dict[str, JsonValue]
    output_contract: dict[str, JsonValue]
    constraints: list[str] = Field(default_factory=list)

    _validate_ids = field_validator("request_id", "objective")(_nonblank)
    _validate_inputs = field_validator("input_artifacts", "output_contract", mode="before")(
        _json_value
    )


class RoleResponse(StrictModel):
    response_id: str
    request_id: str
    role: AgentRole
    success: bool
    output: dict[str, JsonValue]
    notes: list[str] = Field(default_factory=list)

    _validate_ids = field_validator("response_id", "request_id")(_nonblank)
    _validate_output = field_validator("output", mode="before")(_json_value)


class RoleTranscript(StrictModel):
    """Content-addressed references for all bytes and typed role values."""

    invocation_id: str
    request_id: str
    role: AgentRole
    response_id: str | None = None
    request_ref: ArtifactRef
    response_ref: ArtifactRef | None = None
    typed_output_ref: ArtifactRef | None = None
    stdout_ref: ArtifactRef | None = None
    stderr_ref: ArtifactRef | None = None
    input_digest: DigestStr
    output_contract_digest: DigestStr
    output_digest: DigestStr | None = None
    provider: str
    model: str
    backend: str
    authority_id: str
    outcome: RoleOutcome
    timeout_seconds: float
    process_status: int | None = None
    failure: str | None = None

    _validate_ids = field_validator(
        "invocation_id", "request_id", "provider", "model", "backend", "authority_id"
    )(_nonblank)

    @field_validator("timeout_seconds")
    @classmethod
    def validate_timeout(cls, value: float) -> float:
        if not isfinite(value) or value <= 0:
            raise ValueError("timeout_seconds must be positive and finite")
        return value

    @model_validator(mode="after")
    def validate_outcome(self) -> RoleTranscript:
        _validate_role_refs(
            request_ref=self.request_ref,
            response_ref=self.response_ref,
            stdout_ref=self.stdout_ref,
            stderr_ref=self.stderr_ref,
        )
        _validate_outcome_fields(
            outcome=self.outcome,
            response_ref=self.response_ref,
            typed_output_ref=self.typed_output_ref,
            output_digest=self.output_digest,
            response_id=self.response_id,
            process_status=self.process_status,
            failure=self.failure,
        )
        return self


class RoleInvocation(StrictModel):
    """Append-only ledger record for every attempted role call."""

    invocation_id: str
    request_id: str
    role: AgentRole
    provider: str
    model: str
    backend: str
    authority_id: str
    outcome: RoleOutcome
    response_id: str | None = None
    request_ref: ArtifactRef
    transcript_ref: ArtifactRef
    response_ref: ArtifactRef | None = None
    typed_output_ref: ArtifactRef | None = None
    stdout_ref: ArtifactRef | None = None
    stderr_ref: ArtifactRef | None = None
    input_digest: DigestStr
    output_contract_digest: DigestStr
    output_digest: DigestStr | None = None
    timeout_seconds: float
    process_status: int | None = None
    failure: str | None = None

    _validate_ids = field_validator(
        "invocation_id", "request_id", "provider", "model", "backend", "authority_id"
    )(_nonblank)

    @field_validator("timeout_seconds")
    @classmethod
    def validate_timeout(cls, value: float) -> float:
        if not isfinite(value) or value <= 0:
            raise ValueError("timeout_seconds must be positive and finite")
        return value

    @model_validator(mode="after")
    def validate_outcome(self) -> RoleInvocation:
        _validate_role_refs(
            request_ref=self.request_ref,
            response_ref=self.response_ref,
            stdout_ref=self.stdout_ref,
            stderr_ref=self.stderr_ref,
        )
        if self.transcript_ref.model != "RoleTranscript":
            raise ValueError("transcript_ref must reference RoleTranscript")
        _validate_outcome_fields(
            outcome=self.outcome,
            response_ref=self.response_ref,
            typed_output_ref=self.typed_output_ref,
            output_digest=self.output_digest,
            response_id=self.response_id,
            process_status=self.process_status,
            failure=self.failure,
        )
        return self


def _validate_role_refs(
    *,
    request_ref: ArtifactRef,
    response_ref: ArtifactRef | None,
    stdout_ref: ArtifactRef | None,
    stderr_ref: ArtifactRef | None,
) -> None:
    expected = {
        "request_ref": (request_ref, "RoleRequest"),
        "response_ref": (response_ref, "RoleResponse"),
        "stdout_ref": (stdout_ref, "RoleStdout"),
        "stderr_ref": (stderr_ref, "RoleStderr"),
    }
    for name, (reference, model) in expected.items():
        if reference is not None and reference.model != model:
            raise ValueError(f"{name} must reference {model}")


def _validate_outcome_fields(
    *,
    outcome: RoleOutcome,
    response_ref: ArtifactRef | None,
    typed_output_ref: ArtifactRef | None,
    output_digest: str | None,
    response_id: str | None,
    process_status: int | None,
    failure: str | None,
) -> None:
    if isinstance(process_status, bool):
        raise ValueError("process_status must be an integer or null")
    if typed_output_ref is not None and output_digest != typed_output_ref.digest:
        raise ValueError("output_digest must match typed_output_ref")
    if (response_ref is None) != (response_id is None):
        raise ValueError("response_ref and response_id must be present together")
    if outcome == RoleOutcome.SUCCESS:
        if response_ref is None or typed_output_ref is None or output_digest is None:
            raise ValueError("successful role outcome requires response and typed output refs")
        if response_id is None or not response_id.strip() or failure is not None:
            raise ValueError("successful role outcome has invalid response/failure fields")
        if process_status not in {None, 0}:
            raise ValueError("successful role outcome cannot have a failing process status")
        return

    if failure is None or not failure.strip():
        raise ValueError("failed role outcome requires failure detail")
    if outcome == RoleOutcome.SEMANTIC_LINK_FAILURE:
        if response_ref is None or typed_output_ref is None or output_digest is None:
            raise ValueError("semantic-link failure requires response and typed output refs")
        if process_status not in {None, 0}:
            raise ValueError("semantic-link failure cannot have a failing process status")
        return
    if typed_output_ref is not None or output_digest is not None:
        raise ValueError("non-semantic failure cannot retain typed output")
    if outcome in {
        RoleOutcome.REQUEST_MISMATCH,
        RoleOutcome.ROLE_MISMATCH,
        RoleOutcome.UNSUCCESSFUL_RESPONSE,
        RoleOutcome.INVALID_TYPED_OUTPUT,
    }:
        if response_ref is None:
            raise ValueError(f"{outcome.value} requires a parsed response")
        if process_status not in {None, 0}:
            raise ValueError(f"{outcome.value} cannot have a failing process status")
    elif outcome == RoleOutcome.NONZERO_EXIT:
        if process_status is None or process_status == 0:
            raise ValueError("nonzero-exit outcome requires a nonzero process status")
    elif outcome == RoleOutcome.MALFORMED_ENVELOPE:
        if response_ref is not None or process_status not in {None, 0}:
            raise ValueError("malformed envelope cannot retain a response or failing status")
    elif outcome in {RoleOutcome.TIMEOUT, RoleOutcome.BACKEND_EXCEPTION}:
        if response_ref is not None or process_status is not None:
            raise ValueError(f"{outcome.value} cannot retain a response or process status")


class EvolutionPlan(StrictModel):
    diagnostic_scenarios: list[str]
    revealing_cases: list[str]
    structural_variants: list[str]
    regression_suites: list[str]
    long_horizon_suites: list[str]
    forbidden_literals: list[str] = Field(default_factory=list)


class CycleManifest(StrictModel):
    """Immutable composition identity shared by every stage receipt."""

    manifest_version: Literal["1.0"]
    cycle_id: str
    subject: str
    subject_plugin_api_version: str
    subject_plugin_source: str
    baseline_generation_id: str
    subject_generation_fingerprint: str
    plan_digest: str
    baseline_ref: ArtifactRef
    plan_ref: ArtifactRef
    stage_order: tuple[StageName, ...]
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_stage_order(self) -> CycleManifest:
        if self.stage_order != StageName.ordered():
            raise ValueError("Cycle manifest stage order does not match the public contract")
        return self


class IngestResult(StrictModel):
    cycle_id: str
    subject: str
    generation_id: str
    baseline_ref: ArtifactRef
    plan_ref: ArtifactRef
    capability_ref: ArtifactRef
    run_refs: list[ArtifactRef]
    event_refs: list[ArtifactRef]
    runs: list[RunRecord]


class StageReceipt(StrictModel):
    """Hash-chain node proving one typed stage output and its exact inputs."""

    receipt_version: Literal["1.0"]
    receipt_id: str
    cycle_id: str
    manifest_digest: str
    stage: StageName
    subject: str
    subject_generation_fingerprint: str
    input_refs: dict[str, ArtifactRef]
    output_ref: ArtifactRef
    prior_receipt_digest: str | None = None


class StagePointer(StrictModel):
    """Small atomic workspace pointer; the receipt and output remain immutable."""

    pointer_version: Literal["1.0"]
    cycle_id: str
    stage: StageName
    receipt_digest: str


class CycleResult(StrictModel):
    workspace: str
    baseline_generation: GenerationManifest
    diagnostic_runs: list[RunRecord]
    issue: CapabilityIssue
    investigation: InvestigationReport
    specification: CapabilitySpec
    candidate: CandidateManifest
    review: ReviewReport
    experiment: ExperimentResult
    decision: GateDecision
    retained_generation: GenerationManifest | None = None


class ProbePermissions(StrictModel):
    """Explicit probe sandbox; every operation/effect/path is denied by default."""

    allowed_operations: list[str] = Field(default_factory=list)
    allowed_effects: list[str] = Field(default_factory=list)
    allowed_paths: list[str] = Field(default_factory=list)
    max_steps: int = Field(default=0, ge=0)
    max_bytes: int = Field(default=0, ge=0)
    max_duration_seconds: float = Field(default=0.0, ge=0.0)


class ProbeEvidenceTarget(StrictModel):
    named_uncertainty: str
    hypotheses: list[str]
    required_later_observations: list[str]
    prohibited_inferences: list[str]


class ProbeFilePayload(StrictModel):
    """A builder's in-memory file; the orchestrator owns filesystem publication."""

    path: str
    content: str


class ProbeBuildOutput(StrictModel):
    files: list[ProbeFilePayload]
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProbePlan(StrictModel):
    probe_id: str
    issue_id: str
    parent_generation: str
    subject: str
    investigation_ref: ArtifactRef
    capability_manifest_ref: ArtifactRef
    baseline_capability_manifest_digest: DigestStr
    fixture_id: str
    evidence_target: ProbeEvidenceTarget
    permissions: ProbePermissions
    initial_observation: dict[str, Any] = Field(default_factory=dict)
    initial_observation_ref: ArtifactRef | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProbeCandidateManifest(StrictModel):
    """Probe code identity. This intentionally has no spec/claimed/retained fields."""

    candidate_id: str
    probe_id: str
    parent_generation: str
    issue_id: str
    kind: Literal["probe"] = "probe"
    created_at: datetime = Field(default_factory=utc_now)
    workspace_path: str
    source_digest: DigestStr
    artifact_digests: dict[str, DigestStr] = Field(default_factory=dict)
    changed_files: list[str]
    file_digests: dict[str, DigestStr] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProbeReviewReport(StrictModel):
    review_id: str
    candidate_id: str
    probe_id: str
    passed: bool
    checks: dict[str, bool]
    findings: list[ReviewFinding] = Field(default_factory=list)
    reviewed_files: list[str] = Field(default_factory=list)


class ProbeDispatchEvidence(StrictModel):
    operation: str
    effect: str
    target_id: str
    accepted: bool
    changed: bool
    steps: int = Field(default=1, ge=0)
    receipt: dict[str, Any]
    completeness: Completeness


class ProbeObservationEvidence(StrictModel):
    container_id: str
    inspected: bool
    exposed_item_ids: list[str]
    observation: dict[str, Any]
    completeness: Completeness


class ProbeEvaluation(StrictModel):
    evaluation_id: str
    candidate_id: str
    probe_id: str
    named_uncertainty: str
    initial_observation_ref: ArtifactRef
    dispatch_evidence_ref: ArtifactRef | None
    later_observation_ref: ArtifactRef | None
    completeness: Completeness
    dispatch_evidence: ProbeDispatchEvidence | None = None
    later_observation: ProbeObservationEvidence | None = None
    initial_capability_manifest_ref: ArtifactRef
    initial_capability_manifest_digest: DigestStr
    initial_capability_manifest_bytes_digest: DigestStr
    final_capability_manifest_ref: ArtifactRef
    final_capability_manifest_digest: DigestStr
    final_capability_manifest_bytes_digest: DigestStr
    capability_manifest_unchanged: bool = False
    notes: list[str] = Field(default_factory=list)

    @property
    def accepted_receipt(self) -> bool:
        return bool(self.dispatch_evidence is not None and self.dispatch_evidence.accepted)

    @property
    def independent_observation(self) -> bool:
        return bool(
            self.later_observation is not None
            and self.later_observation.completeness == Completeness.COMPLETE
        )


class ProbeDisposition(StrictModel):
    disposition_id: str
    candidate_id: str
    probe_id: str
    named_uncertainty: str
    disposition: ProbeDispositionKind
    rationale: str


class ProbeManifest(StrictModel):
    manifest_version: Literal["1.0"]
    probe_id: str
    subject: str
    baseline_generation_id: str
    baseline_ref: ArtifactRef
    issue_ref: ArtifactRef
    investigation_ref: ArtifactRef
    capability_manifest_ref: ArtifactRef
    baseline_capability_manifest_digest: DigestStr
    stage_order: tuple[ProbeStageName, ...]
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_stage_order(self) -> ProbeManifest:
        if self.stage_order != ProbeStageName.ordered():
            raise ValueError("Probe manifest stage order does not match the probe contract")
        return self


class ProbeStageReceipt(StrictModel):
    receipt_version: Literal["1.0"]
    receipt_id: str
    probe_id: str
    manifest_digest: DigestStr
    stage: ProbeStageName
    subject: str
    input_refs: dict[str, ArtifactRef]
    output_ref: ArtifactRef
    prior_receipt_digest: DigestStr | None = None


class ProbeStagePointer(StrictModel):
    pointer_version: Literal["1.0"]
    probe_id: str
    stage: ProbeStageName
    receipt_digest: DigestStr


class ProbeRequiredResult(StrictModel):
    issue_id: str
    resolution: Literal["build_probe"] = "build_probe"
    message: str


class ProbeResult(StrictModel):
    workspace: str
    manifest: ProbeManifest
    plan: ProbePlan
    candidate: ProbeCandidateManifest
    review: ProbeReviewReport
    evaluation: ProbeEvaluation
    disposition: ProbeDisposition
