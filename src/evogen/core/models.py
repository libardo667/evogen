from __future__ import annotations

from datetime import UTC, datetime
from math import isfinite
from pathlib import Path
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


class SubjectConformanceFixture(StrictModel):
    """Data-only values a subject supplies to exercise generic conformance."""

    scenario_ids: list[str] = Field(min_length=2)
    seeds: list[StrictInt] = Field(min_length=2)
    issue: CapabilityIssue
    specification: CapabilitySpec

    @field_validator("scenario_ids")
    @classmethod
    def validate_scenario_ids(cls, value: list[str]) -> list[str]:
        if any(not _nonblank(item) for item in value):
            raise ValueError("Conformance scenario IDs must be nonblank")
        if len(set(value)) != len(value):
            raise ValueError("Conformance scenario IDs must be unique")
        return value

    @field_validator("seeds")
    @classmethod
    def validate_seeds(cls, value: list[int]) -> list[int]:
        if len(set(value)) != len(value):
            raise ValueError("Conformance seeds must be unique")
        return value


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
    workspace_file_digests: dict[str, str]
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
    seed: StrictInt
    repeat_index: StrictInt = Field(ge=0)
    elapsed_seconds: float = Field(ge=0.0)
    success: bool
    steps: int
    interventions: int
    invalid_actions: int
    blocked: bool
    termination: str
    run_id: str
    trace_digest: str

    @field_validator("elapsed_seconds")
    @classmethod
    def validate_elapsed_seconds(cls, value: float) -> float:
        if not isfinite(value) or value < 0:
            raise ValueError("elapsed_seconds must be finite and non-negative")
        return value


EvaluationCategory: TypeAlias = Literal["revealing", "variant", "regression", "long_horizon"]


class EvaluationCase(StrictModel):
    scenario_id: str
    category: EvaluationCategory
    seeds: list[StrictInt] = Field(min_length=1)
    repeat_count: StrictInt = Field(ge=1)
    per_run_wall_clock_ceiling_seconds: float

    @field_validator("scenario_id")
    @classmethod
    def validate_scenario_id(cls, value: str) -> str:
        return _nonblank(value)

    @field_validator("seeds")
    @classmethod
    def validate_seeds(cls, value: list[int]) -> list[int]:
        if len(set(value)) != len(value):
            raise ValueError("Evaluation case seeds must be unique")
        return value

    @field_validator("per_run_wall_clock_ceiling_seconds")
    @classmethod
    def validate_run_ceiling(cls, value: float) -> float:
        if not isfinite(value) or value <= 0:
            raise ValueError("per-run wall-clock ceiling must be finite and positive")
        return value


class ProtectedPathHash(StrictModel):
    logical_name: str
    absolute_path: str
    sha256: DigestStr

    @field_validator("logical_name")
    @classmethod
    def validate_logical_name(cls, value: str) -> str:
        return _nonblank(value)

    @field_validator("absolute_path")
    @classmethod
    def validate_absolute_path(cls, value: str) -> str:
        value = _nonblank(value)
        if not Path(value).is_absolute():
            raise ValueError("Protected path must be absolute")
        return value


class EvaluationSuiteManifest(StrictModel):
    """Frozen, content-addressed authority for one complete evaluation."""

    manifest_version: Literal["1.0"] = "1.0"
    suite_id: str
    revealing_cases: list[EvaluationCase] = Field(min_length=1)
    structural_variants: list[EvaluationCase] = Field(min_length=1)
    regression_suites: list[EvaluationCase] = Field(min_length=1)
    long_horizon_suites: list[EvaluationCase] = Field(min_length=1)
    total_wall_clock_ceiling_seconds: float
    evaluator_version: str
    evaluator: ArtifactRef
    evaluator_protected_path: str
    environment_artifacts: dict[str, ArtifactRef] = Field(min_length=1)
    protected_paths: list[ProtectedPathHash] = Field(min_length=1)
    subject_metric_namespace: str
    candidate_tests_authoritative: Literal[False] = False

    @field_validator("suite_id", "evaluator_version", "subject_metric_namespace")
    @classmethod
    def validate_nonblank_fields(cls, value: str) -> str:
        return _nonblank(value)

    @field_validator("total_wall_clock_ceiling_seconds")
    @classmethod
    def validate_total_ceiling(cls, value: float) -> float:
        if not isfinite(value) or value <= 0:
            raise ValueError("total wall-clock ceiling must be finite and positive")
        return value

    @field_validator("environment_artifacts")
    @classmethod
    def validate_environment_artifacts(
        cls, value: dict[str, ArtifactRef]
    ) -> dict[str, ArtifactRef]:
        if any(not _nonblank(name) for name in value):
            raise ValueError("Environment artifact names must be nonblank")
        return value

    @model_validator(mode="after")
    def validate_authority(self) -> EvaluationSuiteManifest:
        lists = (
            ("revealing", self.revealing_cases),
            ("variant", self.structural_variants),
            ("regression", self.regression_suites),
            ("long_horizon", self.long_horizon_suites),
        )
        identifiers: list[str] = []
        for expected_category, cases in lists:
            for case in cases:
                if case.category != expected_category:
                    raise ValueError(
                        f"Case {case.scenario_id!r} category does not match "
                        f"{expected_category!r} list"
                    )
                identifiers.append(case.scenario_id)
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("Evaluation suite scenario IDs must be unique")
        names = [path.logical_name for path in self.protected_paths]
        if len(set(names)) != len(names):
            raise ValueError("Protected path logical names must be unique")
        if self.evaluator_protected_path not in names:
            raise ValueError("evaluator_protected_path must name one protected path")
        protected = next(
            path
            for path in self.protected_paths
            if path.logical_name == self.evaluator_protected_path
        )
        if protected.sha256 != self.evaluator.digest:
            raise ValueError("Evaluator artifact digest must match its protected path")
        for name, reference in self.environment_artifacts.items():
            if name in names:
                protected = next(path for path in self.protected_paths if path.logical_name == name)
                if protected.sha256 != reference.digest:
                    raise ValueError(f"Environment artifact {name!r} differs from protected path")
        return self


class EvaluationAuthoritySnapshot(StrictModel):
    suite_ref: ArtifactRef
    suite_id: str
    evaluator_version: str
    protected_path_digests: dict[str, DigestStr]
    timestamp: datetime = Field(default_factory=utc_now)

    @field_validator("suite_id", "evaluator_version")
    @classmethod
    def validate_snapshot_ids(cls, value: str) -> str:
        return _nonblank(value)

    @field_validator("protected_path_digests")
    @classmethod
    def validate_snapshot_paths(cls, value: dict[str, str]) -> dict[str, str]:
        if any(not _nonblank(key) for key in value):
            raise ValueError("Snapshot protected path names must be nonblank")
        return value

    @property
    def captured_at(self) -> datetime:
        return self.timestamp


class SubjectMetricVector(StrictModel):
    namespace: str
    metrics: dict[str, JsonValue]

    @field_validator("namespace")
    @classmethod
    def validate_namespace(cls, value: str) -> str:
        return _nonblank(value)

    @field_validator("metrics", mode="before")
    @classmethod
    def validate_metrics(cls, value: object) -> JsonValue:
        return _json_value(value)


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


class EvaluationOutcome(StrictModel):
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
    baseline_subject_metrics: list[SubjectMetricVector] = Field(min_length=1)
    candidate_subject_metrics: list[SubjectMetricVector] = Field(min_length=1)
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_subject_metric_symmetry(self) -> EvaluationOutcome:
        baseline_names = [metric.namespace for metric in self.baseline_subject_metrics]
        candidate_names = [metric.namespace for metric in self.candidate_subject_metrics]
        if len(set(baseline_names)) != len(baseline_names):
            raise ValueError("Baseline subject metric namespaces must be unique")
        if len(set(candidate_names)) != len(candidate_names):
            raise ValueError("Candidate subject metric namespaces must be unique")
        if baseline_names != candidate_names:
            raise ValueError("Baseline and candidate subject metric namespaces must be symmetric")
        return self


ConformanceStatus: TypeAlias = Literal["pass", "fail", "blocked"]


class SubjectCheck(StrictModel):
    """One host-owned conformance boundary result."""

    boundary_id: str
    status: ConformanceStatus
    message: str
    evidence: dict[str, JsonValue] = Field(min_length=1)
    blocked_dependency: str | None = None

    @field_validator("boundary_id", "message")
    @classmethod
    def validate_check_text(cls, value: str) -> str:
        return _nonblank(value)

    @model_validator(mode="after")
    def validate_blocked_dependency(self) -> SubjectCheck:
        if self.status == "blocked" and not self.blocked_dependency:
            raise ValueError("Blocked checks require a blocked dependency")
        if self.status != "blocked" and self.blocked_dependency is not None:
            raise ValueError("Only blocked checks may name a blocked dependency")
        return self


class SubjectDiagnostic(StrictModel):
    """Additional, non-authoritative evidence returned by a subject doctor."""

    code: str
    message: str
    evidence: dict[str, JsonValue] = Field(default_factory=dict)
    boundary_id: str | None = None

    @field_validator("code", "message")
    @classmethod
    def validate_diagnostic_text(cls, value: str) -> str:
        return _nonblank(value)


class SubjectConformanceReport(StrictModel):
    subject: str
    api_version: str
    checks: list[SubjectCheck] = Field(min_length=1)
    diagnostics: BoundedCollection[SubjectDiagnostic]
    passed: bool = False
    status: Literal["pass", "fail"] = "fail"

    @field_validator("subject", "api_version")
    @classmethod
    def validate_report_identity(cls, value: str) -> str:
        return _nonblank(value)

    @model_validator(mode="after")
    def derive_status(self) -> SubjectConformanceReport:
        derived = (
            all(check.status == "pass" for check in self.checks)
            and self.diagnostics.completeness == Completeness.COMPLETE
            and not self.diagnostics.items
        )
        object.__setattr__(self, "passed", derived)
        object.__setattr__(self, "status", "pass" if derived else "fail")
        return self

    @property
    def failed(self) -> bool:
        return not self.passed


class ExperimentResult(EvaluationOutcome):
    evaluation_suite_ref: ArtifactRef
    pre_authority_snapshot: EvaluationAuthoritySnapshot
    post_authority_snapshot: EvaluationAuthoritySnapshot


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

    manifest_version: Literal["1.1"]
    cycle_id: str
    subject: str
    subject_plugin_api_version: str
    subject_plugin_source: str
    baseline_generation_id: str
    subject_generation_fingerprint: str
    plan_digest: str
    baseline_ref: ArtifactRef
    plan_ref: ArtifactRef
    evaluation_suite_ref: ArtifactRef
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
