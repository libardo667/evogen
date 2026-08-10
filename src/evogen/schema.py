from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from evogen.core.models import (
    BoundedCollection,
    CandidateManifest,
    CapabilityDefinition,
    CapabilityIssue,
    CapabilityManifest,
    CapabilitySpec,
    CycleResult,
    DistilledTrace,
    EvolutionPlan,
    ExperimentResult,
    GateDecision,
    GenerationManifest,
    InvestigationReport,
    PatchSet,
    RoleRequest,
    RoleResponse,
    RunRecord,
    TrajectoryEvent,
)

MODEL_REGISTRY: dict[str, type[BaseModel]] = {
    "bounded-collection": BoundedCollection[dict[str, object]],
    "candidate-manifest": CandidateManifest,
    "capability-definition": CapabilityDefinition,
    "capability-issue": CapabilityIssue,
    "capability-manifest": CapabilityManifest,
    "capability-spec": CapabilitySpec,
    "cycle-result": CycleResult,
    "distilled-trace": DistilledTrace,
    "evolution-plan": EvolutionPlan,
    "experiment-result": ExperimentResult,
    "gate-decision": GateDecision,
    "generation-manifest": GenerationManifest,
    "investigation-report": InvestigationReport,
    "patch-set": PatchSet,
    "role-request": RoleRequest,
    "role-response": RoleResponse,
    "run-record": RunRecord,
    "trajectory-event": TrajectoryEvent,
}


def export_schemas(directory: Path) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    index: dict[str, str] = {}
    for name, model in sorted(MODEL_REGISTRY.items()):
        filename = f"{name}.schema.json"
        path = directory / filename
        schema = model.model_json_schema()
        path.write_text(
            json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        written.append(path)
        index[name] = filename
    index_path = directory / "index.json"
    index_path.write_text(
        json.dumps(index, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    written.append(index_path)
    return written
