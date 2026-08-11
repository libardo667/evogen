from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from evogen.core.models import (
    ArtifactRef,
    BoundedCollection,
    CandidateManifest,
    CapabilityDefinition,
    CapabilityIssue,
    CapabilityManifest,
    CapabilitySpec,
    CycleManifest,
    CycleResult,
    DistilledTrace,
    EvolutionPlan,
    ExperimentResult,
    GateDecision,
    GenerationManifest,
    IngestResult,
    InvestigationReport,
    PatchSet,
    ProbeBuildOutput,
    ProbeCandidateManifest,
    ProbeDispatchEvidence,
    ProbeDisposition,
    ProbeEvaluation,
    ProbeEvidenceTarget,
    ProbeFilePayload,
    ProbeManifest,
    ProbeObservationEvidence,
    ProbePermissions,
    ProbePlan,
    ProbeRequiredResult,
    ProbeResult,
    ProbeReviewReport,
    ProbeStagePointer,
    ProbeStageReceipt,
    RoleRequest,
    RoleResponse,
    RunRecord,
    StagePointer,
    StageReceipt,
    TrajectoryEvent,
)

MODEL_REGISTRY: dict[str, type[BaseModel]] = {
    "artifact-ref": ArtifactRef,
    "bounded-collection": BoundedCollection[dict[str, object]],
    "candidate-manifest": CandidateManifest,
    "capability-definition": CapabilityDefinition,
    "capability-issue": CapabilityIssue,
    "capability-manifest": CapabilityManifest,
    "capability-spec": CapabilitySpec,
    "cycle-manifest": CycleManifest,
    "cycle-result": CycleResult,
    "distilled-trace": DistilledTrace,
    "evolution-plan": EvolutionPlan,
    "experiment-result": ExperimentResult,
    "gate-decision": GateDecision,
    "generation-manifest": GenerationManifest,
    "ingest-result": IngestResult,
    "investigation-report": InvestigationReport,
    "patch-set": PatchSet,
    "probe-build-output": ProbeBuildOutput,
    "probe-candidate-manifest": ProbeCandidateManifest,
    "probe-disposition": ProbeDisposition,
    "probe-dispatch-evidence": ProbeDispatchEvidence,
    "probe-evaluation": ProbeEvaluation,
    "probe-evidence-target": ProbeEvidenceTarget,
    "probe-file-payload": ProbeFilePayload,
    "probe-manifest": ProbeManifest,
    "probe-observation-evidence": ProbeObservationEvidence,
    "probe-plan": ProbePlan,
    "probe-permissions": ProbePermissions,
    "probe-required-result": ProbeRequiredResult,
    "probe-result": ProbeResult,
    "probe-review-report": ProbeReviewReport,
    "probe-stage-pointer": ProbeStagePointer,
    "probe-stage-receipt": ProbeStageReceipt,
    "role-request": RoleRequest,
    "role-response": RoleResponse,
    "run-record": RunRecord,
    "stage-pointer": StagePointer,
    "stage-receipt": StageReceipt,
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
