from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel

from evogen.core.enums import RoleOutcome
from evogen.core.ids import sha256_bytes, stable_digest
from evogen.core.models import (
    CandidateManifest,
    CapabilityIssue,
    ExperimentResult,
    GateDecision,
    GenerationManifest,
    ProbeCandidateManifest,
    ProbeDisposition,
    ProbeEvaluation,
    ProbePlan,
    ProbeReviewReport,
    RoleInvocation,
    RoleRequest,
    RoleResponse,
    RoleTranscript,
    RunRecord,
    TrajectoryEvent,
)
from evogen.trace.io import parse_trajectory_event_json

if TYPE_CHECKING:
    from .artifacts import ArtifactStore

_ModelT = TypeVar("_ModelT", bound=BaseModel)


class Ledger:
    """SQLite index for immutable JSON records and lineage decisions."""

    SCHEMA_VERSION = 2

    def __init__(self, path: Path, *, read_only: bool = False) -> None:
        self.path = path
        self.read_only = read_only
        if read_only:
            if not self.path.is_file():
                raise FileNotFoundError(f"Ledger not found: {self.path}")
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._initialize()

    def connect(self) -> sqlite3.Connection:
        if self.read_only:
            connection = sqlite3.connect(
                f"file:{self.path.resolve()}?mode=ro&immutable=1",
                uri=True,
            )
        else:
            connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        if not self.read_only:
            connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def checkpoint(self) -> None:
        """Materialize WAL pages for deterministic workspace inspection in tests/tools."""
        if self.read_only:
            raise RuntimeError("Read-only ledger cannot checkpoint")
        with self.connect() as connection:
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    def _initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS generations (
                    generation_id TEXT PRIMARY KEY,
                    parent_generation_id TEXT,
                    created_at TEXT NOT NULL,
                    manifest_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    generation_id TEXT NOT NULL,
                    scenario_id TEXT NOT NULL,
                    finished_at TEXT NOT NULL,
                    record_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    UNIQUE(run_id, sequence)
                );

                CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id, sequence);
                CREATE INDEX IF NOT EXISTS idx_runs_generation ON runs(generation_id, scenario_id);

                CREATE TABLE IF NOT EXISTS issues (
                    issue_id TEXT PRIMARY KEY,
                    generation_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    issue_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS candidates (
                    candidate_id TEXT PRIMARY KEY,
                    parent_generation_id TEXT NOT NULL,
                    issue_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    candidate_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS experiments (
                    experiment_id TEXT PRIMARY KEY,
                    candidate_id TEXT NOT NULL,
                    result_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS decisions (
                    decision_id TEXT PRIMARY KEY,
                    candidate_id TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    decision_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS lineage (
                    parent_generation_id TEXT NOT NULL,
                    child_generation_id TEXT NOT NULL,
                    candidate_id TEXT NOT NULL,
                    decision_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(parent_generation_id, child_generation_id)
                );

                CREATE TABLE IF NOT EXISTS probes (
                    probe_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(probe_id, stage)
                );

                CREATE TABLE IF NOT EXISTS role_invocations (
                    invocation_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    record_digest TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            row = connection.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO meta(key, value) VALUES('schema_version', ?)",
                    (str(self.SCHEMA_VERSION),),
                )
            elif int(row["value"]) == 1:
                self._migrate_v1_to_v2(connection)
                connection.execute(
                    "UPDATE meta SET value=? WHERE key='schema_version'",
                    (str(self.SCHEMA_VERSION),),
                )
            elif int(row["value"]) != self.SCHEMA_VERSION:
                raise RuntimeError(
                    f"Unsupported ledger schema {row['value']}; expected {self.SCHEMA_VERSION}"
                )

    @staticmethod
    def _migrate_v1_to_v2(connection: sqlite3.Connection) -> None:
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(role_invocations)")
        }
        if "record_digest" not in columns:
            connection.execute(
                "ALTER TABLE role_invocations ADD COLUMN record_digest TEXT NOT NULL DEFAULT ''"
            )
            rows = connection.execute(
                "SELECT rowid, record_json FROM role_invocations"
            ).fetchall()
            connection.executemany(
                "UPDATE role_invocations SET record_digest=? WHERE rowid=?",
                [
                    (sha256_bytes(row["record_json"].encode("utf-8")), row["rowid"])
                    for row in rows
                ],
            )

    @staticmethod
    def _json(model: BaseModel) -> str:
        return model.model_dump_json()

    @staticmethod
    def _parse(model_type: type[_ModelT], raw: str) -> _ModelT:
        return model_type.model_validate_json(raw)

    def add_generation(self, manifest: GenerationManifest) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO generations(
                    generation_id, parent_generation_id, created_at, manifest_json
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    manifest.generation_id,
                    manifest.parent_generation_id,
                    manifest.created_at.isoformat(),
                    self._json(manifest),
                ),
            )

    def get_generation(self, generation_id: str) -> GenerationManifest:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT manifest_json FROM generations WHERE generation_id=?",
                (generation_id,),
            ).fetchone()
        if row is None:
            raise KeyError(generation_id)
        return self._parse(GenerationManifest, row["manifest_json"])

    def list_generations(self) -> list[GenerationManifest]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT manifest_json FROM generations ORDER BY created_at, generation_id"
            ).fetchall()
        return [self._parse(GenerationManifest, row["manifest_json"]) for row in rows]

    def add_run(self, record: RunRecord, events: Iterable[TrajectoryEvent]) -> None:
        event_list = list(events)
        seen_event_ids: set[str] = set()
        previous_sequence: int | None = None
        for event in event_list:
            if event.run_id != record.run_id:
                raise ValueError(
                    f"Event {event.event_id!r} belongs to run {event.run_id!r}, "
                    f"not {record.run_id!r}"
                )
            if event.generation_id != record.generation_id:
                raise ValueError(
                    f"Event {event.event_id!r} belongs to generation {event.generation_id!r}, "
                    f"not {record.generation_id!r}"
                )
            if event.scenario_id != record.scenario_id:
                raise ValueError(
                    f"Event {event.event_id!r} belongs to scenario {event.scenario_id!r}, "
                    f"not {record.scenario_id!r}"
                )
            if event.event_id in seen_event_ids:
                raise ValueError(f"Duplicate event ID {event.event_id!r} in run")
            if previous_sequence is not None and event.sequence <= previous_sequence:
                raise ValueError(
                    f"Run events must have strictly increasing sequence values; "
                    f"got {event.sequence} after {previous_sequence}"
                )
            seen_event_ids.add(event.event_id)
            previous_sequence = event.sequence
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO runs(
                    run_id, generation_id, scenario_id, finished_at, record_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    record.run_id,
                    record.generation_id,
                    record.scenario_id,
                    record.finished_at.isoformat(),
                    self._json(record),
                ),
            )
            connection.executemany(
                """
                INSERT INTO events(
                    event_id, run_id, sequence, kind, event_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        event.event_id,
                        event.run_id,
                        event.sequence,
                        event.kind.value,
                        self._json(event),
                    )
                    for event in event_list
                ],
            )

    def get_run(self, run_id: str) -> RunRecord:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT record_json FROM runs WHERE run_id=?", (run_id,)
            ).fetchone()
        if row is None:
            raise KeyError(run_id)
        return self._parse(RunRecord, row["record_json"])

    def list_runs(self, generation_id: str | None = None) -> list[RunRecord]:
        sql = "SELECT record_json FROM runs"
        params: tuple[Any, ...] = ()
        if generation_id is not None:
            sql += " WHERE generation_id=?"
            params = (generation_id,)
        sql += " ORDER BY finished_at, run_id"
        with self.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [self._parse(RunRecord, row["record_json"]) for row in rows]

    def events_for_runs(self, run_ids: Iterable[str]) -> list[TrajectoryEvent]:
        ids = list(run_ids)
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        sql = (
            "SELECT event_json FROM events "
            f"WHERE run_id IN ({placeholders}) ORDER BY run_id, sequence"
        )
        with self.connect() as connection:
            rows = connection.execute(sql, ids).fetchall()
        return [parse_trajectory_event_json(row["event_json"]) for row in rows]

    def add_issue(self, issue: CapabilityIssue) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO issues(issue_id, generation_id, status, issue_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    issue.issue_id,
                    issue.subject_generation,
                    issue.status.value,
                    self._json(issue),
                ),
            )

    def get_issue(self, issue_id: str) -> CapabilityIssue:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT issue_json FROM issues WHERE issue_id=?", (issue_id,)
            ).fetchone()
        if row is None:
            raise KeyError(issue_id)
        return self._parse(CapabilityIssue, row["issue_json"])

    def add_candidate(self, candidate: CandidateManifest) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO candidates(
                    candidate_id, parent_generation_id, issue_id, status, candidate_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    candidate.candidate_id,
                    candidate.parent_generation,
                    candidate.issue_id,
                    candidate.status.value,
                    self._json(candidate),
                ),
            )

    def get_candidate(self, candidate_id: str) -> CandidateManifest:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT candidate_json FROM candidates WHERE candidate_id=?", (candidate_id,)
            ).fetchone()
        if row is None:
            raise KeyError(candidate_id)
        return self._parse(CandidateManifest, row["candidate_json"])

    def add_experiment(self, result: ExperimentResult) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO experiments(experiment_id, candidate_id, result_json)
                VALUES (?, ?, ?)
                """,
                (result.experiment_id, result.candidate_id, self._json(result)),
            )

    def add_decision(self, decision: GateDecision) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO decisions(decision_id, candidate_id, verdict, decision_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    decision.decision_id,
                    decision.candidate_id,
                    decision.verdict.value,
                    self._json(decision),
                ),
            )

    def add_lineage(
        self,
        *,
        parent_generation_id: str,
        child_generation_id: str,
        candidate_id: str,
        decision: GateDecision,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO lineage(
                    parent_generation_id, child_generation_id, candidate_id,
                    decision_id, created_at
                ) VALUES (?, ?, ?, ?, datetime('now'))
                """,
                (
                    parent_generation_id,
                    child_generation_id,
                    candidate_id,
                    decision.decision_id,
                ),
            )

    def lineage_rows(self) -> list[dict[str, str]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT parent_generation_id, child_generation_id,
                       candidate_id, decision_id, created_at
                FROM lineage ORDER BY created_at, child_generation_id
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def add_probe_plan(self, plan: ProbePlan) -> None:
        self._add_probe_record(plan.probe_id, "plan", plan)

    def add_probe_candidate(self, candidate: ProbeCandidateManifest) -> None:
        self._add_probe_record(candidate.probe_id, "build", candidate)

    def add_probe_review(self, review: ProbeReviewReport) -> None:
        self._add_probe_record(review.probe_id, "review", review)

    def add_probe_evaluation(self, evaluation: ProbeEvaluation) -> None:
        self._add_probe_record(evaluation.probe_id, "evaluate", evaluation)

    def add_probe_disposition(self, disposition: ProbeDisposition) -> None:
        self._add_probe_record(disposition.probe_id, "dispose", disposition)

    def _add_probe_record(self, probe_id: str, stage: str, record: BaseModel) -> None:
        """Append one immutable probe transition; probe rows are never replaced."""
        serialized = self._json(record)
        try:
            with self.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO probes(probe_id, stage, record_json, created_at)
                    VALUES (?, ?, ?, datetime('now'))
                    """,
                    (probe_id, stage, serialized),
                )
        except sqlite3.IntegrityError as exc:
            with self.connect() as connection:
                row = connection.execute(
                    "SELECT record_json FROM probes WHERE probe_id=? AND stage=?",
                    (probe_id, stage),
                ).fetchone()
            if row is None or row["record_json"] != serialized:
                raise RuntimeError(f"Probe transition {probe_id}/{stage} is immutable") from exc

    def probe_records(self, probe_id: str) -> list[dict[str, str]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT probe_id, stage, record_json, created_at FROM probes "
                "WHERE probe_id=? ORDER BY CASE stage WHEN 'plan' THEN 0 "
                "WHEN 'build' THEN 1 WHEN 'review' THEN 2 WHEN 'evaluate' THEN 3 "
                "WHEN 'dispose' THEN 4 ELSE 5 END, created_at",
                (probe_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def add_role_invocation(self, invocation: RoleInvocation) -> None:
        """Append one immutable invocation; collisions are accepted only byte-for-byte."""
        serialized = self._json(invocation)
        try:
            with self.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO role_invocations(
                        invocation_id, request_id, role, outcome, record_json,
                        record_digest, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                    """,
                    (
                        invocation.invocation_id,
                        invocation.request_id,
                        invocation.role.value,
                        invocation.outcome.value,
                        serialized,
                        sha256_bytes(serialized.encode("utf-8")),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            with self.connect() as connection:
                row = connection.execute(
                    "SELECT record_json FROM role_invocations WHERE invocation_id=?",
                    (invocation.invocation_id,),
                ).fetchone()
            if row is None or row["record_json"] != serialized:
                raise RuntimeError(
                    f"Role invocation {invocation.invocation_id} is immutable"
                ) from exc

    def get_role_invocation(
        self, invocation_id: str, artifacts: ArtifactStore | None = None
    ) -> RoleInvocation:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT request_id, role, outcome, record_json, record_digest "
                "FROM role_invocations WHERE invocation_id=?",
                (invocation_id,),
            ).fetchone()
        if row is None:
            raise KeyError(invocation_id)
        self._verify_record_digest(row["record_json"], row["record_digest"])
        invocation = self._parse(RoleInvocation, row["record_json"])
        if (
            row["request_id"] != invocation.request_id
            or row["role"] != invocation.role.value
            or row["outcome"] != invocation.outcome.value
        ):
            raise RuntimeError("Role invocation SQL identity columns mismatch record")
        if artifacts is not None:
            self._verify_role_refs(invocation, artifacts)
        return invocation

    def list_role_invocations(
        self, artifacts: ArtifactStore | None = None
    ) -> list[RoleInvocation]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT request_id, role, outcome, record_json, record_digest "
                "FROM role_invocations ORDER BY rowid"
            ).fetchall()
        for row in rows:
            self._verify_record_digest(row["record_json"], row["record_digest"])
        values: list[RoleInvocation] = []
        for row in rows:
            value = self._parse(RoleInvocation, row["record_json"])
            if (
                row["request_id"] != value.request_id
                or row["role"] != value.role.value
                or row["outcome"] != value.outcome.value
            ):
                raise RuntimeError("Role invocation SQL identity columns mismatch record")
            values.append(value)
        if artifacts is not None:
            for value in values:
                self._verify_role_refs(value, artifacts)
        return values

    @staticmethod
    def _verify_record_digest(serialized: str, digest: str) -> None:
        if sha256_bytes(serialized.encode("utf-8")) != digest:
            raise RuntimeError("Role invocation ledger record digest mismatch")

    @staticmethod
    def _verify_role_refs(invocation: RoleInvocation, artifacts: ArtifactStore) -> None:
        for reference in (
            invocation.request_ref,
            invocation.transcript_ref,
            invocation.response_ref,
            invocation.typed_output_ref,
            invocation.stdout_ref,
            invocation.stderr_ref,
        ):
            if reference is not None:
                artifacts.read_bytes(reference.digest)
        request = artifacts.read_model(invocation.request_ref, RoleRequest)
        if request.request_id != invocation.request_id or request.role != invocation.role:
            raise RuntimeError("Role request identity mismatch")
        if stable_digest(request.input_artifacts) != invocation.input_digest:
            raise RuntimeError("Role request input digest mismatch")
        if stable_digest(request.output_contract) != invocation.output_contract_digest:
            raise RuntimeError("Role output-contract digest mismatch")
        if invocation.response_ref is not None:
            response = artifacts.read_model(invocation.response_ref, RoleResponse)
            if invocation.response_id != response.response_id:
                raise RuntimeError("Role response ID mismatch")
            if invocation.outcome == RoleOutcome.REQUEST_MISMATCH:
                if response.request_id == request.request_id:
                    raise RuntimeError("Request-mismatch outcome has matching request")
            elif invocation.outcome == RoleOutcome.ROLE_MISMATCH:
                if response.request_id != request.request_id or response.role == request.role:
                    raise RuntimeError("Role-mismatch outcome has inconsistent response")
            elif invocation.outcome == RoleOutcome.UNSUCCESSFUL_RESPONSE:
                if (
                    response.request_id != request.request_id
                    or response.role != request.role
                    or response.success
                ):
                    raise RuntimeError("Unsuccessful role outcome has inconsistent response")
            elif invocation.outcome in {
                RoleOutcome.SUCCESS,
                RoleOutcome.INVALID_TYPED_OUTPUT,
                RoleOutcome.SEMANTIC_LINK_FAILURE,
            } and (
                response.request_id != request.request_id
                or response.role != request.role
                or not response.success
            ):
                raise RuntimeError("Role response identity or success field mismatch")
        elif invocation.response_id is not None:
            raise RuntimeError("Role response ID exists without response reference")
        if invocation.typed_output_ref is not None:
            output_model = Ledger._role_output_model(request)
            artifacts.read_model(invocation.typed_output_ref, output_model)
            output_bytes = artifacts.read_bytes(invocation.typed_output_ref.digest)
            if invocation.output_digest != sha256_bytes(output_bytes):
                raise RuntimeError("Role typed output digest mismatch")
        transcript = artifacts.read_model(invocation.transcript_ref, RoleTranscript)
        if transcript.invocation_id != invocation.invocation_id:
            raise RuntimeError("Role transcript invocation identity mismatch")
        for field in (
            "request_id",
            "role",
            "response_id",
            "request_ref",
            "response_ref",
            "typed_output_ref",
            "stdout_ref",
            "stderr_ref",
            "input_digest",
            "output_contract_digest",
            "output_digest",
            "provider",
            "model",
            "backend",
            "authority_id",
            "outcome",
            "timeout_seconds",
            "process_status",
            "failure",
        ):
            if getattr(transcript, field) != getattr(invocation, field):
                raise RuntimeError(f"Role transcript {field} mismatch")

    @staticmethod
    def _role_output_model(request: RoleRequest) -> type[BaseModel]:
        title = request.output_contract.get("title")
        if not isinstance(title, str) or not title:
            raise RuntimeError("Role output contract has no typed model title")
        # Imported lazily so the storage layer does not participate in schema
        # export initialization.
        from evogen.schema import MODEL_REGISTRY

        matches = {
            model.__name__: model for model in MODEL_REGISTRY.values()
        }
        try:
            return matches[title]
        except KeyError as exc:
            raise RuntimeError(
                f"Role output contract names unregistered model {title!r}"
            ) from exc
