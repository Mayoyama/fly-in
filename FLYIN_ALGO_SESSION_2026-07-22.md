# Fly-in — Algorithm Design Session (2026-07-22, web/chat session)

Read alongside `FLYIN_COLLAB_RULES.md` — that file's rules still apply.
This file is a handoff of what got designed and written *today*, on the
web chat session, so the algorithm work can continue from exactly where
it left off.

## Personal goal driving every decision below

User is aiming for **full bonus points** ("I do this for every project") —
not just the mandatory 30/35/45-turn hard-map benchmarks, but "perfectly"
matching/beating every reference target, including the optional
challenger-map 45-turn record. This is why the architecture below leans
congestion-aware rather than doing the minimum needed for mandatory-tier
credit.

## Architecture decisions locked in

- **Overall approach:** reservation-aware weighted Dijkstra (per-drone,
  planned sequentially) + two-pass turn execution. CBS was considered and
  rejected — sum-of-costs optimality doesn't map cleanly to this project's
  pure-makespan scoring, and cost/complexity is too high for 12–25 drones.
- **Congestion-awareness is baked into the Dijkstra cost function itself**,
  not a bolt-on "detect bottleneck nodes" pass. As reservations fill a
  gate/connection, its effective cost should rise, naturally spreading
  drones across parallel routes (this is the mechanism that let one
  public repo beat the challenger's 45-turn record via manual bottleneck
  detection — here it should fall out of the cost function generically,
  on any map, not just ones with an obvious named bottleneck pattern).
  **The actual congestion-cost formula is NOT yet designed** — only the
  principle is agreed.
- **Blocked zones are excluded from the search space entirely** — not
  costly, structurally absent. No edge into a BLOCKED zone should exist
  for the pathfinder to consider.
- **Planning and execution are fully separated**, specifically so
  drone-reordering / local-search optimization (for challenger bonus
  chasing) can be added later without a rework:
  - `Scheduler` (currently the empty stub in `pathfinder.py`) becomes the
    **entire planning phase** — owns the reservation tables, loops over
    drones, asks the timed pathfinder for each drone's route, commits
    reservations as it goes, hands back one finished turn-indexed
    schedule.
  - `Engine.run()` becomes **pure playback** — takes the finished
    schedule, walks turns 1→N, applies state changes
    (`increase_drone_count`, `set_to_restricted`, etc.), prints, calls
    `render_frame()`. No pathfinding decisions happen here anymore.
  - This split is what makes "try a few drone orderings, keep whichever
    gives fewest total turns" cheap to add later — it's just calling the
    planning phase N times with different orders and keeping the best
    schedule. If planning/execution were interleaved instead, this would
    require a real rework later. **Not built yet — deferred, but the
    door is deliberately kept open.**
- **Existing `pathfinder.py`/`simulation.py` code is disposable** — user
  confirmed the old BFS/naive placeholder loop was only ever there to
  verify animation/parsing worked, not a real implementation. Full
  replacement, no legacy constraints.

## Output-format decision (VII.5)

- `D<ID>-<connection>` for in-transit drones uses **direction of
  travel** (origin→destination), not the connection's file-order name.
  Decided because: (a) collision-free — two drones traversing the same
  connection in opposite directions print different strings, (b) it's
  already available at `Move`-creation time with no extra lookup needed.
  Searched several public 42 fly-in repos for precedent — none had a
  worked example with a restricted zone in transit, so this is genuinely
  unprecedented elsewhere, not something we got wrong relative to a
  convention.
- **The connection string is computed once, at the turn the drone departs
  onto the connection, and reused unchanged for both in-transit turns** —
  not recomputed each turn (there's nothing to recompute from anyway,
  since `curr_pos` doesn't update until arrival).

## Code written and verified today

### `models/drone.py` — `Move` dataclass, expanded

```python
@dataclass
class Move:
    """A single scheduled move: which drone, when, and where — either
    the destination zone (arrived) or the connection when it's currently
    transiting toward a restricted zone."""
    drone_id: int
    dest: str
    turn_nb: int
    in_transit: bool
```

Kept the field name `dest` (not `target`) deliberately — `Drone` already
has its own `target` attribute with different scope (the zone a drone is
restricted-transiting toward), and reusing the name on `Move` would mean
the same word means two different things depending on which class you're
reading.

### `models/zone.py` — new method, `get_max_capacity`

Needed because `available_capacity()` reflects **live** occupancy
(`curr_drone_count`), which is meaningless during planning — planning
needs the zone's **static** limit, independent of what's booked when.

```python
def get_max_capacity(self) -> int:
    """Return max_drones this zone can hold.

    Returns:
        0 if blocked; sys.maxsize for start/end hubs;
        otherwise self.max_drones.
    """
    if self.zone_type == ZoneType.BLOCKED:
        return 0
    if self.hub_role == HubRole.START or self.hub_role == HubRole.END:
        return maxsize
    return self.max_drones
```

### `pathfinder.py` — `Scheduler`, reservation table + move check/reserve

Two separate reservation tables (zones and connections kept apart
deliberately, rather than one unified structure — different capacity
rules, different key shapes). Connection keys use `frozenset[str]` to
match how `Engine.connections` is already keyed — direction is
irrelevant to capacity, `max_link_capacity` is a shared limit regardless
of which way drones are moving. (The direction-of-travel string for
output is a totally separate thing, computed on `Move`, never derived
from this key.)

**Zone occupancy rule (VII.3, not a judgment call — the spec states it
directly):** a drone's reservation window is `[arrival_turn,
departure_turn - 1]` — departure frees that turn's slot immediately, so
an incoming drone can take the same turn a departing drone vacates.

**Restricted moves need an atomic three-way commit** — per VII.3, a
drone can't pause or abort mid-restricted-transit, so the connection's
2-turn block and the destination zone's arrival-turn slot must be
checked together and either both commit or neither does. This was
unified into one function used for both normal (1-turn) and restricted
(2-turn) moves, rather than two separate code paths — the difference is
just how many turns `turns_needed` works out to.

Final structure: `_check_move` (private, does all the actual checking,
returns the arrival turn if feasible or `None` if not — single source of
truth for "is this move legal") → `can_reserve_move` (public, read-only,
for the pathfinder to probe candidate edges while searching without
committing anything) → `try_reserve_move` (public, commits to both
tables — called once a drone's full path is finalized, hop by hop).

```python
class Scheduler:
    def __init__(self, zones: dict[str, Zone],
                 connections: dict[frozenset[str], ZoneConnection]) -> None:
        self.zones = zones
        self.connections = connections
        self.zone_reserves: dict[str, dict[int, int]] = {}
        self.conn_reserves: dict[frozenset[str], dict[int, int]] = {}

    def _check_move(self, origin: str, dest: str, connection: ZoneConnection,
                     depart_turn_nb: int) -> int | None:
        """Check whether this move is legal given current reservations.

        Returns the turn the drone would arrive at `dest` if the move is
        feasible, or None if it isn't (connection or destination zone
        lacks capacity at some required turn).
        """
        if self.zones[dest].zone_type == ZoneType.RESTRICTED:
            turns_needed = 2
        else:
            turns_needed = 1
        arrival_turn = depart_turn_nb + turns_needed
        for turn in range(depart_turn_nb, arrival_turn):
            if self.conn_reserves.get(frozenset({origin, dest}), {}).get(turn, 0) >= connection.max_link_cap:
                return None
        if self.zone_reserves.get(dest, {}).get(arrival_turn, 0) >= self.zones[dest].get_max_capacity():
            return None
        return arrival_turn

    def can_reserve_move(self, origin: str, dest: str, connection: ZoneConnection,
                          depart_turn_nb: int) -> bool:
        """Read-only feasibility check — used by the pathfinder while it's
        still exploring candidate edges. Reserves nothing."""
        return self._check_move(origin, dest, connection, depart_turn_nb) is not None

    def try_reserve_move(self, origin: str, dest: str, connection: ZoneConnection,
                          depart_turn_nb: int) -> bool:
        """Commit this move into the reservation tables if it's legal.

        Called once a drone's path is finalized, to actually book each hop.
        """
        arrival_turn = self._check_move(origin, dest, connection, depart_turn_nb)
        if arrival_turn is None:
            return False
        conn_key = frozenset({origin, dest})
        for turn in range(depart_turn_nb, arrival_turn):
            if conn_key not in self.conn_reserves:
                self.conn_reserves[conn_key] = {}
            current = self.conn_reserves[conn_key].get(turn, 0)
            self.conn_reserves[conn_key][turn] = current + 1
        if dest not in self.zone_reserves:
            self.zone_reserves[dest] = {}
        current = self.zone_reserves[dest].get(arrival_turn, 0)
        self.zone_reserves[dest][arrival_turn] = current + 1
        return True
```

**Note on provenance:** the last version of `try_reserve_move` above was
given directly (not derived step-by-step) because the user was about to
miss a train. Everything else in this file was built incrementally with
the user writing each line. This one method is worth a closer read-through
at the start of the next session before trusting it fully — it hasn't
been run against flake8/mypy or exercised against a real map yet.

**Not yet raised/settled:** `try_reserve_move`/`can_reserve_move` both
take `connection: ZoneConnection` as a parameter, even though `Scheduler`
already holds `self.connections` (keyed by the same `frozenset`). The
caller currently has to look up and pass the connection object itself.
Worth considering whether these methods should just derive it internally
via `self.connections[frozenset({origin, dest})]` instead — minor
cleanup, not decided either way.

## Custom test maps (already delivered, in `maps/custom/`)

Three new maps generated this session specifically to exercise blocked-zone
handling, verified solvable (BFS avoiding blocked zones reaches goal) via a
throwaway sandbox script:

- **`custom/02_fractured_circuit`** (hard-tier, 10 drones) — one blocked
  zone (`short_cut`) sits as a decoy shortcut bypassing a detour chain.
- **`custom/03_sealed_vault_gauntlet`** (hard-tier, 12 drones) — one
  blocked zone (`sealed_vault`), originally a simple dead-end decoy; user
  added two more connections (`sealed_vault-priority_lane1`,
  `sealed_vault-priority_lane2`) afterward, making it a degree-4 decoy hub
  instead — a harder trap for a buggy exclusion check. Re-verified
  solvable after the edit.
- **`custom/01_shattered_route`** (challenger-tier, 20 drones) — three
  blocked zones; user added `express_trap-goal` afterward, making
  `express_trap` sit two hops from `start` and directly adjacent to
  `goal` — the sharpest trap in the set: any gap in blocked-exclusion
  would make this the shortest path in the whole map. Re-verified
  solvable after the edit.

All three are intentionally *not* touched/edited directly by Claude in
this session beyond the initial generation — per project rules, map file
edits after generation were made by the user in their own environment.

## What's NOT done yet — the actual remaining work

In priority order:

1. **The timed pathfinding function itself.** Needs to be Dijkstra (or
   equivalent) over `(zone, turn)` states, not plain zones — because
   `Scheduler` needs to know *when* a drone hits each step, not just the
   route. Must, per hop: exclude BLOCKED zones structurally, apply
   restricted(2)/priority(1-but-preferred) costs, consult
   `can_reserve_move` (read-only) to check feasibility of candidate
   edges, and support "wait in place" as a legal move (per VII.3 — also
   the reason count-only reservations are provably sufficient: a drone
   facing a full bottleneck can always wait at `start`, since start/end
   hubs are unlimited, so nothing ever needs undoing/backtracking).
   **Not started.**
2. **Congestion-cost formula** — the actual function converting current
   reservation occupancy into added Dijkstra edge weight. Only the
   principle is agreed; the formula itself needs designing.
3. **`Engine.run()` rewritten as pure playback** — turn-indexed loop
   reading the finished schedule from `Scheduler`, applying real state
   changes, printing per VII.5 format (using `Move.dest` +
   `Move.in_transit`), calling `render_frame()`. **Not started.**
4. **Drone-ordering / local-search bonus layer** (optional, for beating
   the challenger's 45-turn record specifically) — try a few
   drone-processing orders, keep whichever full schedule has fewest total
   turns. Cheap to add given the planning/execution split above, but
   **not built, deliberately deferred** until the baseline algorithm
   works and can be benchmarked.

## Immediate next step when picking this back up

Design and write the timed pathfinding function (item 1 above) — this is
the next actual piece of new logic, following the same
"outline-then-fill-in-piece-by-piece" style used for `Scheduler` today.
It will call `self.can_reserve_move(...)` from inside its search loop.

## Standing task-list items unaffected by today's session

Still open from before, unchanged: #22 (docstrings for
`simulation.py`/`pathfinder.py`, deferred until the algorithm's done),
#26 (remove debug print in `drone.py`), #29 (recheck
`drone_id`/`total_move_count` usage — will likely resolve naturally once
`Engine.run()`'s playback loop is written, since that's the natural call
site for `increase_move_count()`), #32 (README, still needs writing).
