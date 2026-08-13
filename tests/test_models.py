from __future__ import annotations

from pathlib import Path

import pytest

from evogen.core.enums import CapabilityKind, EvidenceState, GateVerdict, ProofClass
from evogen.core.ids import sha256_bytes
from evogen.core.models import (
    CapabilityDefinition,
    CapabilityEvidenceRef,
    CapabilityManifest,
    GateDecision,
)

CAPABILITY_FIXTURE = Path(__file__).parent / "fixtures" / "capability_authority.txt"


def test_non_retained_decision_cannot_name_retained_generation():
    with pytest.raises(ValueError):
        GateDecision(
            decision_id="decision-1",
            candidate_id="candidate-1",
            verdict=GateVerdict.REJECT,
            passed_rules=[],
            failed_rules=["regression"],
            rationale="Regression failed.",
            retained_generation_id="gen-2",
        )


def _capability(**overrides: object) -> CapabilityDefinition:
    values: dict[str, object] = {
        "name": "action.example",
        "purpose": "An example capability.",
        "kind": CapabilityKind.ACTION,
        "semantic_effects": ["effect"],
        "owner_component": "subject.example",
        "applicability": "when available",
        "implementation_ref": "subject.example.run",
        "introduced_generation": "g0",
        "evidence_state": EvidenceState.PROVEN,
        "proof_class": ProofClass.PORTABLE,
        "evidence_refs": [
            CapabilityEvidenceRef(
                authority_ref="fixture:capability_authority.txt",
                content_digest=sha256_bytes(CAPABILITY_FIXTURE.read_bytes()),
                evidence_state=EvidenceState.PROVEN,
                proof_class=ProofClass.PORTABLE,
            )
        ],
    }
    values.update(overrides)
    return CapabilityDefinition(**values)


def test_capability_definition_requires_explicit_evidence_shape() -> None:
    capability = _capability()
    assert capability.evidence_state is EvidenceState.PROVEN
    assert capability.proof_class is ProofClass.PORTABLE
    assert capability.kind is CapabilityKind.ACTION


def test_capability_kind_is_exactly_six_value_contract() -> None:
    assert [kind.value for kind in CapabilityKind] == [
        "sensing",
        "representation",
        "memory",
        "action",
        "verification",
        "recovery",
    ]
    with pytest.raises(ValueError):
        _capability(kind="not-a-capability-kind")


def test_capability_definition_rejects_omitted_evidence_fields() -> None:
    values = _capability().model_dump()
    values.pop("evidence_state")
    with pytest.raises(ValueError):
        CapabilityDefinition(**values)
    values = _capability().model_dump()
    values.pop("proof_class")
    with pytest.raises(ValueError):
        CapabilityDefinition(**values)


@pytest.mark.parametrize(
    "state",
    [
        EvidenceState.UNPROVEN,
        EvidenceState.ABSENT,
        EvidenceState.WITHHELD,
        EvidenceState.UNKNOWN,
        EvidenceState.UNSUPPORTED,
    ],
)
def test_non_proven_capabilities_cannot_carry_proof_class(state: EvidenceState) -> None:
    evidence_refs = [] if state is EvidenceState.ABSENT else _capability().evidence_refs
    with pytest.raises(ValueError, match="cannot carry proof_class"):
        _capability(
            evidence_state=state,
            proof_class=ProofClass.PORTABLE,
            evidence_refs=evidence_refs,
        )


def test_proven_capabilities_require_proof_class() -> None:
    with pytest.raises(ValueError, match="require proof_class"):
        _capability(evidence_state=EvidenceState.PROVEN, proof_class=None)


def test_proven_capabilities_require_evidence_refs() -> None:
    with pytest.raises(ValueError, match="require evidence_refs"):
        _capability(evidence_refs=[])


@pytest.mark.parametrize(
    "field",
    [
        "name",
        "purpose",
        "owner_component",
        "applicability",
        "implementation_ref",
        "introduced_generation",
    ],
)
def test_capability_identity_and_semantic_strings_must_be_nonblank(field: str) -> None:
    with pytest.raises(ValueError, match="value must be nonblank"):
        _capability(**{field: "  "})


@pytest.mark.parametrize("field", ["semantic_effects", "completion_evidence", "limitations"])
def test_capability_string_lists_cannot_contain_blank_items(field: str) -> None:
    with pytest.raises(ValueError, match="value must be nonblank"):
        _capability(**{field: ["valid", " "]})


def test_capability_requires_at_least_one_semantic_effect() -> None:
    with pytest.raises(ValueError, match="at least 1 item"):
        _capability(semantic_effects=[])


def test_capability_evidence_authority_ref_must_be_nonblank() -> None:
    with pytest.raises(ValueError, match="value must be nonblank"):
        CapabilityEvidenceRef(
            authority_ref=" ",
            content_digest="0" * 64,
            evidence_state=EvidenceState.PROVEN,
            proof_class=ProofClass.PORTABLE,
        )


def test_capability_manifest_requires_unique_sorted_names_and_nonblank_generation() -> None:
    first = _capability(name="a", introduced_generation="genesis")
    second = _capability(name="b", introduced_generation="older")
    manifest = CapabilityManifest(generation_id="current", capabilities=[first, second])
    assert manifest.generation_id == "current"
    assert [capability.introduced_generation for capability in manifest.capabilities] == [
        "genesis",
        "older",
    ]

    with pytest.raises(ValueError, match="duplicate names"):
        CapabilityManifest(generation_id="current", capabilities=[first, first])
    with pytest.raises(ValueError, match="sorted by name"):
        CapabilityManifest(generation_id="current", capabilities=[second, first])
    with pytest.raises(ValueError, match="value must be nonblank"):
        CapabilityManifest(generation_id=" ", capabilities=[first])


def test_capability_evidence_ref_requires_explicit_coherent_shape() -> None:
    with pytest.raises(ValueError):
        CapabilityEvidenceRef(
            authority_ref="artifact.json",
            content_digest="0" * 64,
            evidence_state=EvidenceState.PROVEN,
        )
    with pytest.raises(ValueError):
        CapabilityEvidenceRef(
            authority_ref="artifact.json",
            content_digest="0" * 64,
            evidence_state=EvidenceState.ABSENT,
            proof_class=None,
        )
