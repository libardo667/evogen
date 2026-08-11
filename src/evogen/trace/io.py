from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from evogen.core.enums import EventKind
from evogen.core.ids import new_id, sha256_bytes
from evogen.core.models import TrajectoryEvent

TrajectoryRecordMode = Literal["alpha", "current", "raw"]
_MIGRATION_FIELDS = {
    "envelope_version",
    "source_event_type",
    "source_event_id",
    "source_sequence",
    "source_step_index",
    "source_world_revision",
}
_NORMALIZED_CORE_FIELDS = {
    "event_id",
    "run_id",
    "generation_id",
    "scenario_id",
    "sequence",
    "kind",
}


class TrajectoryRecorder:
    """Append-only event recorder with deterministic sequence ownership."""

    def __init__(
        self,
        *,
        path: Path,
        run_id: str,
        generation_id: str,
        scenario_id: str,
    ) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id
        self.generation_id = generation_id
        self.scenario_id = scenario_id
        self._sequence = 0
        self._events: list[TrajectoryEvent] = []

    @property
    def events(self) -> list[TrajectoryEvent]:
        return list(self._events)

    def record(
        self,
        kind: EventKind,
        payload: dict[str, Any] | None = None,
        *,
        world_revision: str | None = None,
        source_event_type: str | None = None,
        source_event_id: str | None = None,
        source_sequence: int | None = None,
        source_step_index: int | None = None,
        source_world_revision: str | None = None,
    ) -> TrajectoryEvent:
        event = TrajectoryEvent(
            envelope_version="1.0",
            event_id=new_id("evt"),
            run_id=self.run_id,
            generation_id=self.generation_id,
            scenario_id=self.scenario_id,
            sequence=self._sequence,
            kind=kind,
            world_revision=world_revision,
            source_event_type=source_event_type,
            source_event_id=source_event_id,
            source_sequence=source_sequence,
            source_step_index=source_step_index,
            source_world_revision=source_world_revision,
            payload=payload or {},
        )
        self._sequence += 1
        self._events.append(event)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(event.model_dump_json())
            handle.write("\n")
        return event

    def digest(self) -> str:
        return sha256_bytes(self.path.read_bytes())


def read_jsonl_events(path: Path) -> list[TrajectoryEvent]:
    events: list[TrajectoryEvent] = []
    seen_event_ids: set[str] = set()
    run_id: str | None = None
    previous_sequence: int | None = None
    observed_mode: TrajectoryRecordMode | None = None
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                event, mode = parse_trajectory_event_json_with_mode(stripped)
            except ValueError as exc:
                raise ValueError(f"Invalid event at {path}:{line_number}: {exc}") from exc
            if observed_mode is not None and mode != observed_mode:
                raise ValueError(
                    f"Invalid event at {path}:{line_number}: mixed normalized envelope modes; "
                    f"observed {observed_mode}, found {mode}"
                )
            observed_mode = mode
            if event.event_id in seen_event_ids:
                raise ValueError(
                    f"Invalid event at {path}:{line_number}: duplicate event_id {event.event_id!r}"
                )
            if previous_sequence is not None and event.sequence <= previous_sequence:
                raise ValueError(
                    f"Invalid event at {path}:{line_number}: sequence {event.sequence} is not "
                    f"strictly greater than {previous_sequence}"
                )
            if run_id is None:
                run_id = event.run_id
            elif event.run_id != run_id:
                raise ValueError(
                    f"Invalid event at {path}:{line_number}: multiple run IDs "
                    f"({run_id!r}, {event.run_id!r})"
                )
            seen_event_ids.add(event.event_id)
            previous_sequence = event.sequence
            events.append(event)
    return events


def parse_trajectory_event_json(raw: str) -> TrajectoryEvent:
    """Parse a current event or upgrade one complete alpha event record.

    The alpha envelope had no version or source provenance fields.  Only a
    wholly-unmigrated record is accepted at this compatibility boundary;
    partially-added fields are rejected so provenance cannot be silently lost.
    """

    event, _ = parse_trajectory_event_json_with_mode(raw)
    return event


def parse_trajectory_event_json_with_mode(
    raw: str,
) -> tuple[TrajectoryEvent, Literal["alpha", "current"]]:
    try:
        record = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc
    event, mode = parse_trajectory_event_record_with_mode(record)
    if mode == "raw":
        raise ValueError("raw KAE record is not a normalized trajectory event")
    return event, mode


def parse_trajectory_event_record(record: object) -> TrajectoryEvent:
    event, _ = parse_trajectory_event_record_with_mode(record)
    return event


def parse_trajectory_event_record_with_mode(
    record: object,
) -> tuple[TrajectoryEvent, TrajectoryRecordMode]:
    mode = classify_trajectory_record(record)
    if mode == "raw":
        return _raise_raw_record_mode()
    assert isinstance(record, dict)
    present = _MIGRATION_FIELDS.intersection(record)
    if not present:
        upgraded = dict(record)
        upgraded.update(
            {
                "envelope_version": "1.0",
                "source_event_type": None,
                "source_event_id": None,
                "source_sequence": None,
                "source_step_index": None,
                "source_world_revision": None,
            }
        )
        record = upgraded
    if record.get("envelope_version") != "1.0":
        raise ValueError(
            "unsupported trajectory envelope version "
            f"{record.get('envelope_version')!r}"
        )
    try:
        return TrajectoryEvent.model_validate(record), mode
    except ValueError as exc:
        raise ValueError(str(exc)) from exc


def _raise_raw_record_mode() -> tuple[TrajectoryEvent, TrajectoryRecordMode]:
    raise ValueError("raw KAE record is not a normalized trajectory event")


def classify_trajectory_record(record: object) -> TrajectoryRecordMode:
    """Classify raw, wholly-alpha, and wholly-current record topology."""

    if not isinstance(record, dict):
        raise ValueError("event record must be a JSON object")
    core_present = _NORMALIZED_CORE_FIELDS.issubset(record)
    present = _MIGRATION_FIELDS.intersection(record)
    if not core_present:
        if present:
            raise ValueError(
                "partial normalized trajectory record; normalized core fields are missing"
            )
        return "raw"
    if not present:
        return "alpha"
    if present == _MIGRATION_FIELDS:
        return "current"
    missing = sorted(_MIGRATION_FIELDS - present)
    raise ValueError("partially migrated trajectory event; missing " + ", ".join(missing))
