from __future__ import annotations

from dataclasses import dataclass

from evogen.core.models import EnvironmentOperation

from .models import (
    ActionResult,
    ContainerSpec,
    ScenarioSpec,
    VisibleContainer,
    VisibleItem,
    WorldSnapshot,
)


ENVIRONMENT_OPERATIONS = [
    EnvironmentOperation(
        name="move",
        semantic_effects=["change_location"],
        description="Move to an adjacent room exposed by the current world state.",
        source_ref="evogen.demo.microworld.environment:MicroWorld.move",
        input_schema={"destination_room_id": "string"},
        output_schema={"current_room_id": "string"},
        constraints=["Destination must be adjacent at dispatch."],
    ),
    EnvironmentOperation(
        name="take_item",
        semantic_effects=["acquire_visible_item"],
        description="Acquire an item currently exposed in the active room.",
        source_ref="evogen.demo.microworld.environment:MicroWorld.take_item",
        input_schema={"item_id": "string", "source_container_id": "string|null"},
        output_schema={"acquired_item_id": "string"},
        constraints=["The exact item must remain visible at dispatch."],
    ),
    EnvironmentOperation(
        name="inspect_container",
        semantic_effects=["reveal_contents"],
        description=(
            "Inspect an opaque container in the active room so later observations expose "
            "its contents without assuming what they are."
        ),
        source_ref="evogen.demo.microworld.environment:MicroWorld.inspect_container",
        input_schema={"container_id": "string"},
        output_schema={"container_id": "string", "inspected": "boolean"},
        constraints=[
            "Container must be present in the current room.",
            "Already inspected containers are not offered again.",
            "Contents remain unknown until a later snapshot reveals them.",
        ],
    ),
]


@dataclass
class _MutableContainer:
    spec: ContainerSpec
    remaining_item_ids: list[str]


class MicroWorld:
    """Small deterministic world whose full mechanics outstrip the baseline agent body."""

    def __init__(self, scenario: ScenarioSpec) -> None:
        self.scenario = scenario
        self.current_room_id = scenario.start_room_id
        self.revision = 0
        self.acquired: set[str] = set()
        self.inspected_containers: set[str] = set()
        self.loose_items: dict[str, list[str]] = {
            room.room_id: list(room.loose_item_ids) for room in scenario.rooms
        }
        self.containers: dict[str, _MutableContainer] = {
            container.container_id: _MutableContainer(
                spec=container,
                remaining_item_ids=list(container.item_ids),
            )
            for container in scenario.containers
        }
        self.rooms = {room.room_id: room for room in scenario.rooms}
        self.items = {item.item_id: item for item in scenario.items}
        if self.current_room_id not in self.rooms:
            raise ValueError(f"Unknown start room: {self.current_room_id}")

    def snapshot(self) -> WorldSnapshot:
        room = self.rooms[self.current_room_id]
        visible_items = [
            VisibleItem(item_id=item_id, name=self.items[item_id].name)
            for item_id in self.loose_items[self.current_room_id]
        ]
        visible_containers: list[VisibleContainer] = []
        for container in sorted(self.containers.values(), key=lambda item: item.spec.container_id):
            if container.spec.room_id != self.current_room_id:
                continue
            inspected = container.spec.container_id in self.inspected_containers
            revealed = (
                [
                    VisibleItem(
                        item_id=item_id,
                        name=self.items[item_id].name,
                        source_container_id=container.spec.container_id,
                    )
                    for item_id in container.remaining_item_ids
                ]
                if inspected
                else []
            )
            visible_items.extend(revealed)
            visible_containers.append(
                VisibleContainer(
                    container_id=container.spec.container_id,
                    name=container.spec.name,
                    opaque=container.spec.opaque,
                    inspected=inspected,
                    revealed_items=revealed,
                )
            )
        return WorldSnapshot(
            revision=self.revision,
            current_room_id=self.current_room_id,
            current_room_name=room.name,
            neighboring_room_ids=list(room.neighbors),
            visible_items=visible_items,
            visible_containers=visible_containers,
            acquired_item_ids=sorted(self.acquired),
            target_item_id=self.scenario.target_item_id,
            target_acquired=self.scenario.target_item_id in self.acquired,
        )

    def move(self, destination_room_id: str) -> ActionResult:
        room = self.rooms[self.current_room_id]
        if destination_room_id not in room.neighbors:
            return ActionResult(
                accepted=False,
                changed=False,
                message="Destination is not adjacent in the current world revision.",
                evidence={"current_room_id": self.current_room_id},
            )
        self.current_room_id = destination_room_id
        self.revision += 1
        return ActionResult(
            accepted=True,
            changed=True,
            message=f"Moved to {destination_room_id}.",
            evidence={"current_room_id": destination_room_id},
        )

    def take_item(self, item_id: str, source_container_id: str | None = None) -> ActionResult:
        if source_container_id is None:
            loose = self.loose_items[self.current_room_id]
            if item_id not in loose:
                return ActionResult(
                    accepted=False,
                    changed=False,
                    message="Loose item is not visible in the current room.",
                    evidence={"item_id": item_id},
                )
            loose.remove(item_id)
        else:
            container = self.containers.get(source_container_id)
            if container is None or container.spec.room_id != self.current_room_id:
                return ActionResult(
                    accepted=False,
                    changed=False,
                    message="Container is not present in the current room.",
                    evidence={"container_id": source_container_id},
                )
            if source_container_id not in self.inspected_containers:
                return ActionResult(
                    accepted=False,
                    changed=False,
                    message="Container contents are not exposed.",
                    evidence={"container_id": source_container_id},
                )
            if item_id not in container.remaining_item_ids:
                return ActionResult(
                    accepted=False,
                    changed=False,
                    message="Item is not exposed in the selected container.",
                    evidence={"item_id": item_id, "container_id": source_container_id},
                )
            container.remaining_item_ids.remove(item_id)
        self.acquired.add(item_id)
        self.revision += 1
        return ActionResult(
            accepted=True,
            changed=True,
            message=f"Acquired {item_id}.",
            evidence={"acquired_item_id": item_id},
        )

    def inspect_container(self, container_id: str) -> ActionResult:
        container = self.containers.get(container_id)
        if container is None or container.spec.room_id != self.current_room_id:
            return ActionResult(
                accepted=False,
                changed=False,
                message="Container is not present in the current room.",
                evidence={"container_id": container_id},
            )
        if container_id in self.inspected_containers:
            return ActionResult(
                accepted=False,
                changed=False,
                message="Container is already inspected.",
                evidence={"container_id": container_id},
            )
        self.inspected_containers.add(container_id)
        self.revision += 1
        return ActionResult(
            accepted=True,
            changed=True,
            message=f"Inspected {container_id}; contents will appear in later state.",
            evidence={"container_id": container_id, "inspected": True},
        )
