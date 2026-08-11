from __future__ import annotations

import sqlite3

import pytest
from pydantic import ValidationError

from evogen.adapters.agents import RawRoleExecution, RoleInvoker
from evogen.core.enums import AgentRole, RoleOutcome
from evogen.core.ids import sha256_bytes
from evogen.core.models import GenerationManifest, ReviewReport, RoleRequest, RoleResponse
from evogen.storage.artifacts import ArtifactStore
from evogen.storage.ledger import Ledger


def test_ledger_round_trips_generation(tmp_path):
    ledger = Ledger(tmp_path / "evogen.sqlite3")
    generation = GenerationManifest(
        generation_id="gen-1",
        subject="test",
        source_ref="source",
        capability_manifest_digest="0" * 64,
    )
    ledger.add_generation(generation)

    assert ledger.get_generation("gen-1") == generation
    assert ledger.list_generations() == [generation]


class _ReviewBackend:
    def __init__(self, response_id: str) -> None:
        self.response_id = response_id

    timeout_seconds = 5.0

    def execute(self, request: RoleRequest) -> RawRoleExecution:
        response = RoleResponse(
            response_id=self.response_id,
            request_id=request.request_id,
            role=request.role,
            success=True,
            output={
                "review_id": "review-1",
                "candidate_id": "candidate-1",
                "passed": True,
                "checks": {"syntax": True},
                "findings": [],
                "reviewed_files": [],
            },
        )
        return RawRoleExecution(response, b"stdout", b"stderr", 0, RoleOutcome.SUCCESS)


def _retained_invocation(
    tmp_path, *, request_id: str = "request-1", response_id: str = "response-1"
):
    artifacts = ArtifactStore(tmp_path / "artifacts")
    ledger = Ledger(tmp_path / "ledger.sqlite3")
    request = RoleRequest(
        request_id=request_id,
        role=AgentRole.ADVERSARIAL_REVIEWER,
        objective="Review one candidate.",
        input_artifacts={"candidate": "candidate-1"},
        output_contract=ReviewReport.model_json_schema(),
    )
    result = RoleInvoker(
        backend=_ReviewBackend(response_id),
        artifacts=artifacts,
        ledger=ledger,
        provider="test-provider",
        model="test-model",
        authority_id="test-authority",
    ).invoke_with_record(request, ReviewReport)
    return ledger, artifacts, result.invocation


def _rewrite_record(ledger: Ledger, invocation, **updates):
    changed = invocation.model_copy(update=updates)
    serialized = changed.model_dump_json()
    with ledger.connect() as connection:
        connection.execute(
            "UPDATE role_invocations SET record_json=?, record_digest=? "
            "WHERE invocation_id=?",
            (serialized, sha256_bytes(serialized.encode("utf-8")), invocation.invocation_id),
        )
    return changed


def test_v1_role_invocation_migration_backfills_digest_without_data_loss(tmp_path):
    _, _, invocation = _retained_invocation(tmp_path / "source")
    serialized = invocation.model_dump_json()
    path = tmp_path / "v1.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            INSERT INTO meta(key, value) VALUES ('schema_version', '1');
            CREATE TABLE role_invocations (
                invocation_id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                role TEXT NOT NULL,
                outcome TEXT NOT NULL,
                record_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        connection.execute(
            "INSERT INTO role_invocations VALUES (?, ?, ?, ?, ?, ?)",
            (
                invocation.invocation_id,
                invocation.request_id,
                invocation.role.value,
                invocation.outcome.value,
                serialized,
                "2026-01-01 00:00:00",
            ),
        )

    migrated = Ledger(path)
    with migrated.connect() as connection:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(role_invocations)")}
        row = connection.execute(
            "SELECT record_json, record_digest FROM role_invocations WHERE invocation_id=?",
            (invocation.invocation_id,),
        ).fetchone()
        version = connection.execute(
            "SELECT value FROM meta WHERE key='schema_version'"
        ).fetchone()["value"]
    assert "record_digest" in columns
    assert row["record_json"] == serialized
    assert row["record_digest"] == sha256_bytes(serialized.encode("utf-8"))
    assert version == "2"
    assert migrated.get_role_invocation(invocation.invocation_id) == invocation


def test_role_invocation_duplicate_is_accepted_only_byte_identically(tmp_path):
    ledger, _, invocation = _retained_invocation(tmp_path)
    ledger.add_role_invocation(invocation)
    changed = invocation.model_copy(update={"model": "different-model"})
    with pytest.raises(RuntimeError, match="immutable"):
        ledger.add_role_invocation(changed)
    assert ledger.get_role_invocation(invocation.invocation_id) == invocation


def test_role_invocation_replay_catches_sql_identity_tamper(tmp_path):
    ledger, artifacts, invocation = _retained_invocation(tmp_path)
    with ledger.connect() as connection:
        connection.execute(
            "UPDATE role_invocations SET role=? WHERE invocation_id=?",
            (AgentRole.TRACE_ANALYST.value, invocation.invocation_id),
        )
    with pytest.raises(RuntimeError, match="SQL identity"):
        ledger.get_role_invocation(invocation.invocation_id, artifacts)


@pytest.mark.parametrize("column", ["record_json", "record_digest"])
def test_role_invocation_replay_catches_record_tamper(tmp_path, column):
    ledger, artifacts, invocation = _retained_invocation(tmp_path)
    with ledger.connect() as connection:
        if column == "record_json":
            connection.execute(
                "UPDATE role_invocations SET record_json=? WHERE invocation_id=?",
                (invocation.model_dump_json() + " ", invocation.invocation_id),
            )
        else:
            connection.execute(
                "UPDATE role_invocations SET record_digest=? WHERE invocation_id=?",
                ("0" * 64, invocation.invocation_id),
            )
    with pytest.raises(RuntimeError, match="record digest"):
        ledger.get_role_invocation(invocation.invocation_id, artifacts)


def test_role_invocation_replay_catches_transcript_substitution(tmp_path):
    ledger, artifacts, invocation = _retained_invocation(tmp_path / "first")
    _, second_artifacts, second = _retained_invocation(
        tmp_path / "second", request_id="request-2", response_id="response-2"
    )
    substituted = _rewrite_record(
        ledger, invocation, transcript_ref=second.transcript_ref
    )
    # Copying the second transcript into the first store preserves a valid CAS
    # object while exercising transcript-to-invocation mirroring checks.
    artifacts.put_bytes(second_artifacts.read_bytes(second.transcript_ref.digest))
    assert substituted.transcript_ref == second.transcript_ref
    with pytest.raises(RuntimeError, match="transcript invocation identity"):
        ledger.get_role_invocation(invocation.invocation_id, artifacts)


def test_role_invocation_replay_catches_request_substitution(tmp_path):
    ledger, artifacts, invocation = _retained_invocation(tmp_path / "first")
    _, second_artifacts, second = _retained_invocation(
        tmp_path / "second", request_id="request-2", response_id="response-2"
    )
    artifacts.put_bytes(second_artifacts.read_bytes(second.request_ref.digest))
    _rewrite_record(ledger, invocation, request_ref=second.request_ref)
    with pytest.raises(RuntimeError, match="request identity"):
        ledger.get_role_invocation(invocation.invocation_id, artifacts)


def test_role_invocation_replay_catches_response_substitution(tmp_path):
    ledger, artifacts, invocation = _retained_invocation(tmp_path / "first")
    _, second_artifacts, second = _retained_invocation(
        tmp_path / "second", request_id="request-2", response_id="response-2"
    )
    artifacts.put_bytes(second_artifacts.read_bytes(second.response_ref.digest))
    _rewrite_record(
        ledger,
        invocation,
        response_ref=second.response_ref,
        response_id=second.response_id,
    )
    with pytest.raises(RuntimeError, match="response"):
        ledger.get_role_invocation(invocation.invocation_id, artifacts)


def test_role_invocation_replay_catches_typed_output_model_content_mismatch(tmp_path):
    ledger, artifacts, invocation = _retained_invocation(tmp_path)
    # The bytes are a valid RoleResponse but are declared as the expected
    # ReviewReport model; replay must validate both model identity and content.
    wrong = artifacts.put_model(
        RoleResponse(
            response_id="wrong-response",
            request_id="wrong-request",
            role=AgentRole.ADVERSARIAL_REVIEWER,
            success=True,
            output={},
        )
    )
    wrong_ref = wrong.model_copy(update={"model": "ReviewReport"})
    _rewrite_record(
        ledger,
        invocation,
        typed_output_ref=wrong_ref,
        output_digest=wrong_ref.digest,
    )
    with pytest.raises(ValidationError):
        ledger.get_role_invocation(invocation.invocation_id, artifacts)
