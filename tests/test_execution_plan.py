from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs" / "SEQUENCED_SUBAGENT_EXECUTION_PLAN.md"
CHECKPOINT = ROOT / "docs" / "INTEGRATION_CHECKPOINT.md"
GOAL_ROW = re.compile(
    r"^  - \{id: G(?P<number>\d{2}), .* depends: \[(?P<depends>[^]]*)\], "
    r".* state: (?P<state>[a-z_]+),",
    flags=re.MULTILINE,
)


def test_execution_plan_is_a_single_sequenced_goal_queue() -> None:
    text = PLAN.read_text(encoding="utf-8")
    assert "global_active_goal_limit: 1" in text

    rows = [
        (int(match.group("number")), match.group("depends"), match.group("state"))
        for match in GOAL_ROW.finditer(text)
    ]
    assert [number for number, _, _ in rows] == list(range(1, 50))

    next_goals = [number for number, _, state in rows if state == "next"]
    assert len(next_goals) == 1
    next_goal = next_goals[0]

    for number, dependencies, _ in rows[1:]:
        assert dependencies == f"G{number - 1:02d}"

    checkpoint = CHECKPOINT.read_text(encoding="utf-8")
    match = re.search(r"^next unstarted goal\s{2,}Goal (\d+)\b", checkpoint, re.MULTILINE)
    assert match is not None
    assert int(match.group(1)) == next_goal

    states = {number: state for number, _, state in rows}
    assert all(states[number] == "complete" for number in range(1, next_goal))
    assert all(states[number] == "unstarted" for number in range(next_goal + 1, 50))
