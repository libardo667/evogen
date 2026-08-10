from __future__ import annotations

from evogen.demo.microworld.cycle import MicroworldEvolutionCycle
from evogen.demo.microworld.scenarios import get_scenario
from evogen.demo.microworld.subject import MicroworldRunner


def test_baseline_is_blocked_by_opaque_container(tmp_path):
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "workspace")
    generation = cycle._baseline_generation()
    record, events = MicroworldRunner().run(
        generation=generation,
        scenario_id="diag-opaque-near",
        trace_directory=tmp_path / "traces",
    )

    assert not record.success
    assert record.termination == "goal_blocked"
    blocked = [event for event in events if event.kind.value == "goal_blocked"]
    assert len(blocked) == 1
    assert blocked[0].payload["required_effect"] == "reveal_contents"


def test_scenario_fixture_is_stable():
    scenario = get_scenario("variant-opaque-renamed")
    assert scenario.target_item_id == "violet-wafer"
    assert scenario.containers[0].container_id == "urn-zeta"
