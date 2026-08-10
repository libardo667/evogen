from __future__ import annotations

import inspect

from evogen.core.ids import new_id
from evogen.core.models import CapabilityIssue, InvestigationReport

from .environment import ENVIRONMENT_OPERATIONS, MicroWorld


class MicroworldInvestigator:
    """Reference investigator that checks the actual environment surface."""

    def investigate(self, issue: CapabilityIssue) -> InvestigationReport:
        inspected = [
            "evogen.demo.microworld.environment:ENVIRONMENT_OPERATIONS",
            "evogen.demo.microworld.environment:MicroWorld",
        ]
        available_methods = {
            name for name, member in inspect.getmembers(MicroWorld) if callable(member)
        }
        candidates = [
            operation
            for operation in ENVIRONMENT_OPERATIONS
            if operation.name in available_methods
            and (
                issue.required_effect is None
                or issue.required_effect in operation.semantic_effects
            )
        ]
        rejected = [
            operation.name
            for operation in ENVIRONMENT_OPERATIONS
            if operation not in candidates
        ]
        if candidates:
            conclusion = (
                "The underlying environment already exposes one exact operation matching the "
                "required semantic effect; the subject generation lacks a grounded adapter for it."
            )
        else:
            conclusion = (
                "No inspected environment operation matches the required effect. A probe or "
                "environment-limitation disposition is required before implementation."
            )
        return InvestigationReport(
            report_id=new_id("investigation"),
            issue_id=issue.issue_id,
            inspected_sources=inspected,
            candidate_operations=candidates,
            rejected_operations=rejected,
            remaining_unknowns=(
                []
                if candidates
                else ["Whether an uninspected environment layer exposes the required effect."]
            ),
            conclusion=conclusion,
        )
