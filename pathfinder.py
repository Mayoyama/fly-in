from collections import deque
from models.connection import ZoneConnection
from models.zone import Zone, HubRole, ZoneType


def find_path(start: str, conn_dict: dict[frozenset[str], ZoneConnection],
              zone_dict: dict[str, Zone]) -> list[str]:
    queue: deque[list[str]] = deque([[start]])
    visited: set[str] = {start}

    while queue:
        path = queue.popleft()
        current = path[-1]
        if zone_dict[current].hub_role == HubRole.END:
            return path

        for k, connection in conn_dict.items():
            if connection.z1_name == current:
                next_zone = connection.z2_name
            elif connection.z2_name == current:
                next_zone = connection.z1_name
            else:
                continue

            if next_zone not in visited:
                visited.add(next_zone)
                queue.append(path + [next_zone])

    return []


class Scheduler:
    def __init__(self, zones: dict[str, Zone],
                 connections: dict[frozenset[str], ZoneConnection]) -> None:
        self.zones = zones
        self.connections = connections
        self.zone_reserves: dict[str, dict[int, int]] = {}
        self.conn_reserves: dict[frozenset[str], dict[int, int]] = {}

    def _check_move(self, origin: str, dest: str, connection: ZoneConnection, depart_turn_nb: int) -> int | None:
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
            if self.conn_reserves.get(frozenset({origin, dest}), {}).get(turn, 0) >= connection.max_link_cap:
                return None

        if self.zone_reserves.get(dest, {}).get(arrival_turn, 0) >= self.zones[dest].get_max_capacity():
            return None
            
        return arrival_turn

    def can_reserve_move(self, origin: str, dest: str, connection: ZoneConnection, depart_turn_nb: int) -> bool:
        return self._check_move(origin, dest, connection, depart_turn_nb) is not None

def try_reserve_move(self, origin: str, dest: str, connection: ZoneConnection, depart_turn_nb: int) -> bool:
    arrival_turn = self._check_move(origin, dest, connection, depart_turn_nb)
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
    
