from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from evogen.core.enums import (
    Completeness,
    EventKind,
    FailureLayer,
    ProbeDispositionKind,
    ProbeStageName,
    ResolutionKind,
    StageName,
)
from evogen.core.models import (
    ArtifactRef,
    IngestResult,
    ProbeBuildOutput,
    ProbeCandidateManifest,
    ProbeEvaluation,
    ProbeFilePayload,
    ProbePlan,
    ProbeReviewReport,
    ProbeStagePointer,
    TrajectoryEvent,
)
from evogen.demo.microworld.cycle import MicroworldEvolutionCycle
from evogen.demo.microworld.investigator import MicroworldInvestigator
from evogen.demo.microworld.probe import (
    MicroworldProbeBuilder,
    MicroworldProbeEvaluator,
    MicroworldProbePlanner,
    MicroworldProbeReviewer,
)
from evogen.evolution.diagnosis import EvidenceFirstDiagnostician
from evogen.evolution.probes import (
    ProbeIntegrityError,
    ProbeOrchestrator,
    ProbePathError,
    ProbePlanningError,
    execute_probe_source,
    validate_probe_source,
)
from evogen.evolution.stages import EvolutionStageOrchestrator, ProbeRequiredError
from evogen.trace.distill import TraceDistiller


def _probe(
    cycle: MicroworldEvolutionCycle,
    root: Path,
    *,
    evaluator: object | None = None,
    builder: object | None = None,
    initial_observation: dict[str, object] | None = None,
) -> ProbeOrchestrator:
    baseline = cycle._baseline_generation()
    record, events = cycle.runner.run(
        generation=baseline,
        scenario_id="diag-opaque-near",
        trace_directory=root / "baseline-trace",
    )
    del record
    issue = EvidenceFirstDiagnostician().diagnose(
        TraceDistiller().distill(
            generation_id=baseline.generation_id,
            events=events,
            capabilities=cycle.runner.capability_manifest(baseline),
        )
    )
    investigation = MicroworldInvestigator().investigate(issue)
    issue_ref = cycle.artifacts.put_model(issue)
    investigation_ref = cycle.artifacts.put_model(investigation)
    baseline_ref = cycle.artifacts.put_model(baseline)
    capability_ref = ArtifactRef(
        digest=baseline.capability_manifest_digest,
        model="CapabilityManifest",
    )
    return ProbeOrchestrator(
        workspace=root,
        artifacts=cycle.artifacts,
        ledger=cycle.ledger,
        baseline_ref=baseline_ref,
        issue_ref=issue_ref,
        investigation_ref=investigation_ref,
        capability_manifest_ref=capability_ref,
        runner=cycle.runner,
        planner=MicroworldProbePlanner(
            runner=cycle.runner,
            trace_directory=root / "probe-trace",
        ),
        builder=builder or MicroworldProbeBuilder(),
        reviewer=MicroworldProbeReviewer(),
        evaluator=evaluator or MicroworldProbeEvaluator(runner=cycle.runner, baseline=baseline),
        probe_id="probe-test-fixed",
        initial_observation=initial_observation,
    )


class _EvidenceVariantEvaluator:
    def __init__(self, cycle: MicroworldEvolutionCycle, mode: str) -> None:
        self.delegate = MicroworldProbeEvaluator(
            runner=cycle.runner,
            baseline=cycle._baseline_generation(),
        )
        self.mode = mode

    def evaluate(self, *, plan, candidate, review) -> ProbeEvaluation:
        evaluation = self.delegate.evaluate(plan=plan, candidate=candidate, review=review)
        dispatch = evaluation.dispatch_evidence
        later = evaluation.later_observation
        if self.mode == "missing":
            return evaluation.model_copy(
                update={
                    "dispatch_evidence": None,
                    "later_observation": None,
                    "completeness": Completeness.MISSING,
                }
            )
        if self.mode in {"truncated", "unknown"}:
            return evaluation.model_copy(
                update={
                    "completeness": (
                        Completeness.TRUNCATED
                        if self.mode == "truncated"
                        else Completeness.UNKNOWN
                    )
                }
            )
        if self.mode == "dispatch-only":
            return evaluation.model_copy(
                update={"later_observation": None, "completeness": Completeness.COMPLETE}
            )
        if self.mode in {"unchanged", "refused"} and dispatch is not None:
            return evaluation.model_copy(
                update={
                    "dispatch_evidence": dispatch.model_copy(
                        update={
                            "accepted": self.mode != "refused",
                            "changed": False,
                        }
                    )
                }
            )
        if self.mode == "steps" and dispatch is not None:
            return evaluation.model_copy(
                update={
                    "dispatch_evidence": dispatch.model_copy(update={"steps": 2})
                }
            )
        if self.mode == "missing-later" and later is not None:
            return evaluation.model_copy(
                update={
                    "later_observation": later.model_copy(
                        update={"observation": {}}
                    )
                }
            )
        if self.mode == "contradictory-later" and later is not None:
            return evaluation.model_copy(
                update={
                    "later_observation": later.model_copy(
                        update={
                            "container_id": "wrong-container",
                            "observation": {
                                "visible_containers": [
                                    {
                                        "container_id": "wrong-container",
                                        "inspected": True,
                                        "revealed_items": [],
                                    }
                                ]
                            },
                        }
                    )
                }
            )
        return evaluation


class _FailingEvaluator:
    def evaluate(self, **_: object) -> ProbeEvaluation:
        raise RuntimeError("synthetic evaluator failure")


class _AdapterIdEvaluator:
    def __init__(self, cycle: MicroworldEvolutionCycle, adapter_id: str) -> None:
        self.delegate = MicroworldProbeEvaluator(
            runner=cycle.runner,
            baseline=cycle._baseline_generation(),
        )
        self.adapter_id = adapter_id

    def evaluate(self, *, plan, candidate, review) -> ProbeEvaluation:
        return self.delegate.evaluate(
            plan=plan,
            candidate=candidate,
            review=review,
        ).model_copy(update={"evaluation_id": self.adapter_id})


class _OversizedBuilder:
    def build(self, *, plan):
        output = MicroworldProbeBuilder().build(plan=plan)
        source = output.files[0].content + ("\n# oversized\n" + ("x" * 5000))
        return ProbeBuildOutput(
            files=[ProbeFilePayload(path="probe.py", content=source)],
            metadata=output.metadata,
        )


class _ExtraFileBuilder:
    def build(self, *, plan):
        output = MicroworldProbeBuilder().build(plan=plan)
        return ProbeBuildOutput(
            files=[
                *output.files,
                ProbeFilePayload(path="extra.py", content="marker"),
            ]
        )


@pytest.mark.parametrize(
    "mode,initial_observation,expected",
    [
        ("complete", None, ProbeDispositionKind.RESOLVED),
        ("missing", None, ProbeDispositionKind.INCONCLUSIVE),
        ("truncated", None, ProbeDispositionKind.INCONCLUSIVE),
        ("unknown", None, ProbeDispositionKind.INCONCLUSIVE),
        ("dispatch-only", None, ProbeDispositionKind.INCONCLUSIVE),
        ("unchanged", None, ProbeDispositionKind.INCONCLUSIVE),
        ("refused", None, ProbeDispositionKind.INCONCLUSIVE),
        ("steps", None, ProbeDispositionKind.INCONCLUSIVE),
        ("missing-later", None, ProbeDispositionKind.INCONCLUSIVE),
        ("contradictory-later", None, ProbeDispositionKind.INCONCLUSIVE),
        ("complete", {"target_item_id": "hidden"}, ProbeDispositionKind.INCONCLUSIVE),
    ],
)
def test_evidence_completeness_matrix_is_fail_closed(
    tmp_path: Path,
    mode: str,
    initial_observation: dict[str, object] | None,
    expected: ProbeDispositionKind,
) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / mode)
    evaluator = _EvidenceVariantEvaluator(cycle, mode)
    result = _probe(
        cycle,
        cycle.workspace,
        evaluator=evaluator,
        initial_observation=initial_observation,
    ).run()
    assert result.disposition.disposition == expected
    assert [row["stage"] for row in cycle.ledger.probe_records(result.manifest.probe_id)] == [
        "plan",
        "build",
        "review",
        "evaluate",
        "dispose",
    ]


def test_evaluator_failure_is_retained_with_before_after_capability_proof(
    tmp_path: Path,
) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "workspace")
    result = _probe(
        cycle,
        cycle.workspace,
        evaluator=_FailingEvaluator(),
    ).run()
    assert result.disposition.disposition == ProbeDispositionKind.INCONCLUSIVE
    assert result.evaluation.completeness == Completeness.UNKNOWN
    assert any("synthetic evaluator failure" in note for note in result.evaluation.notes)
    assert result.evaluation.initial_capability_manifest_ref == (
        result.evaluation.final_capability_manifest_ref
    )
    assert result.evaluation.initial_capability_manifest_bytes_digest == (
        result.evaluation.final_capability_manifest_bytes_digest
    )


def test_adapter_evaluation_id_cannot_change_deterministic_identity(tmp_path: Path) -> None:
    first_cycle = MicroworldEvolutionCycle.prepare(tmp_path / "first")
    first = _probe(
        first_cycle,
        first_cycle.workspace,
        evaluator=_AdapterIdEvaluator(first_cycle, "adapter-id-a"),
    ).run()
    second_cycle = MicroworldEvolutionCycle.prepare(tmp_path / "second")
    second = _probe(
        second_cycle,
        second_cycle.workspace,
        evaluator=_AdapterIdEvaluator(second_cycle, "adapter-id-b"),
    ).run()
    assert first.evaluation.evaluation_id == second.evaluation.evaluation_id


def test_probe_source_budget_and_declared_action_permissions_fail_closed(
    tmp_path: Path,
) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "workspace")
    with pytest.raises(ProbePathError, match="byte budget"):
        _probe(cycle, cycle.workspace, builder=_OversizedBuilder()).run()
    extra_cycle = MicroworldEvolutionCycle.prepare(tmp_path / "extra")
    with pytest.raises(ProbePathError, match="undeclared"):
        _probe(extra_cycle, extra_cycle.workspace, builder=_ExtraFileBuilder()).run()
    assert "undeclared operation literal" in validate_probe_source(
        'def derive_action(x): return {"operation": "take_item"}',
        allowed_operations=["inspect_container"],
    )
    assert "undeclared effect literal" in validate_probe_source(
        'def derive_action(x): return {"effect": "acquire_visible_item"}',
        allowed_operations=[],
        allowed_effects=["reveal_contents"],
    )


@pytest.mark.parametrize("crash_stage", ["plan", "build", "review", "evaluate", "dispose"])
def test_probe_ledger_insert_crash_is_idempotent_and_resumable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, crash_stage: str
) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / crash_stage)
    orchestrator = _probe(cycle, cycle.workspace)
    method_name = {
        "plan": "add_probe_plan",
        "build": "add_probe_candidate",
        "review": "add_probe_review",
        "evaluate": "add_probe_evaluation",
        "dispose": "add_probe_disposition",
    }[crash_stage]
    for prerequisite in ("plan", "build", "review", "evaluate"):
        if prerequisite == crash_stage:
            break
        orchestrator.invoke(prerequisite)
    original = getattr(cycle.ledger, method_name)
    crashed = False

    def insert_then_crash(record: object) -> None:
        nonlocal crashed
        original(record)
        if not crashed:
            crashed = True
            raise RuntimeError("injected crash after immutable probe insert")

    monkeypatch.setattr(cycle.ledger, method_name, insert_then_crash)
    with pytest.raises(RuntimeError, match="injected crash"):
        orchestrator.invoke(crash_stage)
    monkeypatch.setattr(cycle.ledger, method_name, original)

    resumed = ProbeOrchestrator(
        workspace=cycle.workspace,
        artifacts=cycle.artifacts,
        ledger=cycle.ledger,
        baseline_ref=orchestrator.baseline_ref,
        issue_ref=orchestrator.issue_ref,
        investigation_ref=orchestrator.investigation_ref,
        capability_manifest_ref=orchestrator.capability_manifest_ref,
        runner=cycle.runner,
        planner=MicroworldProbePlanner(
            runner=cycle.runner,
            trace_directory=cycle.workspace / "probe-trace-resume",
        ),
        builder=MicroworldProbeBuilder(),
        reviewer=MicroworldProbeReviewer(),
        evaluator=MicroworldProbeEvaluator(
            runner=cycle.runner,
            baseline=cycle._baseline_generation(),
        ),
        probe_id=orchestrator.probe_id,
    )
    result = resumed.run()
    assert result.disposition.disposition == ProbeDispositionKind.RESOLVED
    rows = cycle.ledger.probe_records(result.manifest.probe_id)
    assert [row["stage"] for row in rows] == [
        "plan",
        "build",
        "review",
        "evaluate",
        "dispose",
    ]


def test_probe_resolves_uncertainty_without_generating_permanent_capability(tmp_path: Path) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "workspace")
    baseline = cycle._baseline_generation()
    baseline_bytes = cycle.artifacts.path_for(
        baseline.capability_manifest_digest
    ).read_bytes()

    result = _probe(cycle, cycle.workspace).run()

    assert result.disposition.disposition == ProbeDispositionKind.RESOLVED
    assert result.evaluation.accepted_receipt
    assert result.evaluation.independent_observation
    assert result.evaluation.initial_capability_manifest_ref == (
        result.evaluation.final_capability_manifest_ref
    )
    assert result.evaluation.initial_capability_manifest_digest == (
        result.evaluation.final_capability_manifest_bytes_digest
    )
    source = (Path(result.candidate.workspace_path) / "probe.py").read_text()
    assert "diag-opaque-near" not in source
    assert "amber-token" not in source
    assert "target_item_id" not in source
    assert (
        cycle.artifacts.path_for(baseline.capability_manifest_digest).read_bytes()
        == baseline_bytes
    )
    assert len(cycle.ledger.list_generations()) == 0
    assert cycle.ledger.lineage_rows() == []
    assert [row["stage"] for row in cycle.ledger.probe_records(result.manifest.probe_id)] == [
        "plan",
        "build",
        "review",
        "evaluate",
        "dispose",
    ]


def test_generated_probe_binds_renamed_observation_and_has_no_fixture_knowledge(
    tmp_path: Path,
) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "workspace")
    result = _probe(cycle, cycle.workspace).run()
    source = (Path(result.candidate.workspace_path) / "probe.py").read_text()
    for forbidden in (
        "diag-opaque-near",
        "amber-token",
        "crate-a",
        "Sealed crate",
        "target_item_id",
        "MicroWorld",
        "environment",
        "evaluator",
    ):
        assert forbidden not in source
    observation = dict(result.plan.initial_observation)
    containers = [dict(item) for item in observation["visible_containers"]]
    containers[0]["container_id"] = "renamed-container"
    observation["visible_containers"] = containers
    action = execute_probe_source(
        source,
        observation,
        1.0,
        allowed_operations=result.plan.permissions.allowed_operations,
        allowed_effects=result.plan.permissions.allowed_effects,
    )
    assert action["container_id"] == "renamed-container"


def test_probe_completed_boundaries_resume_without_new_transitions(tmp_path: Path) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "workspace")
    orchestrator = _probe(cycle, cycle.workspace)
    orchestrator.run(until="evaluate")
    before = cycle.ledger.probe_records(orchestrator.manifest.probe_id)

    # Reconstructing with the persisted id and the same immutable issue input is
    # the supported fresh-process route.
    resumed = ProbeOrchestrator(
        workspace=cycle.workspace,
        artifacts=cycle.artifacts,
        ledger=cycle.ledger,
        baseline_ref=orchestrator.baseline_ref,
        issue_ref=orchestrator.issue_ref,
        investigation_ref=orchestrator.investigation_ref,
        capability_manifest_ref=orchestrator.capability_manifest_ref,
        runner=cycle.runner,
        planner=MicroworldProbePlanner(
            runner=cycle.runner,
            trace_directory=cycle.workspace / "probe-trace-resume",
        ),
        builder=MicroworldProbeBuilder(),
        reviewer=MicroworldProbeReviewer(),
        evaluator=MicroworldProbeEvaluator(
            runner=cycle.runner,
            baseline=cycle._baseline_generation(),
        ),
        probe_id=orchestrator.probe_id,
    )
    result = resumed.run()
    assert result.disposition.disposition == ProbeDispositionKind.RESOLVED
    after = cycle.ledger.probe_records(orchestrator.probe_id)
    assert [row["stage"] for row in after] == [
        "plan",
        "build",
        "review",
        "evaluate",
        "dispose",
    ]
    assert after[: len(before)] == before


def _workspace_bytes(root: Path) -> dict[str, bytes]:
    """Snapshot stable files; SQLite WAL/SHM sidecars are intentionally ephemeral."""
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name not in {"evogen.sqlite3-wal", "evogen.sqlite3-shm"}
    }


def _permanent_snapshot(
    cycle: MicroworldEvolutionCycle,
    root: Path,
    baseline_ref: ArtifactRef,
    capability_ref: ArtifactRef,
) -> dict[str, object]:
    cycle.ledger.checkpoint()
    tables = (
        "generations",
        "runs",
        "events",
        "issues",
        "candidates",
        "experiments",
        "decisions",
        "lineage",
    )
    with cycle.ledger.connect() as connection:
        ledger_rows = {
            table: [tuple(row) for row in connection.execute(f"SELECT * FROM {table} ORDER BY 1")]
            for table in tables
        }
    pointers = {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*pointer.json")
        if "probes" not in path.parts
    }
    return {
        "ledger": ledger_rows,
        "pointers": pointers,
        "baseline_ref": baseline_ref,
        "baseline_bytes": cycle.artifacts.read_bytes(baseline_ref.digest),
        "capability_ref": capability_ref,
        "capability_bytes": cycle.artifacts.read_bytes(capability_ref.digest),
        "artifact_bytes": {
            str(path.relative_to(cycle.artifacts.objects)): path.read_bytes()
            for path in sorted(cycle.artifacts.objects.rglob("*"))
            if path.is_file()
        },
    }


def test_probe_status_and_result_are_read_only_and_byte_stable(tmp_path: Path) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "workspace")
    orchestrator = _probe(cycle, cycle.workspace)
    result = orchestrator.run()
    cycle.ledger.checkpoint()
    before = _workspace_bytes(cycle.workspace)
    first_status = orchestrator.stage_status()
    first_result = orchestrator.result()
    second_status = orchestrator.stage_status()
    second_result = orchestrator.result()
    assert first_status == second_status
    assert first_result == second_result == result
    assert _workspace_bytes(cycle.workspace) == before


def test_probe_reopen_ref_and_candidate_tamper_fail_closed(tmp_path: Path) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "workspace")
    orchestrator = _probe(cycle, cycle.workspace)
    orchestrator.invoke("plan")
    orchestrator.invoke("build")
    candidate_path = (
        orchestrator.probe_workspace / "candidates" / orchestrator.probe_id / "probe.py"
    )
    candidate_path.write_text(candidate_path.read_text() + "\n# tampered\n")
    with pytest.raises(ProbePathError):
        orchestrator.invoke("review")

    changed_issue = orchestrator.issue.model_copy(update={"title": "tampered"})
    changed_issue_ref = cycle.artifacts.put_model(changed_issue)
    with pytest.raises(ProbeIntegrityError, match="Manifest issue_ref"):
        ProbeOrchestrator(
            workspace=cycle.workspace,
            artifacts=cycle.artifacts,
            ledger=cycle.ledger,
            baseline_ref=orchestrator.baseline_ref,
            issue_ref=changed_issue_ref,
            investigation_ref=orchestrator.investigation_ref,
            capability_manifest_ref=orchestrator.capability_manifest_ref,
            runner=cycle.runner,
            planner=orchestrator.planner,
            builder=orchestrator.builder,
            reviewer=orchestrator.reviewer,
            evaluator=orchestrator.evaluator,
            probe_id=orchestrator.probe_id,
        )


def test_corrupt_manifest_and_stage_pointers_are_typed_integrity_failures(
    tmp_path: Path,
) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "manifest")
    orchestrator = _probe(cycle, cycle.workspace)
    orchestrator.manifest_pointer.write_text("{}", encoding="utf-8")
    with pytest.raises(ProbeIntegrityError):
        _probe(cycle, cycle.workspace)

    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "stage")
    orchestrator = _probe(cycle, cycle.workspace)
    orchestrator.invoke(ProbeStageName.PLAN)
    orchestrator._pointer_path(ProbeStageName.PLAN).write_text("{}", encoding="utf-8")
    with pytest.raises(ProbeIntegrityError):
        orchestrator.stage_status()


@pytest.mark.parametrize("corrupt", [False, True])
def test_initial_observation_cas_failures_are_typed(
    tmp_path: Path, corrupt: bool
) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / ("corrupt" if corrupt else "deleted"))
    orchestrator = _probe(cycle, cycle.workspace)
    orchestrator.invoke(ProbeStageName.PLAN)
    plan = orchestrator.completed_stage(ProbeStageName.PLAN)
    assert plan.initial_observation_ref is not None
    observation_path = orchestrator.probe_artifacts.path_for(
        plan.initial_observation_ref.digest
    )
    if corrupt:
        observation_path.write_text("{}", encoding="utf-8")
    else:
        observation_path.unlink()
    with pytest.raises(ProbeIntegrityError):
        orchestrator.stage_status()


def test_probe_authorities_cannot_reuse_builder_as_reviewer_or_evaluator(
    tmp_path: Path,
) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "roles")
    valid = _probe(cycle, cycle.workspace)
    kwargs = dict(
        workspace=cycle.workspace / "roles-reused",
        artifacts=cycle.artifacts,
        ledger=cycle.ledger,
        baseline_ref=valid.baseline_ref,
        issue_ref=valid.issue_ref,
        investigation_ref=valid.investigation_ref,
        capability_manifest_ref=valid.capability_manifest_ref,
        runner=cycle.runner,
        planner=valid.planner,
        builder=valid.builder,
        reviewer=valid.reviewer,
        evaluator=valid.evaluator,
        probe_id="probe-role-reuse",
    )
    with pytest.raises(ProbeIntegrityError, match="distinct"):
        ProbeOrchestrator(**{**kwargs, "reviewer": valid.builder})
    with pytest.raises(ProbeIntegrityError, match="distinct"):
        ProbeOrchestrator(**{**kwargs, "evaluator": valid.builder})


def test_deleted_evidence_cas_is_typed_integrity_failure(tmp_path: Path) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "workspace")
    orchestrator = _probe(cycle, cycle.workspace)
    evaluation = orchestrator.run(until="evaluate")
    evidence_ref = evaluation.dispatch_evidence_ref
    assert evidence_ref is not None
    orchestrator.probe_artifacts.path_for(evidence_ref.digest).unlink()
    with pytest.raises(ProbeIntegrityError, match="evidence"):
        orchestrator.result()


def test_forged_receipt_and_candidate_ids_fail_replay_integrity(tmp_path: Path) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "receipt")
    orchestrator = _probe(cycle, cycle.workspace)
    orchestrator.invoke(ProbeStageName.PLAN)
    plan_receipt = orchestrator._read_receipt(ProbeStageName.PLAN)
    forged_receipt = plan_receipt.model_copy(update={"receipt_id": "forged-receipt"})
    forged_ref = orchestrator.probe_artifacts.put_model(forged_receipt)
    orchestrator.probe_artifacts.write_pointer(
        orchestrator._pointer_path(ProbeStageName.PLAN),
        ProbeStagePointer(
            pointer_version="1.0",
            probe_id=orchestrator.probe_id,
            stage=ProbeStageName.PLAN,
            receipt_digest=forged_ref.digest,
        ),
    )
    with pytest.raises(ProbeIntegrityError, match="deterministic identity"):
        orchestrator.stage_status()

    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "candidate")
    orchestrator = _probe(cycle, cycle.workspace)
    orchestrator.invoke(ProbeStageName.PLAN)
    orchestrator.invoke(ProbeStageName.BUILD)
    candidate_receipt = orchestrator._read_receipt(ProbeStageName.BUILD)
    candidate = orchestrator.probe_artifacts.read_model(
        candidate_receipt.output_ref,
        ProbeCandidateManifest,
    )
    forged_candidate = candidate.model_copy(update={"candidate_id": "forged-candidate"})
    forged_candidate_ref = orchestrator.probe_artifacts.put_model(forged_candidate)
    forged_candidate_receipt = candidate_receipt.model_copy(
        update={
            "output_ref": forged_candidate_ref,
            "receipt_id": orchestrator._receipt_id(
                ProbeStageName.BUILD,
                candidate_receipt.input_refs,
                forged_candidate_ref,
                candidate_receipt.prior_receipt_digest,
            ),
        }
    )
    forged_candidate_receipt_ref = orchestrator.probe_artifacts.put_model(
        forged_candidate_receipt
    )
    orchestrator.probe_artifacts.write_pointer(
        orchestrator._pointer_path(ProbeStageName.BUILD),
        ProbeStagePointer(
            pointer_version="1.0",
            probe_id=orchestrator.probe_id,
            stage=ProbeStageName.BUILD,
            receipt_digest=forged_candidate_receipt_ref.digest,
        ),
    )
    with pytest.raises(ProbeIntegrityError, match="deterministic identity"):
        orchestrator.stage_status()


def test_forged_plan_cas_receipt_and_pointer_fail_planner_replay(tmp_path: Path) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "plan")
    orchestrator = _probe(cycle, cycle.workspace)
    orchestrator.invoke(ProbeStageName.PLAN)
    receipt = orchestrator._read_receipt(ProbeStageName.PLAN)
    plan = orchestrator.probe_artifacts.read_model(receipt.output_ref, ProbePlan)
    forged_plan = plan.model_copy(
        update={
            "evidence_target": plan.evidence_target.model_copy(
                update={"named_uncertainty": "forged uncertainty"}
            )
        }
    )
    forged_ref = orchestrator.probe_artifacts.put_model(forged_plan)
    forged_receipt = receipt.model_copy(
        update={
            "output_ref": forged_ref,
            "receipt_id": orchestrator._receipt_id(
                ProbeStageName.PLAN,
                receipt.input_refs,
                forged_ref,
                receipt.prior_receipt_digest,
            ),
        }
    )
    forged_receipt_ref = orchestrator.probe_artifacts.put_model(forged_receipt)
    orchestrator.probe_artifacts.write_pointer(
        orchestrator._pointer_path(ProbeStageName.PLAN),
        ProbeStagePointer(
            pointer_version="1.0",
            probe_id=orchestrator.probe_id,
            stage=ProbeStageName.PLAN,
            receipt_digest=forged_receipt_ref.digest,
        ),
    )
    with pytest.raises(ProbeIntegrityError, match="replay"):
        orchestrator.stage_status()


def test_coordinated_forged_evidence_and_evaluation_fail_independent_replay(
    tmp_path: Path,
) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "evidence")
    orchestrator = _probe(
        cycle,
        cycle.workspace,
        evaluator=_EvidenceVariantEvaluator(cycle, "missing"),
    )
    evaluation = orchestrator.run(until=ProbeStageName.EVALUATE)
    assert isinstance(evaluation, ProbeEvaluation)
    receipt = orchestrator._read_receipt(ProbeStageName.EVALUATE)
    candidate = orchestrator.completed_stage(ProbeStageName.BUILD)
    review = orchestrator.completed_stage(ProbeStageName.REVIEW)
    assert isinstance(candidate, ProbeCandidateManifest)
    assert isinstance(review, ProbeReviewReport)
    plan = orchestrator.completed_stage(ProbeStageName.PLAN)
    actual = MicroworldProbeEvaluator(
        runner=cycle.runner,
        baseline=cycle._baseline_generation(),
    ).evaluate(plan=plan, candidate=candidate, review=review)
    dispatch = actual.dispatch_evidence
    later = actual.later_observation
    assert dispatch is not None
    assert later is not None
    forged_dispatch = dispatch.model_copy(
        update={"receipt": {**dispatch.receipt, "forged": True}}
    )
    forged_later = later.model_copy()
    dispatch_ref = orchestrator.probe_artifacts.put_model(forged_dispatch)
    later_ref = orchestrator.probe_artifacts.put_model(forged_later)
    forged_evaluation = evaluation.model_copy(
        update={
            "dispatch_evidence_ref": dispatch_ref,
            "dispatch_evidence": forged_dispatch,
            "later_observation_ref": later_ref,
            "later_observation": forged_later,
            "completeness": Completeness.COMPLETE,
        }
    )
    forged_evaluation = forged_evaluation.model_copy(
        update={"evaluation_id": orchestrator._evaluation_id(candidate, forged_evaluation)}
    )
    assert (
        orchestrator._disposition(plan, candidate, review, forged_evaluation).disposition
        == ProbeDispositionKind.RESOLVED
    )
    evaluation_ref = orchestrator.probe_artifacts.put_model(forged_evaluation)
    forged_receipt = receipt.model_copy(
        update={
            "output_ref": evaluation_ref,
            "receipt_id": orchestrator._receipt_id(
                ProbeStageName.EVALUATE,
                receipt.input_refs,
                evaluation_ref,
                receipt.prior_receipt_digest,
            ),
        }
    )
    forged_receipt_ref = orchestrator.probe_artifacts.put_model(forged_receipt)
    orchestrator.probe_artifacts.write_pointer(
        orchestrator._pointer_path(ProbeStageName.EVALUATE),
        ProbeStagePointer(
            pointer_version="1.0",
            probe_id=orchestrator.probe_id,
            stage=ProbeStageName.EVALUATE,
            receipt_digest=forged_receipt_ref.digest,
        ),
    )
    with pytest.raises(ProbeIntegrityError, match="independent replay"):
        orchestrator.stage_status()


def test_cross_probe_pointer_substitution_and_forged_review_fail_closed(
    tmp_path: Path,
) -> None:
    first_cycle = MicroworldEvolutionCycle.prepare(tmp_path / "first")
    first = _probe(first_cycle, first_cycle.workspace)
    first.invoke("plan")
    second_cycle = MicroworldEvolutionCycle.prepare(tmp_path / "second")
    second = _probe(second_cycle, second_cycle.workspace)
    second.invoke("plan")
    second_plan_pointer = second._pointer_path(ProbeStageName.PLAN)
    second_plan_pointer.write_bytes(first._pointer_path(ProbeStageName.PLAN).read_bytes())
    with pytest.raises(ProbeIntegrityError):
        second.stage_status()

    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "review")
    orchestrator = _probe(cycle, cycle.workspace)
    orchestrator.run(until="review")
    review_receipt = orchestrator._read_receipt(ProbeStageName.REVIEW)
    review = orchestrator.probe_artifacts.read_model(
        review_receipt.output_ref, ProbeReviewReport
    )
    forged = review.model_copy(update={"reviewed_files": []})
    forged_ref = orchestrator.probe_artifacts.put_model(forged)
    forged_receipt = review_receipt.model_copy(update={"output_ref": forged_ref})
    forged_receipt_ref = orchestrator.probe_artifacts.put_model(forged_receipt)
    orchestrator.probe_artifacts.write_pointer(
        orchestrator._pointer_path(ProbeStageName.REVIEW),
        ProbeStagePointer(
            pointer_version="1.0",
            probe_id=orchestrator.probe_id,
            stage="review",
            receipt_digest=forged_receipt_ref.digest,
        ),
    )
    with pytest.raises(ProbeIntegrityError):
        orchestrator.stage_status()


def test_probe_fresh_subprocess_resume_and_idempotence(tmp_path: Path) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "workspace")
    orchestrator = _probe(cycle, cycle.workspace)
    orchestrator.run(until="review")
    workspace = str(cycle.workspace)
    script = """
import json
import sys
from pathlib import Path
from evogen.core.models import ArtifactRef, ProbeManifest
from evogen.demo.microworld.probe import (
    MicroworldProbeBuilder, MicroworldProbeEvaluator, MicroworldProbePlanner,
    MicroworldProbeReviewer,
)
from evogen.demo.microworld.subject import MicroworldRunner
from evogen.storage.artifacts import ArtifactStore
from evogen.storage.ledger import Ledger
from evogen.evolution.probes import ProbeOrchestrator

workspace = Path(sys.argv[1])
probe_root = workspace / "probes" / "probe-test-fixed"
probe_store = ArtifactStore(workspace / "probes" / "artifacts")
pointer = json.loads((probe_root / "probe-manifest.pointer.json").read_text())
manifest = probe_store.read_model(
    ArtifactRef(digest=pointer["digest"], model="ProbeManifest"), ProbeManifest
)
runner = MicroworldRunner()
baseline = ArtifactStore(workspace / "artifacts").read_model(
    manifest.baseline_ref,
    __import__("evogen.core.models", fromlist=["GenerationManifest"]).GenerationManifest,
)
probe = ProbeOrchestrator(
    workspace=workspace,
    artifacts=ArtifactStore(workspace / "artifacts"),
    ledger=Ledger(workspace / "evogen.sqlite3"),
    baseline_ref=manifest.baseline_ref,
    issue_ref=manifest.issue_ref,
    investigation_ref=manifest.investigation_ref,
    capability_manifest_ref=manifest.capability_manifest_ref,
    runner=runner,
    planner=MicroworldProbePlanner(runner=runner, trace_directory=workspace / "resume-trace"),
    builder=MicroworldProbeBuilder(),
    reviewer=MicroworldProbeReviewer(),
    evaluator=MicroworldProbeEvaluator(runner=runner, baseline=baseline),
    probe_id=manifest.probe_id,
)
print(json.dumps(probe.run().model_dump(mode="json"), sort_keys=True))
"""
    first = subprocess.run(
        [sys.executable, "-c", script, workspace],
        check=True,
        capture_output=True,
        text=True,
    )
    after_first = {
        key: value
        for key, value in _workspace_bytes(cycle.workspace).items()
        if key.startswith("probes/")
    }
    cycle.ledger.checkpoint()
    ledger_after_first = cycle.ledger.probe_records(orchestrator.probe_id)
    second = subprocess.run(
        [sys.executable, "-c", script, workspace],
        check=True,
        capture_output=True,
        text=True,
    )
    cycle.ledger.checkpoint()
    assert json.loads(first.stdout) == json.loads(second.stdout)
    after_second = {
        key: value
        for key, value in _workspace_bytes(cycle.workspace).items()
        if key.startswith("probes/")
    }
    assert after_second == after_first
    assert cycle.ledger.probe_records(orchestrator.probe_id) == ledger_after_first


def test_probe_id_escape_and_unsafe_source_fail_before_side_effects(tmp_path: Path) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "workspace")
    valid = _probe(cycle, cycle.workspace)
    with pytest.raises(ProbePathError):
        ProbeOrchestrator(
            workspace=cycle.workspace,
            artifacts=cycle.artifacts,
            ledger=cycle.ledger,
            baseline_ref=valid.baseline_ref,
            issue_ref=valid.issue_ref,
            investigation_ref=valid.investigation_ref,
            capability_manifest_ref=valid.capability_manifest_ref,
            runner=cycle.runner,
            planner=valid.planner,
            builder=valid.builder,
            reviewer=valid.reviewer,
            evaluator=valid.evaluator,
            probe_id="../escape",
        )
    assert not (cycle.workspace.parent / "escape").exists()
    assert validate_probe_source(
        "import os\ndef derive_action(x): return {}",
        allowed_operations=[],
    )
    assert validate_probe_source(
        "def derive_action(x):\n while True: pass\n",
        allowed_operations=[],
    )


@pytest.mark.parametrize(
    "probe_id",
    ["", ".", "..", "/tmp/absolute-probe", "nested/probe", r"nested\probe", "../escape"],
)
def test_probe_ids_are_single_components_before_filesystem_creation(
    tmp_path: Path, probe_id: str
) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "workspace")
    valid = _probe(cycle, cycle.workspace)
    with pytest.raises(ProbePathError):
        ProbeOrchestrator(
            workspace=cycle.workspace,
            artifacts=cycle.artifacts,
            ledger=cycle.ledger,
            baseline_ref=valid.baseline_ref,
            issue_ref=valid.issue_ref,
            investigation_ref=valid.investigation_ref,
            capability_manifest_ref=valid.capability_manifest_ref,
            runner=cycle.runner,
            planner=valid.planner,
            builder=valid.builder,
            reviewer=valid.reviewer,
            evaluator=valid.evaluator,
            probe_id=probe_id,
        )
    assert not (tmp_path / "escape").exists()


def test_symlinked_workspace_probe_root_candidate_root_and_file_fail_closed(
    tmp_path: Path,
) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "workspace")
    valid = _probe(cycle, cycle.workspace)

    real_workspace = tmp_path / "real-workspace"
    real_workspace.mkdir()
    workspace_link = tmp_path / "workspace-link"
    workspace_link.symlink_to(real_workspace, target_is_directory=True)
    with pytest.raises(ProbePathError):
        ProbeOrchestrator(
            workspace=workspace_link,
            artifacts=cycle.artifacts,
            ledger=cycle.ledger,
            baseline_ref=valid.baseline_ref,
            issue_ref=valid.issue_ref,
            investigation_ref=valid.investigation_ref,
            capability_manifest_ref=valid.capability_manifest_ref,
            runner=cycle.runner,
            planner=valid.planner,
            builder=valid.builder,
            reviewer=valid.reviewer,
            evaluator=valid.evaluator,
            probe_id="probe-symlink-workspace",
        )

    probes_target = tmp_path / "probes-target"
    probes_target.mkdir()
    probes_workspace = tmp_path / "probes-workspace"
    probes_workspace.mkdir()
    probes_link = probes_workspace / "probes"
    probes_link.symlink_to(probes_target, target_is_directory=True)
    with pytest.raises(ProbePathError):
        ProbeOrchestrator(
            workspace=probes_workspace,
            artifacts=cycle.artifacts,
            ledger=cycle.ledger,
            baseline_ref=valid.baseline_ref,
            issue_ref=valid.issue_ref,
            investigation_ref=valid.investigation_ref,
            capability_manifest_ref=valid.capability_manifest_ref,
            runner=cycle.runner,
            planner=valid.planner,
            builder=valid.builder,
            reviewer=valid.reviewer,
            evaluator=valid.evaluator,
            probe_id="probe-symlink-probes",
        )
    probes_link.unlink()

    orchestrator = valid
    orchestrator.invoke("plan")
    candidate_target = tmp_path / "candidate-target"
    candidate_target.mkdir()
    candidates = orchestrator.probe_workspace / "candidates"
    candidates.symlink_to(candidate_target, target_is_directory=True)
    with pytest.raises(ProbePathError):
        orchestrator.invoke("build")
    assert not (candidate_target / orchestrator.probe_id / "probe.py").exists()


def test_manifest_and_stage_pointer_symlinks_fail_closed(tmp_path: Path) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "workspace")
    orchestrator = _probe(cycle, cycle.workspace)
    manifest_target = tmp_path / "manifest-target"
    manifest_target.write_text("{}")
    manifest_pointer = orchestrator.manifest_pointer
    manifest_pointer.unlink()
    manifest_pointer.symlink_to(manifest_target)
    with pytest.raises(ProbePathError):
        ProbeOrchestrator(
            workspace=cycle.workspace,
            artifacts=cycle.artifacts,
            ledger=cycle.ledger,
            baseline_ref=orchestrator.baseline_ref,
            issue_ref=orchestrator.issue_ref,
            investigation_ref=orchestrator.investigation_ref,
            capability_manifest_ref=orchestrator.capability_manifest_ref,
            runner=cycle.runner,
            planner=orchestrator.planner,
            builder=orchestrator.builder,
            reviewer=orchestrator.reviewer,
            evaluator=orchestrator.evaluator,
            probe_id=orchestrator.probe_id,
        )

    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "stage")
    orchestrator = _probe(cycle, cycle.workspace)
    orchestrator.invoke(ProbeStageName.PLAN)
    stage_pointer = orchestrator._pointer_path(ProbeStageName.PLAN)
    stage_target = tmp_path / "stage-target"
    stage_target.write_text("{}")
    pointer_bytes = stage_pointer.read_bytes()
    stage_pointer.unlink()
    stage_pointer.symlink_to(stage_target)
    with pytest.raises(ProbePathError):
        orchestrator.stage_status()
    assert stage_target.read_text() == "{}"
    assert pointer_bytes


def test_dangling_manifest_and_stage_pointer_symlinks_fail_closed(tmp_path: Path) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "manifest")
    orchestrator = _probe(cycle, cycle.workspace)
    manifest_pointer = orchestrator.manifest_pointer
    manifest_pointer.unlink()
    manifest_pointer.symlink_to(tmp_path / "missing-manifest-target")
    with pytest.raises(ProbePathError):
        _probe(cycle, cycle.workspace)

    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "stage")
    orchestrator = _probe(cycle, cycle.workspace)
    orchestrator.invoke(ProbeStageName.PLAN)
    stage_pointer = orchestrator._pointer_path(ProbeStageName.PLAN)
    stage_pointer.unlink()
    stage_pointer.symlink_to(tmp_path / "missing-stage-target")
    with pytest.raises(ProbePathError):
        orchestrator.stage_status()
    with pytest.raises(ProbePathError):
        orchestrator.invoke(ProbeStageName.PLAN)


@pytest.mark.parametrize(
    "source",
    [
        "import os\ndef derive_action(x): return {}",
        "def derive_action(x): return open('marker', 'w')",
        "def derive_action(x): return __import__('os').system('touch marker')",
        "def derive_action(x): return x.__class__",
        "def derive_action(x):\n while True: pass\n",
    ],
)
def test_probe_sandbox_rejects_code_and_has_no_side_effects(
    tmp_path: Path, source: str
) -> None:
    marker = tmp_path / "marker"
    assert validate_probe_source(source, allowed_operations=[])
    with pytest.raises(ProbeIntegrityError):
        execute_probe_source(
            source,
            {},
            0.1,
            allowed_operations=[],
        )
    assert not marker.exists()


def test_unknown_build_probe_issue_is_refused_by_subject_planner(tmp_path: Path) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "workspace")
    valid = _probe(cycle, cycle.workspace)
    unknown = valid.issue.model_copy(update={"required_effect": None})
    investigation = MicroworldInvestigator().investigate(unknown)
    with pytest.raises(ProbePlanningError):
        valid.planner.plan(
            issue=unknown,
            investigation=investigation,
            parent=valid.baseline,
            probe_id="probe-unknown",
        )


def test_unknown_error_is_insufficient_evidence_without_invented_effect(
    tmp_path: Path,
) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "workspace")
    baseline = cycle._baseline_generation()
    event = TrajectoryEvent(
        envelope_version="1.0",
        event_id="event-unknown-error",
        run_id="run-unknown-error",
        generation_id=baseline.generation_id,
        scenario_id="diag-opaque-near",
        sequence=0,
        kind=EventKind.ERROR,
        world_revision="0",
        source_event_type=None,
        source_event_id=None,
        source_sequence=None,
        source_step_index=None,
        source_world_revision=None,
        payload={"code": "mystery-runtime-error", "layer_hint": None},
    )
    distilled = TraceDistiller().distill(
        generation_id=baseline.generation_id,
        events=[event],
        capabilities=cycle.runner.capability_manifest(baseline),
    )
    issue = EvidenceFirstDiagnostician().diagnose(distilled)
    assert issue.classification.primary == FailureLayer.INSUFFICIENT_EVIDENCE
    assert issue.proposed_resolution == ResolutionKind.BUILD_PROBE
    assert issue.required_effect is None
    investigation = MicroworldInvestigator().investigate(issue)
    assert investigation.candidate_operations == []
    assert investigation.remaining_unknowns
    with pytest.raises(ProbePlanningError):
        MicroworldProbePlanner(
            runner=cycle.runner,
            trace_directory=tmp_path / "trace",
        ).plan(
            issue=issue,
            investigation=investigation,
            parent=baseline,
            probe_id="probe-unknown-error",
        )


def test_persisted_unknown_error_chain_keeps_named_unknowns_and_refuses_probe(
    tmp_path: Path,
) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "workspace")

    class UnknownErrorRunner(type(cycle.runner)):
        def run(self, *, generation, scenario_id, trace_directory):
            record, _ = super().run(
                generation=generation,
                scenario_id=scenario_id,
                trace_directory=trace_directory,
            )
            return record, [
                TrajectoryEvent(
                    envelope_version="1.0",
                    event_id="persisted-unknown-error",
                    run_id=record.run_id,
                    generation_id=generation.generation_id,
                    scenario_id=scenario_id,
                    sequence=0,
                    kind=EventKind.ERROR,
                    world_revision="0",
                    source_event_type=None,
                    source_event_id=None,
                    source_sequence=None,
                    source_step_index=None,
                    source_world_revision=None,
                    payload={"code": "unknown-error", "layer_hint": None},
                )
            ]

    runner = UnknownErrorRunner()
    plan = cycle.composition.bootstrap.plan.model_copy(
        update={"diagnostic_scenarios": ["diag-opaque-near"]}
    )
    stages = EvolutionStageOrchestrator(
        workspace=cycle.workspace / "unknown-chain",
        artifacts=cycle.artifacts,
        ledger=cycle.ledger,
        runner=runner,
        investigator=cycle.composition.investigator,
        builder=cycle.composition.builder,
        reviewer=cycle.composition.reviewer,
        evaluator=cycle.composition.evaluator,
        materializer=cycle.composition.materializer,
        baseline=cycle._baseline_generation(),
        plan=plan,
        evaluation_suite=cycle.composition.bootstrap.evaluation_suite,
        subject_plugin_name="microworld",
        subject_plugin_source="test-unknown-chain",
    )
    stages.run(until=StageName.INVESTIGATE)
    issue = stages.completed_stage(StageName.DIAGNOSE)
    investigation = stages.completed_stage(StageName.INVESTIGATE)
    assert issue.classification.primary == FailureLayer.INSUFFICIENT_EVIDENCE
    assert issue.proposed_resolution == ResolutionKind.BUILD_PROBE
    assert issue.required_effect is None
    assert investigation.candidate_operations == []
    assert investigation.remaining_unknowns
    with pytest.raises(ProbePlanningError):
        MicroworldProbePlanner(
            runner=runner,
            trace_directory=tmp_path / "unknown-trace",
        ).plan(
            issue=issue,
            investigation=investigation,
            parent=cycle._baseline_generation(),
            probe_id="probe-persisted-unknown",
        )


def test_probe_enters_from_persisted_single_case_chain_and_guards_specify(
    tmp_path: Path,
) -> None:
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "workspace")
    baseline = cycle._baseline_generation()
    plan = cycle.composition.bootstrap.plan.model_copy(
        update={"diagnostic_scenarios": ["diag-opaque-near"]}
    )

    class CountingArchitect:
        calls = 0

        def specify(self, **_: object) -> object:
            self.calls += 1
            raise AssertionError("permanent architect must not be called for BUILD_PROBE")

    architect = CountingArchitect()
    stages = EvolutionStageOrchestrator(
        workspace=cycle.workspace / "causal-chain",
        artifacts=cycle.artifacts,
        ledger=cycle.ledger,
        runner=cycle.runner,
        investigator=cycle.composition.investigator,
        builder=cycle.composition.builder,
        reviewer=cycle.composition.reviewer,
        evaluator=cycle.composition.evaluator,
        materializer=cycle.composition.materializer,
        baseline=baseline,
        plan=plan,
        evaluation_suite=cycle.composition.bootstrap.evaluation_suite,
        subject_plugin_name="microworld",
        subject_plugin_api_version="1.0",
        subject_plugin_source="test-causal-chain",
        architect=architect,
    )
    stages.run(until=StageName.INVESTIGATE)
    issue = stages.completed_stage(StageName.DIAGNOSE)
    investigation = stages.completed_stage(StageName.INVESTIGATE)
    assert issue.metadata["occurrence_count"] == 1
    assert issue.proposed_resolution == ResolutionKind.BUILD_PROBE
    assert investigation.issue_id == issue.issue_id
    with pytest.raises(ProbeRequiredError):
        stages.invoke(StageName.SPECIFY)
    assert architect.calls == 0
    assert not (stages.stage_directory / "specify.pointer.json").exists()

    ingest_receipt = stages._read_receipt(StageName.INGEST)
    ingest = IngestResult.model_validate(
        cycle.artifacts.read_json(ingest_receipt.output_ref.digest)
    )
    initial_event = next(
        event
        for event_ref in ingest.event_refs
        for event in [cycle.artifacts.read_model(event_ref, TrajectoryEvent)]
        if event.kind == EventKind.OBSERVATION
    )
    issue_receipt = stages._read_receipt(StageName.DIAGNOSE)
    investigation_receipt = stages._read_receipt(StageName.INVESTIGATE)
    permanent_before = _permanent_snapshot(
        cycle,
        cycle.workspace,
        stages.manifest.baseline_ref,
        ingest.capability_ref,
    )
    assert len(cycle.ledger.list_generations()) == 1
    assert not (stages.stage_directory / "specify.pointer.json").exists()
    probe = ProbeOrchestrator(
        workspace=cycle.workspace / "causal-probe",
        artifacts=cycle.artifacts,
        ledger=cycle.ledger,
        baseline_ref=stages.manifest.baseline_ref,
        issue_ref=issue_receipt.output_ref,
        investigation_ref=investigation_receipt.output_ref,
        capability_manifest_ref=ingest.capability_ref,
        initial_observation=initial_event.payload,
        runner=cycle.runner,
        planner=MicroworldProbePlanner(
            runner=cycle.runner,
            trace_directory=cycle.workspace / "causal-probe-trace",
        ),
        builder=MicroworldProbeBuilder(),
        reviewer=MicroworldProbeReviewer(),
        evaluator=MicroworldProbeEvaluator(runner=cycle.runner, baseline=baseline),
        probe_id="probe-causal-chain",
    )
    result = probe.run()
    assert result.disposition.disposition == ProbeDispositionKind.RESOLVED
    assert result.disposition.named_uncertainty == result.plan.evidence_target.named_uncertainty
    assert result.evaluation.dispatch_evidence is not None
    assert result.evaluation.dispatch_evidence.accepted
    assert result.evaluation.dispatch_evidence.changed
    assert result.evaluation.later_observation is not None
    assert result.evaluation.later_observation.completeness == Completeness.COMPLETE
    permanent_after = _permanent_snapshot(
        cycle,
        cycle.workspace,
        stages.manifest.baseline_ref,
        ingest.capability_ref,
    )
    assert permanent_after == permanent_before
    assert len(cycle.ledger.list_generations()) == 1
    assert cycle.ledger.probe_records(result.manifest.probe_id)
