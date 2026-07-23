from models.connection import ZoneConnection
from models.zone import Zone, ZoneType


class ScheduleError(Exception):
    def __init__(self, message: str = "ScheduleError") -> None:
        """Raised when a planned or committed schedule turns out invalid."""
        super().__init__(message)


class Scheduler:
    def __init__(self, zones: dict[str, Zone],
                 connections: dict[frozenset[str], ZoneConnection]) -> None:
        """Initialize the scheduler's reservation tables against a map.

        Args:
            zones: Map of zone name to Zone, used for capacity/type lookups.
            connections: Map of zone-name-pair to ZoneConnection, used for
                connection capacity lookups.
        """
        self.zones = zones
        self.connections = connections
        self.zone_reserves: dict[str, dict[int, int]] = {}
        self.conn_reserves: dict[frozenset[str], dict[int, int]] = {}

    def _check_move(self, origin: str, dest: str, connection: ZoneConnection,
                    depart_turn_nb: int) -> int | None:
        """Check whether this move is legal given current reservations.

        Returns the turn the drone would arrive at `dest` if the move is
        feasible, or None if it isn't (connection or destination zone
        lacks capacity at some required turn).
        """
        if self.zones[dest].zone_type == ZoneType.RESTRICTED:
            turns_needed = 2
        else:
            turns_needed = 1

        arrival_turn = depart_turn_nb + turns_needed

        for turn in range(depart_turn_nb, arrival_turn):
            conn_key = frozenset({origin, dest})
            reserved = self.conn_reserves.get(conn_key, {}).get(turn, 0)
            if reserved >= connection.max_link_cap:
                return None

        dest_reserved = self.zone_reserves.get(dest, {}).get(arrival_turn, 0)
        if dest_reserved >= self.zones[dest].get_max_capacity():
            return None

        return arrival_turn

    def can_reserve_move(self, origin: str, dest: str,
                         connection: ZoneConnection,
                         depart_turn_nb: int) -> int | None:
        """Check whether a candidate move is legal, without reserving it.

        Read-only — used by the pathfinder to probe candidate edges while
        still searching. Reserves nothing in either table.

        Returns:
            The turn the drone would arrive at `dest` if the move is
            feasible, or None if it isn't.
        """
        return self._check_move(origin, dest, connection, depart_turn_nb)

    def try_reserve_move(self, origin: str, dest: str,
                         connection: ZoneConnection,
                         depart_turn_nb: int) -> bool:
        """Commit a move into the reservation tables if it's legal.

        Called once a drone's path is finalized, to actually book each hop.

        Returns:
            True if the move was legal and has now been reserved, False if
            it wasn't legal (nothing is reserved in that case).
        """
        arrival_turn = self._check_move(origin, dest, connection,
                                        depart_turn_nb)
        if arrival_turn is None:
            return False
        conn_key = frozenset({origin, dest})
        for turn in range(depart_turn_nb, arrival_turn):
            if conn_key not in self.conn_reserves:
                self.conn_reserves[conn_key] = {}
            current = self.conn_reserves[conn_key].get(turn, 0)
            self.conn_reserves[conn_key][turn] = current + 1
        if dest not in self.zone_reserves:
            self.zone_reserves[dest] = {}
        current = self.zone_reserves[dest].get(arrival_turn, 0)
        self.zone_reserves[dest][arrival_turn] = current + 1

        return True

    def can_reserve_wait(self, dest: str, arrival_turn: int) -> bool:
        """Check whether staying in `dest` one more turn is legal.

        Read-only — used by the pathfinder to probe waiting without
        reserving anything.
        """
        dest_reserved = self.zone_reserves.get(dest, {}).get(arrival_turn, 0)
        if dest_reserved >= self.zones[dest].get_max_capacity():
            return False
        return True

    def try_reserve_wait(self, dest: str, arrival_turn: int) -> bool:
        """Commit a wait into the zone reservation table if it's legal.

        Called once a drone's path is finalized, to book each waited turn.
        """
        if not self.can_reserve_wait(dest, arrival_turn):
            return False
        if dest not in self.zone_reserves:
            self.zone_reserves[dest] = {}
        current = self.zone_reserves[dest].get(arrival_turn, 0)
        self.zone_reserves[dest][arrival_turn] = current + 1

        return True

