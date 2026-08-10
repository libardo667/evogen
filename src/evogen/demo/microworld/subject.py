from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

from evogen.core.enums import EventKind, ProofClass
from evogen.core.ids import new_id
from evogen.core.models import (
    CapabilityDefinition,
    CapabilityManifest,
    GenerationManifest,
    RunRecord,
    TrajectoryEvent,
)
from evogen.trace.io import TrajectoryRecorder

from .environment import MicroWorld
from .models import ActionChoice, ActionOffer, ActionResult, ScenarioSpec, WorldSnapshot
from .plugin_api import MicroworldCapability
from .scenarios import get_scenario


class MoveCapability:
    name = "move"

    def definition(self, generation_id: str) -> CapabilityDefinition:
        return CapabilityDefinition(
            name=self.name,
            purpose="Move through a currently adjacent room connection.",
            kind="action",
            semantic_effects=["change_location"],
            owner_component="microworld subject",
            input_schema={"destination_room_id": "string"},
            output_schema={"current_room_id": "string"},
            applicability="A destination is offered only when currently adjacent.",
            completion_evidence=["Later world state reports the destination as current."],
            implementation_ref="builtin:MoveCapability",
            proof_class=ProofClass.PORTABLE,
            introduced_generation="genesis",
        )

    def offers(self, snapshot: WorldSnapshot) -> list[ActionOffer]:
        return [
            ActionOffer(
                action=self.name,
                target_id=room_id,
                arguments={"expected_revision": snapshot.revision},
                description=f"Move to adjacent room {room_id}.",
            )
            for room_id in sorted(snapshot.neighboring_room_ids)
        ]

    def execute(self, world: MicroWorld, choice: ActionChoice) -> ActionResult:
        return world.move(choice.target_id)


class TakeItemCapability:
    name = "take_item"

    def definition(self, generation_id: str) -> CapabilityDefinition:
        return CapabilityDefinition(
            name=self.name,
            purpose="Acquire an exact item already visible in current state.",
            kind="action",
            semantic_effects=["acquire_visible_item"],
            owner_component="microworld subject",
            input_schema={"item_id": "string", "source_container_id": "string|null"},
            output_schema={"acquired_item_id": "string"},
            applicability="The item must be exposed in the active room.",
            completion_evidence=["Later world state includes the item in acquired_item_ids."],
            implementation_ref="builtin:TakeItemCapability",
            proof_class=ProofClass.PORTABLE,
            introduced_generation="genesis",
        )

    def offers(self, snapshot: WorldSnapshot) -> list[ActionOffer]:
        return [
            ActionOffer(
                action=self.name,
                target_id=item.item_id,
                arguments={
                    "source_container_id": item.source_container_id,
                    "expected_revision": snapshot.revision,
                },
                description=f"Acquire visible item {item.name}.",
            )
            for item in sorted(snapshot.visible_items, key=lambda item: item.item_id)
        ]

    def execute(self, world: MicroWorld, choice: ActionChoice) -> ActionResult:
        source = choice.arguments.get("source_container_id")
        return world.take_item(
            choice.target_id,
            source_container_id=source if isinstance(source, str) else None,
        )


class MicroworldSubject:
    """Semantic agent body whose capability plugins can evolve between generations."""

    def __init__(self, *, generation_id: str, plugin_root: Path | None = None) -> None:
        self.generation_id = generation_id
        self.capabilities: dict[str, MicroworldCapability] = {
            "move": MoveCapability(),
            "take_item": TakeItemCapability(),
        }
        if plugin_root is not None:
            self._load_plugins(plugin_root)

    @classmethod
    def from_generation(cls, generation: GenerationManifest) -> "MicroworldSubject":
        plugin_value = generation.config.get("plugin_root")
        plugin_root = Path(plugin_value) if isinstance(plugin_value, str) else None
        return cls(generation_id=generation.generation_id, plugin_root=plugin_root)

    def _load_plugins(self, plugin_root: Path) -> None:
        if not plugin_root.exists():
            return
        for path in sorted(plugin_root.glob("*.py")):
            if path.name.startswith("_"):
                continue
            module = _load_module(path, self.generation_id)
            factory = getattr(module, "build_plugin", None)
            if not callable(factory):
                raise RuntimeError(f"Capability plugin lacks build_plugin(): {path}")
            capability = factory()
            name = getattr(capability, "name", None)
            if not isinstance(name, str):
                raise RuntimeError(f"Capability plugin has no string name: {path}")
            if name in self.capabilities:
                raise RuntimeError(f"Duplicate capability {name!r} from {path}")
            self.capabilities[name] = capability

    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            generation_id=self.generation_id,
            capabilities=[
                capability.definition(self.generation_id)
                for capability in sorted(self.capabilities.values(), key=lambda item: item.name)
            ],
        )

    def offers(self, snapshot: WorldSnapshot) -> list[ActionOffer]:
        offers = [
            offer
            for capability in self.capabilities.values()
            for offer in capability.offers(snapshot)
        ]
        return sorted(offers, key=lambda offer: (offer.action, offer.target_id))

    def execute(
        self,
        world: MicroWorld,
        choice: ActionChoice,
        *,
        expected_revision: int,
    ) -> ActionResult:
        if world.revision != expected_revision:
            return ActionResult(
                accepted=False,
                changed=False,
                message="World revision changed before binding.",
                evidence={
                    "expected_revision": expected_revision,
                    "actual_revision": world.revision,
                },
            )
        capability = self.capabilities.get(choice.action)
        if capability is None:
            return ActionResult(
                accepted=False,
                changed=False,
                message="Capability is not installed in this generation.",
                evidence={"action": choice.action},
            )
        current_offers = capability.offers(world.snapshot())
        exact = [
            offer
            for offer in current_offers
            if offer.action == choice.action
            and offer.target_id == choice.target_id
            and _semantic_arguments(offer.arguments) == _semantic_arguments(choice.arguments)
        ]
        if len(exact) != 1:
            return ActionResult(
                accepted=False,
                changed=False,
                message="Exact affordance disappeared or became ambiguous before execution.",
                evidence={"matching_offer_count": len(exact)},
            )
        return capability.execute(world, choice)


class MicroworldRunner:
    def capability_manifest(self, generation: GenerationManifest) -> CapabilityManifest:
        return MicroworldSubject.from_generation(generation).manifest()

    def run(
        self,
        *,
        generation: GenerationManifest,
        scenario_id: str,
        trace_directory: Path,
    ) -> tuple[RunRecord, list[TrajectoryEvent]]:
        scenario = get_scenario(scenario_id)
        return self.run_scenario(
            generation=generation,
            scenario=scenario,
            trace_directory=trace_directory,
        )

    def run_scenario(
        self,
        *,
        generation: GenerationManifest,
        scenario: ScenarioSpec,
        trace_directory: Path,
    ) -> tuple[RunRecord, list[TrajectoryEvent]]:
        run_id = new_id("run")
        path = trace_directory / f"{run_id}.jsonl"
        recorder = TrajectoryRecorder(
            path=path,
            run_id=run_id,
            generation_id=generation.generation_id,
            scenario_id=scenario.scenario_id,
        )
        started = datetime.now(UTC)
        subject = MicroworldSubject.from_generation(generation)
        world = MicroWorld(scenario)
        visited_rooms = {world.current_room_id}
        observed_opaque: set[str] = set()
        invalid_actions = 0
        steps = 0
        termination = "step_limit"
        success = False

        recorder.record(
            EventKind.RUN_STARTED,
            {
                "objective": f"Acquire item {scenario.target_item_id}.",
                "installed_capabilities": sorted(subject.capabilities),
                "category": scenario.category,
            },
            world_revision=str(world.revision),
        )

        for step_index in range(scenario.max_steps):
            snapshot = world.snapshot()
            observed_opaque.update(
                container.container_id
                for container in snapshot.visible_containers
                if container.opaque and not container.inspected
            )
            recorder.record(
                EventKind.OBSERVATION,
                snapshot.model_dump(mode="json"),
                world_revision=str(snapshot.revision),
            )
            if snapshot.target_acquired:
                success = True
                termination = "goal_achieved"
                recorder.record(
                    EventKind.GOAL_ACHIEVED,
                    {"target_item_id": scenario.target_item_id},
                    world_revision=str(snapshot.revision),
                )
                break

            offers = subject.offers(snapshot)
            recorder.record(
                EventKind.AFFORDANCE_SET,
                {"offers": [offer.model_dump(mode="json") for offer in offers]},
                world_revision=str(snapshot.revision),
            )
            choice = _choose_action(
                snapshot=snapshot,
                offers=offers,
                visited_rooms=visited_rooms,
            )
            if choice is None:
                termination = "goal_blocked"
                recorder.record(
                    EventKind.GOAL_BLOCKED,
                    {
                        "code": "no_supported_action",
                        "blocker_type": (
                            "opaque_container" if observed_opaque else "unexplored_world"
                        ),
                        "required_effect": (
                            "reveal_contents" if observed_opaque else "discover_route"
                        ),
                        "observed_blocking_entity_ids": sorted(observed_opaque),
                        "visited_room_ids": sorted(visited_rooms),
                        "target_item_id_known": True,
                    },
                    world_revision=str(snapshot.revision),
                )
                break

            recorder.record(
                EventKind.DECISION,
                {
                    "choice": choice.model_dump(mode="json"),
                    "basis": "deterministic reference policy",
                },
                world_revision=str(snapshot.revision),
            )
            recorder.record(
                EventKind.BINDING,
                {
                    "action": choice.action,
                    "target_id": choice.target_id,
                    "expected_revision": snapshot.revision,
                },
                world_revision=str(snapshot.revision),
            )
            recorder.record(
                EventKind.DISPATCH,
                {"choice": choice.model_dump(mode="json")},
                world_revision=str(snapshot.revision),
            )
            result = subject.execute(
                world,
                choice,
                expected_revision=snapshot.revision,
            )
            steps += 1
            if not result.accepted:
                invalid_actions += 1
            recorder.record(
                EventKind.EXECUTION_RECEIPT,
                result.model_dump(mode="json"),
                world_revision=str(world.revision),
            )
            later = world.snapshot()
            recorder.record(
                EventKind.OUTCOME_OBSERVATION,
                later.model_dump(mode="json"),
                world_revision=str(later.revision),
            )
            if choice.action == "move" and result.accepted:
                visited_rooms.add(choice.target_id)

        final_snapshot = world.snapshot()
        if final_snapshot.target_acquired and not success:
            success = True
            termination = "goal_achieved"
            recorder.record(
                EventKind.GOAL_ACHIEVED,
                {"target_item_id": scenario.target_item_id},
                world_revision=str(final_snapshot.revision),
            )
        recorder.record(
            EventKind.RUN_FINISHED,
            {
                "success": success,
                "termination": termination,
                "steps": steps,
                "invalid_actions": invalid_actions,
                "interventions": 0,
            },
            world_revision=str(final_snapshot.revision),
        )
        finished = datetime.now(UTC)
        record = RunRecord(
            run_id=run_id,
            generation_id=generation.generation_id,
            scenario_id=scenario.scenario_id,
            started_at=started,
            finished_at=finished,
            success=success,
            termination=termination,
            trace_digest=recorder.digest(),
            steps=steps,
            interventions=0,
            invalid_actions=invalid_actions,
            metadata={"category": scenario.category, "trace_path": str(path)},
        )
        return record, recorder.events


def _choose_action(
    *,
    snapshot: WorldSnapshot,
    offers: list[ActionOffer],
    visited_rooms: set[str],
) -> ActionChoice | None:
    target_take = next(
        (
            offer
            for offer in offers
            if offer.action == "take_item" and offer.target_id == snapshot.target_item_id
        ),
        None,
    )
    if target_take is not None:
        return ActionChoice(
            action=target_take.action,
            target_id=target_take.target_id,
            arguments=target_take.arguments,
        )

    inspect_offer = next(
        (offer for offer in offers if offer.action == "inspect_container"),
        None,
    )
    if inspect_offer is not None:
        return ActionChoice(
            action=inspect_offer.action,
            target_id=inspect_offer.target_id,
            arguments=inspect_offer.arguments,
        )

    unexplored_move = next(
        (
            offer
            for offer in offers
            if offer.action == "move" and offer.target_id not in visited_rooms
        ),
        None,
    )
    if unexplored_move is not None:
        return ActionChoice(
            action=unexplored_move.action,
            target_id=unexplored_move.target_id,
            arguments=unexplored_move.arguments,
        )
    return None


def _semantic_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in arguments.items() if key != "expected_revision"}


def _load_module(path: Path, generation_id: str) -> ModuleType:
    module_name = f"evogen_candidate_{generation_id.replace('-', '_')}_{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load capability plugin: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
