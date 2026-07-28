from models.zone import HubRole, ZoneType
from .pathfinder import Scheduler, ScheduleError
from heapq import heappush, heappop
from collections import deque
from typing import Iterable


class PathPlanner:
    def __init__(self, scheduler: Scheduler) -> None:
        """Initialize the planner against a scheduler and its zones/
        connections.

        Args:
            scheduler: The Scheduler whose reservation tables this
                planner searches against and commits into.
        """
        self.scheduler = scheduler
        self.zones = scheduler.zones
        self.connections = scheduler.connections

    def _is_reachable(self, start: str, end: str) -> bool:
        """Check whether end is reachable from start in the raw zone graph.

        Ignores turns/congestion (a topological-only check), but does
        respect BLOCKED zones, since those can never be entered at any
        turn regardless of congestion. Used once per map to confirm a
        timed path could ever exist before running the real search.

        Returns:
            True if end is reachable from start, False otherwise.
        """
        visited = {start}
        queue = deque([start])

        while queue:
            current = queue.popleft()
            if current == end:
                return True
            for zone_info in self.connections.values():
                neighbor = None
                if current == zone_info.z1_name:
                    neighbor = zone_info.z2_name
                elif current == zone_info.z2_name:
                    neighbor = zone_info.z1_name
                if (
                  neighbor is not None and neighbor not in visited
                  and self.zones[neighbor].zone_type != ZoneType.BLOCKED
                  ):
                    visited.add(neighbor)
                    queue.append(neighbor)

        return False

    def _make_single_path(self, start: str) -> list[tuple[str, int]]:
        """Find the cheapest timed path from start to the goal zone,
        respecting scheduler's existing reservations.

        Returns:
            Ordered (zone, turn) states from start to goal, or an empty
            list if no valid path exists.
        """
        count = 0
        pathed_dict: dict[tuple[str, int], tuple[str, int]] = {}
        state_heap: list[tuple[float, int, tuple[str, int],
                         tuple[str, int] | None]] = [(0, count,
                                                      (start, 0), None)]
        final_path: list[tuple[str, int]] = []

        while state_heap:
            cost, _, state, predecessor = heappop(state_heap)
            if state in pathed_dict:
                continue
            if predecessor is not None:
                pathed_dict[state] = predecessor
            if self.zones[state[0]].hub_role == HubRole.END:
                break
            for k, zone_info in self.connections.items():
                if state[0] == zone_info.z1_name:
                    z1z2 = self.scheduler.can_reserve_move(
                        state[0], zone_info.z2_name, zone_info, state[1])
                    if z1z2 is not None:
                        move_cost: float = z1z2 - state[1]
                        if (
                          self.zones[zone_info.z2_name].zone_type
                          == ZoneType.PRIORITY):
                            move_cost -= 0.01
                        heappush(state_heap, (cost + move_cost, count,
                                 (zone_info.z2_name, z1z2), state))
                        count += 1
                elif state[0] == zone_info.z2_name:
                    z2z1 = self.scheduler.can_reserve_move(
                        state[0], zone_info.z1_name, zone_info, state[1])
                    if z2z1 is not None:
                        move_cost = z2z1 - state[1]
                        if (
                          self.zones[zone_info.z1_name].zone_type
                          == ZoneType.PRIORITY):
                            move_cost -= 0.01
                        heappush(state_heap, (cost + move_cost, count,
                                 (zone_info.z1_name, z2z1), state))
                        count += 1
            wait_discount = 0.01
            if self.scheduler.can_reserve_wait(state[0], state[1] + 1):
                heappush(state_heap,
                         (cost + 1 - wait_discount, count,
                          (state[0], state[1] + 1), state))
                count += 1

        if self.zones[state[0]].hub_role != HubRole.END:
            return []
        else:
            final_path.append(state)
        while state in pathed_dict:
            final_path.append(pathed_dict[state])
            state = pathed_dict[state]
        final_path.reverse()

        return final_path

    def plan_all_paths(
      self, drone_ids: Iterable[int]) -> dict[int, list[tuple[str, int]]]:
        """Plan and commit a timed path for every drone, one at a time.

        For each drone (in dict order for now), find its cheapest path via
        make_single_path against the scheduler's current reservations, then
        commit every hop/wait in that path so later drones plan around it.

        Returns:
            Map of drone id to its final (zone, turn) path.

        Raises:
            ScheduleError: If a drone has no valid path, its path doesn't
                end at the end zone, or committing one of its reserved
                hops/waits fails.
        """
        all_paths: dict[int, list[tuple[str, int]]] = {}
        start = next(name for name, zone_info in self.zones.items()
                     if zone_info.hub_role == HubRole.START)
        end = next(name for name, zone_info in self.zones.items()
                   if zone_info.hub_role == HubRole.END)
        if not self._is_reachable(start, end):
            raise ScheduleError("No possible route exists from start to end")
        for drone_id in drone_ids:
            drone_path = self._make_single_path(start)
            if not drone_path:
                raise ScheduleError(f"Empty schedule path for "
                                    f"drone {drone_id}")
            if drone_path[-1][0] != end:
                raise ScheduleError(f"END not found on schedule path for "
                                    f"drone {drone_id}")
            for i, hub in enumerate(drone_path):
                if hub[0] != end:
                    if hub[0] != drone_path[i + 1][0]:
                        connection = self.connections[frozenset(
                            {hub[0], drone_path[i + 1][0]})]
                        if not self.scheduler.try_reserve_move(
                          hub[0], drone_path[i + 1][0], connection, hub[1]):
                            raise ScheduleError("Invalid request to "
                                                "move zones")
                    else:
                        if not self.scheduler.try_reserve_wait(hub[0],
                                                               hub[1] + 1):
                            raise ScheduleError("Invalid request to wait "
                                                "in zone")
                else:
                    break
            all_paths[drone_id] = drone_path
        return all_paths
