from __future__ import annotations

from pathlib import Path

import pytest

from evogen.core.enums import CapabilityKind, EventKind, EvidenceState
from evogen.core.models import CapabilityDefinition, CapabilityManifest
from evogen.evolution.diagnosis import EvidenceFirstDiagnostician
from evogen.trace.distill import TraceDistiller
from tests.support.historical_kenshi_fixture import read_historical_fixture

FIXTURE = Path(__file__).parent / "fixtures" / "kenshi_missing_close.raw.jsonl"
IDENTITY_FIXTURE = (
    Path(__file__).parent / "fixtures" / "kenshi_same_step_identity.raw.jsonl"
)


def test_fixture_only_historical_reader_distills() -> None:
    events = read_historical_fixture(
        FIXTURE,
        generation_id="kae-g14-fixture",
        scenario_id="historical-missing-close",
        run_id="kae-run-historical",
    )
    assert events[-2].kind == EventKind.GOAL_BLOCKED
    manifest = CapabilityManifest(
        generation_id="kae-g14-fixture",
        capabilities=[
            CapabilityDefinition(
                name="open_trade_window",
                purpose="Open trade.",
                kind=CapabilityKind.ACTION,
                owner_component="kae",
                applicability="fresh target",
                implementation_ref="kae",
                introduced_generation="kae-g14-fixture",
                proof_class=None,
                evidence_state=EvidenceState.UNPROVEN,
            )
        ],
    )
    distilled = TraceDistiller().distill(
        generation_id="kae-g14-fixture",
        events=events,
        capabilities=manifest,
    )
    issue = EvidenceFirstDiagnostician().diagnose(distilled)

    assert issue.required_effect == "close_interface"
    assert issue.classification.primary.value == "affordance_discovery"


def test_historical_reader_is_locked_to_the_two_checked_in_fixtures(
    tmp_path: Path,
) -> None:
    copied = tmp_path / FIXTURE.name
    copied.write_bytes(FIXTURE.read_bytes())

    with pytest.raises(ValueError, match="only its two checked-in fixtures"):
        read_historical_fixture(
            copied,
            generation_id="generation",
            scenario_id="scenario",
            run_id="run",
        )


def test_historical_identity_fixture_does_not_restore_broad_sequence_aliases() -> None:
    events = read_historical_fixture(
        IDENTITY_FIXTURE,
        generation_id="generation",
        scenario_id="scenario",
        run_id="run",
    )

    assert [event.sequence for event in events] == [0, 1, 2, 3]
    assert [event.source_sequence for event in events] == [99, 1, None, None]
    assert [event.source_step_index for event in events] == [7, 7, 7, 7]
    assert [event.source_world_revision for event in events] == ["42", "43", "44", None]
    assert len({event.event_id for event in events}) == 4
