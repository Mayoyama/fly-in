from enum import Enum
from sys import maxsize


class ZoneType(Enum):
    """Category of a zone, determining traversal cost and behavior."""
    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


class HubRole(Enum):
    """A zone's role in the delivery network (start, end, or regular)."""
    START = "start_hub"
    END = "end_hub"
    REGULAR = "hub"


class Zone:
    def __init__(self, name: str, x_coord: int, y_coord: int,
                 zone_type: ZoneType, color: str | None, max_drones: int,
                 hub_role: HubRole) -> None:
        """Initialize a zone with its position, type, and capacity.

        Args:
            name: Unique identifier for the zone.
            x_coord: X coordinate on the map grid.
            y_coord: Y coordinate on the map grid.
            zone_type: Category affecting traversal rules.
            color: Display color name, or None for a default.
            max_drones: Maximum drones allowed at once (ignored for hubs).
            hub_role: Whether this zone is a start hub, end hub, or regular.
        """
        self.name = name
        self.coords = (x_coord, y_coord)
        self.zone_type = zone_type
        self.hub_role = hub_role
        self.color = color
        self.max_drones = max_drones
        self.curr_drone_count = 0

    def get_max_capacity(self) -> int:
        """Return max_drones this zone can hold.

        Returns:
            0 if blocked; sys.maxsize for start/end hubs;
            otherwise self.max_drones.
        """
        if self.zone_type == ZoneType.BLOCKED:
            return 0
        if self.hub_role == HubRole.START or self.hub_role == HubRole.END:
            return maxsize
        return self.max_drones

    def available_capacity(self) -> int:
        """Return how many more drones this zone can currently hold.

        Returns:
            0 if blocked or full; sys.maxsize for start/end hubs;
            otherwise the remaining slots before max_drones is reached.
        """
        if self.zone_type == ZoneType.BLOCKED:
            return 0
        if self.hub_role == HubRole.START or self.hub_role == HubRole.END:
            return maxsize
        elif self.curr_drone_count < self.max_drones:
            return self.max_drones - self.curr_drone_count
        return 0

    def increase_drone_count(self) -> None:
        """Register one more drone occupying this zone.

        Raises:
            ValueError: If the zone is already at maximum capacity.
        """
        if self.available_capacity():
            self.curr_drone_count += 1
        else:
            raise ValueError("Attempt to increase drone count failed. "
                             "Already at maximum")

    def decrease_drone_count(self) -> None:
        """Register one fewer drone occupying this zone.

        Raises:
            ValueError: If the zone's drone count is already 0.
        """
        if self.curr_drone_count > 0:
            self.curr_drone_count -= 1
        else:
            raise ValueError("Attempt to decrease drone count failed. "
                             "Already at 0")
