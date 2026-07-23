from models.zone import Zone, HubRole
from models.drone import Drone
from models.connection import ZoneConnection
from visualizer.visualizer import Visualizer
from parser import Parser
from world_builder import build_drone, build_zone, build_zone_connection
from pathfinding.pathfinder import Scheduler
from pathfinding.path_planner import plan_all_paths
from enum import Enum
from typing import Any
import pygame


class EventType(Enum):
    """What a drone does on a single turn of its planned path."""
    NORMAL = "normal"
    RESTRICTED_START = "restricted start"
    RESTRICTED_MID = "restricted mid"
    RESTRICTED_END = "restricted end"

def _drone_path_to_events(drone_id: int, path: list[tuple[str, int]], 
                          zones: dict[str, Zone], 
                          conn_dict: dict[frozenset[str], ZoneConnection]
                          ) -> dict[int, tuple[EventType, Any, Any, str]]:
    """Convert one drone's finalized (zone, turn) path into per-turn events.

    A same-zone pair is a wait (no event — VII.5 omits stationary drones).
    A 1-turn gap is a normal/priority move (one event, at arrival). A
    2-turn gap is a restricted move, split into three events: entering the
    connection, one turn still in transit, and arriving at the destination.

    Returns:
        Map of turn number to a (EventType, leaves, occupies, token)
        tuple. A turn with no entry means the drone is waiting.
    """
    events: dict[int, tuple[EventType, Any, Any, str]]= {}
    for i in range(len(path) - 1):
        zoneA, turnA = path[i]
        zoneB, turnB = path[i + 1]

        if zoneA == zoneB:
            continue
        gap = turnB - turnA
        if gap == 1:
            events[turnB] = (EventType.NORMAL, zoneA, zoneB, zoneB)
        else:
            conn_key = frozenset({zoneA, zoneB})
            token = ""  # NEED TO UPDATE WITH DIRECTION STRING
            events[turnA] = (EventType.RESTRICTED_START, zoneA, conn_key, token)
            events[turnA + 1] = (EventType.RESTRICTED_MID, None, conn_key, token)
            events[turnB] = (EventType.RESTRICTED_END, conn_key, zoneB, zoneB)

    return events


class Engine:
    def __init__(self, path_to_map_file: str) -> None:
        """Load and parse a map file, then build and plan the full simulation.

        Parses the map file, constructs the Zone/Drone/ZoneConnection objects,
        builds a Scheduler against them, and plans every drone's complete
        timed path via plan_all_paths before any playback begins.

        Args:
            path_to_map_file: Path to the map file to load.
        """
        parser = Parser(path_to_map_file)
        parser.parse_map_data()
        zone_list = parser.zone_list
        connection_list = parser.connection_list
        drone_count = parser.drone_count
        self.zones: dict[str, Zone] = {}
        for hub_role, zone_info in zone_list:
            if hub_role == HubRole.START:
                self.start_point = zone_info.zone_name
            if hub_role == HubRole.END:
                self.end_point = zone_info.zone_name
            self.zones[zone_info.zone_name] = build_zone(hub_role, zone_info)
        self.drones: dict[int, Drone] = {}
        for drone in range(drone_count):
            self.drones[drone] = build_drone(drone, self.start_point,
                                             self.start_point)
        self.connections: dict[frozenset[str], ZoneConnection] = {}
        for connection in connection_list:
            key = frozenset({connection.name1, connection.name2})
            self.connections[key] = build_zone_connection(connection)
        self.scheduler = Scheduler(self.zones, self.connections)
        self.paths = plan_all_paths(self.drones, self.scheduler, 
                                    self.connections, self.zones)
        
    def run(self) -> None:
        """Play back the already-planned schedule turn by turn.

        Waits for the user to start the simulation, then steps through every
        turn from 1 to the makespan: applies each drone's real state changes
        for that turn (zone/connection occupancy, restricted-transit status),
        prints the turn's VII.5-format line, and renders the frame. A drone
        with nothing scheduled for a given turn is waiting and contributes
        nothing to that turn's output.
        """
        visualizer = Visualizer(self.zones, self.connections)
        visualizer.wait_to_start()
        if not visualizer.running:
            return


        total_turns = max(self.paths[drone][-1][1] for drone in self.paths)
        turns: dict[int, list[tuple[int, tuple[EventType, Any,
                                               Any, str]]]] = {}

        for drone_id  in self.paths:
            curr_drone_events = _drone_path_to_events(
                drone_id, self.paths[drone_id], self.zones, self.connections)
            for turn, event in curr_drone_events:
                if turn not in turns:
                    turns[turn] = []
                    turns[turn].append((drone_id, event))

        while visualizer.running:
            visualizer.clock.tick(60)
            visualizer.render_frame()
        pygame.quit()
