from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evogen.core.enums import EventKind
from evogen.core.ids import new_id
from evogen.core.models import TrajectoryEvent
from evogen.trace.io import (
    TrajectoryRecordMode,
    classify_trajectory_record,
    parse_trajectory_event_record,
)

_RAW_KIND_MAP: dict[str, EventKind] = {
    "run_started": EventKind.RUN_STARTED,
    "observation": EventKind.OBSERVATION,
    "observation_delta": EventKind.OBSERVATION_DELTA,
    "world_state_update": EventKind.OUTCOME_OBSERVATION,
    "affordances": EventKind.AFFORDANCE_SET,
    "affordance_set": EventKind.AFFORDANCE_SET,
    "planner_decision": EventKind.DECISION,
    "decision": EventKind.DECISION,
    "action_binding": EventKind.BINDING,
    "binding": EventKind.BINDING,
    "native_command": EventKind.DISPATCH,
    "dispatch": EventKind.DISPATCH,
    "action_result": EventKind.EXECUTION_RECEIPT,
    "execution_receipt": EventKind.EXECUTION_RECEIPT,
    "memory_update": EventKind.MEMORY_UPDATE,
    "human_intervention": EventKind.HUMAN_INTERVENTION,
    "recovery": EventKind.RECOVERY,
    "safety_event": EventKind.ERROR,
    "error": EventKind.ERROR,
    "goal_blocked": EventKind.GOAL_BLOCKED,
    "goal_achieved": EventKind.GOAL_ACHIEVED,
    "run_finalized": EventKind.RUN_FINISHED,
    "run_finished": EventKind.RUN_FINISHED,
}


class KenshiJsonlAdapter:
    """Normalize KAE-like event JSONL without making domain claims for it.

    KAE has evolved over time, so this adapter accepts a small alias vocabulary
    and preserves each original object under ``payload.raw``. Unknown kinds are
    either skipped or rejected; they are never silently relabeled as proof of a
    world outcome.
    """

    def convert(
        self,
        source: Path,
        *,
        generation_id: str,
        scenario_id: str,
        run_id: str | None = None,
        strict: bool = False,
    ) -> list[TrajectoryEvent]:
        resolved_run_id = run_id or new_id("kae-run")
        events: list[TrajectoryEvent] = []
        observed_mode: TrajectoryRecordMode | None = None
        normalized_source_run_ids: set[str] = set()
        normalized_event_ids: set[str] = set()
        with source.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    raw = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON at {source}:{line_number}: {exc}") from exc
                if not isinstance(raw, dict):
                    raise ValueError(f"Expected object at {source}:{line_number}")
                try:
                    mode = classify_trajectory_record(raw)
                except ValueError as exc:
                    raise ValueError(f"Invalid event at {source}:{line_number}: {exc}") from exc
                if observed_mode is not None and mode != observed_mode:
                    raise ValueError(
                        f"Invalid event at {source}:{line_number}: mixed KAE record modes; "
                        f"observed {observed_mode}, found {mode}"
                    )
                observed_mode = mode
                if mode in {"alpha", "current"}:
                    try:
                        normalized = parse_trajectory_event_record(raw)
                    except ValueError as exc:
                        raise ValueError(
                            f"Invalid normalized event at {source}:{line_number}: {exc}"
                        ) from exc
                    if normalized.generation_id != generation_id:
                        normalized = normalized.model_copy(
                            update={"generation_id": generation_id}
                        )
                    normalized_source_run_ids.add(normalized.run_id)
                    if len(normalized_source_run_ids) > 1:
                        raise ValueError(
                            f"Invalid event at {source}:{line_number}: normalized source "
                            f"contains multiple run IDs {sorted(normalized_source_run_ids)}"
                        )
                    if normalized.event_id in normalized_event_ids:
                        raise ValueError(
                            f"Invalid event at {source}:{line_number}: duplicate normalized "
                            f"event_id {normalized.event_id!r}"
                        )
                    normalized_event_ids.add(normalized.event_id)
                    if normalized.scenario_id != scenario_id:
                        normalized = normalized.model_copy(update={"scenario_id": scenario_id})
                    if run_id is not None and normalized.run_id != resolved_run_id:
                        normalized = normalized.model_copy(update={"run_id": resolved_run_id})
                    events.append(normalized)
                    continue

                raw_kind = _raw_kind(raw)
                kind = _RAW_KIND_MAP.get(raw_kind)
                if kind is None:
                    if strict:
                        raise ValueError(
                            f"Unknown KAE event kind {raw_kind!r} at {source}:{line_number}"
                        )
                    continue
                payload = raw.get("payload")
                if not isinstance(payload, dict):
                    payload = {}
                normalized_payload = {**payload, "raw": raw}
                try:
                    world_revision = _world_revision(raw)
                    source_event_id = _source_id(raw)
                    source_sequence = _source_sequence(raw)
                    source_step_index = _source_step_index(raw)
                except ValueError as exc:
                    raise ValueError(
                        f"Malformed KAE source metadata at {source}:{line_number}: {exc}"
                    ) from exc
                events.append(
                    TrajectoryEvent(
                        envelope_version="1.0",
                        event_id=new_id("kae-evt"),
                        run_id=resolved_run_id,
                        generation_id=generation_id,
                        scenario_id=scenario_id,
                        sequence=len(events),
                        recorded_at=_timestamp(raw),
                        kind=kind,
                        world_revision=world_revision,
                        source_event_type=raw_kind,
                        source_event_id=source_event_id,
                        source_sequence=source_sequence,
                        source_step_index=source_step_index,
                        source_world_revision=world_revision,
                        payload=normalized_payload,
                    )
                )
        _assert_strictly_increasing_sequences(events)
        _assert_single_run(events)
        return events

    def convert_to_file(
        self,
        source: Path,
        destination: Path,
        **kwargs: Any,
    ) -> list[TrajectoryEvent]:
        events = self.convert(source, **kwargs)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            "".join(event.model_dump_json() + "\n" for event in events),
            encoding="utf-8",
        )
        return events


def _raw_kind(raw: dict[str, Any]) -> str:
    for key in ("event_type", "type", "kind", "name"):
        value = raw.get(key)
        if isinstance(value, str):
            return value
    return "unknown"


def _source_sequence(raw: dict[str, Any]) -> int | None:
    for key in ("event_sequence", "sequence", "index"):
        if key not in raw or raw[key] is None:
            continue
        value = raw[key]
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        raise ValueError(f"{key} must be an integer or null")
    return None


def _source_step_index(raw: dict[str, Any]) -> int | None:
    if "step_index" not in raw or raw["step_index"] is None:
        return None
    value = raw["step_index"]
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise ValueError("step_index must be an integer or null")


def _source_id(raw: dict[str, Any]) -> str | None:
    for key in ("event_id", "id"):
        if key not in raw or raw[key] is None:
            continue
        value = raw[key]
        if isinstance(value, (str, int)) and not isinstance(value, bool):
            return str(value)
        raise ValueError(f"{key} must be a string, integer, or null")
    return None


def _timestamp(raw: dict[str, Any]) -> datetime:
    for key in ("recorded_at", "timestamp", "created_at"):
        value = raw.get(key)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                continue
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    return datetime.now(UTC)


def _world_revision(raw: dict[str, Any]) -> str | None:
    for key in ("world_revision", "telemetry_sequence", "revision"):
        if key not in raw or raw[key] is None:
            continue
        value = raw[key]
        if isinstance(value, (str, int)) and not isinstance(value, bool):
            return str(value)
        raise ValueError(f"{key} must be a string, integer, or null")
    payload = raw.get("payload")
    if isinstance(payload, dict):
        for key in ("world_revision", "telemetry_sequence", "revision"):
            if key not in payload or payload[key] is None:
                continue
            value = payload[key]
            if isinstance(value, (str, int)) and not isinstance(value, bool):
                return str(value)
            raise ValueError(f"payload.{key} must be a string, integer, or null")
    return None


def _assert_strictly_increasing_sequences(events: list[TrajectoryEvent]) -> None:
    previous: int | None = None
    for event in events:
        if previous is not None and event.sequence <= previous:
            raise ValueError(
                "Converted KAE trajectory contains non-increasing normalized sequence "
                f"{event.sequence} after {previous}"
            )
        previous = event.sequence


def _assert_single_run(events: list[TrajectoryEvent]) -> None:
    run_ids = {event.run_id for event in events}
    if len(run_ids) > 1:
        raise ValueError(f"Converted KAE trajectory contains multiple run IDs: {sorted(run_ids)}")
