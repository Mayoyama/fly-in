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
given greater assistance in writing (not fully derived step-by-step) due to
complexity. Everything else in this file was built incrementally with
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

## Congestion-cost formula — designed on the 2026-07-22 train-ride
## follow-up (web chat, after this file was first written)

This directly resolves item 2 below (previously "only the principle is
agreed"). Not yet implemented, but the design is now concrete:

- **Two candidate formulas**, both additive on top of the existing base
  cost (1 normal / 2 restricted / ~0.99 priority):
  - Linear: `congestion_term = (occupancy / capacity) * epsilon`.
  - Convex/BPR-style (favored): `congestion_term = (occupancy / capacity)
    ** 2 * epsilon` — a simplified version of the real Bureau of Public
    Roads volume-delay function traffic routers use. Cheap until a zone
    is nearly full, then climbs — matches real congestion behavior better
    than linear (a zone at 1/6 full isn't meaningfully worse than empty;
    one at 5/6 full genuinely is). Worked example against
    `02_capacity_hell.txt`'s `convergence` zone (`max_drones=6`,
    `epsilon=0.2`): empty → 0, 2 booked → ~0.022, 5 booked → ~0.139.
  - **Hard constraint on `epsilon`:** must stay well under 1 — smaller
    than the cost difference between any two real path options — so the
    term can only break near-ties or nudge marginal decisions, never make
    Dijkstra prefer an actually-longer path just to dodge moderate
    congestion.
- **Capacity-1 zones need no special-casing in the formula at all.** For
  a capacity-1 zone, `occupancy/capacity` can only ever be 0 (empty) or
  1 (full) — no fractional in-between a soft formula could act on. And
  "full" isn't a soft-cost case here — it's the hard block in
  `_check_move` returning `None`. A second drone wanting that zone at
  that turn can't take the edge at all; it has to route through a later
  arrival turn instead, which costs it real, hard extra turns of
  waiting. So capacity-1 contention already produces a genuine cost
  increase through the existing hard-check mechanics alone — the
  congestion formula only needs to matter for zones with capacity > 1,
  where a real occupancy gradient exists.
- **Single arrival turn vs. duration-aware occupancy — resolved as not
  actually a separate design question.** It's a consequence of how a
  drone's *dwell time* gets reserved, which is a correctness question for
  the hard capacity check, not a congestion-formula nicety. Since "wait
  in place" is already locked in as an explicit edge in the time-expanded
  graph (`(zone, t) → (zone, t+1)`), the natural, consistent
  implementation is for **every wait-edge to get its own
  `try_reserve_move` call** when a winning path is committed, exactly
  like a real move does. A drone dwelling 5 turns then produces 5
  separate per-turn reservation entries. This means checking a single
  future turn's occupancy count *already* correctly reflects everyone
  genuinely present at that moment, including anyone dwelling there via
  their own chain of wait-reservations — duration-awareness falls out of
  the per-turn wait-edges automatically, no separate "how long will this
  drone be here" tracking needed anywhere. (The alternative — reserving
  one arrival-turn entry and treating the zone as occupied "until further
  notice" without reserving the in-between turns — would actually be a
  correctness bug, not just a formula limitation, since a second drone
  could then be told a busy zone has room.) **Practical takeaway:** when
  building the timed pathfinder, make wait-hops commit reservations the
  same way real moves do — the congestion term then just reads the exact
  same `zone_reserves.get(dest, {}).get(turn, 0)` lookup `_check_move`
  already does, no new bookkeeping required.

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
   **Wait-edges must commit their own per-turn reservation** (see
   congestion-cost section above) — this is now a settled requirement,
   not an open question. **Not started.**
2. **Congestion-cost formula** — design is done (see section above:
   likely the quadratic/BPR-style version, `epsilon` small and well under
   1), just not implemented/wired into the timed pathfinder yet.
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

## Bug found and fixed since this file was first written

`try_reserve_move` had landed in the actual `pathfinder.py` file at
module level (zero indentation) instead of as a method under `class
Scheduler:`, despite the embedded code sample above (and the design)
always showing it correctly indented — a paste/indentation slip between
design and file. Confirmed three ways: direct file read, `mypy --strict`
flagging `self` as an untyped parameter (only happens outside a class),
and flake8's `E302` (only fires for top-level defs). **Fixed** — it's
correctly a `Scheduler` method now. Also cleaned up: six `E501`
line-too-long violations (the method signatures and the two capacity
checks in `_check_move` were pulled onto multiple lines / extracted into
named local variables) and a couple of trailing-whitespace-on-blank-line
spots. `flake8` and `mypy --strict` both pass clean across the whole
project as of this fix.

## Is this Dijkstra or A*? (came up mid-session, worth keeping in mind)

The `(zone, turn)` state-space search with reservation checks and
wait-edges is exactly the formulation used in "Cooperative A*"/"Space-Time
A*" in the multi-agent pathfinding literature — same family as A*. The
actual difference between Dijkstra and A* is just whether a heuristic is
added: Dijkstra expands uniformly by cost-so-far; A* adds an admissible
estimate of remaining cost to prioritize expansion toward the goal, exploring
far fewer states for the same optimality guarantee. As currently designed
this is plain Dijkstra (no heuristic yet). Since every drone shares the same
fixed goal (the end hub), a cheap upgrade is available later: precompute a
static distance-to-goal for every zone once (ignoring time/capacity — one
BFS/Dijkstra pass over the whole graph, reused for every drone) and use it
as `h(n)`. That would make it A* in the literal sense and directly speaks to
the efficiency/complexity questions the PDF asks about in VII.1. **Not
decided or built — a follow-up optimization to consider once the baseline
(plain Dijkstra) version works and is benchmarked, not a blocker.**

## Immediate next step when picking this back up

Design and write the timed pathfinding function (item 1 above) — this is
the next actual piece of new logic, following the same
"outline-then-fill-in-piece-by-piece" style used for `Scheduler` today.
It will call `self.can_reserve_move(...)` from inside its search loop,
and must commit a `try_reserve_move` for every wait-edge it takes, not
just real moves (see congestion-cost section above for why).

## Standing task-list items unaffected by today's session

Still open from before, unchanged: #22 (docstrings for
`simulation.py`/`pathfinder.py`, deferred until the algorithm's done),
#26 (remove debug print in `drone.py`), #29 (recheck
`drone_id`/`total_move_count` usage — will likely resolve naturally once
`Engine.run()`'s playback loop is written, since that's the natural call
site for `increase_move_count()`), #32 (README, still needs writing).

## Session continued 2026-07-23 (Claude desktop/Cowork session) — timed
## pathfinder built, tested, and largely wired up

This picks up directly from "Immediate next step" above. Substantial
progress — the baseline algorithm (item 1 from the priority list) is now
functionally complete and verified against real maps, though a couple of
pieces below are still open.

### `can_reserve_move` return-type redesign (settled before the build)

Changed from `bool` to `int | None` (settled explicitly with the user
before writing the search itself, to avoid duplicating restricted-zone
2-turn cost logic between `Scheduler` and the pathfinder). It's now a
direct passthrough to `_check_move`, so the pathfinder gets the actual
arrival turn for free instead of having to recompute it.

### `make_single_path` — the timed Dijkstra search, built and tested

Built incrementally, user writing every line, with heavy line-by-line
correctness checking per their explicit preference for algorithm work.
Full current version lives in `pathfinder.py`. Key points:

- States are `(zone, turn)` tuples. Heap entries are
  `(cost, insertion_counter, state, predecessor)` — the counter exists
  purely to break ties safely (comparing `predecessor` values, which can
  be `None`, would otherwise raise `TypeError` on a cost/state tie).
- Path reconstruction uses a `pathed_dict[state] = predecessor` map,
  populated only at **pop** time (not push time) so a later, worse
  duplicate can never overwrite an earlier correct entry. The true start
  state never becomes a key (predecessor recorded as `None` and
  deliberately skipped), so `while state in pathed_dict:` naturally
  terminates at the true start with no sentinel/KeyError risk.
- Returns `[]` if no path is found (heap exhausts without reaching
  `HubRole.END`).
- Several real bugs were caught and fixed during the build (destination
  confusion between the two move branches, cost not being accumulated,
  arrival vs. departure turn confusion, `.append()` used instead of
  `heappush()` breaking the heap invariant, a `None`-vs-tuple mypy error,
  `list.reverse()`'s `None` return being reassigned instead of called
  bare, and the reconstruction loop not reassigning `state` — infinite
  loop shape). All confirmed fixed via repeated file reads + flake8/mypy.

### Wait-in-place move added

`Scheduler.can_reserve_wait`/`try_reserve_wait` added (single zone-only
capacity check, no connection involved) and wired into
`make_single_path` as a third candidate move alongside the two
zone-to-zone branches. Confirmed working via sandbox tests, including a
manually forced multi-turn wait scenario.

### `plan_all_paths` — the outer per-drone planning loop, built and tested

Lives in `pathfinder.py`, below `make_single_path`. For each drone (dict
order, no priority ordering yet): calls `make_single_path`, raises
`ScheduleError` if it comes back empty or doesn't end at the end hub,
then walks the winning path committing each hop via `try_reserve_move`
(zone changed) or `try_reserve_wait` (zone unchanged), with `assert`
checks on both (they should always succeed since `make_single_path`
already validated feasibility). Verified end-to-end against three real
maps (`easy/03_basic_capacity`, `medium/02_circular_loop`,
`custom/02_fractured_circuit`, 4/6/10 drones respectively) — all drones
planned successfully, congestion-driven waits look correct, no
exceptions, mypy strict clean across all 15 project files.

`ScheduleError(Exception)` added at the top of `pathfinder.py` for this
— this is now how task #34 (no-valid-schedule handling) is resolved in
code, though the task is being left open until the item below is wired
in, since without it the empty-path case can't actually be reached
safely (see next section).

### Infinite-loop bug found, and fixed via `is_reachable`

**Real, load-bearing bug, not a hypothetical:** tested `plan_all_paths`
against a deliberately disconnected two-zone map and it hung forever
(45s timeout, no return). Root cause: `start`/`end` have unlimited
capacity, so `can_reserve_wait` at `start` is always `True` — when the
goal is genuinely unreachable, `make_single_path`'s `while state_heap:`
loop never hits its only break condition (`HubRole.END`) and keeps
pushing `(zone, turn+1)` wait-states onto the heap forever, turn number
climbing without bound.

Key insight that shaped the fix: **congestion can never cause this** —
since reservations only ever occupy specific past/near-term turns, a
topologically-connected graph is *always* eventually reachable at some
large enough turn. The only way the search can loop forever is if `end`
is not reachable from `start` in the raw graph structure at all — a
static fact about the map, true or false the same way for every drone.

Fix: a one-time-per-map topological reachability check (BFS via
`collections.deque`, ignoring turns/capacity), explicitly excluding
`BLOCKED` zones (confirmed required, not just defensive, by PDF text:
"Drones must not enter or pass through this zone. Any path using it is
invalid."). This was consciously modeled on the just-deleted `find_path`
BFS — same underlying technique, repurposed from "find the path to use"
to "confirm a path could ever exist," which is why `deque` came back
into the file after being removed earlier in the session.

```python
def is_reachable(start: str, end: str,
                 conn_dict: dict[frozenset[str], ZoneConnection],
                 zone_dict: dict[str, Zone]) -> bool:
    """Check whether end is reachable from start in the raw zone graph.

    Ignores turns/congestion (a topological-only check), but does
    respect BLOCKED zones, since those can never be entered at any
    turn regardless of congestion. Used once per map to confirm a
    timed path could ever exist before running the real search.
    """
    visited = {start}
    queue = deque([start])

    while queue:
        current = queue.popleft()
        if current == end:
            return True
        for zone_info in conn_dict.values():
            neighbor = None
            if current == zone_info.z1_name:
                neighbor = zone_info.z2_name
            elif current == zone_info.z2_name:
                neighbor = zone_info.z1_name
            if (neighbor is not None and neighbor not in visited
                    and zone_dict[neighbor].zone_type != ZoneType.BLOCKED):
                visited.add(neighbor)
                queue.append(neighbor)

    return False
```

**This is already wired into `plan_all_paths`** — called once, right
after `start`/`end` are computed, before the per-drone loop:
`if not is_reachable(start, end, conn_dict, zone_dict): raise
ScheduleError(...)`. Confirmed correct via a re-read of the actual file
during this session (after initially, incorrectly telling the user it
wasn't wired in yet — the user caught this and asked for a rule about
verifying files before asserting; see updated
`FLYIN_COLLAB_RULES.md`).

**Not yet done:** rename `is_reachable` → `_is_reachable` (it's only
ever called from within `plan_all_paths`, in the same file — matches
the `_convert_atoi`/`_get_parsing_data`/`_create_zone_info` private-
helper convention already established in `parser.py`). Flagged
explicitly: if `pathfinder.py` gets split into a package (see task #35
below) and `_is_reachable` ends up in a different file than its only
caller `plan_all_paths`, the underscore convention would become
contradictory — either keep them in the same file after the split, or
make it properly public at that point.

### Parser-level validation added: `BLOCKED` start/end hubs rejected

The PDF spec doesn't explicitly forbid `zone=blocked` on `start_hub`/
`end_hub` lines (only `max_drones` metadata being ignored there is
called out) — but a `BLOCKED` start/end is a genuine contradiction per
spec (`BLOCKED` zones can never be entered, full stop), unlike
`RESTRICTED` on start/end which is merely odd, not illegal (costs an
extra 2 turns to reach, but nothing actually breaks). User's own words,
given their zero-risk-tolerance stance on 42 peer review:
"knowing the f*d up things evaluators pull to try fail others, I cant
take any risks."

Added in `_create_zone_info` (`parser.py`), right after `zone_info` is
constructed (so `zone_info.zone` is already the validated `ZoneType`):

```python
    if hub_type in (HubRole.START, HubRole.END) and \
            zone_info.zone == ZoneType.BLOCKED:
        raise ValueError("start_hub/end_hub cannot be a blocked zone")
```

Flows through the existing `except ValueError as e: raise ValueError(
f"Line {i}: {e}") from e` wrapper in `parse_map_data`, same as every
other validation error. Verified via a throwaway test: a blocked
`end_hub` correctly raises with the right line number; a restricted
`start_hub` is correctly allowed through unchanged.

### New task added: split `pathfinder.py` (task #35)

`pathfinder.py` has grown to contain `ScheduleError`, `Scheduler`,
`make_single_path`, `plan_all_paths`, and `is_reachable` — user
explicitly wants this split into multiple files/a package once things
stabilize, consistent with how `visualizer/` was already split.
Deliberately deferred, not urgent — see the note above about
`is_reachable`'s privacy depending on where it lands after the split.

### What's left, updated priority order

1. Rename `is_reachable` → `_is_reachable` (trivial, not yet done).
2. Wire `plan_all_paths` into `Engine`'s setup (`simulation.py`) — not
   started. `simulation.py` already imports `make_single_path` and
   `Scheduler` from `pathfinder.py` but doesn't use them yet (flake8
   currently flags both as unused, expected/known).
3. Rewrite `Engine.run()` as pure turn-indexed playback, reading the
   finished schedule from step 2 rather than the current commented-out
   naive placeholder (lines 39-54 of `simulation.py`, left commented
   in-place by the user for now, `find_path` reference and all — that
   whole block will be replaced, not fixed).
4. Congestion-cost formula (design already settled in the section
   above from the prior session) — still not wired into
   `make_single_path`'s cost calculations, which currently use flat
   costs only (1 normal/priority, 2 restricted, 1 wait).
5. Task #35 (split `pathfinder.py`) — deferred until the above
   stabilizes.
6. Drone-ordering/local-search bonus layer — still deliberately
   deferred, unchanged from before.

Task #34 (no-valid-schedule handling) is functionally resolved by
`ScheduleError` + `is_reachable`, but being left open on the tracker
until item 1/2 above are done and re-verified together.

### Full independent validation run, end of 2026-07-23 session

Before closing out, ran a from-scratch validator (recomputes zone/
connection occupancy per turn independently of `Scheduler`'s own
bookkeeping, so it can't share a blind spot) against all 13 real map
files (easy through challenger-tier, 2-25 drones). All 13 passed clean:
correct zone/connection capacity at every turn, correct 1-turn/2-turn
move durations, no path ever entering a `BLOCKED` zone, all paths
properly anchored at `(start, 0)` and the end zone, turns strictly
increasing. Also reconfirmed the disconnected-map case now returns
`ScheduleError` instantly (no hang) with `is_reachable` wired in.

### Real correctness gap found via direct `Scheduler` unit test (not yet fixed)

Everything above tests `Scheduler` only indirectly, through the full
`make_single_path`/`plan_all_paths` pipeline. A direct, isolated test of
`Scheduler`'s own methods (hand-crafted reservations, no search
involved) surfaced a genuine spec-compliance gap:

**VII.3 states explicitly: "Drones moving out of a zone free up capacity
for that same turn."** Tested this directly: a capacity-1 zone `X`, with
drone A reserved to arrive at `X` at turn 4 and depart the same turn
(pass-through, zero dwell) — `zone_reserves['X'] = {4: 1}`. Checked
whether a second drone could also arrive at `X` at that same turn 4 (the
exact turn A vacates). Per spec this should be legal (net occupancy
stays at 1). `can_reserve_move` incorrectly rejected it.

Root cause: `_check_move`'s capacity check
(`zone_reserves[dest].get(arrival_turn, 0) >= capacity`) only counts
"how many drones have this zone as an arrival-turn tuple at turn T" — it
has no way to distinguish a drone still dwelling through turn T from one
departing at turn T. A drone's own last-turn-of-presence reservation
wrongly blocks a same-turn replacement arrival.

**Not a safety bug** — no schedule produced so far has ever exceeded
real capacity; the model is strictly *more conservative* than the spec
requires. But it can produce schedules with unnecessary extra waiting
turns, which matters directly for the bonus-points goal (minimizing
total turns, challenger 45-turn record etc.). **Real design change
needed, not a one-line patch:** the reservation model would need to
track departures per zone per turn separately from arrivals, so
`_check_move` can net "departures this turn" against "existing
occupancy" before rejecting a new arrival at that same turn. Flagged as
a new task below rather than fixed this session, given the hour.

## Morning follow-up (2026-07-23, same day, ~45 min session) — Scheduler
## fix attempted and reverted, nothing merged

Picking up directly from the same-turn vacate/arrive gap found the night
before (previous section). This short session's entire arc: designed a
fix, implemented it, found via full validation that it broke real
correctness, and reverted it completely. **End state: `pathfinder.py` is
byte-for-byte back to the pre-attempt version from the night before** —
flake8/mypy clean, all 13 real maps re-validated with zero constraint
violations. Nothing from this attempt is live in the codebase. Full
details of what was tried and why it failed are in the first bullet of
the task list immediately below — read that before attempting a fix
again, so the same broken approach doesn't get retried.

## RESOLVED: same-turn vacate/arrive is NOT a bug (2026-07-23, separate
## Opus/Cowork analysis session, cross-checked and corroborated)

A separate analysis session, working from the actual PDF text (VII.2/
VII.3), settled this definitively — **closing this item, no further fix
needed.** Independently cross-checked before accepting: the quoted spec
text was verified verbatim against the real PDF, the benchmark numbers
below were verified against my own from-scratch validator run earlier
the same day (exact match, digit for digit), the `shattered_route`
bottleneck claim was verified against the actual map file, and the
drone-ordering no-op claim was independently re-tested (6 shuffles,
including the challenger map) with identical results.

**Why it was never a bug:** VII.2 states plainly — *"Two drones may not
enter the same zone on the same turn unless the zone's capacity allows
it."* A drone present at a zone at turn `t` is part of turn `t`'s
configuration; a second drone also arriving at turn `t` is two drones
in the same configuration, which VII.2 forbids once capacity is
exceeded. VII.3's "departure frees capacity the same turn" describes
the turn-to-turn *handoff* (no cooldown — a slot vacated at turn 4 is
legally reusable at turn 5, which the reverted/current code already
does correctly), not a same-turn double-booking allowance. Both fix
attempts this project made (morning of 07-23, and an earlier one)
broke real capacity precisely because they legalized something VII.2
explicitly forbids — confirmed with a concrete repro: on
`easy/03_basic_capacity`, the "netting" model scored 3 turns instead of
4, but that 3-turn schedule puts 4 drones through the cap-2
`bottleneck` zone in a single turn — an illegal schedule, not a better
one. **The reverted/current reservation model (arrivals-only, no
netting) is the correct, spec-compliant model. Do not attempt this fix
again.**

## Benchmark results — the baseline already meets/beats every VII.7
## target (verified against the real PDF's numeric thresholds)

| tier | map | drones | makespan | VII.7 target | margin |
|---|---|---|---|---|---|
| easy | 01_linear_path | 2 | 4 | ≤ 6 | pass |
| easy | 02_simple_fork | 4 | 4 | ≤ 8 | pass |
| easy | 03_basic_capacity | 4 | 4 | ≤ 6 | pass |
| medium | 01_dead_end_trap | 5 | 8 | ≤ 12 | pass |
| medium | 02_circular_loop | 6 | 15 | ≤ 15 | zero margin |
| medium | 03_priority_puzzle | 5 | 7 | ≤ 12 | pass |
| hard | 01_maze_nightmare | 8 | 13 | ≤ 30 | wide |
| hard | 02_capacity_hell | 12 | 16 | ≤ 35 | wide |
| hard | 03_ultimate_challenge | 15 | 26 | ≤ 45 | wide |
| challenger | 01_the_impossible_dream | 25 | 43 | record 45 | beats record |
| custom | 01_shattered_route | 20 | 29 | — | provably optimal |
| custom | 02_fractured_circuit | 10 | 29 | — | provably optimal |
| custom | 03_sealed_vault_gauntlet | 12 | 19 | — | — |

`shattered_route`/`fractured_circuit` are provably optimal — each is
gated by a single mandatory serial bottleneck with no parallel route
(`final3`, cap 1, sole non-blocked approach to `goal`; and the
`detour1→detour2` restricted+cap-1 connection respectively), so no
reordering or congestion-cost tweak could ever improve them — there's
nothing to reroute to. Only `circular_loop` has zero margin (15 = 15);
worth revisiting only if more breathing room is wanted, not required.

**Drone-ordering / local-search bonus layer confirmed as a genuine
no-op on this project, independently re-tested.** `plan_all_paths`
processes homogeneous drones (all `start`→`goal`), so reordering only
relabels which id gets which already-committed path; the path *set*
and resulting makespan are invariant. This is an empirical finding over
this project's actual maps, not a universal theorem — re-check if the
grader ships additional maps with heterogeneous start/end zones.

**Congestion-cost formula confirmed to earn nothing on any tested map**
(quadratic BPR term swept across ε ∈ {0.1, 0.2, 0.5, 0.9}, all 13 maps,
zero makespan change). Mechanistic reason, directly checkable against
`make_single_path`'s own cost accumulation
(`cost + (arrival_turn - depart_turn)`): congestion is already priced
implicitly, since any capacity-driven delay directly increases path
cost, so the Dijkstra search already avoids congested routes on its
own. The soft formula only breaks near-ties the hard timing has already
decided. **Likely droppable scope** — not proven impossible to matter
on some hypothetical map, but worth nothing on the actual benchmark set.

**Caveat carried forward, worth remembering before final submission:**
42 review is adversarial — before relying on "43 beats the 45-turn
record" as a bonus-point claim, re-run the from-scratch validator
against the challenger schedule one more time close to submission, as
a final sanity check, not just trusting this cross-check from earlier
in the project.

## Updated priority order for remaining work — algorithm design is
## effectively done; what's left is engineering, not design

Given the above, the congestion-cost formula and drone-ordering layer
are both being dropped from the priority list (kept only as "if time
permits" ideas, not required work). The real remaining work, in order:

1. Wire `plan_all_paths` into `Engine.__init__` (`simulation.py`) —
   build a `Scheduler`, call `plan_all_paths` once, store the resulting
   per-drone schedules for `run()` to consume.
2. Rewrite `Engine.run()` as pure turn-indexed playback over the stored
   schedule — replace the commented-out naive placeholder (lines
   ~39-54, still referencing the deleted `find_path`), calling the real
   state-mutation methods (`Zone.increase_drone_count`/
   `decrease_drone_count`, `ZoneConnection.increase_occupancy`/
   `decrease_occupancy`, `Drone.set_to_restricted`/`update_status`/
   `increase_move_count`) that are currently defined but never invoked
   anywhere in the project.
3. VII.5 printed output — one line per turn, space-separated
   `D<ID>-<connection>`, using the direction-of-travel string decision
   already locked in on 07-22 (computed once at departure, reused
   unchanged for both turns of a restricted transit). Depends on #2.
4. Re-verify the visualizer actually still works turn-by-turn against
   real (not placeholder) positions once #2/#3 land — don't assume
   unchanged just because it worked against the naive loop.
5. Docstrings for `simulation.py`/`pathfinder.py` (#22); remove the
   debug `print()` in `drone.py` (#26); resolve `Drone.drone_id`/
   `total_move_count` usage (#29) — all naturally fall out once
   playback exists.
6. `README.md` per Chapter VIII (#32) — now unblocked, since the
   algorithm and its benchmark results exist to write up.
7. Rename `is_reachable` → `_is_reachable` (user's own, not Claude's);
   split `pathfinder.py` into a package (#35) once the above stabilizes.

## Superseded: original task-list bullets below (kept for history,
## see resolution above)

- **Fix the same-turn vacate/arrive capacity gap** described just above
  — `Scheduler`'s reservation model needs to net departures against
  arrivals within a turn, not just count raw arrival-turn reservations,
  to fully match VII.3's stated rule.

  **A first attempt (2026-07-23, same-day morning follow-up) was tried
  and reverted — don't repeat this approach.** Added a `zone_departs`
  table
  (`dict[str, dict[int, int]]`), incremented it in `try_reserve_move`
  at the origin/`depart_turn_nb`, and changed both `_check_move` and
  `can_reserve_wait`'s capacity checks to
  `dest_reserved - departing >= capacity`. This passed the original
  isolated unit test (same-turn vacate/arrive worked), but **broke real
  correctness**: re-running the from-scratch validator against all 13
  maps produced genuine capacity violations (e.g. `bottleneck` at 4
  drones against a cap of 2, `maze_a2` at 3 against a cap of 1) that
  didn't exist before the change. Root cause: the netting subtracts an
  *aggregate* departure count from an *aggregate* arrival count for a
  zone/turn, with no way to tie a specific departure to a specific
  freed slot. A drone that arrives and instantly departs the same turn
  (pass-through, capacity 1) nets its own presence to zero — which
  correctly lets a *replacement* drone in, but incorrectly also reads
  as "zone has room" to any *unrelated* drone wanting that same turn,
  even though the zone can still only physically hold one drone at a
  time. **Reverted in full** — `zone_departs` removed, `_check_move`/
  `can_reserve_wait` back to arrivals-only checks, reconfirmed clean
  against flake8/mypy/the full validator.

  **Likely correct direction for next attempt:** this is a commit-time
  structural issue, not a check-time counter issue. `plan_all_paths`
  already knows a drone's entire finished path before it commits any
  reservations — so the fix probably belongs in *which turns get
  reserved at all* when committing a path, not in netting two counters
  after the fact. Specifically: a drone's *last* turn of presence in a
  zone (the turn used as its own `depart_turn_nb` for the next hop)
  probably shouldn't be reserved as "occupying" in the first place —
  matching the half-open `[depart_turn_nb, arrival_turn)` convention
  connection reservations already use correctly (a connection is never
  considered occupied at its own arrival turn). Worth designing this
  properly with more time before attempting again, not as a quick
  patch.
- **Wire `plan_all_paths` into `Engine`'s setup** (`simulation.py`) —
  `Engine.__init__` needs to build a `Scheduler` and call
  `plan_all_paths` once, storing the resulting per-drone schedules for
  `run()` to consume. Not started.
- **Rewrite `Engine.run()` as pure turn-indexed playback** — replace the
  commented-out naive placeholder (lines 39-54, still referencing the
  now-deleted `find_path`) with a loop over turns 1→makespan, applying
  each drone's precomputed schedule, calling the real state-mutation
  methods (`Zone.increase_drone_count`/`decrease_drone_count`,
  `ZoneConnection.increase_occupancy`/`decrease_occupancy`,
  `Drone.set_to_restricted`/`update_status`/`increase_move_count`) that
  are currently defined but never invoked anywhere in the project.
- **Printed output per VII.5 format** — one line per turn, listing every
  drone that moved that turn, space-separated, using the
  direction-of-travel connection string decision already locked in
  above (`D<ID>-<connection>` computed once at departure, reused
  unchanged for both turns of a restricted transit). Not started —
  depends on the `Engine.run()` rewrite above.
- **Check the visualizer still lines up with the new scheduling model**
  once `Engine.run()` is rewritten — `render_frame()`/`clock.tick()`
  cadence, drone dot rendering, and the mouseover/popup info should all
  still work turn-by-turn against real (not placeholder) drone
  positions, but this needs to be actually re-verified visually once
  playback is wired up, not assumed to still work unchanged just
  because it worked against the naive loop.
- **Congestion-cost formula** — design settled in the section above from
  the prior session, still not implemented/wired into
  `make_single_path`'s cost calculations (flat costs only right now: 1
  normal/priority, 2 restricted, 1 wait, no congestion term at all).
- **Drone-ordering/local-search bonus layer** — still deliberately
  deferred, unchanged from before.
- **Task #35 (split `pathfinder.py` into a package)** — deferred until
  the above stabilizes; remember the `_is_reachable` privacy dependency
  noted above when this happens.
