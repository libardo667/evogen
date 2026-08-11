from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from evogen.core.models import (
    CandidateManifest,
    CapabilityIssue,
    ExperimentResult,
    GateDecision,
    GenerationManifest,
    RunRecord,
    TrajectoryEvent,
)
from evogen.trace.io import parse_trajectory_event_json

_ModelT = TypeVar("_ModelT", bound=BaseModel)


class Ledger:
    """SQLite index for immutable JSON records and lineage decisions."""

    SCHEMA_VERSION = 1

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
                """
            )
            row = connection.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO meta(key, value) VALUES('schema_version', ?)",
                    (str(self.SCHEMA_VERSION),),
                )
            elif int(row["value"]) != self.SCHEMA_VERSION:
                raise RuntimeError(
                    f"Unsupported ledger schema {row['value']}; expected {self.SCHEMA_VERSION}"
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
