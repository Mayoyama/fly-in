from enum import Enum
from dataclasses import dataclass
import logging


@dataclass
class Move:
    """Dataclass to hold move data for Scheduler"""
    drone_id: int
    dest: str


logger = logging.getLogger(__name__)


class DroneStatus(Enum):
    STATIONARY = "stationary"
    RESTRICTED = "restricted"


class Drone:
    def __init__(self, drone_id: int, status: DroneStatus, curr_pos: str,
                 target: str) -> None:
        self.drone_id = drone_id
        self.status = status
        self.curr_pos = curr_pos
        self.target = target
        self.total_move_count = 0
        self.turns_to_restricted = 0

    def increase_move_count(self) -> None:
        self.total_move_count += 1

    def set_to_restricted(self) -> None:
        if self.status == DroneStatus.STATIONARY:
            self.turns_to_restricted = 2
            self.status = DroneStatus.RESTRICTED
        else:
            logger.debug("Illegal function call: [set_to_restricted]")
            raise ValueError("Drone not STATIONARY. Cannot assign RESTRICTED "
                             "status")

    def update_status(self) -> None:
        if self.status == DroneStatus.STATIONARY:
            logger.debug(f"Call to [update_status] when drone status is "
                         f"already {self.status}")
        if (
          self.status == DroneStatus.RESTRICTED
          and self.turns_to_restricted >= 1
          ):
            self.turns_to_restricted -= 1
        if (
          self.status == DroneStatus.RESTRICTED
          and self.turns_to_restricted == 0
          ):
            self.status = DroneStatus.STATIONARY
            self.curr_pos = self.target
