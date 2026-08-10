from __future__ import annotations

from evogen.demo.microworld.cycle import MicroworldEvolutionCycle
from evogen.demo.microworld.scenarios import DIAGNOSTIC_SCENARIOS
from evogen.demo.microworld.subject import MicroworldRunner
from evogen.evolution.diagnosis import EvidenceFirstDiagnostician
from evogen.trace.distill import TraceDistiller


def test_repeated_absent_effect_becomes_capability_issue(tmp_path):
    cycle = MicroworldEvolutionCycle.prepare(tmp_path / "workspace")
    generation = cycle._baseline_generation()
    runner = MicroworldRunner()
    events = []
    for scenario_id in DIAGNOSTIC_SCENARIOS:
        _, run_events = runner.run(
            generation=generation,
            scenario_id=scenario_id,
            trace_directory=tmp_path / "traces",
        )
        events.extend(run_events)

    distilled = TraceDistiller().distill(
        generation_id=generation.generation_id,
        events=events,
        capabilities=runner.capability_manifest(generation),
    )
    issue = EvidenceFirstDiagnostician().diagnose(distilled)

    assert issue.classification.primary.value == "affordance_discovery"
    assert issue.required_effect == "reveal_contents"
    assert issue.proposed_resolution.value == "add_capability"
    assert len(issue.supporting_evidence) == 3
