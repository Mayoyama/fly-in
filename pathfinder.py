from collections import deque
from models.connection import ZoneConnection
from models.zone import Zone, HubRole


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
    def __init__(self) -> None:
        pass
