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
        "completed_goal_count": 15,
        "next_goal_id": "G16",
        "last_closed_goal_id": "G15",
        "checkpoint_current_goal_id": "G15",
        "current_route_id": "replay_showcase",
    }
    assert [goal["state"] for goal in STATE["goals"][:15]] == ["complete"] * 15
    assert STATE["goals"][15]["state"] == "next"
    assert [goal["state"] for goal in STATE["goals"][16:]] == ["unstarted"] * 33


def test_cockpit_shows_the_exact_proof_first_route_and_boundaries() -> None:
    routes = STATE["execution_route"]
    assert [route["id"] for route in routes] == [
        "replay_showcase",
        "historical_evolution",
        "supervised_live_evolution",
        "deferred_scientific_depth",
        "openttd_and_release",
    ]
    assert [goal for route in routes for goal in route["goals"]] == [
        "G14", "G15", "G16", "G17",
        "G18", "G22", "G23", "G24", "G25", "G26", "G27",
        "G28", "G29",
        "G19", "G20", "G21",
        *[f"G{number:02d}" for number in range(30, 50)],
    ]
    assert [route["status"] for route in routes] == [
        "next", "planned", "planned", "deferred", "planned"
    ]
    assert all(route["delivers"] and route["boundary"] for route in routes)
    assert "not optional" in routes[3]["boundary"]
    assert "availability evidence only" in routes[4]["boundary"]


def test_cockpit_exposes_the_exact_g14_mapping_and_uncertainty() -> None:
    proof = STATE["trajectory_export_proof"]
    assert proof["portable_source"] == {
        "normalized_events": 5,
        "normalized_sequence": "0..4",
        "raw_records": 5,
        "raw_sha256": (
            "98f3d6cfbc5173692e7bcf3b12942aab80e121695582ca82310188693490e08a"
        ),
        "run_id": "kae-g14-portable",
        "source_sequence": "1..5",
    }
    assert proof["mapping"] == [
        {"normalized": "run_started", "source": "run_started"},
        {"normalized": "execution_receipt", "source": "action_receipt"},
        {"normalized": "outcome_observation", "source": "action_outcome"},
        {"normalized": "observation_delta", "source": "world_state_update"},
        {"normalized": "run_finished", "source": "run_finished"},
    ]
    assert proof["real_run_acceptance"]["raw_records"] == 38_293
    assert proof["real_run_acceptance"]["normalized_events"] == 22_995
    assert proof["withheld"] == ["binding", "dispatch"]
    assert "original generation identity" in proof["boundary"]
    assert "G15 registration is complete" in proof["boundary"]
    assert "G16 replay" in proof["boundary"]


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
    assert "Last closed:</strong> G15" in index
    assert "Next authorized:</strong> G16" in index
    assert "Proof-first route:</strong> Real KAE replay showcase" in index
    assert 'id="proof-roadmap"' in index
    assert 'id="trajectory-panel"' in index
    assert "38,293 retained raw records" in index


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
    kenshi = next(
        item for item in STATE["capabilities"] if item["id"] == "kae_subject_plugin"
    )
    assert kenshi["proof"] == ["source", "static", "portable", "hosted", "installed"]
    assert "synthetic conformance" in kenshi["not_proven"]


def test_demo_results_always_show_denominators() -> None:
    for suite in STATE["demo_result"]["suites"]:
        assert re.fullmatch(r"\d+ / [1-9]\d*", suite["baseline"])
        assert re.fullmatch(r"\d+ / [1-9]\d*", suite["candidate"])
