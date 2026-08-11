"""Subject-neutral API 1.1 conformance checks and doctor execution."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import cast

from evogen.adapters.subjects import (
    SUBJECT_PLUGIN_API_VERSION,
    SubjectComposition,
    SubjectFactoryContext,
    SubjectPluginError,
    SubjectWorkspaceError,
    _contains_git_repository,
    compose_subject,
    load_subject_plugin,
)
from evogen.core.enums import Completeness, GateVerdict
from evogen.core.ids import sha256_bytes, stable_digest
from evogen.core.models import (
    ArtifactRef,
    BoundedCollection,
    CandidateManifest,
    CapabilityManifest,
    EvaluationAuthoritySnapshot,
    EvaluationOutcome,
    EvaluationSuiteManifest,
    ExperimentResult,
    JsonValue,
    MetricVector,
    RunRecord,
    ScenarioResult,
    SubjectCheck,
    SubjectConformanceReport,
    SubjectDiagnostic,
    TrajectoryEvent,
)
from evogen.evolution.selection import RetentionPolicy
from evogen.storage.artifacts import ArtifactStore
from evogen.storage.ledger import Ledger
from evogen.trace.io import read_jsonl_events

BOUNDARIES = (
    "generation_manifest",
    "capability_manifest",
    "trajectory_ordering",
    "scenario_isolation",
    "candidate_workspace_isolation",
    "evaluation_symmetry",
    "retained_generation_materialization",
)


def _passed(
    boundary: str, message: str, evidence: dict[str, JsonValue] | None = None
) -> SubjectCheck:
    return SubjectCheck(
        boundary_id=boundary,
        status="pass",
        message=message,
        evidence=evidence or {"message": message},
    )


def _failed(
    boundary: str, message: str, evidence: dict[str, JsonValue] | None = None
) -> SubjectCheck:
    return SubjectCheck(
        boundary_id=boundary,
        status="fail",
        message=message,
        evidence=evidence or {"message": message},
    )


def _blocked(boundary: str, dependency: str, message: str) -> SubjectCheck:
    return SubjectCheck(
        boundary_id=boundary,
        status="blocked",
        blocked_dependency=dependency,
        message=message,
        evidence={"dependency": dependency, "message": message},
    )


def _files_digest(root: Path, *, exclude: Path | None = None) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if exclude is not None and (path == exclude or exclude in path.parents):
            continue
        result[str(path.relative_to(root))] = sha256_bytes(path.read_bytes())
    return result


def _workspace_inventory(root: Path) -> dict[str, str]:
    """Capture files, directories, and symlinks without following hostile links."""
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        relative = str(path.relative_to(root))
        if path.is_symlink():
            result[relative] = f"symlink:{os.readlink(path)}"
        elif path.is_dir():
            result[relative] = "directory"
        elif path.is_file():
            result[relative] = f"file:{sha256_bytes(path.read_bytes())}"
        else:
            result[relative] = "special"
    return result


def _artifact_exists(store: ArtifactStore, digest: str) -> bool:
    path = store.path_for(digest)
    return not path.is_symlink() and path.is_file() and sha256_bytes(path.read_bytes()) == digest


def _suite_cases(suite: EvaluationSuiteManifest) -> list[tuple[str, int, int, str]]:
    result: list[tuple[str, int, int, str]] = []
    for case in (
        *suite.revealing_cases,
        *suite.structural_variants,
        *suite.regression_suites,
        *suite.long_horizon_suites,
    ):
        for seed in case.seeds:
            for repeat_index in range(case.repeat_count):
                result.append((case.scenario_id, seed, repeat_index, case.category))
    return result


def _result_coordinates(results: Iterable[ScenarioResult]) -> list[tuple[str, int, int, str]]:
    return [(r.scenario_id, r.seed, r.repeat_index, r.category) for r in results]


def _metrics(results: list[ScenarioResult]) -> MetricVector:
    def rate(category: str) -> float:
        selected = [r for r in results if r.category == category]
        return sum(r.success for r in selected) / len(selected) if selected else 1.0

    return MetricVector(
        revealing_success_rate=rate("revealing"),
        variant_success_rate=rate("variant"),
        regression_success_rate=rate("regression"),
        long_horizon_success_rate=rate("long_horizon"),
        intervention_count=sum(r.interventions for r in results),
        invalid_action_count=sum(r.invalid_actions for r in results),
        blocked_run_count=sum(r.blocked for r in results),
        average_steps=sum(r.steps for r in results) / len(results) if results else 0.0,
        new_high_severity_issues=0,
    )


def _trace_fingerprint(events: Sequence[TrajectoryEvent]) -> str:
    values = []
    for event in events:
        dumped = event.model_dump(mode="json")
        dumped["event_id"] = "<event>"
        dumped["run_id"] = "<run>"
        dumped["recorded_at"] = "<time>"
        values.append(dumped)
    return stable_digest(values)


def _canonical_run_evidence(
    composition: SubjectComposition,
    record: object,
    returned: object,
    *,
    requested_generation: str,
    requested_scenario: str,
    requested_seed: int,
    add_to_ledger: bool = True,
) -> tuple[RunRecord, list[TrajectoryEvent]]:
    if not isinstance(record, RunRecord) or not isinstance(returned, list):
        raise ValueError("runner returned non-typed RunRecord evidence")
    events = cast(list[TrajectoryEvent], returned)
    if not events or not all(isinstance(event, TrajectoryEvent) for event in events):
        raise ValueError("runner returned no typed trajectory events")
    if record.generation_id != requested_generation or record.scenario_id != requested_scenario:
        raise ValueError("runner ignored requested generation or scenario identity")
    if record.metadata.get("seed") != requested_seed:
        raise ValueError("runner record seed does not match requested seed")
    if record.finished_at < record.started_at:
        raise ValueError("runner record has inverted timestamps")
    path_value = record.metadata.get("trace_path")
    if not isinstance(path_value, str) or not path_value.strip():
        raise ValueError("runner record lacks a trace path")
    path = Path(path_value)
    workspace = composition.context.workspace.resolve()
    if path.is_symlink() or not path.is_file():
        raise ValueError("runner trace is not a regular-file trace")
    resolved_path = path.resolve()
    if resolved_path == workspace or workspace not in resolved_path.parents:
        raise ValueError(
            "runner trace is not a regular-file trace within the conformance workspace"
        )
    on_disk = read_jsonl_events(path)
    if [event.model_dump(mode="json") for event in events] != [
        event.model_dump(mode="json") for event in on_disk
    ]:
        raise ValueError(
            "returned and on-disk trajectory events disagree; trace fingerprint is not canonical"
        )
    if any(
        event.run_id != record.run_id
        or event.generation_id != record.generation_id
        or event.scenario_id != record.scenario_id
        for event in events
    ):
        raise ValueError("trajectory event identity disagrees with RunRecord")
    if len({event.event_id for event in events}) != len(events):
        raise ValueError("trajectory event IDs are not unique")
    if [event.sequence for event in events] != list(range(len(events))):
        raise ValueError("trajectory sequences are not canonical and contiguous")
    if sha256_bytes(path.read_bytes()) != record.trace_digest:
        raise ValueError("trace digest does not match regular-file evidence")
    if add_to_ledger:
        composition.context.ledger.add_run(record, events)
    if composition.context.ledger.get_run(record.run_id) != record:
        raise ValueError("ledger read-back RunRecord differs from runner record")
    ledger_events = composition.context.ledger.events_for_runs([record.run_id])
    if [event.model_dump(mode="json") for event in ledger_events] != [
        event.model_dump(mode="json") for event in events
    ]:
        raise ValueError("ledger events differ from returned trajectory events")
    return record, events


def _protected_files_snapshot(suite: EvaluationSuiteManifest) -> dict[str, str]:
    result: dict[str, str] = {}
    for protected in suite.protected_paths:
        path = Path(protected.absolute_path)
        if path.is_symlink() or not path.is_file():
            raise ValueError(
                f"protected authority {protected.logical_name!r} is not a regular file"
            )
        try:
            digest = sha256_bytes(path.read_bytes())
        except OSError as exc:
            raise ValueError(
                f"protected authority {protected.logical_name!r} is unreadable"
            ) from exc
        if digest != protected.sha256:
            raise ValueError(f"protected authority {protected.logical_name!r} digest changed")
        result[protected.logical_name] = digest
    return result


def _verify_authority_artifacts(
    composition: SubjectComposition,
    suite: EvaluationSuiteManifest,
) -> dict[str, str]:
    protected = _protected_files_snapshot(suite)
    refs = {suite.evaluator_protected_path: suite.evaluator, **suite.environment_artifacts}
    for name, reference in refs.items():
        if not _artifact_exists(composition.context.artifacts, reference.digest):
            raise ValueError(f"authority CAS artifact {name!r} is missing or corrupt")
        if reference.model not in {"SourceArtifact", "EvaluationSuiteManifest"}:
            raise ValueError(f"authority CAS artifact {name!r} has wrong model")
        if name in protected and reference.digest != protected[name]:
            raise ValueError(f"authority CAS artifact {name!r} does not match protected source")
    return protected


def _authority_snapshot(
    composition: SubjectComposition, suite: EvaluationSuiteManifest
) -> EvaluationAuthoritySnapshot:
    protected = _verify_authority_artifacts(composition, suite)
    store = composition.context.artifacts
    return EvaluationAuthoritySnapshot(
        suite_ref=store.put_model(suite),
        suite_id=suite.suite_id,
        evaluator_version=suite.evaluator_version,
        protected_path_digests=protected,
    )


def run_subject_conformance(
    subject_name: str,
    *,
    workspace: Path | None = None,
) -> SubjectConformanceReport:
    """Load one installed subject and run seven checks without any stage dispatch."""
    if workspace is None:
        with tempfile.TemporaryDirectory(prefix="evogen-subject-doctor-") as name:
            try:
                return _run(subject_name, Path(name))
            except SubjectPluginError as exc:
                return subject_conformance_failure_report(subject_name, exc)
            except Exception as exc:
                return subject_conformance_failure_report(subject_name, exc)
    try:
        # The caller-provided spelling is part of the safety boundary.  Check it
        # before resolve so a broken symlink cannot become an apparently new path.
        symlink_ancestor = next(
            (ancestor for ancestor in (workspace, *workspace.parents) if ancestor.is_symlink()),
            None,
        )
        if symlink_ancestor is not None:
            raise SubjectWorkspaceError(
                f"Refusing symlink doctor workspace path component {symlink_ancestor}",
                boundary_id="workspace",
                code=(
                    "workspace_symlink"
                    if symlink_ancestor == workspace
                    else "workspace_ancestor_symlink"
                ),
            )
        if workspace.exists():
            raise SubjectWorkspaceError(
                f"Refusing existing doctor workspace {workspace}; provide a new scratch path.",
                boundary_id="workspace",
                code="workspace_not_new",
            )
        resolved = workspace.resolve(strict=False)
        if resolved in {Path(resolved.anchor), Path.home(), Path.cwd().resolve()}:
            raise SubjectWorkspaceError(
                f"Refusing doctor workspace {resolved}",
                boundary_id="workspace",
                code="workspace_protected_path",
            )
        if _contains_git_repository(resolved):
            raise SubjectWorkspaceError(
                f"Refusing doctor workspace inside a repository: {resolved}",
                boundary_id="workspace",
                code="workspace_repository_path",
            )
        resolved.mkdir(parents=True, exist_ok=False)
        return _run(subject_name, resolved)
    except SubjectPluginError as exc:
        return subject_conformance_failure_report(subject_name, exc)
    except Exception as exc:
        return subject_conformance_failure_report(subject_name, exc)


def _error_report(subject_name: str, error: SubjectPluginError) -> SubjectConformanceReport:
    checks = [
        SubjectCheck(
            boundary_id=error.boundary_id,
            status="fail",
            message=str(error),
            evidence={"code": error.code, "boundary_id": error.boundary_id},
        )
    ]
    checks.extend(
        _blocked(boundary, error.boundary_id, "Blocked by subject loading/composition failure")
        for boundary in BOUNDARIES
        if boundary != error.boundary_id
    )
    return SubjectConformanceReport(
        subject=subject_name,
        api_version=SUBJECT_PLUGIN_API_VERSION,
        checks=checks,
        diagnostics=BoundedCollection(items=[], completeness=Completeness.COMPLETE, known_total=0),
    )


def subject_conformance_failure_report(
    subject_name: str, error: Exception
) -> SubjectConformanceReport:
    """Convert an unexpected doctor exception into the public report contract."""
    if isinstance(error, SubjectPluginError):
        typed = error
    else:
        typed = SubjectPluginError(
            f"Subject doctor failed: {error}",
            boundary_id="doctor",
            code="subject_doctor_error",
        )
    return _error_report(subject_name, typed)


def _run(subject_name: str, workspace: Path) -> SubjectConformanceReport:
    try:
        plugin = load_subject_plugin(subject_name)
    except SubjectPluginError:
        raise
    except Exception as exc:
        raise SubjectPluginError(
            f"Subject loading failed: {exc}",
            boundary_id="load",
            code="subject_load_error",
        ) from exc
    context = SubjectFactoryContext(
        workspace=workspace.resolve(),
        artifacts=ArtifactStore(workspace / "artifacts"),
        ledger=Ledger(workspace / "evogen.sqlite3"),
    )
    try:
        composition = compose_subject(plugin, context=context, publish_cycle_manifest=False)
    except SubjectPluginError:
        raise
    except Exception as exc:
        raise SubjectPluginError(
            f"Subject composition failed: {exc}",
            boundary_id="composition",
            code="subject_composition_error",
        ) from exc
    checks: list[SubjectCheck] = []
    try:
        checks.append(_generation_check(composition))
    except Exception as exc:
        checks.append(
            _failed(
                "generation_manifest",
                f"Generation manifest boundary failed: {exc}",
                {"code": "generation_manifest_error", "error": str(exc)},
            )
        )
    if checks[-1].status != "pass":
        checks.extend(
            _blocked(boundary, "generation_manifest", "Generation boundary did not pass")
            for boundary in BOUNDARIES[1:]
        )
        diagnostics = _doctor_diagnostics(composition)
        return SubjectConformanceReport(
            subject=plugin.name,
            api_version=plugin.api_version,
            checks=checks,
            diagnostics=diagnostics,
        )
    try:
        checks.append(_capability_check(composition))
    except Exception as exc:
        checks.append(
            _failed(
                "capability_manifest",
                f"Capability manifest boundary failed: {exc}",
                {"code": "capability_manifest_error", "error": str(exc)},
            )
        )
    if checks[-1].status != "pass":
        checks.extend(
            _blocked(boundary, "capability_manifest", "Capability boundary did not pass")
            for boundary in BOUNDARIES[2:]
        )
        diagnostics = _doctor_diagnostics(composition)
        return SubjectConformanceReport(
            subject=plugin.name,
            api_version=plugin.api_version,
            checks=checks,
            diagnostics=diagnostics,
        )
    state: dict[str, object] = {}
    checks.append(_run_check(composition, state, "trajectory_ordering", _trajectory_check))
    if checks[-1].status != "pass":
        checks.extend(
            _blocked(boundary, "trajectory_ordering", "Blocked by trajectory failure")
            for boundary in BOUNDARIES[3:]
        )
    else:
        checks.append(_run_check(composition, state, "scenario_isolation", _isolation_check))
        if checks[-1].status != "pass":
            checks.append(
                _blocked(
                    "candidate_workspace_isolation",
                    "scenario_isolation",
                    "Blocked by scenario isolation failure",
                )
            )
            checks.append(
                _blocked(
                    "evaluation_symmetry",
                    "scenario_isolation",
                    "Blocked by scenario isolation failure",
                )
            )
            checks.append(
                _blocked(
                    "retained_generation_materialization",
                    "scenario_isolation",
                    "Blocked by scenario isolation failure",
                )
            )
        else:
            checks.append(
                _run_check(composition, state, "candidate_workspace_isolation", _builder_check)
            )
            if checks[-1].status != "pass":
                checks.append(
                    _blocked(
                        "evaluation_symmetry",
                        "candidate_workspace_isolation",
                        "Blocked by candidate workspace failure",
                    )
                )
                checks.append(
                    _blocked(
                        "retained_generation_materialization",
                        "candidate_workspace_isolation",
                        "Blocked by candidate workspace failure",
                    )
                )
            else:
                checks.append(
                    _run_check(composition, state, "evaluation_symmetry", _evaluation_check)
                )
                if checks[-1].status != "pass":
                    checks.append(
                        _blocked(
                            "retained_generation_materialization",
                            "evaluation_symmetry",
                            "Blocked by evaluation failure",
                        )
                    )
                else:
                    checks.append(
                        _run_check(
                            composition,
                            state,
                            "retained_generation_materialization",
                            _materialization_check,
                        )
                    )
    diagnostics = _doctor_diagnostics(composition)
    return SubjectConformanceReport(
        subject=plugin.name,
        api_version=plugin.api_version,
        checks=checks,
        diagnostics=diagnostics,
    )


def _run_check(
    composition: SubjectComposition,
    state: dict[str, object],
    boundary: str,
    function: Callable[[SubjectComposition, dict[str, object]], SubjectCheck],
) -> SubjectCheck:
    try:
        return function(composition, state)
    except Exception as exc:
        return _failed(
            boundary,
            f"{boundary} boundary failed: {exc}",
            {"code": f"{boundary}_error", "error": str(exc)},
        )


def _generation_check(composition: SubjectComposition) -> SubjectCheck:
    baseline = composition.bootstrap.baseline
    if not baseline.generation_id.strip() or not baseline.source_ref.strip():
        raise ValueError("baseline identity and source_ref must be nonblank")
    store = composition.context.artifacts
    if not _artifact_exists(store, baseline.capability_manifest_digest):
        raise ValueError("baseline capability CAS is missing, corrupt, or wrong model")
    capability_reference = ArtifactRef(
        digest=baseline.capability_manifest_digest, model="CapabilityManifest"
    )
    capability = store.read_model(capability_reference, CapabilityManifest)
    if capability.generation_id != baseline.generation_id:
        raise ValueError("baseline capability manifest has the wrong generation identity")
    if stable_digest(capability.model_dump(mode="json")) != baseline.capability_manifest_digest:
        raise ValueError("baseline capability CAS does not match canonical manifest bytes")
    if baseline.artifact_digests.get("capability_manifest") != baseline.capability_manifest_digest:
        raise ValueError("baseline capability artifact link is missing or incorrect")
    for name, digest in baseline.artifact_digests.items():
        if not _artifact_exists(store, digest):
            raise ValueError(f"baseline artifact {name!r} is missing or corrupt")
    suite = composition.bootstrap.evaluation_suite
    suite_ids = {
        case.scenario_id
        for cases in (
            suite.revealing_cases,
            suite.structural_variants,
            suite.regression_suites,
            suite.long_horizon_suites,
        )
        for case in cases
    }
    plan_ids = set(
        composition.bootstrap.plan.revealing_cases
        + composition.bootstrap.plan.structural_variants
        + composition.bootstrap.plan.regression_suites
        + composition.bootstrap.plan.long_horizon_suites
    )
    if suite_ids != plan_ids:
        raise ValueError("suite and plan scenario authority differ")
    refs = [suite.evaluator, *suite.environment_artifacts.values()]
    for ref in refs:
        if not _artifact_exists(store, ref.digest):
            raise ValueError(f"suite artifact {ref.digest} is missing or corrupt")
        if ref.model not in {"SourceArtifact", "EvaluationSuiteManifest"}:
            raise ValueError(f"suite artifact {ref.digest} declares wrong model {ref.model!r}")
    verified_authority = _verify_authority_artifacts(composition, suite)
    return _passed(
        "generation_manifest",
        "Typed bootstrap identity and authority artifacts verified",
        {
            "generation_id": baseline.generation_id,
            "capability_digest": baseline.capability_manifest_digest,
            "verified_artifacts": cast(list[object], sorted(baseline.artifact_digests)),
            "verified_authority": cast(list[object], sorted(verified_authority)),
        },
    )


def _capability_check(composition: SubjectComposition) -> SubjectCheck:
    baseline = composition.bootstrap.baseline
    first = composition.runner.capability_manifest(baseline)
    second = composition.runner.capability_manifest(baseline)
    if (
        first.generation_id != baseline.generation_id
        or second.generation_id != baseline.generation_id
    ):
        raise ValueError("capability manifest is not generation-bound")
    if len(first.capabilities) != len(first.names) or any(
        not c.name.strip() for c in first.capabilities
    ):
        raise ValueError("capabilities must be unique and nonblank")
    digest = stable_digest(first.model_dump(mode="json"))
    if digest != stable_digest(second.model_dump(mode="json")):
        raise ValueError("capability manifest digest is unstable")
    if digest != baseline.capability_manifest_digest:
        raise ValueError("capability digest does not equal baseline CAS")
    return _passed(
        "capability_manifest",
        "Generation-bound capability manifest is stable and CAS-matched",
        {"generation_id": baseline.generation_id, "canonical_digest": digest},
    )


def _trajectory_check(composition: SubjectComposition, state: dict[str, object]) -> SubjectCheck:
    fixture = composition.conformance_fixture
    directory = composition.context.workspace / "trajectory-check"
    requested_scenario = fixture.scenario_ids[0]
    requested_seed = fixture.seeds[0]
    record, returned = composition.runner.run(
        generation=composition.bootstrap.baseline,
        scenario_id=requested_scenario,
        seed=requested_seed,
        trace_directory=directory,
    )
    record, returned_events = _canonical_run_evidence(
        composition,
        record,
        returned,
        requested_generation=composition.bootstrap.baseline.generation_id,
        requested_scenario=requested_scenario,
        requested_seed=requested_seed,
    )
    state["trajectory_record"] = record
    return _passed(
        "trajectory_ordering",
        "Runner trajectory and ledger evidence are canonical",
        {
            "run_id": record.run_id,
            "trace_digest": record.trace_digest,
            "event_count": len(returned_events),
        },
    )


def _isolation_check(composition: SubjectComposition, state: dict[str, object]) -> SubjectCheck:
    fixture = composition.conformance_fixture
    if len(fixture.scenario_ids) < 2:
        raise ValueError("fixture must provide two isolation scenario IDs")
    results: list[tuple[RunRecord, list[TrajectoryEvent]]] = []
    for index, scenario in enumerate(
        (fixture.scenario_ids[0], fixture.scenario_ids[1], fixture.scenario_ids[0])
    ):
        record, events = composition.runner.run(
            generation=composition.bootstrap.baseline,
            scenario_id=scenario,
            seed=fixture.seeds[index % len(fixture.seeds)],
            trace_directory=composition.context.workspace / "isolation" / str(index),
        )
        record, events = _canonical_run_evidence(
            composition,
            record,
            events,
            requested_generation=composition.bootstrap.baseline.generation_id,
            requested_scenario=scenario,
            requested_seed=fixture.seeds[index % len(fixture.seeds)],
        )
        if any(existing.run_id == record.run_id for existing, _ in results):
            raise ValueError("run identity was reused")
        results.append((record, events))
    a1, b, a2 = results
    if _trace_fingerprint(a1[1]) != _trace_fingerprint(a2[1]):
        raise ValueError("A fingerprint changed after running B")
    if _trace_fingerprint(a1[1]) == _trace_fingerprint(b[1]):
        raise ValueError("A and B did not provide independent semantic fingerprints")
    all_event_ids = [event.event_id for _, events in results for event in events]
    if len(all_event_ids) != len(set(all_event_ids)):
        raise ValueError("cross-scenario event identity overlap")
    state["isolation"] = results
    return _passed(
        "scenario_isolation",
        "A/B/A runs are isolated and identity-independent",
        {
            "run_ids": [record.run_id for record, _ in results],
            "a_fingerprint": _trace_fingerprint(a1[1]),
            "b_fingerprint": _trace_fingerprint(b[1]),
        },
    )


def _builder_check(composition: SubjectComposition, state: dict[str, object]) -> SubjectCheck:
    root = composition.context.workspace / "candidates"
    root.mkdir(parents=True, exist_ok=True)
    # Fixture data is staged by the host, before the build snapshot.  The
    # subject factory remains data-only and cannot pre-seed its own pass.
    fixture = composition.conformance_fixture
    composition.context.artifacts.put_json(fixture.issue.model_dump(mode="json"))
    composition.context.artifacts.put_json(fixture.specification.model_dump(mode="json"))
    before = _workspace_inventory(composition.context.workspace)
    candidate = composition.builder.build(
        parent=composition.bootstrap.baseline,
        issue=composition.conformance_fixture.issue,
        specification=composition.conformance_fixture.specification,
        candidate_root=root,
    )
    baseline = composition.bootstrap.baseline
    if (
        candidate.parent_generation != baseline.generation_id
        or candidate.issue_id != fixture.issue.issue_id
        or candidate.spec_id != fixture.specification.spec_id
        or not candidate.source_digest
        or len(candidate.changed_files) != len(set(candidate.changed_files))
        or len(candidate.claimed_capabilities) != len(set(candidate.claimed_capabilities))
    ):
        raise ValueError("candidate manifest identity is not bound to fixture and parent")
    candidate_path = Path(candidate.workspace_path)
    if candidate_path.is_symlink():
        raise ValueError("candidate workspace root is a symlink")
    workspace = candidate_path.resolve()
    resolved_root = root.resolve()
    if not workspace.is_dir() or resolved_root not in workspace.parents:
        raise ValueError("candidate workspace is not a strict descendant")
    for path in workspace.rglob("*"):
        if path.is_symlink() or not path.is_file():
            if path.is_symlink():
                raise ValueError("candidate workspace contains a symlink")
    declared = set(candidate.workspace_file_digests)
    actual = {str(p.relative_to(workspace)) for p in workspace.rglob("*") if p.is_file()}
    if actual != declared:
        raise ValueError("candidate workspace has undeclared or missing files")
    if set(candidate.file_digests) != set(candidate.changed_files):
        raise ValueError("candidate changed-file digest map is incomplete")
    outside = [path for path in root.rglob("*") if path.is_file() and workspace not in path.parents]
    if outside:
        raise ValueError("builder created undeclared sibling files")
    for relative, digest in candidate.workspace_file_digests.items():
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError("candidate workspace contains traversal")
        path = (workspace / relative_path).resolve()
        if (
            path.parent != workspace / relative_path.parent
            or sha256_bytes(path.read_bytes()) != digest
        ):
            raise ValueError("candidate workspace contains traversal or forged digest")
    for relative, digest in candidate.file_digests.items():
        path = workspace / relative
        if path.is_symlink() or not path.is_file() or sha256_bytes(path.read_bytes()) != digest:
            raise ValueError("candidate changed-file bytes differ from declared digest")
    if candidate.source_digest not in candidate.file_digests.values():
        raise ValueError("candidate source digest is not bound to changed file bytes")
    after = _workspace_inventory(composition.context.workspace)
    before_outside = {
        key: value
        for key, value in before.items()
        if (
            key != str(workspace.relative_to(composition.context.workspace))
            and workspace.relative_to(composition.context.workspace) not in Path(key).parents
        )
    }
    after_outside = {
        key: value
        for key, value in after.items()
        if (
            key != str(workspace.relative_to(composition.context.workspace))
            and workspace.relative_to(composition.context.workspace) not in Path(key).parents
        )
    }
    if before_outside != after_outside:
        raise ValueError("builder changed parent, CAS, ledger, or protected authority")
    # Source bytes are discovered only after the builder returns; the host
    # records that CAS link after the side-effect snapshot and then verifies it.
    for path in workspace.rglob("*"):
        if path.is_file() and not path.is_symlink():
            composition.context.artifacts.put_bytes(path.read_bytes())
    for name, digest in candidate.artifact_digests.items():
        if not _artifact_exists(composition.context.artifacts, digest):
            raise ValueError(f"candidate artifact {name!r} is missing or corrupt")
    state["candidate"] = candidate
    return _passed(
        "candidate_workspace_isolation",
        "Builder output is a strict, declared isolated workspace",
        {
            "candidate_id": candidate.candidate_id,
            "workspace": str(workspace),
            "file_count": len(actual),
        },
    )


def _evaluation_check(composition: SubjectComposition, state: dict[str, object]) -> SubjectCheck:
    candidate = state.get("candidate")
    if not isinstance(candidate, CandidateManifest):
        raise ValueError("candidate workspace check did not produce a candidate")
    candidate_workspace = Path(candidate.workspace_path).resolve()
    candidate_before = _files_digest(candidate_workspace)
    suite = composition.bootstrap.evaluation_suite
    before_authority = _authority_snapshot(composition, suite)
    review = composition.reviewer.review(
        candidate, forbidden_literals=composition.bootstrap.plan.forbidden_literals
    )
    if review.candidate_id != candidate.candidate_id:
        raise ValueError("review candidate identity is not bound")
    outcome = composition.evaluator.evaluate(
        baseline=composition.bootstrap.baseline,
        candidate=candidate,
        evaluation_suite=composition.bootstrap.evaluation_suite,
        trace_directory=composition.context.workspace / "evaluation",
        review_passed=review.passed,
    )
    after_authority = _authority_snapshot(composition, suite)
    if (
        before_authority.suite_ref != after_authority.suite_ref
        or before_authority.suite_id != after_authority.suite_id
        or before_authority.evaluator_version != after_authority.evaluator_version
        or before_authority.protected_path_digests != after_authority.protected_path_digests
    ):
        raise ValueError("evaluation suite authority changed during execution")
    if outcome.candidate_id != candidate.candidate_id:
        raise ValueError("evaluation candidate identity is not bound")
    if outcome.baseline_generation != composition.bootstrap.baseline.generation_id:
        raise ValueError("evaluation baseline generation is not bootstrap-bound")
    if outcome.review_passed != review.passed:
        raise ValueError("evaluation review status is not bound to reviewer result")
    if not (
        before_authority.timestamp
        <= outcome.started_at
        <= outcome.finished_at
        <= after_authority.timestamp
    ):
        raise ValueError("evaluation outcome timestamps escape authority window")
    if after_authority.timestamp < before_authority.timestamp:
        raise ValueError("evaluation authority snapshots are not ordered")
    outcome_window = (outcome.finished_at - outcome.started_at).total_seconds()
    authority_window = (after_authority.timestamp - before_authority.timestamp).total_seconds()
    if (
        outcome_window > suite.total_wall_clock_ceiling_seconds
        or authority_window > suite.total_wall_clock_ceiling_seconds
    ):
        raise ValueError("evaluation outcome exceeds suite total wall-clock ceiling")
    expected = _suite_cases(composition.bootstrap.evaluation_suite)
    if (
        _result_coordinates(outcome.baseline_results) != expected
        or _result_coordinates(outcome.candidate_results) != expected
    ):
        raise ValueError("baseline/candidate suite coordinates are not symmetric and ordered")
    all_ids = [r.run_id for r in (*outcome.baseline_results, *outcome.candidate_results)]
    if len(all_ids) != len(set(all_ids)):
        raise ValueError("evaluation run IDs are not unique")
    case_limits: dict[tuple[str, int, int, str], float] = {
        (case.scenario_id, seed, repeat_index, case.category): (
            case.per_run_wall_clock_ceiling_seconds
        )
        for case in (
            *suite.revealing_cases,
            *suite.structural_variants,
            *suite.regression_suites,
            *suite.long_horizon_suites,
        )
        for seed in case.seeds
        for repeat_index in range(case.repeat_count)
    }
    for result in (*outcome.baseline_results, *outcome.candidate_results):
        record = composition.context.ledger.get_run(result.run_id)
        expected_generation = (
            outcome.baseline_generation
            if result in outcome.baseline_results
            else candidate.candidate_id
        )
        if (
            record.generation_id != expected_generation
            or record.scenario_id != result.scenario_id
            or record.success != result.success
            or record.steps != result.steps
            or record.interventions != result.interventions
            or record.invalid_actions != result.invalid_actions
            or (record.termination == "goal_blocked") != result.blocked
            or record.termination != result.termination
            or record.trace_digest != result.trace_digest
        ):
            raise ValueError(f"evaluation run {result.run_id!r} differs from ScenarioResult")
        if (
            record.metadata.get("category") != result.category
            or record.metadata.get("seed") != result.seed
        ):
            raise ValueError(f"evaluation run {result.run_id!r} has wrong category or seed")
        trace_value = record.metadata.get("trace_path")
        trace_path = Path(trace_value) if isinstance(trace_value, str) else Path()
        workspace = composition.context.workspace.resolve()
        if (
            not isinstance(trace_value, str)
            or trace_path.is_symlink()
            or not trace_path.is_file()
            or trace_path.resolve() == workspace
            or workspace not in trace_path.resolve().parents
        ):
            raise ValueError(f"evaluation run {result.run_id!r} lacks regular-file trace evidence")
        events = read_jsonl_events(trace_path)
        ledger_events = composition.context.ledger.events_for_runs([record.run_id])
        if [event.model_dump(mode="json") for event in events] != [
            event.model_dump(mode="json") for event in ledger_events
        ]:
            raise ValueError(f"evaluation run {result.run_id!r} ledger trace differs")
        coordinate = (result.scenario_id, result.seed, result.repeat_index, result.category)
        ceiling = case_limits.get(coordinate)
        if ceiling is None or result.elapsed_seconds > ceiling:
            raise ValueError(
                f"evaluation run {result.run_id!r} exceeds suite coordinate or ceiling"
            )
        if sha256_bytes(trace_path.read_bytes()) != result.trace_digest:
            raise ValueError(f"evaluation run {result.run_id!r} trace digest is not canonical")
        persisted_duration = (record.finished_at - record.started_at).total_seconds()
        if result.steps > 0 and result.elapsed_seconds <= 0:
            raise ValueError(f"evaluation run {result.run_id!r} has forged zero elapsed time")
        if (
            record.finished_at < record.started_at
            or abs(persisted_duration - result.elapsed_seconds) > 0.05
        ):
            raise ValueError(f"evaluation run {result.run_id!r} has inconsistent duration")
        if (
            record.started_at < outcome.started_at
            or record.finished_at > outcome.finished_at
            or record.started_at < before_authority.timestamp
            or record.finished_at > after_authority.timestamp
            or persisted_duration > (ceiling or 0.0)
        ):
            raise ValueError(
                f"evaluation run {result.run_id!r} escapes evaluation authority window"
            )
    if outcome.baseline_metrics != _metrics(
        outcome.baseline_results
    ) or outcome.candidate_metrics != _metrics(outcome.candidate_results):
        raise ValueError("evaluation metrics are not generic recomputations")
    expected_namespaces = [suite.subject_metric_namespace]
    if [m.namespace for m in outcome.baseline_subject_metrics] != expected_namespaces:
        raise ValueError("baseline subject metrics have the wrong namespace")
    if [m.namespace for m in outcome.candidate_subject_metrics] != expected_namespaces:
        raise ValueError("candidate subject metrics have the wrong namespace")
    if candidate_before != _files_digest(candidate_workspace):
        raise ValueError(
            "candidate-workspace-change: reviewer or evaluator changed candidate workspace"
        )
    state["review"] = review
    state["outcome"] = outcome
    state["authority_pre"] = before_authority
    state["authority_post"] = after_authority
    return _passed(
        "evaluation_symmetry",
        "Reviewer and evaluator produced symmetric authoritative evidence",
        {
            "experiment_id": outcome.experiment_id,
            "run_count": len(all_ids),
            "suite_id": suite.suite_id,
        },
    )


def _materialization_check(
    composition: SubjectComposition, state: dict[str, object]
) -> SubjectCheck:
    candidate = state.get("candidate")
    outcome = state.get("outcome")
    review = state.get("review")
    if not isinstance(candidate, CandidateManifest) or not isinstance(outcome, EvaluationOutcome):
        raise ValueError("evaluation boundary did not produce an outcome")
    if not getattr(review, "passed", False):
        raise ValueError("candidate review did not pass")
    suite = composition.bootstrap.evaluation_suite
    candidate_files_before = _files_digest(Path(candidate.workspace_path).resolve())
    before = state.get("authority_pre")
    after = state.get("authority_post")
    if (
        not isinstance(before, EvaluationAuthoritySnapshot)
        or not isinstance(after, EvaluationAuthoritySnapshot)
        or before == after
    ):
        raise ValueError("evaluation authority snapshots are missing or not independent")
    protected_before = _verify_authority_artifacts(composition, suite)
    experiment = ExperimentResult(
        **outcome.model_dump(mode="python"),
        evaluation_suite_ref=before.suite_ref,
        pre_authority_snapshot=before,
        post_authority_snapshot=after,
    )
    experiment_ref = composition.context.artifacts.put_model(experiment)
    candidate = candidate.model_copy(
        update={
            "artifact_digests": {
                **candidate.artifact_digests,
                "experiment_object": experiment_ref.digest,
            }
        }
    )
    decision = RetentionPolicy().decide(experiment)
    if decision.verdict != GateVerdict.RETAIN:
        raise ValueError(f"fixture was not retainable: {decision.verdict.value}")
    child = composition.materializer.materialize(
        baseline=composition.bootstrap.baseline,
        candidate=candidate,
        experiment=experiment,
        decision=decision,
    )
    protected_after = _verify_authority_artifacts(composition, suite)
    if protected_before != protected_after:
        raise ValueError("materializer changed protected authority")
    if candidate_files_before != _files_digest(Path(candidate.workspace_path).resolve()):
        raise ValueError("candidate-workspace-change: materializer changed candidate workspace")
    forbidden_publications = (
        "cycle-result.json",
        "report.md",
        "cycle-manifest.pointer.json",
        "lineage.pointer.json",
    )
    if any((composition.context.workspace / name).exists() for name in forbidden_publications):
        raise ValueError("materializer published a cycle, stage, report, or lineage pointer")
    if composition.context.ledger.list_generations() or composition.context.ledger.lineage_rows():
        raise ValueError("materializer published generation or lineage ledger authority")
    if (
        child.parent_generation_id != composition.bootstrap.baseline.generation_id
        or child.subject != composition.plugin.name
        or child.generation_id == composition.bootstrap.baseline.generation_id
        or not child.source_ref.startswith("candidate:")
        or child.artifact_digests.get("experiment") != experiment_ref.digest
    ):
        raise ValueError("materialized child has incorrect parent or subject")
    if (
        child.metadata.get("retained_from_candidate") != candidate.candidate_id
        or child.metadata.get("experiment_id") != experiment.experiment_id
    ):
        raise ValueError("materialized child lacks candidate and experiment lineage evidence")
    manifest = composition.runner.capability_manifest(child)
    if stable_digest(manifest.model_dump(mode="json")) != child.capability_manifest_digest:
        raise ValueError("materialized capability CAS does not match runner manifest")
    if not _artifact_exists(composition.context.artifacts, child.capability_manifest_digest):
        raise ValueError("materialized capability CAS is missing")
    capability_ref = ArtifactRef(
        digest=child.capability_manifest_digest, model="CapabilityManifest"
    )
    parsed = composition.context.artifacts.read_model(capability_ref, CapabilityManifest)
    if (
        parsed.generation_id != child.generation_id
        or stable_digest(parsed.model_dump(mode="json")) != child.capability_manifest_digest
        or child.artifact_digests.get("capability_manifest") != child.capability_manifest_digest
    ):
        raise ValueError("materialized capability CAS is not a typed child-bound manifest")
    return _passed(
        "retained_generation_materialization",
        "Retention and direct materialization produced a valid child",
        {
            "child_generation": child.generation_id,
            "parent_generation": child.parent_generation_id,
            "experiment_id": experiment.experiment_id,
        },
    )


def _doctor_diagnostics(composition: SubjectComposition) -> BoundedCollection[SubjectDiagnostic]:
    try:
        value = composition.doctor.check()
    except Exception as exc:
        return BoundedCollection(
            items=[
                SubjectDiagnostic(
                    code="doctor_exception",
                    boundary_id="subject_doctor",
                    message=str(exc),
                    evidence={"exception": type(exc).__name__},
                )
            ],
            completeness=Completeness.COMPLETE,
            known_total=1,
        )
    if not isinstance(value, BoundedCollection):
        return BoundedCollection(
            items=[
                SubjectDiagnostic(
                    code="doctor_non_typed_result",
                    boundary_id="subject_doctor",
                    message="Subject doctor returned a non-typed result",
                    evidence={"result_type": type(value).__name__},
                )
            ],
            completeness=Completeness.COMPLETE,
            known_total=1,
        )
    try:
        return BoundedCollection[SubjectDiagnostic].model_validate(value.model_dump(mode="python"))
    except Exception as exc:
        return BoundedCollection(
            items=[
                SubjectDiagnostic(
                    code="doctor_invalid_result",
                    boundary_id="subject_doctor",
                    message=str(exc),
                    evidence={"exception": type(exc).__name__},
                )
            ],
            completeness=Completeness.COMPLETE,
            known_total=1,
        )


__all__ = ["BOUNDARIES", "run_subject_conformance"]
