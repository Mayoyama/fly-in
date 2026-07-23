# Fly-in — Engine.run() Wiring Session (2026-07-23, web/chat session)

Read alongside `FLYIN_COLLAB_RULES.md`, `FLYIN_ALGO_SESSION_2026-07-22.md`, and
`FLYIN_SCHEDULING_ANALYSIS_2026-07-23.md`. Those cover the algorithm design and
the Cowork session's benchmark analysis from earlier today; this file picks up
from there.

This session has no live/persistent access to the repo (unlike the desktop
Claude Code session) — everything below reflects only what was explicitly
typed or pasted into this chat.

## 1. Independent verification of the Scheduling Analysis claims

Rebuilt a minimal sandbox (parser.py + world_builder.py + models/* + the
current pathfinder.py, pydantic installed via `pip install pydantic
--break-system-packages`) and wrote a from-scratch validator — not reusing
the Cowork session's described logic — checking zone capacity per turn,
connection capacity per turn, restricted-move durations, blocked-zone
avoidance, and path contiguity.

First pass found violations on 3 maps the other session called clean. Traced
it to a double-count bug in the validator itself (a wait-hop was re-counting
a turn its preceding move-hop had already counted). Fixed, reran — all 10
maps available in this session (the 3 "easy" maps were never uploaded here)
came back clean, exactly matching the Cowork session's reported makespans:

| map | drones | makespan | result |
|---|---|---|---|
| 01_the_impossible_dream (challenger) | 25 | 43 | beats 45-turn record, clean |
| custom/01_shattered_route | 20 | 29 | clean |
| custom/02_fractured_circuit | 10 | 29 | clean |
| custom/03_sealed_vault_gauntlet | 12 | 19 | clean |
| 01_maze_nightmare (hard) | 8 | 13 | clean |
| 02_capacity_hell (hard) | 12 | 16 | clean |
| 03_ultimate_challenge (hard) | 15 | 26 | clean |
| 01_dead_end_trap (medium) | 5 | 8 | clean |
| 02_circular_loop (medium) | 6 | 15 | clean (exactly at the ≤15 target) |
| 03_priority_puzzle (medium) | 5 | 7 | clean |

The headline claim (43 beats the 45-turn challenger record) and both custom
29-turn optimality claims hold up under independent re-checking.

## 2. Real bugs found and fixed in `plan_all_paths` this session

- `drones: dict[str, Drone]` parameter and `-> dict[str, ...]` return type
  both corrected to `int` keys, matching `Engine.drones`'s actual type
  (`dict[int, Drone]`). Both the signature and the `all_paths: dict[...]`
  variable declaration were fixed.
- Bare `assert move, "..."` / `assert wait, "..."` replaced with
  `if not scheduler.try_reserve_move(...): raise ScheduleError(...)` (and
  the equivalent for `try_reserve_wait`), then inlined further to drop the
  intermediate variable. Reasoning: asserts vanish under `python -O`, and
  `ScheduleError` already exists and is already caught by name in
  `main.py` — routing through it keeps every failure mode consistent
  instead of mixing exception types.
- A misplaced `break` — originally written inside the wait-succeeded
  branch instead of guarding `hub[0] == end` — was corrected back to where
  it belongs (stopping reservation once a drone's path reaches the goal).
  This was a real correctness bug: as briefly written, it would have
  silently stopped committing reservations for any drone whose path
  included even one wait step.

## 3. `pathfinder.py` split into a `pathfinding/` package

Reasoning: a single file holding reservation state, a search algorithm, and
multi-drone orchestration bundled three genuinely separate concerns — the
project's own OOP/separation-of-concerns grading was the deciding factor.

Final structure:
```
pathfinding/
    __init__.py       — exposes Scheduler, ScheduleError, plan_all_paths
    pathfinder.py      — ScheduleError, Scheduler (reservation tables +
                         _check_move/can_reserve_move/try_reserve_move/
                         can_reserve_wait/try_reserve_wait — unchanged
                         from the 07-22/07-23 design)
    path_planner.py    — _is_reachable, _make_single_path (both now
                         private, leading underscore — neither has any
                         legitimate caller outside plan_all_paths), and
                         plan_all_paths (the only public thing here)
```

The old flat root-level `pathfinder.py` is deleted (confirmed, not just
superseded). `simulation.py`'s import was auto-updated by the editor to
`from pathfinding.pathfinder import Scheduler` /
`from pathfinding.path_planner import plan_all_paths` — confirmed no
leftover reference to the old `pathfinder.make_single_path` import.

## 4. `Engine.__init__` — confirmed wired correctly

```python
self.scheduler = Scheduler(self.zones, self.connections)
self.paths = plan_all_paths(self.drones, self.scheduler,
                            self.connections, self.zones)
```
Parameter order matches both signatures exactly. Planning now happens once,
eagerly, before `run()` ever touches the visualizer. A `ScheduleError`
raised here propagates up through `main()`'s existing except chain
unchanged.

## 5. `Engine.run()` — in progress, not finished

### Decided: `Move` (from 07-22) is not being used for this

07-22 designed `Move` for printing only (drone_id, dest, turn_nb,
in_transit). Once playback needed to know not just *what to print* but
*what to mutate* (which zone loses a drone, which connection gains
occupancy, etc.), `Move`'s fields turned out insufficient — flagged
mid-session (Move has no `origin` field, and `in_transit` alone can't
distinguish a restricted move's first transit turn from its second, which
need different mutations).

**What actually got built instead**, in `simulation.py`, is a new
`EventType` enum + tuple structure, not an expanded `Move`:

```python
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
    events: dict[int, tuple[EventType, Any, Any, str]] = {}
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
            token = ""  # NEEDS the real direction-of-travel string — see §6
            events[turnA] = (EventType.RESTRICTED_START, zoneA, conn_key, token)
            events[turnA + 1] = (EventType.RESTRICTED_MID, None, conn_key, token)
            events[turnB] = (EventType.RESTRICTED_END, conn_key, zoneB, zoneB)

    return events
```

**Open item worth a deliberate decision, not urgent**: `Move` now sits
unused in `models/drone.py`. Either retire it as vestigial, or fold this
event structure into it (e.g. rename/extend `Move` to carry origin +
distinguish restricted-start/mid/end) so there's one structure instead of
two doing adjacent jobs. Not resolved this session.

**Unused parameters**: `drone_id` and `zones` are both currently dead
weight inside `_drone_path_to_events` — the restricted/normal split is
inferred purely from the turn gap (`gap == 1` vs not), never by checking
`zones[zoneB].zone_type` directly. `drone_id` is the caller's concern
(attached when merging into the combined per-turn structure), not this
function's. Not a bug, just flagged so it isn't mistaken for something
still needing to be wired up.

### The same-turn arrival-vs-restricted-departure question — resolved

Real, verified example (drone 4, `maze_nightmare`, from the clean run in
§1): arrives at `maze_a2` at turn 3, then *at that same turn 3* begins a
restricted move into `trap_loop1` (arriving turn 5) — no wait turn in
between. This is not two actions compressed into one turn — VII.3's
per-turn choice ("move" / "enter a restricted connection" / "stay") is
made fresh every turn, with nothing requiring a mandatory settling turn
after any arrival. Turn 2 picks "move" (into `maze_a2`); turn 3, a wholly
separate turn, picks "enter restricted connection" (into `trap_loop1`).

The actual implementation subtlety: turn 3 is *both* the endpoint of one
hop and the start point of the next hop in the raw path list, so a naive
per-hop conversion would want to write two different events to
`events[3]`. Resolved for free by dict-overwrite semantics in the loop
above — the later hop's assignment simply replaces the earlier one, with
no special-case needed. This also happens to match the more accurate
description of what the drone is doing that turn (entering the connection,
not idling in `maze_a2`), but that specific tie-break (departure event
wins over a same-turn arrival print) is an implementation choice, not
something VII.5 states explicitly either way.

### `run()` as currently written

```python
def run(self) -> None:
    visualizer = Visualizer(self.zones, self.connections)
    visualizer.wait_to_start()
    if not visualizer.running:
        return

    total_turns = max(self.paths[drone][-1][1] for drone in self.paths)
    turns: dict[int, list[tuple[int, tuple[EventType, Any, Any, str]]]] = {}

    for drone_id in self.paths:
        curr_drone_events = _drone_path_to_events(drone_id, self.paths[drone_id],
                                                    self.zones, self.connections)
        for turn, event in curr_drone_events.items():
            if turn not in turns:
                turns[turn] = []
            turns[turn].append((drone_id, event))

    # NOT YET WRITTEN — see §6 for what's left
```

## 6. What's actually left to finish `run()`

**A. The playback loop itself** — `for turn in range(1, total_turns + 1):`,
consuming `turns.get(turn, [])`, calling `visualizer.render_frame()` /
`visualizer.clock.tick(...)` each turn, breaking if `not visualizer.running`.

**B. The mutation dispatch — this is NOT a generic leaves/occupies
interpretation.** It needs to switch explicitly on `EventType`, because
`RESTRICTED_MID`'s tuple carries `conn_key` in the "occupies" slot for
bookkeeping/token purposes only — it must NOT trigger a fresh
`increase_occupancy()` call (the connection was already occupied by the
preceding `RESTRICTED_START` turn; incrementing again would double-book
it). The actual per-EventType mapping, as discussed this session:

| EventType | Mutations |
|---|---|
| `NORMAL` | `zoneA.decrease_drone_count()`, `zoneB.increase_drone_count()` |
| `RESTRICTED_START` | `zoneA.decrease_drone_count()`, `connection.increase_occupancy()`, `drone.target = zoneB`, `drone.set_to_restricted()` |
| `RESTRICTED_MID` | `drone.update_status()` only — no zone/connection count changes |
| `RESTRICTED_END` | `connection.decrease_occupancy()`, `zoneB.increase_drone_count()` |

`drone.increase_move_count()` should also get called somewhere in this
dispatch (once per drone per turn it actually moves) — this is what
resolves task #29 (checking `total_move_count`/`increase_move_count`
usage) once it's wired in here.

**C. The direction-of-travel token** — still a literal empty string
placeholder in `_drone_path_to_events`. Needs the actual origin→destination
string per the 07-22 decision (computed once, reused identically across
both `RESTRICTED_START` and `RESTRICTED_MID` — the single `token` variable
already does the reuse correctly, it just needs real content instead of
`""`).

**D. Building and printing each turn's line** — for every `(drone_id,
event)` in that turn's list, `f"D{drone_id}-{event[3]}"` (the token is
always the last tuple element regardless of `EventType`); join with
spaces; print only if the list is non-empty (VII.5 omits turns/drones with
nothing happening).

## 7. Everything else still outstanding (unchanged in substance from the
07-22/07-23 handoffs, listed here for one place to check)

1. Finish `run()` per §6 above.
2. Watch a real map play out against the visualizer once `run()` is
   complete — `render_frame()` was written before any of this existed and
   has never actually been exercised against real per-turn state changes,
   only read through.
3. `README.md` (#32) — description, instructions, resources/AI-usage
   section, algorithm write-up, visualizer documentation. Unblocked now
   that there's a finished, benchmarked algorithm to describe.
4. Docstring sweep (#22) — `Scheduler`, `ScheduleError`, `EventType`, and
   `_drone_path_to_events` all got docstrings this session; `Engine.run`
   and `Engine.__init__` got theirs too. Worth a final pass once `run()`'s
   body is actually finished, since docstrings were written slightly ahead
   of the implementation in a couple of cases.
5. Remove the debug `print` in `drone.py` (#26).
6. Run `flake8`/`mypy` for real across everything touched today — the
   `Any` usage in `_drone_path_to_events`'s tuple type, and the new
   `pathfinding/` package's imports, haven't been checked yet.
7. Resolve the `Move`-vs-`EventType` open item from §5 before it's
   forgotten — right now there are two structures serving adjacent
   purposes, and only one is actually wired in.
