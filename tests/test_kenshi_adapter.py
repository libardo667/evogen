from __future__ import annotations

from pathlib import Path

from evogen.core.enums import EventKind, ProofClass
from evogen.core.models import CapabilityDefinition, CapabilityManifest
from evogen.evolution.diagnosis import EvidenceFirstDiagnostician
from evogen.integrations.kenshi.adapter import KenshiJsonlAdapter
from evogen.trace.distill import TraceDistiller

FIXTURE = Path(__file__).parent / "fixtures" / "kenshi_missing_close.raw.jsonl"


def test_kenshi_like_trace_normalizes_and_distills():
    events = KenshiJsonlAdapter().convert(
        FIXTURE,
        generation_id="kae-gen-1",
        scenario_id="historical-missing-close",
        run_id="kae-run-1",
        strict=True,
    )
    assert events[-2].kind == EventKind.GOAL_BLOCKED
    manifest = CapabilityManifest(
        generation_id="kae-gen-1",
        capabilities=[
            CapabilityDefinition(
                name="open_trade_window",
                purpose="Open trade.",
                kind="action",
                owner_component="kae",
                applicability="fresh target",
                implementation_ref="kae",
                introduced_generation="kae-gen-1",
                proof_class=ProofClass.REPLAY,
            )
        ],
    )
    distilled = TraceDistiller().distill(
        generation_id="kae-gen-1",
        events=events,
        capabilities=manifest,
    )
    issue = EvidenceFirstDiagnostician().diagnose(distilled)

    assert issue.required_effect == "close_interface"
    assert issue.classification.primary.value == "affordance_discovery"
