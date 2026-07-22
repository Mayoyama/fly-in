class ZoneConnection:
    def __init__(self, z1_name: str, z2_name: str,
                 max_link_cap: int = 1) -> None:
        """Initialize a link between two zones with a traversal cap.

        Args:
            z1_name: Name of the first connected zone.
            z2_name: Name of the second connected zone.
            max_link_cap: Maximum drones allowed on this link at once.
        """
        self.z1_name = z1_name
        self.z2_name = z2_name
        self.max_link_cap = max_link_cap
        self.curr_occupancy = 0

    def can_traverse(self) -> int:
        """Return how many more drones may currently use this link."""
        if self.curr_occupancy < self.max_link_cap:
            return self.max_link_cap - self.curr_occupancy
        return 0

    def increase_occupancy(self) -> None:
        """Register one more drone using this connection.

        Raises:
            ValueError: If the connection is already at maximum capacity.
        """
        if self.curr_occupancy < self.max_link_cap:
            self.curr_occupancy += 1
        else:
            raise ValueError("Attempt to increase occupancy failed. Already "
                             "at maximum")

    def decrease_occupancy(self) -> None:
        """Register one fewer drone using this connection.

        Raises:
            ValueError: If the connection's occupancy is already 0.
        """
        if self.curr_occupancy > 0:
            self.curr_occupancy -= 1
        else:
            raise ValueError("Attempt to decrease occupancy failed. Already "
                             "at 0")
