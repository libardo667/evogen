from __future__ import annotations

from pathlib import Path

from evogen.core.enums import GateVerdict
from evogen.demo.microworld.cycle import MicroworldEvolutionCycle


def test_complete_cycle_retains_generalizing_candidate(tmp_path):
    workspace = tmp_path / "cycle"
    result = MicroworldEvolutionCycle.prepare(workspace, clean=True).run()

    assert result.decision.verdict == GateVerdict.RETAIN
    assert result.retained_generation is not None
    assert result.experiment.baseline_metrics.revealing_success_rate == 0.0
    assert result.experiment.candidate_metrics.revealing_success_rate == 1.0
    assert result.experiment.candidate_metrics.variant_success_rate == 1.0
    assert result.experiment.candidate_metrics.regression_success_rate == 1.0
    assert result.experiment.candidate_metrics.long_horizon_success_rate == 1.0
    assert Path(result.candidate.workspace_path, "plugins", "inspect_container.py").exists()
    assert (workspace / "report.md").exists()
    assert (workspace / "cycle-result.json").exists()

    lineage = MicroworldEvolutionCycle(workspace).ledger.lineage_rows()
    assert len(lineage) == 1
    assert lineage[0]["child_generation_id"] == result.retained_generation.generation_id
