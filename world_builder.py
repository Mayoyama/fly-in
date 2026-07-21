from models.connection import ZoneConnection
from models.drone import Drone, DroneStatus
from models.zone import Zone, HubRole
from parser import ZoneInfo, ConnectionInfo


def build_drone(drone_id: int, curr_pos: str, target: str,
                status: DroneStatus = DroneStatus.STATIONARY) -> Drone:
    return Drone(drone_id, status, curr_pos, target)


def build_zone(role: HubRole, zone_info: ZoneInfo) -> Zone:
    return Zone(zone_info.zone_name, zone_info.x_coord, zone_info.y_coord,
                zone_info.zone, zone_info.color,
                zone_info.max_drones, role)


def build_zone_connection(conn_info: ConnectionInfo) -> ZoneConnection:
    return ZoneConnection(conn_info.name1, conn_info.name2,
                          conn_info.max_link_capacity)
