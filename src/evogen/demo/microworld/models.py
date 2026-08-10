from __future__ import annotations

from typing import Any

from pydantic import Field

from evogen.core.models import StrictModel


class ItemSpec(StrictModel):
    item_id: str
    name: str


class RoomSpec(StrictModel):
    room_id: str
    name: str
    neighbors: list[str]
    loose_item_ids: list[str] = Field(default_factory=list)


class ContainerSpec(StrictModel):
    container_id: str
    name: str
    room_id: str
    item_ids: list[str] = Field(default_factory=list)
    opaque: bool = True


class ScenarioSpec(StrictModel):
    scenario_id: str
    category: str
    description: str
    start_room_id: str
    target_item_id: str
    max_steps: int = Field(default=24, ge=1)
    items: list[ItemSpec]
    rooms: list[RoomSpec]
    containers: list[ContainerSpec] = Field(default_factory=list)


class VisibleItem(StrictModel):
    item_id: str
    name: str
    source_container_id: str | None = None


class VisibleContainer(StrictModel):
    container_id: str
    name: str
    opaque: bool
    inspected: bool
    revealed_items: list[VisibleItem] = Field(default_factory=list)


class WorldSnapshot(StrictModel):
    revision: int
    current_room_id: str
    current_room_name: str
    neighboring_room_ids: list[str]
    visible_items: list[VisibleItem]
    visible_containers: list[VisibleContainer]
    acquired_item_ids: list[str]
    target_item_id: str
    target_acquired: bool
    completeness: str = "complete"


class ActionOffer(StrictModel):
    action: str
    target_id: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    description: str


class ActionChoice(StrictModel):
    action: str
    target_id: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ActionResult(StrictModel):
    accepted: bool
    changed: bool
    message: str
    evidence: dict[str, Any] = Field(default_factory=dict)
