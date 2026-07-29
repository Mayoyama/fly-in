from models import Zone, HubRole, Drone, ZoneConnection
from pygame_outputs import Visualizer
from parsing import Parser
from pathfinding import Scheduler, PathPlanner
from terminal_outputs import seeded_color_text, rainbow_text
from world_builder import (build_drone, build_zone,
                           build_zone_connection)
from dataclasses import dataclass
from shutil import get_terminal_size
from enum import Enum
import pygame


class EventType(Enum):
    """What a drone does on a single turn of its planned path."""
    NORMAL = "normal"
    RESTRICTED_MID = "restricted mid"
    RESTRICTED_END = "restricted end"


@dataclass
class Move:
    """A single scheduled move: which drone, when, and where — either
    the destination zone (arrived) or the connection when it's currently
    transiting toward a restricted zone.

    Attributes:
        drone_id: Which drone this move belongs to.
        turn_nb: The turn this move takes effect.
        event_type: NORMAL, RESTRICTED_MID, or RESTRICTED_END.
        releases: The zone or connection being vacated.
        occupies: The zone or connection being claimed.
        anim_from: Zone name to animate the drone sliding from.
        anim_to: Zone name to animate the drone sliding to.
        token: The print token for this turn's line.
    """
    drone_id: int
    turn_nb: int
    event_type: EventType
    releases: str | frozenset[str]
    occupies: str | frozenset[str]
    anim_from: str
    anim_to: str
    token: str


def _lin_interpol_point(start: tuple[float, float], end: tuple[float, float],
                        t: float) -> tuple[float, float]:
    """Return the point a fraction `t` of the way from `start` to `end`.

    Args:
        start: Starting (x, y) point.
        end: Ending (x, y) point.
        t: Interpolation fraction, 0 at start, 1 at end.

    Returns:
        The interpolated (x, y) point.
    """
    x1, y1 = start
    x2, y2 = end
    new_x = x1 + (x2 - x1) * t
    new_y = y1 + (y2 - y1) * t
    return new_x, new_y


class Engine:
    def __init__(self, path_to_map_file: str) -> None:
        """Load and parse a map file, then build and plan the full simulation.

        Parses the map file, constructs the Zone/Drone/ZoneConnection objects,
        builds a Scheduler against them, and plans every drone's complete
        timed path via plan_all_paths before any playback begins.

        Args:
            path_to_map_file: Path to the map file to load.
        """
        self.map_path = path_to_map_file
        parser = Parser(self.map_path)
        parser.parse_map_data()
        zone_list = parser.zone_list
        connection_list = parser.connection_list
        drone_count = parser.drone_count
        self.zones: dict[str, Zone] = {}
        for hub_role, zone_info in zone_list:
            if hub_role == HubRole.START:
                self.start_point = zone_info.zone_name
            self.zones[zone_info.zone_name] = build_zone(hub_role, zone_info)
        self.drones: dict[int, Drone] = {}
        for drone in range(1, drone_count + 1):
            self.drones[drone] = build_drone(drone)
        self.connections: dict[frozenset[str], ZoneConnection] = {}
        for connection in connection_list:
            key = frozenset({connection.name1, connection.name2})
            self.connections[key] = build_zone_connection(connection)
        scheduler = Scheduler(self.zones, self.connections)
        path_planner = PathPlanner(scheduler)
        self.paths = path_planner.plan_all_paths(self.drones.keys())

    @staticmethod
    def _drone_path_to_events(path: list[tuple[str, int]],
                              drone_id: int) -> list[tuple[int, Move]]:
        """Convert one drone's finalized (zone, turn) path into an ordered
        list of (turn, Move) events. A same-turn collision (a hop's final
        event and the next hop's first event landing on the same turn)
        resolves by the later hop replacing the earlier entry.

        Args:
            path: The drone's finalized (zone, turn) states.
            drone_id: Id of the drone the events belong to.

        Returns:
            Ordered (turn, Move) pairs. A turn with no entry means the
            drone is waiting.
        """
        events: list[tuple[int, Move]] = []
        for i in range(len(path) - 1):
            zoneA, turnA = path[i]
            zoneB, turnB = path[i + 1]

            if zoneA == zoneB:
                continue
            gap = turnB - turnA
            if gap == 1:
                new_events = [(turnB, Move(drone_id, turnB, EventType.NORMAL,
                                           zoneA, zoneB, zoneA, zoneB, zoneB))]
            else:
                conn_key = frozenset({zoneA, zoneB})
                token = f"{zoneA}-{zoneB}"
                new_events = [
                    (turnA + 1, Move(drone_id, turnA + 1,
                                     EventType.RESTRICTED_MID, zoneA,
                                     conn_key, zoneA, zoneB, token)),
                    (turnB, Move(drone_id, turnB, EventType.RESTRICTED_END,
                                 conn_key, zoneB, zoneA, zoneB, zoneB))
                ]

            for turn, move in new_events:
                if events and events[-1][0] == turn:
                    events[-1] = (turn, move)
                else:
                    events.append((turn, move))
        return events

    def _release_zone(self, move: Move) -> None:
        """Apply one move's release side: free the zone or connection
        it's leaving.

        Args:
            move: The Move whose release this turn applies.
        """
        if move.event_type in (EventType.NORMAL, EventType.RESTRICTED_MID):
            self.zones[str(move.releases)].decrease_drone_count()
        elif move.event_type == EventType.RESTRICTED_END:
            assert isinstance(move.releases, frozenset)
            self.connections[move.releases].decrease_occupancy()

    def _occupy_zone(self, move: Move) -> None:
        """Apply one move's occupy side: claim the zone or connection
        it's entering, and count the move against the drone if it has
        genuinely arrived.

        Args:
            move: The Move whose occupy this turn applies.
        """
        if move.event_type == EventType.NORMAL:
            self.zones[str(move.occupies)].increase_drone_count()
            self.drones[move.drone_id].increase_move_count()
        elif move.event_type == EventType.RESTRICTED_MID:
            assert isinstance(move.occupies, frozenset)
            self.connections[move.occupies].increase_occupancy()
        elif move.event_type == EventType.RESTRICTED_END:
            self.zones[str(move.occupies)].increase_drone_count()
            self.drones[move.drone_id].increase_move_count()

    def run(self) -> None:
        """Play back the already-planned schedule turn by turn.

        Waits for the user to start the simulation, then for each turn
        from 1 to the makespan: releases each move's vacated zone/
        connection, animates every in-transit drone sliding toward its
        destination, occupies each move's claimed zone/connection,
        prints the turn's VII.5-format line, and renders a settled frame
        (including any drone still mid-transit through a RESTRICTED_MID
        hop). After the last turn, prints a summary (map, drone count,
        total turns, average moves per drone) and keeps the window open
        until closed.
        """
        visualizer = Visualizer(self.zones, self.connections)
        terminal_width = get_terminal_size().columns
        rb_str = rainbow_text(' Drone Movements '.center(terminal_width, '='))
        print(rb_str)
        visualizer.wait_to_start()
        if not visualizer.running:
            return

        for _ in range(len(self.drones)):
            self.zones[self.start_point].increase_drone_count()
        total_turns = max(self.paths[drone][-1][1] for drone in self.paths)
        turns: dict[int, list[tuple[int, Move]]] = {}

        for drone_id in self.paths:
            curr_drone_events = self._drone_path_to_events(
                self.paths[drone_id], drone_id)
            for turn, move in curr_drone_events:
                if turn not in turns:
                    turns[turn] = []
                turns[turn].append((drone_id, move))

        timeframe_to_animate = 800
        for turn in range(1, total_turns + 1):
            for drone_id, move in turns.get(turn, []):
                assert drone_id == move.drone_id
                assert turn == move.turn_nb
                self._release_zone(move)

            running_animation_time = 0
            while running_animation_time < timeframe_to_animate:
                running_animation_time += visualizer.clock.tick(60)
                progress = running_animation_time / timeframe_to_animate
                draw_positions: list[tuple[float, float]] = []

                for drone_id, move in turns.get(turn, []):
                    start: tuple[float, float] = \
                        visualizer.positions[move.anim_from]
                    stop: tuple[float, float] = \
                        visualizer.positions[move.anim_to]
                    if move.event_type == EventType.RESTRICTED_MID:
                        stop = _lin_interpol_point(start, stop, 0.5)
                    elif move.event_type == EventType.RESTRICTED_END:
                        start = _lin_interpol_point(start, stop, 0.5)
                    draw_positions.append(_lin_interpol_point(start, stop,
                                                              progress))
                visualizer.render_frame(draw_positions)

            mid_positions: list[tuple[float, float]] = []
            for drone_id, move in turns.get(turn, []):
                if move.event_type == EventType.RESTRICTED_MID:
                    start = visualizer.positions[move.anim_from]
                    stop = visualizer.positions[move.anim_to]
                    mid_positions.append(_lin_interpol_point(start, stop, 0.5))

            for drone_id, move in turns.get(turn, []):
                self._occupy_zone(move)
            tokens = []
            for drone_id, move in turns.get(turn, []):
                drone_label = seeded_color_text('D' + str(drone_id), drone_id)
                tokens.append(f"{drone_label}-{move.token}")
            line = " ".join(tokens)
            print(f"{line}\n")
            if not visualizer.running:
                break
            visualizer.render_frame(mid_positions)
            pygame.time.delay(100)

        total_moves = sum(drone.total_move_count
                          for drone in self.drones.values())
        nb_drones = len(self.drones)
        print()
        print("Summary")
        print(f"Map: {self.map_path}")
        print(f"Number of drones: {nb_drones}")
        print("Drone movement counts: ", end="")
        drone_moves = ", ".join(
            f"{seeded_color_text('D' + str(drone.drone_id), drone.drone_id)}"
            f" -> {drone.total_move_count}"
            for drone in self.drones.values())
        print(drone_moves)
        print(f"Total number of turns to solve: {total_turns}")
        print(f"Average move count per drone: {total_moves / nb_drones:.2f}")

        while visualizer.running:
            visualizer.clock.tick(30)
            visualizer.render_frame()
        pygame.quit()
