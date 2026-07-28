class Drone:
    def __init__(self, drone_id: int) -> None:
        """Initialize a drone at a starting position with a target.

        Args:
            drone_id: Unique identifier for this drone.
        """
        self.drone_id = drone_id
        self.total_move_count = 0

    def increase_move_count(self) -> None:
        """Increment this drone's total completed move count."""
        self.total_move_count += 1

    @classmethod
    def build_drone(cls, drone_id: int) -> "Drone":
        """Construct a Drone with a unique drone ID number."""
        return Drone(drone_id)
