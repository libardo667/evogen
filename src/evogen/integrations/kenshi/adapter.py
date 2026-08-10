from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evogen.core.enums import EventKind
from evogen.core.ids import new_id
from evogen.core.models import TrajectoryEvent


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
                if _already_normalized(raw):
                    normalized = TrajectoryEvent.model_validate(raw)
                    if normalized.generation_id != generation_id:
                        normalized = normalized.model_copy(
                            update={"generation_id": generation_id}
                        )
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
                sequence = _sequence(raw, fallback=len(events))
                events.append(
                    TrajectoryEvent(
                        event_id=str(raw.get("event_id") or raw.get("id") or new_id("kae-evt")),
                        run_id=resolved_run_id,
                        generation_id=generation_id,
                        scenario_id=scenario_id,
                        sequence=sequence,
                        recorded_at=_timestamp(raw),
                        kind=kind,
                        world_revision=_world_revision(raw),
                        payload=normalized_payload,
                    )
                )
        events.sort(key=lambda event: (event.sequence, event.event_id))
        _assert_unique_sequences(events)
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


def _already_normalized(raw: dict[str, Any]) -> bool:
    required = {
        "event_id",
        "run_id",
        "generation_id",
        "scenario_id",
        "sequence",
        "kind",
        "payload",
    }
    return required.issubset(raw)


def _raw_kind(raw: dict[str, Any]) -> str:
    for key in ("event_type", "type", "kind", "name"):
        value = raw.get(key)
        if isinstance(value, str):
            return value
    return "unknown"


def _sequence(raw: dict[str, Any], *, fallback: int) -> int:
    for key in ("sequence", "event_sequence", "index", "step_index"):
        value = raw.get(key)
        if isinstance(value, int) and value >= 0:
            return value
    return fallback


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
        value = raw.get(key)
        if isinstance(value, (str, int)):
            return str(value)
    payload = raw.get("payload")
    if isinstance(payload, dict):
        for key in ("world_revision", "telemetry_sequence", "revision"):
            value = payload.get(key)
            if isinstance(value, (str, int)):
                return str(value)
    return None


def _assert_unique_sequences(events: list[TrajectoryEvent]) -> None:
    seen: set[int] = set()
    for event in events:
        if event.sequence in seen:
            raise ValueError(
                f"Converted KAE trajectory contains duplicate sequence {event.sequence}"
            )
        seen.add(event.sequence)
