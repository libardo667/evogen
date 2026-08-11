from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from evogen.core.enums import StageName
from evogen.core.models import (
    ArtifactRef,
    CapabilityManifest,
    CycleManifest,
    DistilledTrace,
    IngestResult,
    StageReceipt,
    TrajectoryEvent,
)
from evogen.storage.artifacts import ArtifactStore

ROOT = Path(__file__).parents[1]


def _evogen(workspace: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = {
        **os.environ,
        "PYTHONPATH": str(ROOT / "src")
        + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else ""),
    }
    return subprocess.run(
        [sys.executable, "-m", "evogen", *arguments, "--workspace", str(workspace)],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def _files(workspace: Path) -> dict[str, str]:
    return {
        str(path.relative_to(workspace)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(workspace.rglob("*"))
        if path.is_file()
    }


def _semantic_result(workspace: Path) -> dict[str, object]:
    result = json.loads((workspace / "cycle-result.json").read_text(encoding="utf-8"))
    random_keys = {
        "created_at",
        "started_at",
        "finished_at",
        "issue_id",
        "report_id",
        "spec_id",
        "candidate_id",
        "experiment_id",
        "decision_id",
        "review_id",
        "run_id",
        "event_id",
        "trace_digest",
        "retained_generation_id",
        "retained_from_candidate",
        "closed_issue",
    }

    def normalized(value: object) -> object:
        if isinstance(value, dict):
            return {
                key: (
                    "<artifact>"
                    if key
                    in {
                        "issue",
                        "issue_object",
                        "specification",
                        "specification_object",
                        "review_object",
                        "experiment",
                        "experiment_object",
                        "capability_manifest",
                        "capability_manifest_digest",
                    }
                    else normalized(item)
                )
                for key, item in sorted(value.items())
                if key not in random_keys
            }
        if isinstance(value, list):
            return [normalized(item) for item in value]
        if isinstance(value, str):
            value = value.replace(str(workspace), "<workspace>")
            value = re.sub(r"candidate-[0-9a-f]+", "<candidate>", value)
            value = re.sub(r"gen-[0-9a-f]+", "<generation>", value)
            value = re.sub(r"issue-[0-9a-f]+", "<issue>", value)
            return value
        return value

    candidate = normalized(result["candidate"])
    decision = normalized(result["decision"])
    experiment = normalized(result["experiment"])
    return {
        "verdict": decision["verdict"],
        "issue": normalized(result["issue"]),
        "investigation": normalized(result["investigation"]),
        "specification": normalized(result["specification"]),
        "candidate": candidate,
        "review": normalized(result["review"]),
        "experiment": experiment,
        "decision": decision,
        "retained": normalized(result["retained_generation"]),
    }


def _lineage_join(workspace: Path) -> tuple[str, str, str, str]:
    with sqlite3.connect(workspace / "evogen.sqlite3") as connection:
        row = connection.execute(
            """
            SELECT l.parent_generation_id, l.child_generation_id,
                   l.candidate_id, l.decision_id
            FROM lineage AS l
            JOIN candidates AS c ON c.candidate_id = l.candidate_id
            JOIN decisions AS d ON d.decision_id = l.decision_id
            JOIN generations AS g ON g.generation_id = l.child_generation_id
            """
        ).fetchone()
    assert row is not None
    return tuple(row)  # type: ignore[return-value]


def _lineage_semantics(workspace: Path) -> tuple[object, ...]:
    with sqlite3.connect(workspace / "evogen.sqlite3") as connection:
        row = connection.execute(
            """
            SELECT parent.manifest_json, child.manifest_json,
                   candidate.candidate_json, decision.decision_json
            FROM lineage
            JOIN generations AS parent ON parent.generation_id = lineage.parent_generation_id
            JOIN generations AS child ON child.generation_id = lineage.child_generation_id
            JOIN candidates AS candidate ON candidate.candidate_id = lineage.candidate_id
            JOIN decisions AS decision ON decision.decision_id = lineage.decision_id
            """
        ).fetchone()
    assert row is not None
    parent, child, candidate, decision = (json.loads(value) for value in row)
    return (
        parent["source_ref"],
        child["source_ref"],
        candidate["source_digest"],
        decision["verdict"],
        tuple(decision["passed_rules"]),
        tuple(decision["failed_rules"]),
    )


def test_individual_stages_are_ordered_and_idempotent(tmp_path: Path) -> None:
    workspace = tmp_path / "individual"
    for stage in StageName:
        completed = _evogen(workspace, "stage", stage.value)
        assert completed.returncode == 0, completed.stderr
    pointers = _files(workspace / "stages")
    artifacts = _files(workspace / "artifacts")
    lineage = _files(workspace)["evogen.sqlite3"]
    authoritative = _files(workspace)
    replay = _evogen(workspace, "cycle")
    assert replay.returncode == 0, replay.stderr
    assert _files(workspace) == authoritative
    assert _files(workspace / "stages") == pointers
    assert _files(workspace / "artifacts") == artifacts
    assert _files(workspace)["evogen.sqlite3"] == lineage


def test_read_only_status_and_result_do_not_change_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "read-only"
    assert _evogen(workspace, "cycle").returncode == 0
    before = _files(workspace)
    assert _evogen(workspace, "status").returncode == 0
    assert _files(workspace) == before
    assert _evogen(workspace, "show-result").returncode == 0
    assert _files(workspace) == before


def test_completed_replay_uses_cas_events_not_mutable_trace_jsonl(tmp_path: Path) -> None:
    workspace = tmp_path / "cas-replay"
    assert _evogen(workspace, "cycle").returncode == 0
    trace = next((workspace / "traces" / "diagnostic").glob("*.jsonl"))
    trace.write_text("not authoritative replay evidence\n", encoding="utf-8")
    status = _evogen(workspace, "status")
    assert status.returncode == 0, status.stderr


@pytest.mark.parametrize("forged_field", ["run_generation", "capability_digest"])
def test_forged_ingest_cas_objects_fail_closed(tmp_path: Path, forged_field: str) -> None:
    workspace = tmp_path / forged_field
    assert _evogen(workspace, "cycle", "--until", "ingest").returncode == 0
    store = ArtifactStore(workspace / "artifacts")
    pointer_path = workspace / "stages" / "ingest.pointer.json"
    pointer_value = json.loads(pointer_path.read_text(encoding="utf-8"))
    receipt = store.read_model(
        ArtifactRef(digest=pointer_value["receipt_digest"], model="StageReceipt"),
        StageReceipt,
    )
    ingest = store.read_model(receipt.output_ref, IngestResult)
    if forged_field == "run_generation":
        selected_run = ingest.runs[0]
        forged_run = selected_run.model_copy(update={"generation_id": "forged-generation"})
        run_refs = [
            store.put_model(forged_run) if run.run_id == selected_run.run_id else ref
            for ref, run in zip(ingest.run_refs, ingest.runs, strict=True)
        ]
        event_refs = []
        for ref in ingest.event_refs:
            event = store.read_model(ref, TrajectoryEvent)
            if event.run_id == selected_run.run_id:
                event_refs.append(
                    store.put_model(event.model_copy(update={"generation_id": "forged-generation"}))
                )
            else:
                event_refs.append(ref)
        forged_ingest = ingest.model_copy(
            update={
                "runs": [forged_run, *ingest.runs[1:]],
                "run_refs": run_refs,
                "event_refs": event_refs,
            }
        )
    else:
        capability = store.read_model(ingest.capability_ref, CapabilityManifest)
        forged_capability = capability.model_copy(update={"generation_id": "forged-generation"})
        forged_ingest = ingest.model_copy(
            update={"capability_ref": store.put_model(forged_capability)}
        )
    forged_output = store.put_model(forged_ingest)
    forged_receipt = receipt.model_copy(update={"output_ref": forged_output})
    pointer_value["receipt_digest"] = store.put_model(forged_receipt).digest
    pointer_path.write_text(json.dumps(pointer_value), encoding="utf-8")
    failed = _evogen(workspace, "status")
    assert failed.returncode != 0


def test_review_and_evaluate_persist_candidate_lifecycle_status(tmp_path: Path) -> None:
    workspace = tmp_path / "lifecycle"
    for stage in ("ingest", "distill", "diagnose", "investigate", "specify", "build"):
        completed = _evogen(workspace, "stage", stage)
        assert completed.returncode == 0, completed.stderr
    reviewed = _evogen(workspace, "stage", "review")
    assert reviewed.returncode == 0, reviewed.stderr
    with sqlite3.connect(workspace / "evogen.sqlite3") as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM candidates WHERE status='reviewed'"
            ).fetchone()
            == (1,)
        )
    evaluated = _evogen(workspace, "stage", "evaluate")
    assert evaluated.returncode == 0, evaluated.stderr
    with sqlite3.connect(workspace / "evogen.sqlite3") as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM candidates WHERE status='evaluated'"
            ).fetchone()
            == (1,)
        )


def test_subprocess_resume_matches_uninterrupted_semantics(tmp_path: Path) -> None:
    resumed = tmp_path / "resumed"
    first = _evogen(resumed, "cycle", "--until", "diagnose")
    assert first.returncode == 0, first.stderr
    assert not (resumed / "stages" / "investigate.pointer.json").exists()
    second = _evogen(resumed, "cycle")
    assert second.returncode == 0, second.stderr

    uninterrupted = tmp_path / "uninterrupted"
    complete = _evogen(uninterrupted, "cycle")
    assert complete.returncode == 0, complete.stderr
    assert _semantic_result(resumed) == _semantic_result(uninterrupted)
    assert _lineage_semantics(resumed) == _lineage_semantics(uninterrupted)
    for workspace in (resumed, uninterrupted):
        parent, child, candidate_id, decision_id = _lineage_join(workspace)
        result = json.loads((workspace / "cycle-result.json").read_text(encoding="utf-8"))
        assert parent == result["baseline_generation"]["generation_id"]
        assert child == result["retained_generation"]["generation_id"]
        assert child == result["decision"]["retained_generation_id"]
        assert candidate_id == result["candidate"]["candidate_id"]
        assert decision_id == result["decision"]["decision_id"]


@pytest.mark.parametrize(
    "tamper",
    [
        "cas",
        "manifest",
        "bootstrap",
        "chain",
        "prior_pointer",
        "forged_receipt",
        "forged_distill",
        "candidate",
    ],
)
def test_integrity_tampering_fails_closed(tmp_path: Path, tamper: str) -> None:
    workspace = tmp_path / tamper
    assert _evogen(workspace, "cycle").returncode == 0
    if tamper == "cas":
        pointer = json.loads(
            (workspace / "stages" / "distill.pointer.json").read_text(encoding="utf-8")
        )
        receipt_digest = pointer["receipt_digest"]
        receipt_path = workspace / "artifacts" / "sha256" / receipt_digest[:2] / receipt_digest[2:]
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        output_digest = receipt["output_ref"]["digest"]
        output_path = workspace / "artifacts" / "sha256" / output_digest[:2] / output_digest[2:]
        output_path.write_bytes(b"corrupt")
        command = ("cycle",)
    elif tamper == "manifest":
        pointer = workspace / "cycle-manifest.pointer.json"
        value = json.loads(pointer.read_text(encoding="utf-8"))
        value["digest"] = "0" * 64
        pointer.write_text(json.dumps(value), encoding="utf-8")
        command = ("status",)
    elif tamper == "bootstrap":
        pointer = workspace / "cycle-manifest.pointer.json"
        pointer_value = json.loads(pointer.read_text(encoding="utf-8"))
        store = ArtifactStore(workspace / "artifacts")
        manifest = store.read_model(
            ArtifactRef(digest=pointer_value["digest"], model="CycleManifest"),
            CycleManifest,
        )
        forged = manifest.model_copy(update={"subject_generation_fingerprint": "f" * 64})
        pointer_value["digest"] = store.put_model(forged).digest
        pointer.write_text(json.dumps(pointer_value), encoding="utf-8")
        command = ("status",)
    elif tamper == "chain":
        pointer = workspace / "stages" / "select.pointer.json"
        value = json.loads(pointer.read_text(encoding="utf-8"))
        value["receipt_digest"] = "0" * 64
        pointer.write_text(json.dumps(value), encoding="utf-8")
        command = ("show-result",)
    elif tamper == "prior_pointer":
        pointer = workspace / "stages" / "evaluate.pointer.json"
        value = json.loads(pointer.read_text(encoding="utf-8"))
        value["stage"] = "ingest"
        pointer.write_text(json.dumps(value), encoding="utf-8")
        command = ("show-result",)
    elif tamper == "forged_receipt":
        pointer = workspace / "stages" / "select.pointer.json"
        value = json.loads(pointer.read_text(encoding="utf-8"))
        store = ArtifactStore(workspace / "artifacts")
        receipt = store.read_model(
            ArtifactRef(digest=value["receipt_digest"], model="StageReceipt"),
            StageReceipt,
        )
        forged = receipt.model_copy(update={"subject": "forged-subject"})
        value["receipt_digest"] = store.put_model(forged).digest
        pointer.write_text(json.dumps(value), encoding="utf-8")
        command = ("show-result",)
    elif tamper == "forged_distill":
        pointer = workspace / "stages" / "distill.pointer.json"
        value = json.loads(pointer.read_text(encoding="utf-8"))
        store = ArtifactStore(workspace / "artifacts")
        receipt = store.read_model(
            ArtifactRef(digest=value["receipt_digest"], model="StageReceipt"),
            StageReceipt,
        )
        distilled = store.read_model(receipt.output_ref, DistilledTrace)
        forged_output = distilled.model_copy(update={"event_count": distilled.event_count + 1})
        forged_receipt = receipt.model_copy(update={"output_ref": store.put_model(forged_output)})
        value["receipt_digest"] = store.put_model(forged_receipt).digest
        pointer.write_text(json.dumps(value), encoding="utf-8")
        command = ("status",)
    else:
        candidate = json.loads(
            (workspace / "stages" / "build.pointer.json").read_text(encoding="utf-8")
        )
        receipt_digest = candidate["receipt_digest"]
        receipt_path = workspace / "artifacts" / "sha256" / receipt_digest[:2] / receipt_digest[2:]
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        output_digest = receipt["output_ref"]["digest"]
        output_path = workspace / "artifacts" / "sha256" / output_digest[:2] / output_digest[2:]
        candidate_manifest = json.loads(output_path.read_text(encoding="utf-8"))
        changed = (
            workspace
            / "candidates"
            / candidate_manifest["candidate_id"]
            / "plugins"
            / "inspect_container.py"
        )
        changed.write_text(changed.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")
        command = ("show-result",)
    failed = _evogen(workspace, *command)
    assert failed.returncode != 0
