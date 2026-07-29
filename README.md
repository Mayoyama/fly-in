*This project has been created as part of the 42 curriculum by speterse.*

---

# Fly-in

Fly-in routes a fleet of drones through a network of connected zones, from a shared start hub to a shared end hub, in the fewest possible simulation turns. It parses a plain-text map, plans a complete conflict-free schedule for every drone up front, then plays that schedule back — printing the required turn-by-turn output to the terminal while animating it in a graphical window.

## Table of Contents
- [Description](#description)
- [Instructions](#instructions)
- [Map File Format](#map-file-format)
- [Architecture & Object Model](#architecture--object-model)
- [Pathfinding & Scheduling](#pathfinding--scheduling)
- [Visual Representation](#visual-representation)
- [Performance](#performance)
- [Resources](#resources)

---

## Description

The task is to move every drone from the start zone to the end zone while respecting a set of strict movement and capacity constraints, minimising the total number of simulation turns. The graph is a network of zones connected by bidirectional links; zones carry a type that affects their traversal cost, and both zones and links carry capacity limits that must never be exceeded on any turn.

The following rules govern the simulation:

- Drones may move simultaneously, as long as every capacity constraint is respected on the turn.
- By default a zone holds at most one drone per turn; a `max_drones=N` zone holds up to `N`. The start and end hubs are exempt — all drones may begin at the start, and any number may be delivered to the end.
- A connection carries at most `max_link_capacity` drones traversing it at once (default 1).
- Entering a `restricted` zone costs 2 turns; the drone occupies the connection in transit and **must** arrive on the following turn — it cannot wait mid-link.
- `blocked` zones can never be entered or passed through.
- The simulation ends once every drone has reached the end zone.

The program runs as a single pipeline:

1. A chosen map file is parsed and validated into typed `ZoneInfo` / `ConnectionInfo` objects.
2. Those objects are used to build the runtime `Zone`, `ZoneConnection`, and `Drone` domain objects.
3. A time-expanded search plans a complete, conflict-free `(zone, turn)` path for every drone.
4. The planned schedule is converted into per-turn move events and played back — printed to the terminal in the required format and animated in a `pygame` window.

---

## Instructions

### Requirements

- **Language:** Python 3.10 or higher.
- **Dependencies:** [`pydantic`](https://docs.pydantic.dev/) (map validation) and [`pygame`](https://www.pygame.org/) (graphical display).
- **Dev tools:** `flake8` and `mypy` for style and static type checking.
- **Environment:** managed with [`uv`](https://docs.astral.sh/uv/).

### Available Makefile Rules

| Rule | Description |
|---|---|
| `make install` | Install project dependencies and set up the environment (`uv sync`) |
| `make run` | Launch the simulation (`main.py`) |
| `make debug` | Run the simulation under Python's built-in debugger (`pdb`) |
| `make lint` | Run `flake8` and `mypy` with the required flags |
| `make lint-strict` | Run `flake8` and `mypy --strict` |
| `make clean` | Remove caches (`__pycache__`, `.mypy_cache`, etc.) |
| `make uninstall` | Remove the virtual environment |

### Execution

```bash
make install
make run
```

`make run` lists every map under `maps/` (grouped by difficulty) and prompts for a selection, or accepts a custom map file path. Once a map is chosen a window opens — press **SPACE** to begin playback. The terminal prints one line per turn, followed by a summary once every drone has been delivered.

### Example

```
$> make run
Select your map: 7
[ window opens -> press SPACE ]

D1-gate1 D2-gate2 D3-gate3
D1-waiting_area1 D2-waiting_area2 D3-restricted_tunnel1
...
```

---

## Map File Format

A map is a plain-text file. The first non-comment line sets the drone count; the rest define zones and connections. Lines beginning with `#` and blank lines are ignored.

```
nb_drones: 5

start_hub: start 0 0 [color=green]
end_hub: goal 10 10 [color=yellow]
hub: corridorA 4 3 [zone=priority color=green max_drones=2]
hub: tunnelB 7 4 [zone=restricted color=red]
connection: start-corridorA
connection: corridorA-tunnelB [max_link_capacity=2]
connection: tunnelB-goal
```

- **Zones** are declared with a type prefix — `start_hub:`, `end_hub:`, or `hub:` — followed by `<name> <x> <y>` and optional bracketed metadata. There is exactly one start hub and one end hub. Names may use any characters except dashes and spaces.
- **Metadata** is optional, order-independent, and enclosed in `[...]`: `zone=<type>` (default `normal`), `color=<value>`, and `max_drones=<n>` (default 1). Capacity values must be positive integers; `max_drones` is ignored on the start and end hubs.
- **Connections** declare a bidirectional link with `connection: <name1>-<name2>` and optional `[max_link_capacity=<n>]`. They may only link previously-defined zones, and a link may not be declared twice.

### Zone Types

| Type | Traversal Cost | Behaviour |
|---|---|---|
| `normal` | 1 turn | Standard zone (default) |
| `priority` | 1 turn | Preferred in pathfinding when it costs no extra turns |
| `restricted` | 2 turns | Drone occupies the connection in transit; must arrive next turn |
| `blocked` | — | Impassable; any path using it is invalid |

Any structural or syntactic error (missing hub, duplicate name, invalid type, malformed metadata, unknown zone in a connection, etc.) stops the program with a message identifying the offending line.

---

## Architecture & Object Model

The project is fully object-oriented: simulation state and the behaviour that acts on it live together in classes, and no third-party graph library is used — the graph and its search are built from scratch on the standard library (`heapq`, `collections.deque`). Dependencies flow in one direction: `parsing` produces pure validated data objects, `models` holds runtime state, and `world_builder` sits above both as the single layer that turns parsed data into domain objects.

### Module Overview

| Module / Package | Key Classes | Responsibility |
|---|---|---|
| `main.py` | — | Entry point: renders the map-selection menu, validates input, and launches the `Engine` |
| `simulation.py` | `Engine`, `Move`, `EventType` | Orchestrates parse → build → plan → playback; converts planned paths into per-turn move events and prints the required output |
| `world_builder.py` | *(factory functions)* | Builds runtime `Zone` / `ZoneConnection` / `Drone` objects from parsed data — the one construction layer between parsing and models |
| `models/` | `Zone`, `Drone`, `ZoneConnection`, `ZoneType`, `HubRole` | Core domain objects holding simulation state and capacity logic |
| `parsing/` | `Parser`, `ZoneInfo`, `ConnectionInfo` | Reads and validates the map file into typed, `pydantic`-backed data objects |
| `pathfinding/` | `Scheduler`, `PathPlanner`, `ScheduleError` | Reservation tables plus the time-expanded search that plans every drone's timed path |
| `pygame_outputs/` | `Visualizer`, `Layout`, `Dimensions` | Graphical rendering: window, layout geometry, and per-turn animation |
| `terminal_outputs/` | *(colour helpers)* | ANSI-coloured terminal output (rainbow banners, per-drone colours) |
| `maps/` | — | Test maps grouped by difficulty (easy, medium, hard, challenger, custom) |
| `resources/` | — | Fonts and the terrain background image |

### Design Notes

- **`Layout` isolates coordinate geometry.** All map-to-pixel maths (bounds, scale, centring offsets, zone radius, and both coordinate conversions) live in a single `Layout` object rather than being scattered across the `Visualizer` as loose attributes. `Layout` is `pygame`-free and can be constructed and tested without a window.
- **`world_builder` keeps construction separate from data.** Parsed `ZoneInfo` / `ConnectionInfo` objects are pure validated data; `world_builder` is the only place that maps them onto runtime domain objects. This keeps `parsing` from depending on `models` and gives object construction a single home.
- **Stateless helpers stay as functions on purpose.** Rendering primitives (icon and badge factories, colour resolution, geometry maths) and small utilities are pure functions with no state to encapsulate. Wrapping them in classes would add ceremony without benefit, so they remain module-level functions — object-orientation applied where there is state, not everywhere for its own sake.

---

## Pathfinding & Scheduling

### Time-Expanded Search

Each drone's route is found with Dijkstra's algorithm over a **time-expanded** state space: a state is a `(zone, turn)` pair rather than just a zone, so the search reasons about *when* a drone is somewhere, not only *where*. From any state a drone can move to a connected zone, transit toward a `restricted` zone (a fixed 2-turn commitment, matching the "cannot wait on the connection" rule), or wait one turn in place. A one-off breadth-first reachability check (respecting `blocked` zones) confirms a route can exist before the real search runs.

### Cooperative Reservation Scheduling

The `Scheduler` holds two turn-indexed reservation tables — one for zone occupancy, one for connection occupancy. Every candidate move is probed against these tables (read-only) before the search will consider it, and committed into them once a drone's path is finalised. Drones are then planned one at a time, each against the reservations already committed by every earlier drone (prioritised planning). Congestion is priced implicitly: once a zone or link is full for a given turn, the search is forced to arrive later, which raises that path's cost, so later drones naturally route around busy areas without any separate congestion formula.

### Movement Costs & Priority Handling

Move cost equals the turn cost of the destination: 1 for `normal` and `priority`, 2 for `restricted`, and `blocked` is unreachable. A small fixed discount (`0.01`) biases the search toward `priority` zones, and a matching discount on waiting prevents it from ever preferring a pointless back-and-forth over simply waiting.

Because a `priority` zone costs the same as a `normal` one (1 turn) and the solution is scored purely on total turns, the discount is deliberately smaller than any whole turn — it can never override an integer-turn difference. It therefore acts as a **pure tie-breaker**: drones route through priority zones whenever doing so is free, and skip them only when a strictly shorter path exists or capacity blocks the way. This satisfies both the "prefer priority" guidance and the "fewest turns" scoring rule without letting them conflict.

### Efficiency

Each drone's path is computed once and its reservations committed; nothing is recalculated during playback. The reservation tables are sparse dictionaries keyed by turn, so memory scales with the number of moves actually made rather than with the full turn range.

---

## Visual Representation

Alongside the required terminal output, the simulation opens a `pygame` window that renders the full map and plays back every turn live:

- Zones are drawn as coloured circles, scaled and centred to fit the window from their map coordinates.
- Zone type is shown by outline: red for `blocked`, orange for `restricted`, and an animated rainbow ring for `priority`.
- Drones are drawn as icons on their zone, with a "5+" overflow badge once a zone holds more than four.
- A legend bar documents every icon and outline colour, and hovering a zone shows a popup with its name, role, coordinates, and current/maximum capacity.
- Hovering a connection highlights it as a rainbow line and shows a popup with its two endpoints and traversal capacity; zones take precedence, so the highlight appears only when the cursor is over a link rather than a zone circle.
- Movement is animated as a smooth slide rather than an instant jump — including drones mid-transit through a 2-turn `restricted` move, correctly shown at the halfway point on both of their turns.
- The window stays open once the simulation ends so the final state can still be inspected.

The terminal side complements this with rainbow banners and a deterministic per-drone colour (the same drone id always renders in the same colour), making individual drones easy to follow across turns.

**How this enhances the experience.** Together these features turn an otherwise abstract turn-by-turn log into something that can actually be watched and followed drone by drone. It becomes far easier to spot congestion forming at bottlenecks, to visually confirm that zone and connection capacity limits are respected on every turn, and to understand *why* the scheduler chose a given route. The hover popups and live occupancy counts let a viewer inspect any zone's name, role, and current/maximum capacity — or any connection's endpoints and traversal capacity — at any moment, and animating multi-turn `restricted` transits as a slide — rather than an instant jump — keeps those slower moves legible instead of confusing. In short, the visual layer makes the correctness and the strategy of the schedule directly observable, which is far harder to grasp from the raw output alone.

---

## Performance

The reference targets below come from the subject. Every provided map is solved within its target, and the optional challenger map beats its reference record. Turn counts are the total simulation turns to deliver all drones.

| Map | Drones | Turns | Target |
|---|---|---|---|
| easy / linear path | 2 | 4 | ≤ 6 |
| easy / simple fork | 4 | 4 | ≤ 8 |
| easy / basic capacity | 4 | 4 | ≤ 6 |
| medium / dead end trap | 5 | 8 | ≤ 12 |
| medium / circular loop | 6 | 15 | ≤ 15 |
| medium / priority puzzle | 5 | 7 | ≤ 12 |
| hard / maze nightmare | 8 | 13 | ≤ 30 |
| hard / capacity hell | 12 | 16 | ≤ 35 |
| hard / ultimate challenge | 15 | 26 | ≤ 45 |
| challenger / the impossible dream | 25 | **43** | 45 (record) |

Custom maps (`custom/`) are additional stress tests written on top of the provided set for edge-case and error-handling coverage: shattered route (20 drones, 29 turns), fractured circuit (10, 17), and sealed vault gauntlet (12, 19).

---

## Resources

### Documentation

- Dijkstra, E. W. (1959). *A note on two problems in connexion with graphs.*
- Silver, D. (2005). *Cooperative Pathfinding.* AIIDE — reservation-based, time-expanded multi-agent pathfinding, the same underlying approach used here.
- [Dijkstra's Shortest Path Algorithm — GeeksforGeeks](https://www.geeksforgeeks.org/dsa/dijkstras-shortest-path-algorithm-greedy-algo-7/)
- [Amit Patel — Introduction to A\*](https://theory.stanford.edu/~amitp/GameProgramming/AStarComparison.html)
- [`heapq` — Python documentation](https://docs.python.org/3/library/heapq.html)
- [`pydantic` documentation](https://docs.pydantic.dev/)
- [`pygame` documentation](https://www.pygame.org/docs/)

### AI Usage

Claude was used in this project as a peer-learning aid, consistent with the 42 project guidelines. Specifically:

- **Conceptual explanations** — time-expanded and cooperative (reservation-based) pathfinding, and `pygame` animation techniques (frame-rate-independent timing, linear interpolation, supersampled anti-aliasing).
- **Design review** — discussing OOP coding philosophy/practices and separation of concerns: example - extracting the `Layout` class out of the `Visualizer`, deciding which helpers should stay as standalone functions rather than being forced into classes.
- **Explanations of algebraic formulas** - helped workshop algebraic forumlas for calculating things such as segmenting circle into 60+ segments with sin/cosine. 
- **Debugging assistance** — diagnosing a same-turn zone-vacate/arrive ordering crash, a tie-break issue that let drones oscillate pointlessly, and animation timing artifacts.
- **Verification** — an independent replay validator that re-derives each drone's position turn-by-turn and checks move legality and capacity limits across every map, plus benchmark turn-count and `flake8` / `mypy` audits.
- **Documentation** — structuring this README and normalising docstrings for consistency.

All implementation logic was written and is fully understood by me. Claude's role was to explain concepts, review design decisions, and point out problems for me to resolve independently — not to generate production code — and I am prepared to explain or modify any part of the project during peer review.
