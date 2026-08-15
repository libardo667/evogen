from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from evogen.trace.io import read_jsonl_events

FIXTURE_DIR = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).parents[1]
EXPORT_DIR = FIXTURE_DIR / "kae_g14_export"
MANIFEST = EXPORT_DIR / "manifest.json"
RAW = EXPORT_DIR / "raw-events.jsonl"
TRAJECTORY = EXPORT_DIR / "trajectory.jsonl"


def test_compact_kae_export_bundle_is_reconstructable() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    raw_records = [
        json.loads(line) for line in RAW.read_text(encoding="utf-8").splitlines()
    ]
    events = read_jsonl_events(TRAJECTORY)

    assert hashlib.sha256(RAW.read_bytes()).hexdigest() == manifest["source"]["sha256"]
    assert hashlib.sha256(TRAJECTORY.read_bytes()).hexdigest() == manifest["trajectory"]["sha256"]
    assert manifest["source"]["file"] == "raw-events.jsonl"
    assert manifest["trajectory"]["file"] == "trajectory.jsonl"
    assert manifest["source"]["record_count"] == 5
    assert manifest["trajectory"]["event_count"] == 5
    assert manifest["trajectory"]["withheld_projection_kinds"] == ["binding", "dispatch"]
    assert [event.sequence for event in events] == list(range(5))
    assert [event.source_sequence for event in events] == [1, 2, 3, 4, 5]
    assert {event.run_id for event in events} == {manifest["run_id"]}
    assert {event.generation_id for event in events} == {manifest["generation_id"]}
    assert {event.scenario_id for event in events} == {manifest["scenario_id"]}
    assert [event.payload["raw"] for event in events] == raw_records
    assert Counter(event.kind.value for event in events) == Counter(
        manifest["trajectory"]["kind_counts"]
    )

    receipt = next(event for event in events if event.source_event_type == "action_receipt")
    outcome = next(event for event in events if event.source_event_type == "action_outcome")
    world_delta = next(event for event in events if event.source_event_type == "world_state_update")
    assert receipt.kind.value == "execution_receipt"
    assert outcome.kind.value == "outcome_observation"
    assert world_delta.kind.value == "observation_delta"
    assert receipt.event_id != outcome.event_id
    assert receipt.payload["correlation"]["command_id"] == "command-1"
    assert outcome.payload["correlation"]["command_id"] == "command-1"
    assert receipt.world_revision != outcome.world_revision
    assert "binding" not in {event.kind.value for event in events}
    assert "dispatch" not in {event.kind.value for event in events}


def test_exported_current_envelope_round_trips_without_normalization() -> None:
    events = read_jsonl_events(TRAJECTORY)
    round_tripped = [
        type(event).model_validate_json(event.model_dump_json()) for event in events
    ]
    assert round_tripped == events


def test_raw_kae_records_are_not_accepted_by_the_generic_reader() -> None:
    with pytest.raises(ValueError, match="raw KAE record"):
        read_jsonl_events(RAW)


@pytest.mark.parametrize(
    "name",
    ["kenshi_missing_close.raw.jsonl", "kenshi_same_step_identity.raw.jsonl"],
)
def test_historical_alias_records_are_not_a_production_input(name: str) -> None:
    with pytest.raises(ValueError, match="raw KAE record"):
        read_jsonl_events(FIXTURE_DIR / name)


def test_no_production_source_imports_the_retired_adapter() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "src" / "evogen").rglob("*.py"))
    )

    assert "KenshiJsonlAdapter" not in source
    assert "integrations.kenshi" not in source
