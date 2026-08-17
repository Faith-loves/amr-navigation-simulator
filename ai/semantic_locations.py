from dataclasses import dataclass

from environment.scenario import cell_center


@dataclass(frozen=True)
class SemanticLocation:
    name: str
    cell: tuple[int, int]
    aliases: tuple[str, ...] = ()

    @property
    def position(self) -> tuple[float, float]:
        return cell_center(*self.cell)


def locations_for_scenario(scenario_name: str) -> dict[str, SemanticLocation]:
    key = scenario_name.strip().lower()
    locations = _CUSTOM_SCENARIO_LOCATIONS.get(key) or _SCENARIO_LOCATIONS.get(key, _SCENARIO_LOCATIONS["open space"])
    resolved = {}
    for location in locations:
        resolved[location.name] = location
        for alias in location.aliases:
            resolved[alias] = location
    return resolved


def register_custom_locations(
    scenario_name: str,
    locations: dict[str, tuple[int, int]] | None,
) -> None:
    key = scenario_name.strip().lower()
    if not locations:
        _CUSTOM_SCENARIO_LOCATIONS.pop(key, None)
        return
    _CUSTOM_SCENARIO_LOCATIONS[key] = tuple(
        SemanticLocation(name, cell, ())
        for name, cell in sorted(locations.items())
    )


_CUSTOM_SCENARIO_LOCATIONS: dict[str, tuple[SemanticLocation, ...]] = {}


_SCENARIO_LOCATIONS: dict[str, tuple[SemanticLocation, ...]] = {
    "open space": (
        SemanticLocation("start area", (3, 2), ("start", "entrance")),
        SemanticLocation("charging station", (4, 17), ("charger", "charging dock")),
        SemanticLocation("inspection point", (14, 10), ("middle", "center")),
        SemanticLocation("target", (26, 17), ("goal", "delivery point")),
    ),
    "tight corridor": (
        SemanticLocation("entrance", (3, 2), ("start",)),
        SemanticLocation("corridor bend", (23, 6), ("bend", "turn")),
        SemanticLocation("charging station", (4, 17), ("charger", "charging dock")),
        SemanticLocation("target", (26, 17), ("goal", "exit")),
    ),
    "house layout": (
        SemanticLocation("living room", (3, 3), ("lounge",)),
        SemanticLocation("hallway", (10, 9), ("hall", "corridor")),
        SemanticLocation("kitchen", (4, 14), ("kitchen area",)),
        SemanticLocation("bedroom", (26, 16), ("bed room",)),
        SemanticLocation("entrance", (3, 3), ("front door", "entry")),
        SemanticLocation("charging station", (24, 3), ("charger", "charging dock")),
    ),
    "warehouse": (
        SemanticLocation("loading area", (27, 2), ("loading dock", "dock")),
        SemanticLocation("aisle 1", (9, 6), ("first aisle",)),
        SemanticLocation("aisle 2", (14, 10), ("second aisle",)),
        SemanticLocation("aisle 3", (20, 14), ("third aisle",)),
        SemanticLocation("storage area", (8, 17), ("storage", "store room", "storeroom")),
        SemanticLocation("packing station", (26, 10), ("packing", "pack station")),
        SemanticLocation("charging station", (2, 2), ("charger", "charging dock")),
        SemanticLocation("delivery point", (2, 17), ("delivery", "target")),
    ),
    "office": (
        SemanticLocation("reception", (26, 2), ("front desk", "entrance")),
        SemanticLocation("meeting room", (4, 16), ("conference room",)),
        SemanticLocation("workspace", (15, 8), ("work area", "desks")),
        SemanticLocation("manager office", (3, 17), ("manager", "office")),
        SemanticLocation("hallway", (11, 10), ("hall", "corridor")),
        SemanticLocation("charging station", (25, 7), ("charger", "charging dock")),
    ),
}
