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
    EvaluationAuthoritySnapshot,
    EvaluationCase,
    EvaluationOutcome,
    EvaluationSuiteManifest,
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
    ProtectedPathHash,
    ReviewReport,
    RoleInvocation,
    RoleRequest,
    RoleResponse,
    RoleTranscript,
    RunRecord,
    ScenarioResult,
    StagePointer,
    StageReceipt,
    SubjectCheck,
    SubjectConformanceFixture,
    SubjectConformanceReport,
    SubjectDiagnostic,
    SubjectMetricVector,
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
    "evaluation-authority-snapshot": EvaluationAuthoritySnapshot,
    "evaluation-case": EvaluationCase,
    "evaluation-suite-manifest": EvaluationSuiteManifest,
    "evaluation-outcome": EvaluationOutcome,
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
    "protected-path-hash": ProtectedPathHash,
    "role-request": RoleRequest,
    "role-response": RoleResponse,
    "role-invocation": RoleInvocation,
    "role-transcript": RoleTranscript,
    "review-report": ReviewReport,
    "run-record": RunRecord,
    "scenario-result": ScenarioResult,
    "stage-pointer": StagePointer,
    "stage-receipt": StageReceipt,
    "subject-metric-vector": SubjectMetricVector,
    "subject-check": SubjectCheck,
    "subject-conformance-fixture": SubjectConformanceFixture,
    "subject-conformance-report": SubjectConformanceReport,
    "subject-diagnostic": SubjectDiagnostic,
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
