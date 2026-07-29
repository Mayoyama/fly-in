from models import Zone, HubRole, ZoneConnection, Drone
from parsing import ZoneInfo, ConnectionInfo


def build_zone(role: HubRole, zone_info: ZoneInfo) -> Zone:
    """Construct a runtime Zone from parsed ZoneInfo and its hub role.

    Args:
        role: The hub role to assign the zone.
        zone_info: The parsed zone data.

    Returns:
        The constructed Zone.
    """
    return Zone(zone_info.zone_name, zone_info.x_coord, zone_info.y_coord,
                zone_info.zone, zone_info.color, zone_info.max_drones, role)


def build_zone_connection(conn_info: ConnectionInfo) -> ZoneConnection:
    """Construct a runtime ZoneConnection from parsed ConnectionInfo.

    Args:
        conn_info: The parsed connection data.

    Returns:
        The constructed ZoneConnection.
    """
    return ZoneConnection(conn_info.name1, conn_info.name2,
                          conn_info.max_link_capacity)


def build_drone(drone_id: int) -> Drone:
    """Construct a runtime Drone with a unique id.

    Args:
        drone_id: Unique identifier for the drone.

    Returns:
        The constructed Drone.
    """
    return Drone(drone_id)
