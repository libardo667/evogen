from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from evogen.core.enums import EventKind
from evogen.core.models import (
    CapabilityManifest,
    DistilledTrace,
    EvidenceRef,
    FailureSignature,
    TrajectoryEvent,
)


class TraceDistiller:
    """Turn raw events into bounded, evidence-linked failure signatures."""

    def distill(
        self,
        *,
        generation_id: str,
        events: Iterable[TrajectoryEvent],
        capabilities: CapabilityManifest,
    ) -> DistilledTrace:
        event_list = list(events)
        if not event_list:
            raise ValueError("Cannot distill an empty trajectory set")
        wrong_generation = {
            event.generation_id for event in event_list if event.generation_id != generation_id
        }
        if wrong_generation:
            raise ValueError(f"Events contain other generations: {sorted(wrong_generation)}")

        grouped: dict[tuple[str, str | None, str | None], list[TrajectoryEvent]] = defaultdict(list)
        offered_by_run: dict[str, set[str]] = defaultdict(set)
        for event in event_list:
            if event.kind == EventKind.AFFORDANCE_SET:
                for offer in event.payload.get("offers", []):
                    if isinstance(offer, dict) and isinstance(offer.get("action"), str):
                        offered_by_run[event.run_id].add(offer["action"])
            if event.kind == EventKind.GOAL_BLOCKED:
                code = str(event.payload.get("code", "goal_blocked"))
                blocker = _optional_str(event.payload.get("blocker_type"))
                effect = _optional_str(event.payload.get("required_effect"))
                grouped[(code, blocker, effect)].append(event)
            elif event.kind == EventKind.ERROR:
                code = str(event.payload.get("code", "runtime_error"))
                layer_hint = _optional_str(event.payload.get("layer_hint"))
                grouped[(code, layer_hint, None)].append(event)

        signatures: list[FailureSignature] = []
        for (code, blocker, effect), matching_events in sorted(grouped.items()):
            offered = sorted(
                {
                    action
                    for event in matching_events
                    for action in offered_by_run.get(event.run_id, set())
                }
            )
            facts: dict[str, Any] = {}
            for event in matching_events:
                for key, value in event.payload.items():
                    if key in {"code", "blocker_type", "required_effect"}:
                        continue
                    if key not in facts:
                        facts[key] = value
                    elif facts[key] != value:
                        facts[key] = "varies_across_evidence"
            signatures.append(
                FailureSignature(
                    code=code,
                    count=len(matching_events),
                    blocker_type=blocker,
                    required_effect=effect,
                    offered_actions=offered,
                    evidence=[
                        EvidenceRef(
                            run_id=event.run_id,
                            event_id=event.event_id,
                            note=f"{event.kind.value} at sequence {event.sequence}",
                        )
                        for event in matching_events
                    ],
                    facts=facts,
                )
            )

        return DistilledTrace(
            generation_id=generation_id,
            run_ids=sorted({event.run_id for event in event_list}),
            scenario_ids=sorted({event.scenario_id for event in event_list}),
            existing_capabilities=sorted(capabilities.names),
            existing_semantic_effects=sorted(
                {
                    effect
                    for capability in capabilities.capabilities
                    for effect in capability.semantic_effects
                }
            ),
            signatures=signatures,
            event_count=len(event_list),
        )


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) else None
