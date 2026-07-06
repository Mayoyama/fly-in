import logging


logger = logging.getLogger(__name__)


class ZoneConnection:
    def __init__(self, z1_name: str, z2_name: str,
                 max_link_cap: int = 1) -> None:
        self.z1_name = z1_name
        self.z2_name = z2_name
        self.max_link_cap = max_link_cap
        self.curr_occupancy = 0

    def can_traverse(self) -> int:
        if self.curr_occupancy < self.max_link_cap:
            return self.max_link_cap - self.curr_occupancy
        return 0

    def increase_occupancy(self) -> None:
        if self.curr_occupancy < self.max_link_cap:
            self.curr_occupancy += 1
        else:
            logger.debug("Illegal function call: [increase_occupancy]")
            raise ValueError("Attempt to increase occupancy failed. Already "
                             "at maximum")

    def decrease_occupancy(self) -> None:
        if self.curr_occupancy > 0:
            self.curr_occupancy -= 1
        else:
            logger.debug("Illegal function call: [decrease_occupancy]")
            raise ValueError("Attempt to decrease occupancy failed. Already "
                             "at 0")
