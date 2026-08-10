from __future__ import annotations

from evogen.core.enums import ResolutionKind
from evogen.core.ids import new_id
from evogen.core.models import (
    CapabilityIssue,
    CapabilitySpec,
    InvestigationReport,
)


class CapabilityArchitect:
    """Convert an issue plus environment evidence into an implementable contract."""

    def specify(
        self,
        *,
        issue: CapabilityIssue,
        investigation: InvestigationReport,
        revealing_cases: list[str],
        structural_variants: list[str],
        regression_suites: list[str],
        long_horizon_suites: list[str],
    ) -> CapabilitySpec:
        if issue.proposed_resolution != ResolutionKind.ADD_CAPABILITY:
            raise ValueError(
                f"Reference architect only implements add-capability issues, got "
                f"{issue.proposed_resolution.value}"
            )
        if issue.required_effect is None:
            raise ValueError("Capability issue has no required semantic effect")

        matching = [
            operation
            for operation in investigation.candidate_operations
            if issue.required_effect in operation.semantic_effects
        ]
        if len(matching) != 1:
            raise ValueError(
                "Capability specification requires exactly one environment operation matching "
                f"{issue.required_effect!r}; found {[operation.name for operation in matching]}"
            )
        operation = matching[0]

        return CapabilitySpec(
            spec_id=new_id("spec"),
            issue_id=issue.issue_id,
            parent_generation=issue.subject_generation,
            capability_name=operation.name,
            purpose=operation.description,
            semantic_effects=operation.semantic_effects,
            owner_component="subject capability plugin",
            input_schema=operation.input_schema,
            output_schema=operation.output_schema,
            applicability=(
                "Offer only when fresh authoritative state exposes an eligible target and the "
                "effect has not already been completed for that target."
            ),
            binding_rules=[
                "Bind the exact opaque target identifier from the current affordance.",
                "Re-enumerate applicability against the current world revision before execution.",
                "Reject missing, ambiguous, or already-resolved targets without side effects.",
            ],
            execution_route=operation.source_ref,
            completion_evidence=[
                "The environment returns an accepted execution receipt.",
                "A later observation independently exposes the target's revealed state.",
                "Dispatch acceptance alone is not completion evidence.",
            ],
            non_goals=[
                "Do not encode a revealing scenario identifier or target item identifier.",
                "Do not alter the environment or evaluator to make the capability pass.",
                "Do not infer hidden contents before the environment reveals them.",
            ],
            prediction=issue.prediction,
            revealing_cases=revealing_cases,
            structural_variants=structural_variants,
            regression_suites=regression_suites,
            long_horizon_suites=long_horizon_suites,
            implementation_constraints=[
                *operation.constraints,
                "Implementation must be loadable as an isolated capability plugin.",
                "The existing move and take capabilities must remain unchanged.",
            ],
        )
