from __future__ import annotations

from evogen.core.enums import FailureLayer, ResolutionKind
from evogen.core.ids import new_id
from evogen.core.models import (
    CapabilityIssue,
    DistilledTrace,
    IssueClassification,
)


class EvidenceFirstDiagnostician:
    """Conservative reference diagnostician used by the offline prototype.

    It deliberately diagnoses only a small set of evidence shapes. Unknown
    shapes become probe requests rather than speculative feature patches.
    External model-backed diagnosticians can replace this class through the
    same CapabilityIssue contract.
    """

    def diagnose(self, trace: DistilledTrace) -> CapabilityIssue:
        if not trace.signatures:
            raise ValueError("No failure signatures were present to diagnose")

        signature = max(trace.signatures, key=lambda item: (item.count, item.code))
        semantic_effects = set(trace.existing_semantic_effects)
        effect_missing = (
            signature.required_effect is not None
            and signature.required_effect not in semantic_effects
        )

        if signature.code == "no_supported_action" and effect_missing:
            repeated = signature.count >= 2
            classification = IssueClassification(
                primary=FailureLayer.AFFORDANCE_DISCOVERY,
                alternatives=[
                    FailureLayer.PLANNING_STRATEGY,
                    FailureLayer.ENVIRONMENT_LIMITATION,
                    FailureLayer.OBSERVABILITY,
                ],
                confidence=0.88 if repeated else 0.62,
                rationale=(
                    "The executor reached the same semantically relevant blocker, "
                    "but the required effect never appeared in its offered action language. "
                    "No dispatch or execution failure occurred because no candidate action existed."
                ),
            )
            resolution = (
                ResolutionKind.ADD_CAPABILITY if repeated else ResolutionKind.BUILD_PROBE
            )
            title = f"Capability surface cannot {signature.required_effect}"
            prediction = (
                f"A generation exposing a grounded {signature.required_effect!r} effect will "
                "replace the blocked terminal state with either a causal state change or an "
                "explicit environment refusal in the same scenarios."
            )
        elif "outcome" in signature.code:
            classification = IssueClassification(
                primary=FailureLayer.OUTCOME_VERIFICATION,
                alternatives=[FailureLayer.EXECUTION, FailureLayer.CAUSAL_ATTRIBUTION],
                confidence=0.72,
                rationale=(
                    "A command lifecycle exists, but the trace does not contain sufficient later "
                    "world evidence to determine whether the intended effect occurred."
                ),
            )
            resolution = ResolutionKind.ADD_OUTCOME_EVIDENCE
            title = f"Outcome is not verifiable for {signature.code}"
            prediction = (
                "Adding independent post-action evidence will classify the same attempts as "
                "succeeded, refused, or unknown without relying on dispatch acceptance."
            )
        elif "stale" in signature.code or "binding" in signature.code:
            classification = IssueClassification(
                primary=FailureLayer.BINDING_PRECONDITIONS,
                alternatives=[FailureLayer.OBSERVABILITY, FailureLayer.EXECUTION],
                confidence=0.70,
                rationale=(
                    "The offered intention could not be rebound against the world revision used "
                    "for execution."
                ),
            )
            resolution = ResolutionKind.CORRECT_CAPABILITY
            title = f"Action binding is unstable for {signature.code}"
            prediction = (
                "Revalidation against a fresh authoritative target will either execute the exact "
                "choice or reject it before side effects."
            )
        else:
            classification = IssueClassification(
                primary=FailureLayer.INSUFFICIENT_EVIDENCE,
                alternatives=[FailureLayer.RUNTIME_INFRASTRUCTURE],
                confidence=0.40,
                rationale=(
                    "The current evidence does not distinguish a capability defect from a local "
                    "planning, environment, or instrumentation failure."
                ),
            )
            resolution = ResolutionKind.BUILD_PROBE
            title = f"More evidence required for {signature.code}"
            prediction = (
                "A targeted probe will separate at least two currently viable diagnoses without "
                "changing the permanent action surface."
            )

        scenario_ids = trace.scenario_ids
        return CapabilityIssue(
            issue_id=new_id("issue"),
            subject_generation=trace.generation_id,
            title=title,
            symptom_summary=(
                f"Observed {signature.count} occurrence(s) of {signature.code!r} involving "
                f"blocker {signature.blocker_type!r}; required effect was "
                f"{signature.required_effect!r}."
            ),
            classification=classification,
            supporting_evidence=signature.evidence,
            contradicting_evidence=[
                "The executor was able to observe and navigate the surrounding world.",
                "No invalid dispatch was needed to produce the blocked state.",
            ],
            known_unknowns=[
                "Whether the underlying environment exposes the required effect.",
                "Whether the effect can be grounded to a stable target identity.",
                "What independent evidence can prove completion or refusal.",
            ],
            required_effect=signature.required_effect,
            blocker_type=signature.blocker_type,
            proposed_resolution=resolution,
            prediction=prediction,
            acceptance_hints={
                "revealing_cases": scenario_ids[:1],
                "structural_variants": scenario_ids[1:],
            },
            metadata={
                "failure_code": signature.code,
                "offered_actions": signature.offered_actions,
                "occurrence_count": signature.count,
            },
        )
