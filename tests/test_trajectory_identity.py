from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from evogen.core.enums import EventKind
from evogen.core.models import RunRecord, TrajectoryEvent
from evogen.integrations.kenshi.adapter import KenshiJsonlAdapter
from evogen.storage.ledger import Ledger
from evogen.trace.io import read_jsonl_events

FIXTURE_DIR = Path(__file__).parent / "fixtures"
RAW_FIXTURE = FIXTURE_DIR / "kenshi_same_step_identity.raw.jsonl"
ALPHA_FIXTURE = FIXTURE_DIR / "trajectory_alpha_normalized.jsonl"


def test_kae_sequence_is_encounter_order_and_source_metadata_is_exact() -> None:
    events = KenshiJsonlAdapter().convert(
        RAW_FIXTURE,
        generation_id="generation",
        scenario_id="scenario",
        run_id="run",
        strict=True,
    )

    assert [event.sequence for event in events] == [0, 1, 2, 3]
    assert [event.kind for event in events] == [
        EventKind.DISPATCH,
        EventKind.EXECUTION_RECEIPT,
        EventKind.OUTCOME_OBSERVATION,
        EventKind.OBSERVATION,
    ]
    assert [event.source_event_type for event in events] == [
        "native_command",
        "action_result",
        "world_state_update",
        "observation",
    ]
    assert [event.source_sequence for event in events] == [99, 1, 0, 77]
    assert [event.source_step_index for event in events] == [7, 7, 7, 7]
    assert [event.source_world_revision for event in events] == ["42", "43", "44", None]
    assert [event.world_revision for event in events] == ["42", "43", "44", None]
    assert [event.source_event_id for event in events[:2]] == [
        "duplicate-source",
        "duplicate-source",
    ]
    assert len({event.event_id for event in events[:2]}) == 2
    assert events[1].kind == EventKind.EXECUTION_RECEIPT
    assert events[1].kind != EventKind.OUTCOME_OBSERVATION
    assert events[0].payload["raw"] == {
        "event_type": "native_command",
        "event_id": "duplicate-source",
        "event_sequence": 99,
        "sequence": 10,
        "index": 1,
        "step_index": 7,
        "world_revision": 42,
        "payload": {"command": "open"},
    }


def test_alpha_reader_upgrades_complete_unversioned_records() -> None:
    events = read_jsonl_events(ALPHA_FIXTURE)

    assert [event.event_id for event in events] == ["alpha-event-1", "alpha-event-2"]
    assert all(event.envelope_version == "1.0" for event in events)
    assert all(
        getattr(event, field) is None
        for event in events
        for field in (
            "source_event_type",
            "source_event_id",
            "source_sequence",
            "source_step_index",
            "source_world_revision",
        )
    )


def test_jsonl_reader_rejects_mixed_alpha_and_current_modes(tmp_path: Path) -> None:
    alpha = json.loads(ALPHA_FIXTURE.read_text(encoding="utf-8").splitlines()[0])
    current = _current_event(event_id="current-event", sequence=1)

    with pytest.raises(ValueError, match="mixed normalized envelope modes"):
        read_jsonl_events(_write_records(tmp_path, "mixed.jsonl", [alpha, current]))


def test_reader_accepts_payload_omitted_alpha_and_current_records(tmp_path: Path) -> None:
    alpha = _alpha_event(event_id="alpha-event", sequence=0)
    current = _current_event(event_id="current-event", sequence=1)
    alpha.pop("payload")
    current.pop("payload")

    alpha_events = read_jsonl_events(_write_records(tmp_path, "alpha-no-payload.jsonl", [alpha]))
    current_events = read_jsonl_events(
        _write_records(tmp_path, "current-no-payload.jsonl", [current])
    )
    assert alpha_events[0].payload == {}
    assert current_events[0].payload == {}


def _write_records(tmp_path: Path, name: str, records: list[dict[str, object]]) -> Path:
    path = tmp_path / name
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
    return path


def _current_event(
    *, event_id: str = "event", run_id: str = "run", sequence: int = 0
) -> dict[str, object]:
    return {
        "envelope_version": "1.0",
        "event_id": event_id,
        "run_id": run_id,
        "generation_id": "generation",
        "scenario_id": "scenario",
        "sequence": sequence,
        "recorded_at": "2026-08-10T12:00:00Z",
        "kind": "observation",
        "world_revision": None,
        "source_event_type": None,
        "source_event_id": None,
        "source_sequence": None,
        "source_step_index": None,
        "source_world_revision": None,
        "payload": {},
    }


def _alpha_event(**overrides: object) -> dict[str, object]:
    event = _current_event(**overrides)
    for field in (
        "envelope_version",
        "source_event_type",
        "source_event_id",
        "source_sequence",
        "source_step_index",
        "source_world_revision",
    ):
        event.pop(field)
    return event


def test_kae_rejects_mixed_record_modes_and_duplicate_normalized_ids(tmp_path: Path) -> None:
    raw = json.loads(RAW_FIXTURE.read_text(encoding="utf-8").splitlines()[0])
    current = _current_event(event_id="current-event")
    alpha = _alpha_event(event_id="alpha-event")
    for name, records in (
        ("raw-current.jsonl", [raw, current]),
        ("alpha-current.jsonl", [alpha, current]),
    ):
        with pytest.raises(ValueError, match="mixed KAE record modes"):
            KenshiJsonlAdapter().convert(
                _write_records(tmp_path, name, records),
                generation_id="generation",
                scenario_id="scenario",
                strict=True,
            )

    duplicate = [
        _current_event(event_id="same", sequence=0),
        _current_event(event_id="same", sequence=1),
    ]
    with pytest.raises(ValueError, match="duplicate normalized event_id"):
        KenshiJsonlAdapter().convert(
            _write_records(tmp_path, "duplicate-normalized.jsonl", duplicate),
            generation_id="generation",
            scenario_id="scenario",
            strict=True,
        )


def test_kae_rejects_multiple_normalized_source_runs_before_rebinding(tmp_path: Path) -> None:
    records = [
        _current_event(event_id="first", run_id="first-run", sequence=0),
        _current_event(event_id="second", run_id="second-run", sequence=1),
    ]
    with pytest.raises(ValueError, match="multiple run IDs"):
        KenshiJsonlAdapter().convert(
            _write_records(tmp_path, "multiple-source-runs.jsonl", records),
            generation_id="generation",
            scenario_id="scenario",
            run_id="rebound-run",
            strict=True,
        )

    one = KenshiJsonlAdapter().convert(
        _write_records(tmp_path, "one-source-run.jsonl", [_current_event()]),
        generation_id="generation",
        scenario_id="scenario",
        run_id="rebound-run",
        strict=True,
    )
    assert one[0].run_id == "rebound-run"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("event_id", True),
        ("event_id", 1.5),
        ("event_id", {"id": "nested"}),
        ("event_sequence", True),
        ("event_sequence", 1.5),
        ("event_sequence", "1"),
        ("event_sequence", {"sequence": 1}),
        ("step_index", True),
        ("step_index", 1.5),
        ("step_index", "1"),
        ("step_index", [1]),
        ("world_revision", True),
        ("world_revision", 1.5),
        ("world_revision", {"revision": 1}),
    ],
)
def test_kae_rejects_malformed_present_source_metadata(
    tmp_path: Path, field: str, value: object
) -> None:
    raw = json.loads(RAW_FIXTURE.read_text(encoding="utf-8").splitlines()[0])
    raw[field] = value
    with pytest.raises(ValueError, match="Malformed KAE source metadata"):
        KenshiJsonlAdapter().convert(
            _write_records(tmp_path, f"malformed-{field}.jsonl", [raw]),
            generation_id="generation",
            scenario_id="scenario",
            strict=True,
        )


def test_kae_does_not_fall_through_malformed_revision_to_payload(tmp_path: Path) -> None:
    raw = json.loads(RAW_FIXTURE.read_text(encoding="utf-8").splitlines()[0])
    raw["world_revision"] = 1.5
    raw["payload"]["revision"] = 99
    with pytest.raises(ValueError, match="Malformed KAE source metadata"):
        KenshiJsonlAdapter().convert(
            _write_records(tmp_path, "malformed-top-level-revision.jsonl", [raw]),
            generation_id="generation",
            scenario_id="scenario",
            strict=True,
        )


@pytest.mark.parametrize(
    ("name", "records", "message"),
    [
        (
            "duplicate.jsonl",
            [_current_event(), _current_event(sequence=1)],
            "duplicate event_id",
        ),
        (
            "duplicate-sequence.jsonl",
            [_current_event(), _current_event(event_id="event-2")],
            "strictly greater",
        ),
        (
            "nonmonotonic.jsonl",
            [_current_event(sequence=1), _current_event(event_id="event-2", sequence=0)],
            "strictly greater",
        ),
        (
            "multiple-runs.jsonl",
            [_current_event(), _current_event(event_id="event-2", run_id="other", sequence=1)],
            "multiple run IDs",
        ),
        (
            "partial.jsonl",
            [
                {
                    key: value
                    for key, value in _current_event().items()
                    if key != "source_event_id"
                }
            ],
            "partially migrated",
        ),
        (
            "unsupported.jsonl",
            [{**_current_event(), "envelope_version": "2.0"}],
            "unsupported trajectory envelope version",
        ),
    ],
)
def test_alpha_boundary_rejects_invalid_migrations(
    tmp_path: Path, name: str, records: list[dict[str, object]], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        read_jsonl_events(_write_records(tmp_path, name, records))


def test_direct_model_requires_complete_supported_envelope() -> None:
    record = _current_event()
    with pytest.raises(ValueError):
        TrajectoryEvent.model_validate(
            {key: value for key, value in record.items() if key != "envelope_version"}
        )
    with pytest.raises(ValueError):
        TrajectoryEvent.model_validate({**record, "envelope_version": "2.0"})
    with pytest.raises(ValueError):
        TrajectoryEvent.model_validate(
            {key: value for key, value in record.items() if key != "source_event_id"}
        )
    with pytest.raises(ValueError):
        TrajectoryEvent.model_validate({**record, "source_sequence": True})
    with pytest.raises(ValueError):
        TrajectoryEvent.model_validate({**record, "source_step_index": 1.5})
    for invalid_sequence in (True, 1.0, "1", -1):
        with pytest.raises(ValueError):
            TrajectoryEvent.model_validate({**record, "sequence": invalid_sequence})
    assert TrajectoryEvent.model_validate({**record, "sequence": 1}).sequence == 1


def test_ledger_round_trip_and_collision_are_immutable(tmp_path: Path) -> None:
    events = KenshiJsonlAdapter().convert(
        RAW_FIXTURE,
        generation_id="generation",
        scenario_id="scenario",
        run_id="run",
        strict=True,
    )
    record = RunRecord(
        run_id="run",
        generation_id="generation",
        scenario_id="scenario",
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        success=False,
        termination="goal_blocked",
        trace_digest="trace",
        steps=4,
    )
    ledger = Ledger(tmp_path / "ledger.sqlite3")
    ledger.add_run(record, events)
    assert [event.sequence for event in ledger.events_for_runs(["run"])] == [0, 1, 2, 3]
    assert len({event.event_id for event in ledger.events_for_runs(["run"])}) == 4

    with pytest.raises(sqlite3.IntegrityError):
        ledger.add_run(record, events)
    assert len(ledger.list_runs()) == 1
    assert len(ledger.events_for_runs(["run"])) == 4
