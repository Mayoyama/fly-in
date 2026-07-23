from models.zone import Zone, HubRole
from models.drone import Drone
from models.connection import ZoneConnection
from visualizer.visualizer import Visualizer
from parser import Parser
from world_builder import build_drone, build_zone, build_zone_connection
from pathfinder import make_single_path, Scheduler
import pygame


class Engine:
    def __init__(self, path_to_map_file: str) -> None:
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

    def run(self) -> None:
        visualizer = Visualizer(self.zones, self.connections)
        visualizer.wait_to_start()
        if not visualizer.running:
            return
        # delivered = 0
        # for drone_id in sorted(self.drones.keys()):
        #     drone = self.drones[drone_id]
        #     path = find_path(self.start_point, self.connections, self.zones)
        #     for next_zone in path[1:]:
        #         drone.curr_pos = next_zone  # NEEDS TO BE CHANGED
        #         drone.target = next_zone
        #         visualizer.clock.tick(3)
        #         visualizer.render_frame()
        #         if not visualizer.running:
        #             break
        #         print(f"D{drone_id}-{next_zone}")
        #     if not visualizer.running:
        #         break
        #     if drone.curr_pos == self.end_point:
        #         delivered += 1
        while visualizer.running:
            visualizer.clock.tick(60)
            visualizer.render_frame()
        pygame.quit()
