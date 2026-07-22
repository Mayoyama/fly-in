from enum import Enum
from dataclasses import dataclass
from sys import stderr


@dataclass
class Move:
    """A single scheduled move: which drone, when, and where — either
    the destination zone (arrived) or the connection when it's currently
    transiting toward a restricted zone."""
    drone_id: int
    dest: str
    turn_nb: int
    in_transit: bool


class DroneStatus(Enum):
    """Whether a drone is idle (stationary) or mid-transit (restricted)."""
    STATIONARY = "stationary"
    RESTRICTED = "restricted"


class Drone:
    def __init__(self, drone_id: int, status: DroneStatus, curr_pos: str,
                 target: str) -> None:
        """Initialize a drone at a starting position with a target.

        Args:
            drone_id: Unique identifier for this drone.
            status: Initial movement status.
            curr_pos: Name of the zone the drone currently occupies.
            target: Name of the zone the drone is heading toward.
        """
        self.drone_id = drone_id
        self.status = status
        self.curr_pos = curr_pos
        self.target = target
        self.total_move_count = 0
        self.turns_to_restricted = 0

    def increase_move_count(self) -> None:
        """Increment this drone's total completed move count."""
        self.total_move_count += 1

    def set_to_restricted(self) -> None:
        """Begin a 2-turn restricted-zone transit.

        Raises:
            ValueError: If the drone is not currently STATIONARY.
        """
        if self.status == DroneStatus.STATIONARY:
            self.turns_to_restricted = 2
            self.status = DroneStatus.RESTRICTED
        else:
            raise ValueError("Drone not STATIONARY. Cannot assign RESTRICTED "
                             "status")

    def update_status(self) -> None:
        """Advance restricted-transit countdown by one turn.

        Once the countdown reaches 0, the drone becomes STATIONARY
        and arrives at its target zone.
        """
        if self.status == DroneStatus.STATIONARY:
            print(f"Call to [update_status] when drone status is "
                  f"already {self.status}", file=stderr)
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
