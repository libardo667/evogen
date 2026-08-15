#!/usr/bin/env python3
"""Build the offline EvoGen evidence cockpit from checked-in authorities."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COCKPIT = ROOT / "docs" / "cockpit"
CONTENT_PATH = COCKPIT / "content.json"
STATE_JSON_PATH = COCKPIT / "state.json"
STATE_JS_PATH = COCKPIT / "state.js"
INDEX_PATH = COCKPIT / "index.html"
PLAN_PATH = ROOT / "docs" / "SEQUENCED_SUBAGENT_EXECUTION_PLAN.md"
CHECKPOINT_PATH = ROOT / "docs" / "INTEGRATION_CHECKPOINT.md"
KAE_EXPORT_DIR = ROOT / "tests" / "fixtures" / "kae_g14_export"

FALLBACK_START = "<!-- generated:fallback:start -->"
FALLBACK_END = "<!-- generated:fallback:end -->"

GOAL_ROW = re.compile(
    r"- \{id: (?P<id>G[0-9]{2}), repo: \[(?P<repos>[^]]*)\], "
    r"depends: \[(?P<depends>[^]]*)\], profile: (?P<profile>[^,]+), "
    r"state: (?P<state>[^,]+), human_gate: \[(?P<gates>[^]]*)\]\}"
)
ROUTE_ROW = re.compile(
    r"^  - \{id: (?P<id>[a-z_]+), status: (?P<status>[a-z_]+), "
    r"goals: \[(?P<goals>[^]]+)\]\}$",
    re.MULTILINE,
)


class CockpitBuildError(ValueError):
    """The cockpit source disagrees with a durable project authority."""


def _list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _goal_number(goal_id: str) -> int:
    return int(goal_id.removeprefix("G"))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_goals(plan: str) -> list[dict[str, Any]]:
    goals = [
        {
            "id": match.group("id"),
            "repositories": _list(match.group("repos")),
            "depends_on": _list(match.group("depends")),
            "profile": match.group("profile").strip(),
            "state": match.group("state").strip(),
            "human_gates": _list(match.group("gates")),
        }
        for match in GOAL_ROW.finditer(plan)
    ]
    expected = [f"G{number:02d}" for number in range(1, 50)]
    if [goal["id"] for goal in goals] != expected:
        raise CockpitBuildError("execution plan must contain the exact G01-G49 queue")
    next_goals = [goal["id"] for goal in goals if goal["state"] == "next"]
    if len(next_goals) != 1:
        raise CockpitBuildError("execution plan must have exactly one next goal")
    return goals


def parse_execution_route(plan: str) -> list[dict[str, Any]]:
    routes = [
        {
            "id": match.group("id"),
            "status": match.group("status"),
            "goals": _list(match.group("goals")),
        }
        for match in ROUTE_ROW.finditer(plan)
    ]
    expected_ids = [
        "replay_showcase",
        "historical_evolution",
        "supervised_live_evolution",
        "deferred_scientific_depth",
        "openttd_and_release",
    ]
    if [route["id"] for route in routes] != expected_ids:
        raise CockpitBuildError("execution plan must contain the exact proof-first route")
    flattened = [goal for route in routes for goal in route["goals"]]
    expected_goals = {f"G{number:02d}" for number in range(14, 50)}
    if len(flattened) != len(set(flattened)) or set(flattened) != expected_goals:
        raise CockpitBuildError("proof-first route must cover G14-G49 exactly once")
    if [route["status"] for route in routes] != [
        "next",
        "planned",
        "planned",
        "deferred",
        "planned",
    ]:
        raise CockpitBuildError("proof-first route has invalid milestone statuses")
    return routes


def checkpoint_value(checkpoint: str, label: str) -> str:
    match = re.search(rf"^{re.escape(label)}\s{{2,}}(.+)$", checkpoint, re.MULTILINE)
    if match is None:
        raise CockpitBuildError(f"checkpoint has no {label!r} field")
    return match.group(1).strip()


def checkpoint_goal_id(checkpoint: str, label: str) -> str:
    value = checkpoint_value(checkpoint, label)
    match = re.match(r"Goal ([0-9]{1,2})\b", value)
    if match is None:
        raise CockpitBuildError(f"checkpoint {label!r} is not a numbered goal")
    return f"G{int(match.group(1)):02d}"


def _journey_for(goal_id: str, journeys: list[dict[str, Any]]) -> str:
    number = _goal_number(goal_id)
    for journey in journeys:
        if journey["first_goal"] <= number <= journey["last_goal"]:
            return str(journey["id"])
    raise CockpitBuildError(f"no journey covers {goal_id}")


def _validate_local_links(value: Any) -> None:
    if isinstance(value, dict):
        href = value.get("href")
        if isinstance(href, str) and href:
            scheme = href.split(":", 1)[0].lower() if ":" in href else ""
            if scheme and scheme not in {"http", "https"}:
                raise CockpitBuildError(f"unsafe evidence-link scheme: {href}")
            if not scheme:
                target = (COCKPIT / href.split("#", 1)[0]).resolve()
                if not target.exists():
                    raise CockpitBuildError(f"local evidence link does not exist: {href}")
        for item in value.values():
            _validate_local_links(item)
    elif isinstance(value, list):
        for item in value:
            _validate_local_links(item)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if not all(isinstance(record, dict) for record in records):
        raise CockpitBuildError(f"fixture contains a non-object record: {path}")
    return records


def _validate_trajectory_export_proof(
    proof: dict[str, Any], checkpoint: str
) -> list[Path]:
    manifest_path = KAE_EXPORT_DIR / "manifest.json"
    raw_path = KAE_EXPORT_DIR / "raw-events.jsonl"
    trajectory_path = KAE_EXPORT_DIR / "trajectory.jsonl"
    readme_path = KAE_EXPORT_DIR / "README.md"
    paths = [manifest_path, raw_path, trajectory_path, readme_path]
    if not all(path.is_file() for path in paths):
        raise CockpitBuildError("KAE trajectory proof bundle is incomplete")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw = _read_jsonl(raw_path)
    trajectory = _read_jsonl(trajectory_path)
    source = manifest["source"]
    normalized = manifest["trajectory"]
    if source["file"] != raw_path.name or normalized["file"] != trajectory_path.name:
        raise CockpitBuildError("KAE trajectory manifest filenames do not match the bundle")
    if source["sha256"] != _sha256(raw_path.read_bytes()):
        raise CockpitBuildError("KAE raw trajectory fixture digest does not match")
    if normalized["sha256"] != _sha256(trajectory_path.read_bytes()):
        raise CockpitBuildError("KAE normalized trajectory fixture digest does not match")
    if source["record_count"] != len(raw) or normalized["event_count"] != len(trajectory):
        raise CockpitBuildError("KAE trajectory fixture counts do not match")
    pairs = zip(raw, trajectory, strict=True)
    if any(event.get("payload", {}).get("raw") != record for record, event in pairs):
        raise CockpitBuildError("KAE normalized fixture does not retain its exact source records")

    portable = proof["portable_source"]
    expected_mapping = [
        {"source": event["source_event_type"], "normalized": event["kind"]}
        for event in trajectory
    ]
    if proof["bundle_id"] != manifest["bundle_id"]:
        raise CockpitBuildError("cockpit KAE bundle identity is stale")
    if portable["raw_records"] != len(raw) or portable["normalized_events"] != len(trajectory):
        raise CockpitBuildError("cockpit KAE portable counts are stale")
    if portable["raw_sha256"] != source["sha256"]:
        raise CockpitBuildError("cockpit KAE source identity is stale")
    if portable["run_id"] != manifest["run_id"]:
        raise CockpitBuildError("cockpit KAE run identity is stale")
    if portable["source_sequence"] != "1..5" or [
        event["source_sequence"] for event in trajectory
    ] != [1, 2, 3, 4, 5]:
        raise CockpitBuildError("cockpit KAE source ordering is stale")
    if portable["normalized_sequence"] != "0..4" or [
        event["sequence"] for event in trajectory
    ] != [0, 1, 2, 3, 4]:
        raise CockpitBuildError("cockpit KAE normalized ordering is stale")
    if proof["mapping"] != expected_mapping:
        raise CockpitBuildError("cockpit KAE event mapping is stale")
    if proof["withheld"] != normalized["withheld_projection_kinds"]:
        raise CockpitBuildError("cockpit KAE withheld projection list is stale")

    real = proof["real_run_acceptance"]
    for value in (
        f"{real['raw_records']:,}",
        f"{real['normalized_events']:,}",
        real["source_sha256"],
    ):
        if str(value) not in checkpoint:
            raise CockpitBuildError("cockpit real-run acceptance evidence is stale")
    return paths


def build_state() -> dict[str, Any]:
    content_bytes = CONTENT_PATH.read_bytes()
    config = json.loads(content_bytes)
    if config.get("schema_version") != "evogen-cockpit/v1":
        raise CockpitBuildError("cockpit state schema_version must be evogen-cockpit/v1")

    plan_bytes = PLAN_PATH.read_bytes()
    checkpoint_bytes = CHECKPOINT_PATH.read_bytes()
    goals = parse_goals(plan_bytes.decode("utf-8"))
    routes = parse_execution_route(plan_bytes.decode("utf-8"))
    checkpoint = checkpoint_bytes.decode("utf-8")
    trajectory_paths = _validate_trajectory_export_proof(
        config["trajectory_export_proof"], checkpoint
    )
    titles = config.pop("goal_titles")
    if sorted(titles) != [f"G{number:02d}" for number in range(1, 50)]:
        raise CockpitBuildError("cockpit state must title every goal G01-G49 exactly once")

    next_goal = next(goal for goal in goals if goal["state"] == "next")
    completed = [goal for goal in goals if goal["state"] == "complete"]
    last_closed = max(completed, key=lambda goal: _goal_number(goal["id"]))
    checkpoint_next = checkpoint_goal_id(checkpoint, "next unstarted goal")
    checkpoint_current = checkpoint_goal_id(checkpoint, "current goal")

    if next_goal["id"] != checkpoint_next:
        raise CockpitBuildError("plan next goal and checkpoint next goal disagree")
    if config["current_focus"]["goal_id"] != next_goal["id"]:
        raise CockpitBuildError("current_focus must name the plan's sole next goal")
    if config["last_closed_goal"]["goal_id"] != last_closed["id"]:
        raise CockpitBuildError("last_closed_goal must name the latest completed goal")
    if checkpoint_current != last_closed["id"]:
        raise CockpitBuildError("checkpoint current goal must be the latest closed goal")

    configured_routes = [
        {
            "id": route["id"],
            "status": route["status"],
            "goals": route["goals"],
        }
        for route in config["execution_route"]
    ]
    if configured_routes != routes:
        raise CockpitBuildError("cockpit execution route disagrees with the plan")
    current_route = next(
        route for route in routes if next_goal["id"] in route["goals"]
    )
    first_incomplete = next(
        goal_id
        for route in routes
        for goal_id in route["goals"]
        if next(goal for goal in goals if goal["id"] == goal_id)["state"] != "complete"
    )
    if first_incomplete != next_goal["id"]:
        raise CockpitBuildError("sole next goal must be first incomplete route goal")

    kae_commit = checkpoint_value(checkpoint, "KAE completion commit")
    kae_repo = next(repo for repo in config["repositories"] if repo["id"] == "kae")
    if kae_repo["evidence_commit"] != kae_commit:
        raise CockpitBuildError("KAE repository evidence commit disagrees with checkpoint")

    for goal in goals:
        goal["title"] = titles[goal["id"]]
        goal["journey_id"] = _journey_for(goal["id"], config["journeys"])

    _validate_local_links(config)
    inputs = [
        {"path": str(PLAN_PATH.relative_to(ROOT)), "sha256": _sha256(plan_bytes)},
        {
            "path": str(CHECKPOINT_PATH.relative_to(ROOT)),
            "sha256": _sha256(checkpoint_bytes),
        },
        {"path": str(CONTENT_PATH.relative_to(ROOT)), "sha256": _sha256(content_bytes)},
        *[
            {"path": str(path.relative_to(ROOT)), "sha256": _sha256(path.read_bytes())}
            for path in trajectory_paths
        ],
    ]
    input_digest = _sha256(
        json.dumps(inputs, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    state = {
        **config,
        "source_authority": {
            "repository": "evogen",
            "branch": "main",
            "plan_revision_commit": config["plan_revision_commit"],
            "input_digest": input_digest,
            "inputs": inputs,
        },
        "progress": {
            "goal_count": len(goals),
            "completed_goal_count": len(completed),
            "next_goal_id": next_goal["id"],
            "last_closed_goal_id": last_closed["id"],
            "checkpoint_current_goal_id": checkpoint_current,
            "current_route_id": current_route["id"],
        },
        "goals": goals,
    }
    identity = _sha256(
        json.dumps(state, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode(
            "utf-8"
        )
    )
    state["state_id"] = f"sha256:{identity}"
    return state


def render_state_js(state: dict[str, Any]) -> str:
    payload = json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True)
    return f"window.EVOGEN_COCKPIT_STATE = {payload};\n"


def render_state_json(state: dict[str, Any]) -> str:
    return json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def render_fallback(state: dict[str, Any]) -> str:
    last_goal = state["last_closed_goal"]
    next_goal = state["current_focus"]
    trajectory = state["trajectory_export_proof"]
    proof_labels = ", ".join(lane["label"] for lane in state["proof_lanes"])
    route_labels = " -> ".join(item["label"] for item in state["execution_route"])
    withheld = "".join(f"<li>{item}</li>" for item in state["withheld_claims"])
    return f"""{FALLBACK_START}
    <noscript>
      <section class="noscript-card" aria-labelledby="noscript-title">
        <p class="eyebrow">Read-only evidence snapshot</p>
        <h1 id="noscript-title">EvoGen project cockpit</h1>
        <p><strong>Last closed:</strong> {last_goal['goal_id']} — {last_goal['title']}</p>
        <p><strong>Next authorized:</strong> {next_goal['goal_id']} —
        {next_goal['title']} (unstarted)</p>
        <p><strong>Proof lanes:</strong> {proof_labels}</p>
        <p><strong>Proof-first route:</strong> {route_labels}</p>
        <p><strong>KAE export proof:</strong>
        {trajectory['real_run_acceptance']['raw_records']:,} retained raw records →
        {trajectory['real_run_acceptance']['normalized_events']:,} strict events;
        binding and dispatch remain withheld.</p>
        <h2>Claims still withheld</h2>
        <ul>{withheld}</ul>
        <p><a href="../INTEGRATION_CHECKPOINT.md">Open the exact checkpoint</a> ·
        <a href="../SEQUENCED_SUBAGENT_EXECUTION_PLAN.md">Open the 49-goal plan</a></p>
      </section>
    </noscript>
    {FALLBACK_END}"""


def render_index(index: str, state: dict[str, Any]) -> str:
    if FALLBACK_START not in index or FALLBACK_END not in index:
        raise CockpitBuildError("index.html is missing generated fallback markers")
    before, remainder = index.split(FALLBACK_START, 1)
    _, after = remainder.split(FALLBACK_END, 1)
    return before + render_fallback(state) + after


def _check(path: Path, expected: str) -> None:
    actual = path.read_text(encoding="utf-8") if path.exists() else ""
    if actual != expected:
        raise CockpitBuildError(f"generated cockpit artifact is stale: {path.relative_to(ROOT)}")


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        handle.write(content)
        handle.flush()
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail when generated files are stale")
    args = parser.parse_args()

    state = build_state()
    state_json = render_state_json(state)
    state_js = render_state_js(state)
    index = render_index(INDEX_PATH.read_text(encoding="utf-8"), state)
    if args.check:
        _check(STATE_JSON_PATH, state_json)
        _check(STATE_JS_PATH, state_js)
        _check(INDEX_PATH, index)
        return
    _write_atomic(STATE_JSON_PATH, state_json)
    _write_atomic(STATE_JS_PATH, state_js)
    _write_atomic(INDEX_PATH, index)


if __name__ == "__main__":
    main()
