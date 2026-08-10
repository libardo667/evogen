from __future__ import annotations

from .models import ContainerSpec, ItemSpec, RoomSpec, ScenarioSpec


def _item(item_id: str, name: str) -> ItemSpec:
    return ItemSpec(item_id=item_id, name=name)


def _room(
    room_id: str,
    name: str,
    neighbors: list[str],
    loose: list[str] | None = None,
) -> RoomSpec:
    return RoomSpec(
        room_id=room_id,
        name=name,
        neighbors=neighbors,
        loose_item_ids=loose or [],
    )


def _container(
    container_id: str,
    name: str,
    room_id: str,
    items: list[str],
) -> ContainerSpec:
    return ContainerSpec(
        container_id=container_id,
        name=name,
        room_id=room_id,
        item_ids=items,
    )


SCENARIOS: dict[str, ScenarioSpec] = {
    "diag-opaque-near": ScenarioSpec(
        scenario_id="diag-opaque-near",
        category="revealing",
        description="The target exists in the only opaque container in the starting room.",
        start_room_id="entry",
        target_item_id="amber-token",
        items=[_item("amber-token", "Amber token")],
        rooms=[_room("entry", "Entry", [])],
        containers=[_container("crate-a", "Sealed crate", "entry", ["amber-token"])],
    ),
    "diag-opaque-after-move": ScenarioSpec(
        scenario_id="diag-opaque-after-move",
        category="variant",
        description="The target is hidden after one valid movement transition.",
        start_room_id="entry",
        target_item_id="cobalt-key",
        items=[_item("cobalt-key", "Cobalt key")],
        rooms=[
            _room("entry", "Entry", ["store"]),
            _room("store", "Store", ["entry"]),
        ],
        containers=[_container("locker-b", "Tall locker", "store", ["cobalt-key"])],
    ),
    "diag-opaque-decoys": ScenarioSpec(
        scenario_id="diag-opaque-decoys",
        category="variant",
        description="One empty container precedes the container that holds the target.",
        start_room_id="workshop",
        target_item_id="green-sigil",
        items=[_item("green-sigil", "Green sigil")],
        rooms=[_room("workshop", "Workshop", [])],
        containers=[
            _container("box-1", "Small box", "workshop", []),
            _container("box-2", "Long box", "workshop", ["green-sigil"]),
        ],
    ),
    "variant-opaque-renamed": ScenarioSpec(
        scenario_id="variant-opaque-renamed",
        category="variant",
        description="Different identifiers and names test against literal specialization.",
        start_room_id="foyer-z",
        target_item_id="violet-wafer",
        items=[
            _item("violet-wafer", "Violet wafer"),
            _item("brass-decoy", "Brass decoy"),
        ],
        rooms=[_room("foyer-z", "Foyer Z", [])],
        containers=[
            _container("urn-zeta", "Ceramic urn", "foyer-z", ["brass-decoy", "violet-wafer"])
        ],
    ),
    "regression-loose-near": ScenarioSpec(
        scenario_id="regression-loose-near",
        category="regression",
        description="A visible loose target must remain directly acquirable.",
        start_room_id="yard",
        target_item_id="silver-chip",
        items=[_item("silver-chip", "Silver chip")],
        rooms=[_room("yard", "Yard", [], ["silver-chip"])],
    ),
    "regression-loose-after-move": ScenarioSpec(
        scenario_id="regression-loose-after-move",
        category="regression",
        description="Movement followed by a visible-item acquisition must not regress.",
        start_room_id="south",
        target_item_id="paper-star",
        items=[_item("paper-star", "Paper star")],
        rooms=[
            _room("south", "South room", ["north"]),
            _room("north", "North room", ["south"], ["paper-star"]),
        ],
    ),
    "long-horizon-container-chain": ScenarioSpec(
        scenario_id="long-horizon-container-chain",
        category="long_horizon",
        description=(
            "Five rooms and multiple opaque decoys require repeated use of the new capability "
            "without target-specific shortcuts."
        ),
        start_room_id="r1",
        target_item_id="final-prism",
        max_steps=30,
        items=[
            _item("scrap-1", "Scrap one"),
            _item("scrap-2", "Scrap two"),
            _item("scrap-3", "Scrap three"),
            _item("final-prism", "Final prism"),
        ],
        rooms=[
            _room("r1", "Room 1", ["r2"]),
            _room("r2", "Room 2", ["r1", "r3"]),
            _room("r3", "Room 3", ["r2", "r4"]),
            _room("r4", "Room 4", ["r3", "r5"]),
            _room("r5", "Room 5", ["r4"]),
        ],
        containers=[
            _container("c1", "Container 1", "r1", []),
            _container("c2", "Container 2", "r2", ["scrap-1"]),
            _container("c3", "Container 3", "r3", ["scrap-2"]),
            _container("c4", "Container 4", "r4", ["scrap-3"]),
            _container("c5", "Container 5", "r5", ["final-prism"]),
        ],
    ),
}

DIAGNOSTIC_SCENARIOS = [
    "diag-opaque-near",
    "diag-opaque-after-move",
    "diag-opaque-decoys",
]

REVEALING_CASES = ["diag-opaque-near"]
STRUCTURAL_VARIANTS = [
    "diag-opaque-after-move",
    "diag-opaque-decoys",
    "variant-opaque-renamed",
]
REGRESSION_SUITES = [
    "regression-loose-near",
    "regression-loose-after-move",
]
LONG_HORIZON_SUITES = ["long-horizon-container-chain"]
EVALUATION_SCENARIOS = [
    *REVEALING_CASES,
    *STRUCTURAL_VARIANTS,
    *REGRESSION_SUITES,
    *LONG_HORIZON_SUITES,
]


def get_scenario(scenario_id: str) -> ScenarioSpec:
    try:
        return SCENARIOS[scenario_id]
    except KeyError as exc:
        raise KeyError(f"Unknown microworld scenario {scenario_id!r}") from exc
