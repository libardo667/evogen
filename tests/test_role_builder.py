from __future__ import annotations

import pytest

from evogen.adapters.agents import RawRoleExecution, RoleInvoker
from evogen.adapters.role_builder import CandidateBuildError, RoleBackedDirectoryBuilder
from evogen.core.enums import AgentRole, FailureLayer, ResolutionKind, RoleOutcome
from evogen.core.ids import new_id
from evogen.core.models import (
    CapabilityIssue,
    CapabilitySpec,
    GenerationManifest,
    IssueClassification,
    RoleRequest,
    RoleResponse,
)
from evogen.storage.artifacts import ArtifactStore
from evogen.storage.ledger import Ledger


class FakeBackend:
    def __init__(self, output):
        self.output = output
        self.requests: list[RoleRequest] = []

    timeout_seconds = 5.0

    def execute(self, request: RoleRequest) -> RawRoleExecution:
        self.requests.append(request)
        response = RoleResponse(
            response_id=new_id("response"),
            request_id=request.request_id,
            role=AgentRole.IMPLEMENTER,
            success=True,
            output=self.output,
        )
        return RawRoleExecution(
            response=response,
            stdout=None,
            stderr=None,
            process_status=0,
            outcome=RoleOutcome.SUCCESS,
        )


def parent() -> GenerationManifest:
    return GenerationManifest(
        generation_id="gen-1",
        subject="subject",
        source_ref="source",
        capability_manifest_digest="0" * 64,
    )


def issue() -> CapabilityIssue:
    return CapabilityIssue(
        issue_id="issue-1",
        subject_generation="gen-1",
        title="Missing inspect",
        symptom_summary="No inspect action exists.",
        classification=IssueClassification(
            primary=FailureLayer.AFFORDANCE_DISCOVERY,
            confidence=0.9,
            rationale="No offer exists.",
        ),
        supporting_evidence=[],
        proposed_resolution=ResolutionKind.ADD_CAPABILITY,
        required_effect="reveal_contents",
        prediction="Contents become visible.",
    )


def specification() -> CapabilitySpec:
    return CapabilitySpec(
        spec_id="spec-1",
        issue_id="issue-1",
        parent_generation="gen-1",
        capability_name="inspect",
        purpose="Reveal contents.",
        semantic_effects=["reveal_contents"],
        owner_component="plugin",
        input_schema={},
        output_schema={},
        applicability="Exact current target.",
        binding_rules=[],
        execution_route="environment.inspect",
        completion_evidence=["Later state reveals contents."],
        non_goals=["Do not encode scenarios."],
        prediction="Contents become visible.",
        revealing_cases=["case-1"],
        structural_variants=["case-2"],
        regression_suites=["regression"],
        long_horizon_suites=["long"],
    )


def test_role_backed_builder_writes_validated_patch_set(tmp_path):
    backend = FakeBackend(
        {
            "summary": "Add generic inspection plugin.",
            "files": [{"path": "plugins/inspect.py", "content": "VALUE = 1\n"}],
            "claimed_capabilities": ["inspect"],
        }
    )
    invoker = RoleInvoker(
        backend=backend,
        artifacts=ArtifactStore(tmp_path / "artifacts"),
        ledger=Ledger(tmp_path / "ledger.sqlite3"),
        provider="test-provider",
        model="test-model",
        authority_id="test-authority",
    )
    builder = RoleBackedDirectoryBuilder(invoker=invoker)
    candidate = builder.build(
        parent=parent(),
        issue=issue(),
        specification=specification(),
        candidate_root=tmp_path / "candidates",
    )

    assert (tmp_path / "candidates" / candidate.candidate_id / "plugins" / "inspect.py").exists()
    assert candidate.changed_files == ["plugins/inspect.py"]
    assert candidate.claimed_capabilities == ["inspect"]
    assert backend.requests[0].role == AgentRole.IMPLEMENTER


def test_role_backed_builder_rejects_path_traversal(tmp_path):
    backend = FakeBackend(
        {
            "summary": "Escape candidate root.",
            "files": [{"path": "../outside.py", "content": "bad = True\n"}],
        }
    )
    invoker = RoleInvoker(
        backend=backend,
        artifacts=ArtifactStore(tmp_path / "artifacts"),
        ledger=Ledger(tmp_path / "ledger.sqlite3"),
        provider="test-provider",
        model="test-model",
        authority_id="test-authority",
    )
    builder = RoleBackedDirectoryBuilder(invoker=invoker)

    with pytest.raises(CandidateBuildError):
        builder.build(
            parent=parent(),
            issue=issue(),
            specification=specification(),
            candidate_root=tmp_path / "candidates",
        )
    assert not (tmp_path / "outside.py").exists()
