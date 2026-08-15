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
ROUTE_ROW = re.compile(
    r"^  - \{id: (?P<route>[a-z_]+), status: (?P<status>[a-z_]+), "
    r"goals: \[(?P<goals>[^]]+)\]\}$",
    flags=re.MULTILINE,
)


def _ids(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def test_execution_plan_is_a_single_proof_first_goal_queue() -> None:
    text = PLAN.read_text(encoding="utf-8")
    assert "global_active_goal_limit: 1" in text
    assert "ordering: proof_first" in text

    rows = [
        (
            f"G{int(match.group('number')):02d}",
            _ids(match.group("depends")),
            match.group("state"),
        )
        for match in GOAL_ROW.finditer(text)
    ]
    assert [goal_id for goal_id, _, _ in rows] == [
        f"G{number:02d}" for number in range(1, 50)
    ]
    by_id = {
        goal_id: {"depends": dependencies, "state": state}
        for goal_id, dependencies, state in rows
    }

    routes = {
        match.group("route"): {
            "status": match.group("status"),
            "goals": _ids(match.group("goals")),
        }
        for match in ROUTE_ROW.finditer(text)
    }
    assert list(routes) == [
        "replay_showcase",
        "historical_evolution",
        "supervised_live_evolution",
        "deferred_scientific_depth",
        "openttd_and_release",
    ]
    assert [item["status"] for item in routes.values()] == [
        "next", "planned", "planned", "deferred", "planned"
    ]
    assert routes["replay_showcase"]["goals"] == ["G14", "G15", "G16", "G17"]
    assert routes["historical_evolution"]["goals"] == [
        "G18", "G22", "G23", "G24", "G25", "G26", "G27"
    ]
    assert routes["supervised_live_evolution"]["goals"] == ["G28", "G29"]
    assert routes["deferred_scientific_depth"]["goals"] == ["G19", "G20", "G21"]
    assert routes["openttd_and_release"]["goals"] == [
        f"G{number:02d}" for number in range(30, 50)
    ]
    route = [goal for item in routes.values() for goal in item["goals"]]
    assert len(route) == len(set(route))
    assert set(route) == {f"G{number:02d}" for number in range(14, 50)}
    assert route[:18] == [
        "G14", "G15", "G16", "G17",
        "G18", "G22", "G23", "G24", "G25", "G26", "G27",
        "G28", "G29",
        "G19", "G20", "G21",
        "G30", "G31",
    ]

    next_goals = [goal_id for goal_id, _, state in rows if state == "next"]
    assert len(next_goals) == 1
    next_goal = next_goals[0]

    for goal_id, dependencies, _ in rows:
        assert all(dependency in by_id for dependency in dependencies), goal_id

    # The dependency graph is explicit and acyclic even though execution is no
    # longer numeric. A route is scheduling authority, not permission to ignore
    # prerequisites.
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(goal_id: str) -> None:
        assert goal_id not in visiting, f"dependency cycle at {goal_id}"
        if goal_id in visited:
            return
        visiting.add(goal_id)
        for dependency in by_id[goal_id]["depends"]:
            visit(dependency)
        visiting.remove(goal_id)
        visited.add(goal_id)

    for goal_id in by_id:
        visit(goal_id)

    assert by_id["G22"]["depends"] == ["G18"]
    assert by_id["G26"]["depends"] == ["G25"]
    assert by_id["G27"]["depends"] == ["G18", "G26"]
    assert by_id["G30"]["depends"] == ["G21", "G29"]

    for dependency in by_id[next_goal]["depends"]:
        assert by_id[dependency]["state"] == "complete"
    first_incomplete = next(
        goal_id for goal_id in route if by_id[goal_id]["state"] != "complete"
    )
    assert first_incomplete == next_goal
    assert all(
        by_id[dependency]["state"] == "complete"
        for goal_id, row in by_id.items()
        if row["state"] == "complete"
        for dependency in row["depends"]
    )

    checkpoint = CHECKPOINT.read_text(encoding="utf-8")
    match = re.search(r"^next unstarted goal\s{2,}Goal (\d+)\b", checkpoint, re.MULTILINE)
    assert match is not None
    assert f"G{int(match.group(1)):02d}" == next_goal
