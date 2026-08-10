from __future__ import annotations

from pathlib import Path
from typing import Any

from evogen.core.enums import EventKind
from evogen.core.ids import new_id, sha256_bytes
from evogen.core.models import TrajectoryEvent


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
    ) -> TrajectoryEvent:
        event = TrajectoryEvent(
            event_id=new_id("evt"),
            run_id=self.run_id,
            generation_id=self.generation_id,
            scenario_id=self.scenario_id,
            sequence=self._sequence,
            kind=kind,
            world_revision=world_revision,
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
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                event = TrajectoryEvent.model_validate_json(stripped)
            except ValueError as exc:
                raise ValueError(f"Invalid event at {path}:{line_number}: {exc}") from exc
            events.append(event)
    return events
