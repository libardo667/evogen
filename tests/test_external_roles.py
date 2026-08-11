from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

from evogen.adapters.agents import (
    JsonStdioRoleBackend,
    RawRoleExecution,
    RoleInvocationError,
    RoleInvoker,
)
from evogen.adapters.role_adapters import (
    AdversarialReviewerAdapter,
    CapabilityArchitectAdapter,
    DiagnosticianAdapter,
    InvestigatorAdapter,
    ReleaseStewardAdapter,
    TraceAnalystAdapter,
)
from evogen.core.enums import (
    AgentRole,
    FailureLayer,
    GateVerdict,
    ResolutionKind,
    RoleOutcome,
    StageName,
)
from evogen.core.ids import new_id, sha256_bytes, stable_digest
from evogen.core.models import (
    ArtifactRef,
    CandidateManifest,
    CapabilityIssue,
    CapabilityManifest,
    CapabilitySpec,
    DistilledTrace,
    EvaluationAuthoritySnapshot,
    ExperimentResult,
    GateDecision,
    GenerationManifest,
    InvestigationReport,
    IssueClassification,
    MetricVector,
    ReviewReport,
    RoleRequest,
    RoleResponse,
    StagePointer,
    StageReceipt,
    SubjectMetricVector,
)
from evogen.demo.microworld.cycle import MicroworldEvolutionCycle
from evogen.demo.microworld.scenarios import get_scenario
from evogen.evolution.orchestrator import EvolutionOrchestrator
from evogen.storage.artifacts import ArtifactStore
from evogen.storage.ledger import Ledger


class _Backend:
    def __init__(self, values: dict[AgentRole, dict[str, Any]]) -> None:
        self.values = values
        self.requests: list[RoleRequest] = []

    timeout_seconds = 5.0

    def execute(self, request: RoleRequest) -> RawRoleExecution:
        self.requests.append(request)
        response = RoleResponse(
            response_id=new_id("response"),
            request_id=request.request_id,
            role=request.role,
            success=True,
            output=self.values[request.role],
        )
        return RawRoleExecution(response, None, None, 0, RoleOutcome.SUCCESS)


class _ReturningBackend:
    timeout_seconds = 2.0

    def __init__(self, value: object) -> None:
        self.value = value

    def execute(self, request: RoleRequest) -> object:
        del request
        return self.value


class _ExplodingBackend:
    timeout_seconds = 2.0

    def execute(self, request: RoleRequest) -> RawRoleExecution:
        del request
        raise RuntimeError("duck backend exploded")


def _clone_workspace(source: Path, destination: Path) -> Path:
    """Clone a prepared workspace without changing any of its bytes."""
    shutil.copytree(source, destination)
    return destination


def _cas_digests(workspace: Path) -> set[str]:
    objects = workspace / "artifacts" / "sha256"
    return {
        path.parent.name + path.name
        for path in objects.glob("??/*")
        if path.is_file() and len(path.parent.name) == 2 and len(path.name) == 62
    }


def _ingest_snapshot(workspace: Path, artifacts: ArtifactStore) -> tuple[Any, ...]:
    pointer_path = workspace / "stages" / "ingest.pointer.json"
    pointer_bytes = pointer_path.read_bytes()
    pointer = artifacts.read_pointer(pointer_path, StagePointer)
    receipt_ref = pointer.receipt_digest
    receipt_bytes = artifacts.read_bytes(receipt_ref)
    receipt = artifacts.read_model(
        ArtifactRef(digest=receipt_ref, model="StageReceipt"), StageReceipt
    )
    output_bytes = artifacts.read_bytes(receipt.output_ref.digest)
    input_bytes = tuple(
        (name, reference.digest, reference.model, artifacts.read_bytes(reference.digest))
        for name, reference in sorted(receipt.input_refs.items())
    )
    return (
        pointer_bytes,
        pointer.stage,
        pointer.receipt_digest,
        receipt_bytes,
        receipt.input_refs,
        receipt.output_ref,
        output_bytes,
        input_bytes,
    )


def _clone_orchestrator(
    source: MicroworldEvolutionCycle,
    workspace: Path,
    *,
    trace_analyst: Any,
    ledger: Ledger,
    artifacts: ArtifactStore,
) -> EvolutionOrchestrator:
    original = source.composition
    original_stages = original.orchestrator.stages
    return EvolutionOrchestrator(
        workspace=workspace,
        artifacts=artifacts,
        ledger=ledger,
        runner=original.runner,
        investigator=original.investigator,
        builder=original.builder,
        reviewer=original.reviewer,
        evaluator=original.evaluator,
        materializer=original.materializer,
        baseline=original.bootstrap.baseline,
        plan=original.bootstrap.plan,
        evaluation_suite=original.bootstrap.evaluation_suite,
        subject_plugin_name=original_stages.subject_plugin_name,
        subject_plugin_api_version=original_stages.subject_plugin_api_version,
        subject_plugin_source=original_stages.subject_plugin_source,
        trace_analyst=trace_analyst,
    )


def _issue() -> CapabilityIssue:
    return CapabilityIssue(
        issue_id="issue-1",
        subject_generation="gen-1",
        title="missing effect",
        symptom_summary="blocked",
        classification=IssueClassification(
            primary=FailureLayer.INSUFFICIENT_EVIDENCE,
            confidence=0.5,
            rationale="unknown",
        ),
        supporting_evidence=[],
        proposed_resolution=ResolutionKind.ADD_CAPABILITY,
        prediction="effect appears",
    )


def test_all_six_typed_adapters_share_retained_executor(tmp_path: Path) -> None:
    issue = _issue()
    investigation = InvestigationReport(
        report_id="report-1",
        issue_id=issue.issue_id,
        inspected_sources=["source"],
        candidate_operations=[],
        conclusion="unknown",
    )
    spec = CapabilitySpec(
        spec_id="spec-1",
        issue_id=issue.issue_id,
        parent_generation="gen-1",
        capability_name="effect",
        purpose="effect",
        semantic_effects=["effect"],
        owner_component="plugin",
        input_schema={},
        output_schema={},
        applicability="fresh",
        binding_rules=[],
        execution_route="subject.effect",
        completion_evidence=[],
        non_goals=[],
        prediction="effect appears",
        revealing_cases=[],
        structural_variants=[],
        regression_suites=[],
        long_horizon_suites=[],
    )
    trace = DistilledTrace(
        generation_id="gen-1",
        run_ids=[],
        scenario_ids=[],
        existing_capabilities=[],
        existing_semantic_effects=[],
        signatures=[],
        event_count=0,
    )
    generation = GenerationManifest(
        generation_id="gen-1",
        subject="test",
        source_ref="source",
        capability_manifest_digest="0" * 64,
    )
    candidate_root = tmp_path / "candidate"
    candidate_root.mkdir()
    candidate_path = candidate_root / "candidate-1"
    candidate_path.mkdir()
    source = b"VALUE = 1\n"
    (candidate_path / "plugin.py").write_bytes(source)
    candidate = CandidateManifest(
        candidate_id="candidate-1",
        parent_generation="gen-1",
        issue_id=issue.issue_id,
        spec_id=spec.spec_id,
        workspace_path=str(candidate_path),
        source_digest=stable_digest({"plugin.py": sha256_bytes(source)}),
        artifact_digests={},
        changed_files=["plugin.py"],
        file_digests={"plugin.py": sha256_bytes(source)},
        claimed_capabilities=[],
        workspace_file_digests={"plugin.py": sha256_bytes(source)},
    )
    review = ReviewReport(
        review_id="review-1", candidate_id=candidate.candidate_id, passed=True, checks={}
    )
    metrics = MetricVector(
        revealing_success_rate=1,
        variant_success_rate=1,
        regression_success_rate=1,
        long_horizon_success_rate=1,
        intervention_count=0,
        invalid_action_count=0,
        blocked_run_count=0,
        average_steps=1,
    )
    experiment = ExperimentResult(
        experiment_id="experiment-1",
        candidate_id=candidate.candidate_id,
        baseline_generation="gen-1",
        started_at=generation.created_at,
        finished_at=generation.created_at,
        baseline_results=[],
        candidate_results=[],
        baseline_metrics=metrics,
        candidate_metrics=metrics,
        prediction_matched=True,
        review_passed=True,
        baseline_subject_metrics=[SubjectMetricVector(namespace="test", metrics={})],
        candidate_subject_metrics=[SubjectMetricVector(namespace="test", metrics={})],
        evaluation_suite_ref=ArtifactRef(digest="a" * 64, model="EvaluationSuiteManifest"),
        pre_authority_snapshot=EvaluationAuthoritySnapshot(
            suite_ref=ArtifactRef(digest="a" * 64, model="EvaluationSuiteManifest"),
            suite_id="suite", evaluator_version="v1", protected_path_digests={}
        ),
        post_authority_snapshot=EvaluationAuthoritySnapshot(
            suite_ref=ArtifactRef(digest="a" * 64, model="EvaluationSuiteManifest"),
            suite_id="suite", evaluator_version="v1", protected_path_digests={}
        ),
    )
    decision = GateDecision(
        decision_id="decision-1",
        candidate_id=candidate.candidate_id,
        verdict=GateVerdict.REJECT,
        passed_rules=[],
        failed_rules=["x"],
        rationale="x",
    )
    values = {
        AgentRole.TRACE_ANALYST: trace.model_dump(mode="json"),
        AgentRole.DIAGNOSTICIAN: issue.model_dump(mode="json"),
        AgentRole.INVESTIGATOR: investigation.model_dump(mode="json"),
        AgentRole.CAPABILITY_ARCHITECT: spec.model_dump(mode="json"),
        AgentRole.ADVERSARIAL_REVIEWER: review.model_dump(mode="json"),
        AgentRole.RELEASE_STEWARD: decision.model_dump(mode="json"),
    }
    store = ArtifactStore(tmp_path / "artifacts")
    ledger = Ledger(tmp_path / "ledger.sqlite3")
    backend = _Backend(values)

    def invoke(role: AgentRole, adapter_factory: Any) -> Any:
        invoker: RoleInvoker[Any] = RoleInvoker(
            backend=backend,
            artifacts=store,
            ledger=ledger,
            provider="test-provider",
            model="test-model",
            authority_id="test-authority",
        )
        return adapter_factory(invoker)

    assert invoke(AgentRole.TRACE_ANALYST, TraceAnalystAdapter).distill(
        generation_id="gen-1",
        events=[],
        capabilities=CapabilityManifest(generation_id="gen-1", capabilities=[]),
    ) == trace
    assert invoke(AgentRole.DIAGNOSTICIAN, DiagnosticianAdapter).diagnose(trace) == issue
    assert invoke(AgentRole.INVESTIGATOR, InvestigatorAdapter).investigate(issue) == investigation
    assert invoke(AgentRole.CAPABILITY_ARCHITECT, CapabilityArchitectAdapter).specify(
        issue=issue,
        investigation=investigation,
        revealing_cases=[],
        structural_variants=[],
        regression_suites=[],
        long_horizon_suites=[],
    ) == spec
    assert (
        invoke(AgentRole.ADVERSARIAL_REVIEWER, AdversarialReviewerAdapter).review(candidate)
        == review
    )
    assert (
        invoke(AgentRole.RELEASE_STEWARD, ReleaseStewardAdapter).recommend(experiment)
        == decision
    )
    assert len(ledger.list_role_invocations(store)) == 6
    reopened = Ledger(tmp_path / "ledger.sqlite3")
    assert len(reopened.list_role_invocations(store)) == 6


def test_microworld_review_forbids_every_scenario_and_target_literal(
    tmp_path: Path,
) -> None:
    prepared = MicroworldEvolutionCycle.prepare(tmp_path / "prepared", clean=True)
    plan = prepared.composition.bootstrap.plan
    scenario_ids = set(
        [
            *plan.diagnostic_scenarios,
            *plan.revealing_cases,
            *plan.structural_variants,
            *plan.regression_suites,
            *plan.long_horizon_suites,
        ]
    )
    expected = scenario_ids | {
        get_scenario(identifier).target_item_id for identifier in scenario_ids
    }
    assert expected <= set(plan.forbidden_literals)


def test_json_stdio_failures_are_retained_and_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ArtifactStore(tmp_path / "artifacts")
    ledger = Ledger(tmp_path / "ledger.sqlite3")
    request = RoleRequest(
        request_id="request-1",
        role=AgentRole.TRACE_ANALYST,
        objective="test",
        input_artifacts={"value": "self-contained"},
        output_contract=DistilledTrace.model_json_schema(),
    )
    valid = {
        "response_id": "response-1",
        "request_id": request.request_id,
        "role": request.role.value,
        "success": True,
        "output": {
            "generation_id": "gen-1",
            "run_ids": [],
            "scenario_ids": [],
            "existing_capabilities": [],
            "existing_semantic_effects": [],
            "signatures": [],
            "event_count": 0,
        },
        "notes": ["This prose is not the typed result."],
    }
    cases = [
        (f"import json; print(json.dumps({valid!r}))", "success"),
        ("print('plain prose')", "malformed_envelope"),
        (
            f"import json; print(json.dumps({valid!r})); print('trailing prose')",
            "malformed_envelope",
        ),
        (f"import json,sys; print(json.dumps({valid!r})); sys.exit(3)", "nonzero_exit"),
        ("raise RuntimeError('backend boom')", "nonzero_exit"),
        (
            f"import json; value={valid!r}; del value['response_id']; print(json.dumps(value))",
            "malformed_envelope",
        ),
        (
            f"import json; value={valid!r}; value['extra']=1; print(json.dumps(value))",
            "malformed_envelope",
        ),
        (
            f"import json; value={valid!r}; value['request_id']='wrong'; print(json.dumps(value))",
            "request_mismatch",
        ),
        (
            f"import json; value={valid!r}; "
            "value['role']='diagnostician'; print(json.dumps(value))",
            "role_mismatch",
        ),
        (
            f"import json; value={valid!r}; value['success']=False; print(json.dumps(value))",
            "unsuccessful_response",
        ),
        (
            f"import json; value={valid!r}; value['output']={{}}; print(json.dumps(value))",
            "invalid_typed_output",
        ),
    ]
    for source, outcome in cases:
        backend = JsonStdioRoleBackend([sys.executable, "-c", source])
        invoker: RoleInvoker[Any] = RoleInvoker(
            backend=backend,
            artifacts=store,
            ledger=ledger,
            provider="test-provider",
            model="test-model",
            authority_id="test-authority",
        )
        if outcome == "success":
            assert invoker.invoke(request, DistilledTrace).generation_id == "gen-1"
        else:
            with pytest.raises(RoleInvocationError):
                invoker.invoke(request, DistilledTrace)
        records = ledger.list_role_invocations(store)
        assert records[-1].outcome.value == outcome
        if outcome == "success":
            assert records[-1].typed_output_ref is not None

    timeout_backend = JsonStdioRoleBackend(
        [
            sys.executable,
            "-c",
            "import sys,time; print('partial-out'); "
            "print('partial-err', file=sys.stderr); "
            "sys.stdout.flush(); sys.stderr.flush(); time.sleep(1)",
        ],
        timeout_seconds=0.05,
    )
    timeout_invoker: RoleInvoker[Any] = RoleInvoker(
        backend=timeout_backend,
        artifacts=store,
        ledger=ledger,
        provider="test-provider",
        model="test-model",
        authority_id="test-authority-timeout",
    )
    with pytest.raises(RoleInvocationError):
        timeout_invoker.invoke(request, DistilledTrace)
    timeout_record = ledger.list_role_invocations(store)[-1]
    assert timeout_record.outcome.value == "timeout"
    assert timeout_record.timeout_seconds == 0.05
    assert timeout_record.stdout_ref is not None
    assert store.read_bytes(timeout_record.stdout_ref.digest) == b"partial-out\n"
    assert timeout_record.stderr_ref is not None
    assert store.read_bytes(timeout_record.stderr_ref.digest) == b"partial-err\n"

    missing_backend = JsonStdioRoleBackend([str(tmp_path / "does-not-exist")])
    missing_invoker: RoleInvoker[Any] = RoleInvoker(
        backend=missing_backend,
        artifacts=store,
        ledger=ledger,
        provider="test-provider",
        model="test-model",
        authority_id="test-authority-oserror",
    )
    with pytest.raises(RoleInvocationError):
        missing_invoker.invoke(request, DistilledTrace)
    assert ledger.list_role_invocations(store)[-1].outcome.value == "backend_exception"

    monkeypatch.setenv("EVOGEN_SENTINEL", "ambient-secret-must-not-cross")
    secret_backend = JsonStdioRoleBackend(
        [sys.executable, "-c", "import os; print(os.getenv('EVOGEN_SENTINEL', 'missing'))"]
    )
    secret_invoker: RoleInvoker[Any] = RoleInvoker(
        backend=secret_backend,
        artifacts=store,
        ledger=ledger,
        provider="test-provider",
        model="test-model",
        authority_id="test-authority-secret",
    )
    with pytest.raises(RoleInvocationError):
        secret_invoker.invoke(request, DistilledTrace)
    secret_record = ledger.list_role_invocations(store)[-1]
    assert secret_record.stderr_ref is not None
    assert store.read_bytes(secret_record.stderr_ref.digest) == b""
    assert secret_record.stdout_ref is not None
    assert store.read_bytes(secret_record.stdout_ref.digest) == b"missing\n"


def test_generic_backend_results_are_reclassified_and_always_retained(
    tmp_path: Path,
) -> None:
    store = ArtifactStore(tmp_path / "artifacts")
    ledger = Ledger(tmp_path / "ledger.sqlite3")
    request = RoleRequest(
        request_id="request-generic",
        role=AgentRole.TRACE_ANALYST,
        objective="test generic boundary",
        input_artifacts={},
        output_contract=DistilledTrace.model_json_schema(),
    )
    output = DistilledTrace(
        generation_id="gen-1",
        run_ids=[],
        scenario_ids=[],
        existing_capabilities=[],
        existing_semantic_effects=[],
        signatures=[],
        event_count=0,
    ).model_dump(mode="json")

    def response(**changes: Any) -> RoleResponse:
        values: dict[str, Any] = {
            "response_id": new_id("response"),
            "request_id": request.request_id,
            "role": request.role,
            "success": True,
            "output": output,
        }
        values.update(changes)
        return RoleResponse.model_validate(values)

    raw_values: list[tuple[object, RoleOutcome]] = [
        (
            RawRoleExecution(
                response(request_id="other-request"),
                None,
                None,
                0,
                RoleOutcome.SUCCESS,
            ),
            RoleOutcome.REQUEST_MISMATCH,
        ),
        (
            RawRoleExecution(
                response(role=AgentRole.DIAGNOSTICIAN),
                None,
                None,
                0,
                RoleOutcome.SUCCESS,
            ),
            RoleOutcome.ROLE_MISMATCH,
        ),
        (
            RawRoleExecution(
                response(success=False), None, None, 0, RoleOutcome.SUCCESS
            ),
            RoleOutcome.UNSUCCESSFUL_RESPONSE,
        ),
        (object(), RoleOutcome.BACKEND_EXCEPTION),
    ]
    for index, (raw, expected) in enumerate(raw_values):
        invoker: RoleInvoker[Any] = RoleInvoker(
            backend=_ReturningBackend(raw),  # type: ignore[arg-type]
            artifacts=store,
            ledger=ledger,
            provider="test-provider",
            model="test-model",
            authority_id=f"generic-authority-{index}",
        )
        with pytest.raises(RoleInvocationError) as raised:
            invoker.invoke(request, DistilledTrace)
        assert raised.value.invocation.outcome == expected

    exploding: RoleInvoker[Any] = RoleInvoker(
        backend=_ExplodingBackend(),
        artifacts=store,
        ledger=ledger,
        provider="test-provider",
        model="test-model",
        authority_id="generic-authority-exception",
    )
    with pytest.raises(RoleInvocationError) as raised:
        exploding.invoke(request, DistilledTrace)
    assert raised.value.invocation.outcome == RoleOutcome.BACKEND_EXCEPTION
    assert [record.outcome for record in ledger.list_role_invocations(store)] == [
        RoleOutcome.REQUEST_MISMATCH,
        RoleOutcome.ROLE_MISMATCH,
        RoleOutcome.UNSUCCESSFUL_RESPONSE,
        RoleOutcome.BACKEND_EXCEPTION,
        RoleOutcome.BACKEND_EXCEPTION,
    ]


def test_microworld_trace_role_swap_preserves_ingest_and_records_external_provenance(
    tmp_path: Path,
) -> None:
    prepared = MicroworldEvolutionCycle.prepare(tmp_path / "prepared", clean=True)
    prepared.composition.orchestrator.stages.invoke(StageName.INGEST)
    deterministic_workspace = _clone_workspace(prepared.workspace, tmp_path / "deterministic")
    external_workspace = _clone_workspace(prepared.workspace, tmp_path / "external")
    deterministic_artifacts = ArtifactStore(deterministic_workspace / "artifacts")
    deterministic_ledger = Ledger(deterministic_workspace / "evogen.sqlite3")
    external_artifacts = ArtifactStore(external_workspace / "artifacts")
    external_ledger = Ledger(external_workspace / "evogen.sqlite3")

    deterministic_before = _ingest_snapshot(deterministic_workspace, deterministic_artifacts)
    external_before = _ingest_snapshot(external_workspace, external_artifacts)
    assert deterministic_before == external_before

    original_trace_analyst = prepared.composition.orchestrator.stages.trace_analyst
    deterministic_orchestrator = _clone_orchestrator(
        prepared,
        deterministic_workspace,
        trace_analyst=original_trace_analyst,
        artifacts=deterministic_artifacts,
        ledger=deterministic_ledger,
    )
    deterministic_before_cas = _cas_digests(deterministic_workspace)
    deterministic_trace = deterministic_orchestrator.invoke(StageName.DISTILL)
    assert isinstance(deterministic_trace, DistilledTrace)
    assert deterministic_ledger.list_role_invocations(deterministic_artifacts) == []
    deterministic_after = _ingest_snapshot(deterministic_workspace, deterministic_artifacts)
    assert deterministic_after == deterministic_before

    external_backend = _Backend(
        {AgentRole.TRACE_ANALYST: deterministic_trace.model_dump(mode="json")}
    )
    external_invoker: RoleInvoker[DistilledTrace] = RoleInvoker(
        backend=external_backend,
        artifacts=external_artifacts,
        ledger=external_ledger,
        provider="g06-retained-provider",
        model="g06-retained-model",
        authority_id="g06-retained-trace-authority",
    )
    external_trace_analyst = TraceAnalystAdapter(external_invoker)
    external_orchestrator = _clone_orchestrator(
        prepared,
        external_workspace,
        trace_analyst=external_trace_analyst,
        artifacts=external_artifacts,
        ledger=external_ledger,
    )
    external_stages = external_orchestrator.stages
    for name in ("runner", "investigator", "builder", "reviewer", "evaluator", "materializer"):
        assert getattr(external_stages, name) is getattr(prepared.composition, name)
    assert external_stages.baseline == prepared.composition.bootstrap.baseline
    assert external_stages.plan == prepared.composition.bootstrap.plan
    assert external_stages.trace_analyst is external_trace_analyst

    external_before_cas = _cas_digests(external_workspace)
    external_trace_result = external_orchestrator.invoke(StageName.DISTILL)
    assert external_trace_result == deterministic_trace
    assert external_stages.completed_stage(StageName.DISTILL) == deterministic_trace
    assert len(external_backend.requests) == 1
    external_after = _ingest_snapshot(external_workspace, external_artifacts)
    assert external_after == external_before

    deterministic_receipt = deterministic_artifacts.read_model(
        ArtifactRef(
            digest=deterministic_artifacts.read_pointer(
                deterministic_workspace / "stages" / "distill.pointer.json", StagePointer
            ).receipt_digest,
            model="StageReceipt",
        ),
        StageReceipt,
    )
    external_pointer = external_artifacts.read_pointer(
        external_workspace / "stages" / "distill.pointer.json", StagePointer
    )
    external_receipt = external_artifacts.read_model(
        ArtifactRef(digest=external_pointer.receipt_digest, model="StageReceipt"),
        StageReceipt,
    )
    assert external_receipt.input_refs == deterministic_receipt.input_refs
    assert external_receipt.output_ref == deterministic_receipt.output_ref
    assert external_artifacts.read_bytes(
        external_receipt.output_ref.digest
    ) == deterministic_artifacts.read_bytes(deterministic_receipt.output_ref.digest)

    invocations = external_ledger.list_role_invocations(external_artifacts)
    assert len(invocations) == 1
    invocation = invocations[0]
    assert invocation.role == AgentRole.TRACE_ANALYST
    assert invocation.provider == "g06-retained-provider"
    assert invocation.model == "g06-retained-model"
    assert invocation.backend.endswith("._Backend")
    assert invocation.authority_id == "g06-retained-trace-authority"
    assert invocation.timeout_seconds == external_backend.timeout_seconds
    assert invocation.output_digest == deterministic_receipt.output_ref.digest

    before_bytes = {
        digest: (external_artifacts.path_for(digest)).read_bytes()
        for digest in external_before_cas
    }
    for digest, content in before_bytes.items():
        assert external_artifacts.path_for(digest).read_bytes() == content
    external_new_cas = _cas_digests(external_workspace) - external_before_cas
    allowed_external_provenance = {
        external_pointer.receipt_digest,
        invocation.request_ref.digest,
        invocation.response_ref.digest if invocation.response_ref is not None else None,
        invocation.transcript_ref.digest,
        invocation.typed_output_ref.digest if invocation.typed_output_ref is not None else None,
    }
    assert external_new_cas == {digest for digest in allowed_external_provenance if digest}
    assert _cas_digests(deterministic_workspace) - deterministic_before_cas == {
        deterministic_receipt.output_ref.digest,
        deterministic_artifacts.read_pointer(
            deterministic_workspace / "stages" / "distill.pointer.json", StagePointer
        ).receipt_digest,
    }


def test_microworld_malformed_external_trace_output_is_retained_and_blocks_distill(
    tmp_path: Path,
) -> None:
    prepared = MicroworldEvolutionCycle.prepare(tmp_path / "prepared", clean=True)
    prepared.composition.orchestrator.stages.invoke(StageName.INGEST)
    workspace = _clone_workspace(prepared.workspace, tmp_path / "malformed")
    artifacts = ArtifactStore(workspace / "artifacts")
    ledger = Ledger(workspace / "evogen.sqlite3")
    backend = _Backend({AgentRole.TRACE_ANALYST: {}})
    invoker: RoleInvoker[DistilledTrace] = RoleInvoker(
        backend=backend,
        artifacts=artifacts,
        ledger=ledger,
        provider="g06-malformed-provider",
        model="g06-malformed-model",
        authority_id="g06-malformed-trace-authority",
    )
    orchestrator = _clone_orchestrator(
        prepared,
        workspace,
        trace_analyst=TraceAnalystAdapter(invoker),
        artifacts=artifacts,
        ledger=ledger,
    )

    with pytest.raises(RoleInvocationError) as raised:
        orchestrator.invoke(StageName.DISTILL)
    assert raised.value.invocation.outcome == RoleOutcome.INVALID_TYPED_OUTPUT
    invocations = ledger.list_role_invocations(artifacts)
    assert len(invocations) == 1
    assert invocations[0] == raised.value.invocation
    assert invocations[0].role == AgentRole.TRACE_ANALYST
    assert not (workspace / "stages" / "distill.pointer.json").exists()
