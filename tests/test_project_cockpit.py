"""Keep the human evidence cockpit faithful, offline, and reproducible."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COCKPIT = ROOT / "docs" / "cockpit"
STATE = json.loads((COCKPIT / "state.json").read_text(encoding="utf-8"))


def _walk(value: Any) -> list[Any]:
    if isinstance(value, dict):
        return [value, *(nested for item in value.values() for nested in _walk(item))]
    if isinstance(value, list):
        return [value, *(nested for item in value for nested in _walk(item))]
    return [value]


def test_generated_cockpit_is_fresh() -> None:
    result = subprocess.run(
        (sys.executable, "scripts/build_project_cockpit.py", "--check"),
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_state_preserves_the_exact_execution_boundary() -> None:
    assert STATE["schema_version"] == "evogen-cockpit/v1"
    assert len(STATE["goals"]) == 49
    assert [goal["id"] for goal in STATE["goals"]] == [
        f"G{number:02d}" for number in range(1, 50)
    ]
    assert STATE["progress"] == {
        "goal_count": 49,
        "completed_goal_count": 12,
        "next_goal_id": "G13",
        "last_closed_goal_id": "G12",
        "checkpoint_current_goal_id": "G12",
    }
    assert [goal["state"] for goal in STATE["goals"][:12]] == ["complete"] * 12
    assert STATE["goals"][12]["state"] == "next"
    assert [goal["state"] for goal in STATE["goals"][13:]] == ["unstarted"] * 36


def test_json_and_file_protocol_script_are_the_same_state() -> None:
    script = (COCKPIT / "state.js").read_text(encoding="utf-8")
    prefix = "window.EVOGEN_COCKPIT_STATE = "
    assert script.startswith(prefix)
    assert script.endswith(";\n")
    assert json.loads(script[len(prefix) : -2]) == STATE


def test_cockpit_has_no_runtime_network_or_module_dependency() -> None:
    index = (COCKPIT / "index.html").read_text(encoding="utf-8")
    javascript = (COCKPIT / "cockpit.js").read_text(encoding="utf-8")
    assert 'type="module"' not in index
    assert "fetch(" not in javascript
    assert "XMLHttpRequest" not in javascript
    assert not re.search(r'''(?:src|href)=["']https?://''', index)
    assert "generated:fallback:start" in index
    assert "Last closed:</strong> G12" in index
    assert "Next authorized:</strong> G13" in index


def test_evidence_links_are_safe_and_local_links_resolve() -> None:
    links = [
        item["href"]
        for item in _walk(STATE)
        if isinstance(item, dict) and isinstance(item.get("href"), str)
    ]
    assert links
    for href in links:
        if re.match(r"^https?://", href):
            continue
        assert ":" not in href
        target = (COCKPIT / href.split("#", 1)[0]).resolve()
        assert target.exists(), href


def test_capability_claims_name_proof_and_a_boundary() -> None:
    lane_ids = {lane["id"] for lane in STATE["proof_lanes"]}
    assert {"built", "installed", "live", "withheld"} <= lane_ids
    for capability in STATE["capabilities"]:
        assert capability["proof"]
        assert set(capability["proof"]) <= lane_ids
        assert capability["not_proven"]
        if capability["status"] in {"next", "planned"}:
            assert capability["proof"] == ["withheld"]
    demo = next(item for item in STATE["capabilities"] if item["id"] == "cycle")
    assert "live" not in demo["proof"]


def test_demo_results_always_show_denominators() -> None:
    for suite in STATE["demo_result"]["suites"]:
        assert re.fullmatch(r"\d+ / [1-9]\d*", suite["baseline"])
        assert re.fullmatch(r"\d+ / [1-9]\d*", suite["candidate"])
