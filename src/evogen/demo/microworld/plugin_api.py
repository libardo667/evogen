from __future__ import annotations

from typing import Protocol

from evogen.core.models import CapabilityDefinition

from .environment import MicroWorld
from .models import ActionChoice, ActionOffer, ActionResult, WorldSnapshot


class MicroworldCapability(Protocol):
    name: str

    def definition(self, generation_id: str) -> CapabilityDefinition: ...

    def offers(self, snapshot: WorldSnapshot) -> list[ActionOffer]: ...

    def execute(self, world: MicroWorld, choice: ActionChoice) -> ActionResult: ...
