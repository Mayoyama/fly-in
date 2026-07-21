from enum import Enum
from sys import maxsize
import logging

logger = logging.getLogger(__name__)


class ZoneType(Enum):
    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


class HubRole(Enum):
    START = "start_hub"
    END = "end_hub"
    REGULAR = "hub"


class Zone:
    def __init__(self, name: str, x_coord: int, y_coord: int,
                 zone_type: ZoneType, color: str | None, max_drones: int,
                 hub_role: HubRole) -> None:
        self.name = name
        self.coords = (x_coord, y_coord)
        self.zone_type = zone_type
        self.hub_role = hub_role
        self.color = color
        self.max_drones = max_drones
        self.curr_drone_count = 0

    def available_capacity(self) -> int:
        if self.zone_type == ZoneType.BLOCKED:
            return 0
        if self.hub_role == HubRole.START or self.hub_role == HubRole.END:
            return maxsize
        elif self.curr_drone_count < self.max_drones:
            return self.max_drones - self.curr_drone_count
        return 0

    def increase_drone_count(self) -> None:
        if self.available_capacity():
            self.curr_drone_count += 1
        else:
            logger.debug("Illegal function call: [increase_drone_count]")
            raise ValueError("Attempt to increase drone count failed. "
                             "Already at maximum")

    def decrease_drone_count(self) -> None:
        if self.curr_drone_count > 0:
            self.curr_drone_count -= 1
        else:
            logger.debug("Illegal function call: [decrease_drone_count]")
            raise ValueError("Attempt to decrease drone count failed. "
                             "Already at 0")
