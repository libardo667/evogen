from __future__ import annotations

import pytest

from evogen.core.enums import GateVerdict
from evogen.core.models import GateDecision


def test_non_retained_decision_cannot_name_retained_generation():
    with pytest.raises(ValueError):
        GateDecision(
            decision_id="decision-1",
            candidate_id="candidate-1",
            verdict=GateVerdict.REJECT,
            passed_rules=[],
            failed_rules=["regression"],
            rationale="Regression failed.",
            retained_generation_id="gen-2",
        )
