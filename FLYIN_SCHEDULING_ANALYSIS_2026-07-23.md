# Fly-in — Scheduling Analysis & Benchmark Findings (2026-07-23, Cowork session)

Read alongside `FLYIN_COLLAB_RULES.md` and `FLYIN_ALGO_SESSION_2026-07-22.md`.
This file is a handoff of the **analysis** done this session. No project files were
edited — everything below was produced in a throwaway sandbox that imports and calls
the real `parser.py` / `world_builder.py` / `pathfinder.py`, so the numbers are this
codebase's actual output, not a reimplementation.

The headline: the current (reverted, flat-cost) algorithm already clears **every**
VII.7 benchmark and **beats the optional challenger reference record (43 < 45)**. The
one open "scheduling bug" turned out not to be a bug. Details below.

---

## 1. The "same-turn vacate/arrive" gap is NOT a bug — recommend closing the task

The task carried over from the 07-23 sessions (netting departures against arrivals so a
drone can arrive at a zone the same turn another leaves) was chased twice and reverted
twice. With the PDF now in hand, the exact spec text settles it:

- **VII.2:** *"Two drones may not enter the same zone on the same turn unless the zone's
  capacity allows it."* and *"A drone may not move into a zone that would exceed its
  maximum capacity."*
- **VII.3:** *"Drones moving out of a zone free up capacity for that same turn."* and
  *"A zone must have available capacity for a drone to move into it (after all drones
  moving out have freed up space)."*

**Why it's not a bug.** A drone that arrives at zone `X` at turn `t` is *present in the
turn-`t` configuration* — it does not leave until the `t → t+1` transition. So "a second
drone also arrives at `X` at turn `t`" is literally two drones in the same config, which
VII.2 forbids for a cap-1 zone. The unit test that "surfaced the gap" expected that to be
legal; that expectation contradicts VII.2.

What VII.3's "free up capacity that same turn" actually means is the **pipeline / handoff
across consecutive turns**: no cooldown, the slot is reusable the very next turn after a
drone leaves. The current code already does this. Confirmed against the real `Scheduler`:
after a drone arrives at cap-1 `X` at turn 4 and departs turn 4, a second arrival at
turn 4 is (correctly) rejected, and an arrival at turn 5 is (correctly) allowed.

**The current code == the strict config-snapshot model, exactly.** `zone_reserves[Z][t]`
= number of drones present in `Z` at turn `t`. A drone books its arrival turn plus each
wait turn; its final present-turn genuinely is the departure turn, and it genuinely is in
the zone then. There is no over-conservatism to fix. Relevant code: `pathfinder.py`
`_check_move` (zone check, lines 49–51), `can_reserve_move` (55–67), `try_reserve_move`
(69–95), `can_reserve_wait`/`try_reserve_wait` (97–120).

**Empirical confirmation on the actual maps.** Re-implemented the morning "netting"
model (a `zone_departs` table subtracted from arrivals) and ran both models on six maps:

| map | conservative | netting | netting legal? |
|---|---|---|---|
| linear_path | 4 | 4 | — (identical) |
| simple_fork | 4 | 4 | — (identical) |
| basic_capacity | 4 | **3** | **NO — 4 drones in `bottleneck` (cap 2) at turn 1** |
| shattered_route | 29 | 29 | — (identical) |
| fractured_circuit | 29 | 29 | — (identical) |
| sealed_vault_gauntlet | 19 | 19 | — (identical) |

Netting helped on exactly one map, and that "improvement" is an illegal schedule (real
capacity violation flagged by the from-scratch validator). Conservative `4` is the true
legal optimum for `basic_capacity` (4 drones through a cap-2 gate = two waves). This is
why both prior fixes broke the validator: they permitted something the spec forbids.

**Action:** close the same-turn task as *not-a-bug*. Leave the reservation model as the
reverted version. Do not attempt a third fix.

---

## 2. Drone-ordering is a no-op on this project

`plan_all_paths` processes drones in dict order. Tried 6 shuffled orders on both hard
maps → makespan 29 every time. Reason: the drones are **homogeneous** (all
`start` → `goal`), so reordering them only relabels which id gets which path; the
committed path *set* (and thus makespan) is invariant. Drone-ordering / local-search only
pays off in heterogeneous MAPF (distinct starts/goals), which this problem is not.
**The planned "try N orderings, keep the best" bonus layer buys nothing here.**

---

## 3. Both custom 29-turn results are provably optimal

Each is a perfect gapless pipeline against a single mandatory serial bottleneck with no
parallel route — so neither ordering nor congestion cost can improve them:

- **`shattered_route` (20 drones):** every path to `goal` must pass through `final3`
  (cap 1) — it is the only zone adjacent to `goal` (`express_trap` is blocked). `final3`
  runs at exactly 1 drone/turn for 20 consecutive turns; goal arrivals are
  10, 11, …, 29 with **zero gaps**. Floor = shortest-path(10) + (20 − 1) = **29**.
- **`fractured_circuit` (10 drones):** every path must cross `detour1 → detour2`
  (`short_cut` is blocked). That connection is **restricted** and **link-cap 1**, so each
  transit occupies it for 2 turns → throughput 1 drone per *2* turns. Departures land on
  turns 2, 4, …, 20; goal arrivals on 11, 13, …, 29. Floor = **29**.

A single mandatory resource can't be sped up by rerouting or reordering, because there is
nothing to reroute *to*.

---

## 4. Congestion-cost formula earns nothing on any tested map

Wired a quadratic BPR term `ε·(occupancy/capacity)²` into a sandbox copy of
`make_single_path` and swept `ε ∈ {0.1, 0.2, 0.5, 0.9}` across all 13 maps: **makespan
unchanged everywhere, no violations.** Even purpose-built synthetic maps (parallel
routes, unequal-length routes) showed no benefit unless hard link caps were already
forcing the split.

**Why:** the time-expanded `(zone, turn)` Dijkstra already prices congestion *implicitly*.
When a zone fills, the hard-capacity check in `_check_move` pushes the arrival turn later,
and a later arrival is a higher path cost (`cost += arrival − depart_turn`), so the search
already prefers less-congested / earlier-arriving routes. The soft BPR term only breaks
near-ties that the hard timing has, in practice, already decided.

**Implication:** the congestion-cost formula (designed on the 07-22 train ride) appears
to be **droppable scope** for meeting the targets. Not proven useless on *every*
conceivable map, but it is worth nothing on the actual benchmark set — verify with a
targeted test before investing effort in it.

---

## 5. Benchmark results — all 13 maps, fully validated CLEAN

Full independent validation per schedule: zone capacity per turn, **connection capacity
per turn**, **restricted 2-turn move durations**, no BLOCKED-zone entry, contiguous paths
anchored at `(start, 0)` and ending at the end hub. All 13 pass with zero violations.

| tier | map | drones | makespan | VII.7 target | margin |
|---|---|---|---|---|---|
| easy | 01_linear_path | 2 | 4 | ≤ 6 | pass |
| easy | 02_simple_fork | 4 | 4 | ≤ 8 | pass |
| easy | 03_basic_capacity | 4 | 4 | ≤ 6 | pass |
| medium | 01_dead_end_trap | 5 | 8 | ≤ 12 | pass |
| medium | 02_circular_loop | 6 | **15** | ≤ 15 | **zero margin** |
| medium | 03_priority_puzzle | 5 | 7 | ≤ 12 | pass |
| hard | 01_maze_nightmare | 8 | 13 | ≤ 30 | wide |
| hard | 02_capacity_hell | 12 | 16 | ≤ 35 | wide |
| hard | 03_ultimate_challenge | 15 | 26 | ≤ 45 | wide |
| challenger | 01_the_impossible_dream | 25 | **43** | record 45 | **beats record** |
| custom | 01_shattered_route | 20 | 29 | — | optimal (§3) |
| custom | 02_fractured_circuit | 10 | 29 | — | optimal (§3) |
| custom | 03_sealed_vault_gauntlet | 12 | 19 | — | — |

**The Impossible Dream comes in at 43, under the 45 reference record**, fully valid.

Only `circular_loop` (15 = 15) has zero margin — the single map worth revisiting if you
want breathing room. Everything else clears comfortably.

---

## 6. What this means for the remaining work

The baseline (flat-cost, dict-order, sequential per-drone time-expanded Dijkstra +
reservation tables) appears to **already secure the bonus goal**. So of the deferred
"bonus-chasing" stack:

- **Congestion-cost formula** — no benefit on any tested map (§4). Likely droppable.
- **Drone-ordering / local-search** — no-op for homogeneous drones (§2). Droppable.
- **A\* heuristic upgrade** — still only an efficiency (speed) optimization, never a
  makespan change; optional.

The **real** remaining work is unchanged and is about turning the correct *plan* into a
finished *program* (none of it affects makespan):

1. Wire `plan_all_paths` into `Engine.__init__` (`simulation.py`) — build a `Scheduler`,
   call `plan_all_paths` once, store the per-drone schedules.
2. Rewrite `Engine.run()` as pure turn-indexed playback over the stored schedule, calling
   the real state-mutators (`Zone.increase/decrease_drone_count`,
   `ZoneConnection.increase/decrease_occupancy`,
   `Drone.set_to_restricted`/`update_status`/`increase_move_count`), replacing the
   commented-out naive block (lines ~39–54).
3. VII.5 printed output — one line per turn, space-separated `D<ID>-<connection>`, using
   the direction-of-travel string decided on 07-22 (computed once at departure, reused for
   both turns of a restricted transit).
4. Re-verify the visualizer still lines up turn-by-turn against real (not placeholder)
   positions.
5. Docstrings for `simulation.py` / `pathfinder.py` (#22); remove `drone.py` debug print
   (#26); resolve `drone_id` / `total_move_count` usage (#29) once playback exists.
6. `README.md` per Chapter VIII (#32) — now unblocked, since the algorithm and its
   benchmark results exist to write up.
7. Rename `is_reachable` → `_is_reachable`; split `pathfinder.py` into a package (#35),
   minding the `_is_reachable` privacy note in the 07-22 handoff.

---

## 7. Caveats (read before relying on the above)

- These are **planning-phase** results from `plan_all_paths`. The final printed program
  (steps 1–3 above) doesn't exist yet. The makespan won't change when it's wired up, but
  the deliverable is not done.
- 42 review is adversarial. Before counting on **43 beats 45**, run *your own* from-scratch
  validator (the one referenced in the 07-22 handoff) on the challenger schedule to confirm
  independently. My validator checks zone caps, connection caps, restricted durations,
  blocked-zone avoidance, and contiguity, and reports clean — but a second pair of eyes on
  the record claim is warranted.
- "Congestion cost / ordering are droppable" is an empirical finding over these 13 maps,
  not a theorem for all maps. If the grader ships additional maps, re-run §4/§5 first.

---

## 8. How to reproduce (sandbox)

The project `.venv` at the repo root is a **Windows-format venv** (`Scripts/`/`Lib/`, no
`bin/`) and is unusable from a Linux sandbox. Build a throwaway venv instead:

```
python3 -m venv /tmp/flyin_venv && source /tmp/flyin_venv/bin/activate
pip install pydantic pygame flake8 mypy
```

Then, from the repo root, a harness that imports the real modules:

```python
from parser import Parser
from world_builder import build_zone, build_zone_connection, build_drone
from models.zone import HubRole
from pathfinder import Scheduler, plan_all_paths

p = Parser(path); p.parse_map_data()
zones = {zi.zone_name: build_zone(r, zi) for r, zi in p.zone_list}
conns = {frozenset({c.name1, c.name2}): build_zone_connection(c)
         for c in p.connection_list}
start = next(n for n, z in zones.items() if z.hub_role == HubRole.START)
end   = next(n for n, z in zones.items() if z.hub_role == HubRole.END)
drones = {i: build_drone(i, start, end) for i in range(p.drone_count)}

paths = plan_all_paths(drones, Scheduler(zones, conns), conns, zones)
makespan = max(pth[-1][1] for pth in paths.values())
```

The full validator, netting comparison, ordering test, and congestion sweep used this
same skeleton. Validate a schedule by walking each `(zone, turn)` path: check move
durations (2 if destination is RESTRICTED else 1), connection occupancy over
`[depart, arrival)`, and zone occupancy per turn against `Zone.get_max_capacity()`.
