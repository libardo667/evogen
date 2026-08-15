"""Fixture-only reader for the two pre-G14 historical KAE traces.

This deliberately does not participate in the EvoGen package or CLI. It keeps
old diagnosis fixtures replayable while production consumes only KAE's strict
current trajectory envelope.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from evogen.core.enums import EventKind
from evogen.core.models import TrajectoryEvent

_FIXTURE_NAMES = {
    "kenshi_missing_close.raw.jsonl": "type",
    "kenshi_same_step_identity.raw.jsonl": "event_type",
}
_KINDS = {
    "run_started": EventKind.RUN_STARTED,
    "observation": EventKind.OBSERVATION,
    "affordances": EventKind.AFFORDANCE_SET,
    "planner_decision": EventKind.DECISION,
    "action_binding": EventKind.BINDING,
    "native_command": EventKind.DISPATCH,
    "action_result": EventKind.EXECUTION_RECEIPT,
    "world_state_update": EventKind.OUTCOME_OBSERVATION,
    "goal_blocked": EventKind.GOAL_BLOCKED,
    "run_finalized": EventKind.RUN_FINISHED,
}


def read_historical_fixture(
    source: Path,
    *,
    generation_id: str,
    scenario_id: str,
    run_id: str,
) -> list[TrajectoryEvent]:
    """Read only the checked-in historical fixtures using their literal schema."""

    source = source.resolve()
    expected_directory = Path(__file__).resolve().parents[1] / "fixtures"
    if source.parent != expected_directory or source.name not in _FIXTURE_NAMES:
        raise ValueError("historical KAE reader accepts only its two checked-in fixtures")

    kind_key = _FIXTURE_NAMES[source.name]
    events: list[TrajectoryEvent] = []
    with source.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            raw = json.loads(line)
            if not isinstance(raw, dict) or not isinstance(raw.get(kind_key), str):
                raise ValueError(f"malformed historical fixture record {index}")
            raw_kind = raw[kind_key]
            kind = _KINDS.get(raw_kind)
            if kind is None:
                raise ValueError(f"unmapped historical fixture event {raw_kind!r}")
            payload = raw.get("payload")
            if not isinstance(payload, dict):
                raise ValueError(f"historical fixture payload {index} is not an object")
            events.append(
                TrajectoryEvent(
                    envelope_version="1.0",
                    event_id=f"historical-fixture-{index:02d}",
                    run_id=run_id,
                    generation_id=generation_id,
                    scenario_id=scenario_id,
                    sequence=index,
                    recorded_at=datetime(2026, 8, 15, tzinfo=UTC) + timedelta(seconds=index),
                    kind=kind,
                    world_revision=_revision(raw),
                    source_event_type=raw_kind,
                    source_event_id=_source_id(raw),
                    source_sequence=_source_sequence(raw),
                    source_step_index=_source_step(raw),
                    source_world_revision=_revision(raw),
                    payload={**payload, "raw": raw},
                )
            )
    return events


def _source_id(raw: dict[str, Any]) -> str | None:
    value = raw.get("event_id", raw.get("id"))
    return str(value) if isinstance(value, (str, int)) and not isinstance(value, bool) else None


def _source_sequence(raw: dict[str, Any]) -> int | None:
    value = raw.get("event_sequence")
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _source_step(raw: dict[str, Any]) -> int | None:
    value = raw.get("step_index")
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _revision(raw: dict[str, Any]) -> str | None:
    value = raw.get("world_revision", raw.get("telemetry_sequence"))
    if value is None:
        payload = raw.get("payload")
        if isinstance(payload, dict):
            value = payload.get("telemetry_sequence", payload.get("revision"))
    return str(value) if isinstance(value, (str, int)) and not isinstance(value, bool) else None
