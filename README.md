*This project has been created as part of the 42 curriculum by <speterse>.*

# Fly-in

Design an efficient drone routing system that navigates multiple drones through connected zones while minimizing simulation turns and handling movement constraints.

## Table of Contents

- [Description](#description)
- [Instructions](#instructions)
- [Algorithm & Implementation Strategy](#algorithm--implementation-strategy)
- [Visual Representation](#visual-representation)
- [Resources](#resources)

## Description

Fly-in simulates a fleet of drones traveling through a network of connected zones from a shared start zone to a shared end zone, in the fewest possible simulation turns.

The map is defined in a plain-text file: zones (start, end, and regular hubs) with a type (`normal`, `restricted`, `priority`, `blocked`), an optional occupancy limit, and connections between them with an optional traversal capacity. Each zone type carries its own movement cost — normal and priority zones cost 1 turn to enter, restricted zones cost 2, blocked zones can never be entered — and every zone/connection has a capacity limit that must never be exceeded on any given turn.

The program parses a chosen map, plans a complete, conflict-free, turn-by-turn schedule for every drone up front, then plays that schedule back turn by turn — printing the required output format to the terminal and animating it in a graphical window.

[Back to top](#table-of-contents)

## Instructions

**Requirements:** Python 3.10+, [`pydantic`](https://docs.pydantic.dev/), [`pygame`](https://www.pygame.org/). Dev tools: `flake8` and `mypy`. Managed via [`uv`](https://docs.astral.sh/uv/).

**Makefile targets:**

| Command | Effect |
|---|---|
| `make install` | Install project dependencies |
| `make run` | Run the simulation |
| `make debug` | Run the simulation under `pdb` |
| `make lint` | `flake8` + `mypy` (standard flags) |
| `make lint-strict` | `flake8` + `mypy --strict` |
| `make clean` | Remove caches (`__pycache__`, `.mypy_cache`, etc.) |

**Running it:** `make run` launches `main.py`, which lists every map under `maps/` (grouped by difficulty: easy, medium, hard, challenger, custom) and prompts for a selection, or accepts a custom map file path. Once a map is chosen, the simulation is planned and a window opens — press **SPACE** to start playback. The terminal prints one line per turn in the required `D<id>-<zone/connection>` format, followed by a summary (map, drone count, total turns, average moves per drone) once every drone has reached the end zone.

[Back to top](#table-of-contents)

## Algorithm & Implementation Strategy

**Pathfinding.** Each drone's route is found with Dijkstra's algorithm over a *time-expanded* state space: a state is a `(zone, turn)` pair rather than just a zone, so the search reasons about *when* a drone is somewhere, not only *where*. From any state a drone can move to a connected zone, transit toward a restricted zone (a fixed 2-turn commitment, matching the spec's "cannot wait on the connection" rule), or wait one turn in place. Every candidate move is checked against a `Scheduler` holding turn-indexed reservation tables for zone and connection occupancy before it's added to the search.

**Cooperative scheduling.** Drones are planned one at a time, in order, against the reservations already committed by every earlier drone (prioritized planning). Congestion is priced implicitly: once a zone or connection is full for a given turn, the search is forced to arrive later, which raises that path's cost, so later drones naturally route around busy areas without any separate congestion-cost formula. A small fixed discount biases route selection toward `priority` zones when two routes are otherwise equally short, and a matching discount on waiting prevents the search from ever preferring a pointless back-and-forth move over simply waiting when both are otherwise equal in cost.

**Object model.** The project is fully object-oriented: `Zone`, `Drone`, and `ZoneConnection` hold simulation state; `Parser`, `ZoneInfo`, and `ConnectionInfo` (backed by `pydantic`) validate and parse the map file, with each parsed-info object responsible for building its own runtime object; `Scheduler` owns reservation bookkeeping; `PathPlanner` owns the search; `Engine` orchestrates parsing, planning, and turn-by-turn playback; `Visualizer` owns all rendering. No third-party graph library is used anywhere — the graph and search are implemented from scratch with the standard library (`heapq`, `collections.deque`).

[Back to top](#table-of-contents)

## Visual Representation

Alongside the required terminal output, the simulation opens a `pygame` window that renders the full map and plays back every turn live:

- Zones are drawn as colored circles, laid out and scaled to fit the window from their map coordinates.
- Zone type is shown via outline: red for `blocked`, orange for `restricted`, and an animated rainbow ring for `priority`.
- Occupying drones are drawn as icons on their zone, with a "+5" overflow badge once a zone holds more than four.
- A legend bar documents what every icon and outline color means, and hovering a zone shows a popup with its name, role, coordinates, and current/maximum capacity.
- Movement between zones is animated as a smooth slide rather than an instant jump — including drones mid-transit through a 2-turn restricted move, correctly shown at the halfway point between zones on both of their turns.
- The window remains open once the simulation ends so the final state can still be inspected.

This turns an otherwise abstract turn-by-turn log into something that's actually possible to watch and follow drone-by-drone, which makes it far easier to spot congestion, verify capacity rules are being respected, and understand *why* the scheduler made the choices it did.

[Back to top](#table-of-contents)

## Resources

**References:**

- Dijkstra, E. W. (1959). *A note on two problems in connexion with graphs.*
- Silver, D. (2005). *Cooperative Pathfinding.* AIIDE — reservation-based, time-expanded multi-agent pathfinding, the same underlying approach used here (included in `resources/`).
- [GeeksforGeeks — Dijkstra's Shortest Path Algorithm](https://www.geeksforgeeks.org/dsa/dijkstras-shortest-path-algorithm-greedy-algo-7/)
- [Amit Patel — Introduction to A\*](https://theory.stanford.edu/~amitp/GameProgramming/AStarComparison.html)
- [Dijkstra's Algorithm — video walkthrough](https://www.youtube.com/watch?v=BwWHXN2rZHQ)
- [pydantic documentation](https://docs.pydantic.dev/)
- [pygame documentation](https://www.pygame.org/docs/)

**AI usage:** AI (Claude) was used throughout as a review and debugging partner, not as a code generator — all implementation was written personally. Specific uses: verifying the scheduling/reservation model and print-format logic line-by-line against the project PDF; diagnosing bugs found during manual testing (a same-turn zone-vacate/arrive ordering crash, a tie-break issue that let drones oscillate pointlessly, priority-zone cost farming, animation timing/rendering artifacts); explaining `pygame` animation techniques (frame-rate-independent timing, linear interpolation, supersampling for anti-aliasing) from scratch; and auditing the finished code for consistency — docstring coverage and accuracy, `flake8`/`mypy --strict` compliance, and a full re-check against the literal PDF requirements before submission.

[Back to top](#table-of-contents)
