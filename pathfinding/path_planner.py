from models.connection import ZoneConnection
from models.zone import Zone, HubRole, ZoneType
from models.drone import Drone
from .pathfinder import Scheduler, ScheduleError
from heapq import heappush, heappop
from collections import deque


def _is_reachable(start: str, end: str,
                 conn_dict: dict[frozenset[str], ZoneConnection],
                 zone_dict: dict[str, Zone]) -> bool:
    """Check whether end is reachable from start in the raw zone graph.

    Ignores turns/congestion (a topological-only check), but does
    respect BLOCKED zones, since those can never be entered at any
    turn regardless of congestion. Used once per map to confirm a
    timed path could ever exist before running the real search.
    """
    visited = {start}
    queue = deque([start])

    while queue:
        current = queue.popleft()
        if current == end:
            return True
        for zone_info in conn_dict.values():
            neighbor = None
            if current == zone_info.z1_name:
                neighbor = zone_info.z2_name
            elif current == zone_info.z2_name:
                neighbor = zone_info.z1_name
            if (neighbor is not None and neighbor not in visited
                    and zone_dict[neighbor].zone_type != ZoneType.BLOCKED):
                visited.add(neighbor)
                queue.append(neighbor)

    return False


def _make_single_path(start: str, scheduler: Scheduler,
                     conn_dict: dict[frozenset[str], ZoneConnection],
                     zone_dict: dict[str, Zone]) -> list[tuple[str, int]]:
    """Find the cheapest timed path from start to the goal zone,
    respecting scheduler's existing reservations.

    Returns:
        Ordered (zone, turn) states from start to goal, or an empty
        list if no valid path exists.
    """
    count = 0
    pathed_dict: dict[tuple[str, int], tuple[str, int]] = {}
    state_heap: list[tuple[int, int, tuple[str, int],
                     tuple[str, int] | None]] = [(0, count, (start, 0), None)]
    final_path: list[tuple[str, int]] = []

    while state_heap:
        cost, _, state, predecessor = heappop(state_heap)
        if state in pathed_dict:
            continue
        if predecessor is not None:
            pathed_dict[state] = predecessor
        if zone_dict[state[0]].hub_role == HubRole.END:
            break
        for k, zone_info in conn_dict.items():
            if state[0] == zone_info.z1_name:
                z1z2 = scheduler.can_reserve_move(state[0], zone_info.z2_name,
                                                  zone_info, state[1])
                if z1z2 is not None:
                    heappush(state_heap, (cost + (z1z2 - state[1]), count,
                             (zone_info.z2_name, z1z2), state))
                    count += 1
            elif state[0] == zone_info.z2_name:
                z2z1 = scheduler.can_reserve_move(state[0], zone_info.z1_name,
                                                  zone_info, state[1])
                if z2z1 is not None:
                    heappush(state_heap, (cost + (z2z1 - state[1]), count,
                             (zone_info.z1_name, z2z1), state))
                    count += 1
        if scheduler.can_reserve_wait(state[0], state[1] + 1):
            heappush(state_heap,
                     (cost + 1, count, (state[0], state[1] + 1), state))
            count += 1

    if zone_dict[state[0]].hub_role != HubRole.END:
        return []
    else:
        final_path.append(state)
    while state in pathed_dict:
        final_path.append(pathed_dict[state])
        state = pathed_dict[state]
    final_path.reverse()

    return final_path


def plan_all_paths(drones: dict[int, Drone], scheduler: Scheduler,
                   conn_dict: dict[frozenset[str], ZoneConnection],
                   zone_dict: dict[str,
                                   Zone]) -> dict[int, list[tuple[str, int]]]:
    """Plan and commit a timed path for every drone, one at a time.

    For each drone (in dict order for now), find its cheapest path via
    make_single_path against the scheduler's current reservations, then
    commit every hop/wait in that path so later drones plan around it.

    Returns:
        Map of drone id/name to its final (zone, turn) path. Drones with
        no valid path map to an empty list.
    """
    all_paths: dict[int, list[tuple[str, int]]] = {}
    start = next(name for name, zone_info in zone_dict.items()
                 if zone_info.hub_role == HubRole.START)
    end = next(name for name, zone_info in zone_dict.items()
               if zone_info.hub_role == HubRole.END)
    if not _is_reachable(start, end, conn_dict, zone_dict):
        raise ScheduleError("No possible route exists from start to end")
    for drone_id in drones:
        drone_path = _make_single_path(start, scheduler, conn_dict, zone_dict)
        if not drone_path:
            raise ScheduleError(f"Empty schedule path for drone {drone_id}")
        if drone_path[-1][0] != end:
            raise ScheduleError(f"END not found on schedule path for "
                                f"drone {drone_id}")
        for i, hub in enumerate(drone_path):
            if hub[0] != end:
                if hub[0] != drone_path[i + 1][0]:
                    connection = conn_dict[frozenset({hub[0],
                                                     drone_path[i + 1][0]})]
                    if not scheduler.try_reserve_move(hub[0],
                                                      drone_path[i + 1][0],
                                                      connection, hub[1]):
                        raise ScheduleError("Invalid request to move zones")
                else:
                    if not scheduler.try_reserve_wait(hub[0], hub[1] + 1):
                        raise ScheduleError("Invalid request to wait in zone")
            else:
                break
        all_paths[drone_id] = drone_path
    return all_paths

