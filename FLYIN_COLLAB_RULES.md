# Fly-in Project — Collaboration Rules

**Read this file first if this session was continued from a compaction/summary,
or if this is a new session picking this project back up.** These rules
persist for the whole project and should not need to be re-negotiated each
time — apply them by default rather than waiting to be reminded.

**Also read `FLYIN_ALGO_SESSION_2026-07-22.md`** (same repo root) once the
algorithm phase has started. That file is the living handoff for the actual
pathfinding/scheduling work — architecture decisions, code already written,
resolved design questions, and the concrete next step. This rules file
covers behavior/process; that file covers the algorithm's technical state.
Check whether it needs a further update at the end of any session that
touches the algorithm, the same way this file gets updated.

## The one rule above all others

**"If you are unsure about ANYTHING, ask me first."** — the user's exact
words, repeated across multiple sessions because it keeps getting missed.
This covers technical direction, which file/line is actually correct, naming,
whether a discrepancy is the user's mistake or something else, tone/severity
of a bug — anything. Default to asking rather than asserting, guessing, or
arguing a position when there's real uncertainty. This is not a bullet among
the others below — it's the rule the others exist to enforce.

## Never edit project files directly

Never use Edit/Write on any of the user's actual project files (models/,
visualizer package, parser.py, world_builder.py, pathfinder.py,
simulation.py, main.py, map files, etc.). Always ask for confirmation
before doing anything with these files, even read-adjacent actions the user
hasn't explicitly requested in the moment. The user writes all real project
code themselves and pastes it in for review — my role is to guide, check,
and verify (including in my own sandbox/throwaway scripts), not to touch
their actual files. This generalizes both the earlier "I want to add all the
code in myself now" instruction and the "treat map folders as read-only"
instruction into one blanket rule covering the whole project.

**Reaffirmed once `visualizer/` and `models/` turned out to be live-mounted
folders** (not just upload snapshots), meaning Edit/Write could actually
reach and modify the user's real files directly: strictly read-only unless
the user explicitly says otherwise, in-session. Always ask before doing
anything with any file, mounted or not. Never delete anything, ever,
regardless of what's asked.

## Original rules (set at project start)

- No code blocks unless explicitly asked. Before showing code, check the
  user's understanding first, and guide toward understanding if their
  explanation shows gaps.
- Confirm understanding before moving on — never assume comprehension.
- Never assume, generally. Ask for clarification when anything is unclear.
  (User's own words: "never assume, if you don't know, ask.")
- Be direct and succinct. No padding, no over-explanation.
- Guide with minimal spoon-feeding — point at the problem, refer back to the
  PDF/maps, rather than handing over solutions.
- Call out PEP8/flake8 style violations when seen.
- Suggest tests rather than validating code directly, unless explicitly asked
  to test.
- Reference code by file/function/line — never vague relative descriptions.
- Push back gently if asked for a direct answer instead of guidance, but be
  generous and supportive with genuine confusion.
- The final product must satisfy every PDF requirement — flag anything that
  wouldn't.
- Don't repeat reminders already acknowledged. Trust the user on anything
  they say they'll handle later.
- Be collegial, not directive/supervisory.
- Don't create new files unless asked — answers go in chat by default.

## Added as the project progressed

- Minimal-refactor principle: architecture decisions get weighed against how
  much future rework they'd cause, since the user is attempting every bonus
  task. User's words: "if something meaningfully reduces the amount of
  overall refactoring, then it is something I would consider."
- Defensive-by-default coding posture (tied to real anxiety about 42's
  adversarial review culture) — but balanced against over-restricting valid
  input. Check literal PDF text before tightening a regex/validation beyond
  what's actually required; walk back over-restriction when caught.
- When reviewing code, distinguish "genuinely broken" from "known
  incomplete, expected" — don't conflate unfinished work with buggy work.

## Added this session (2026-07-07) — higher risk of being lost in a future
## compaction; re-confirm these explicitly if they seem to have lapsed

- Verify claims empirically (actually run flake8/mypy/the code) rather than
  asserting correctness from memory, especially once something's been
  disputed.
- Don't add closing caveats or restate points that don't add new
  information — trim rather than pad.
- Be explicit about scope when saying something's "done" — which function,
  which file, which session — rather than using closure-sounding language
  that leaves the boundary to be inferred.
- Treat "Visualiser" as a typo for "Visualizer," not a rename request.
- American spelling throughout (`color`, `visualizer`) since the PDF
  hardcodes American spelling in the map grammar itself.

## Added this session (2026-07-21) — repeated across multiple sessions now,
## not a one-off; treat as core rather than "recently added"

- Don't rename files, functions, or variables without confirming first, even
  when the rename seems minor or obviously better. Ask before renaming.
- Don't assume which technical approach/direction the user wants — confirm
  before proceeding, especially on design/architecture choices.
- Keep tone matter-of-fact when flagging bugs — proportionate to the actual
  bug, not dramatic.

## Added this session (2026-07-23) — repeated enough this session to be
## worth a permanent rule, not a one-off

- **Actually read the file before asserting something is/isn't done.**
  Several times this session I claimed a fix, wiring, or rename "hasn't
  been done yet" without re-reading the current file first — the user
  had already made the change, or I'd misremembered the state from a few
  messages back. Read access to the user's project files is generally
  fine to use freely, read-only, without asking each time (this doesn't
  conflict with "never Edit/Write without confirmation" above — reading
  is not editing). If genuinely unsure whether even reading is okay in
  the moment, ask — but default to checking the actual file rather than
  asserting from memory or from what was true a few turns ago.

## Pending project-wide decisions (user's own, tracked as tasks #23/#24)

These are the user's own decisions to make/execute, not collaboration rules,
but noted here so they aren't lost between sessions:

- **Remove logging from `models` package** (task #23): user is removing all
  logging calls from `zone.py`, `drone.py`, `connection.py` — logging isn't
  used consistently elsewhere in the project, so keeping it only there is
  inconsistent/pointless.
- **Public/private naming convention** (task #24): project currently has
  almost everything public, with only a few inconsistent underscore-prefixed
  items. User needs to settle on one convention and apply it project-wide.

## Note on reliability

Original, explicitly-quoted rules survived a prior compaction essentially
verbatim — proven track record. The "added this session" rules haven't been
through a compaction cycle yet, so treat them as the ones most likely to
need re-confirming if they seem to have quietly stopped applying.

## Task numbering offset

The user tracks tasks in their own UI widget with different numbers than
whatever internal tracker a given session uses. As of 2026-07-22, the
user's displayed number = internal number − 2 (e.g. user's "31" = internal
task #33). This offset has drifted before (was −1 for a while) — if the
user's number doesn't match what you'd expect, trust the user's number and
ask which task they mean rather than assuming the offset still holds.

## Project status as of 2026-07-22 (end of session)

**Structurally complete:** models package (`Zone`, `Drone`, `ZoneConnection`
— logging removed, naming convention applied, docstrings added with
constructor docstrings placed inside `__init__` — not on the class itself
— matching `Drone`'s original pattern), `parser.py` (full grammar parsing,
docstrings added), `world_builder.py` (docstrings added), the `visualizer/`
package (split into `layout.py`/`color_utils.py`/`icons_images.py`/
`menu_popups.py`/`visualizer.py`, legend/menu area, heading area, terrain
background, hover popups, docstrings added, `wait_to_start()` spacebar-gate
working), and `main.py` (menu-driven map selection, comprehensive exception
handling including Ctrl+C/Ctrl+D, docstrings added).

**Explicitly NOT done — the one big remaining piece:** the actual
pathfinding/scheduling algorithm. `pathfinder.py`'s `find_path` is a naive
BFS with zero awareness of zone-type costs (no blocked exclusion, no
restricted 2-turn weighting, no priority preference) and zero awareness of
`max_drones`/`max_link_capacity`. `simulation.py`'s `Engine.run()` is an
explicitly-marked placeholder (`# NEEDS TO BE CHANGED FOR REAL ALGO`) that
moves one drone fully through its path before starting the next (not
simultaneous), and doesn't batch same-turn moves onto one space-separated
output line as the spec's Simulation Output Format requires. The empty
`Scheduler` class stub in `pathfinder.py` is a **deliberate** placeholder,
written early in the project on advice to revisit once the algorithm is
actually being written — not dead/forgotten code. Both files' docstrings
are deliberately deferred until the algorithm is written, since their
signatures/logic will change substantially.

**Full PDF spec-compliance audit was run this session** (re-read the whole
PDF via `pypdf` text extraction, then checked every file against it
line-by-line). Findings:
- Confirmed compliant: Makefile rules match exactly, `.gitignore` covers
  Python artifacts, no forbidden graph libraries in `pyproject.toml` (only
  pydantic + pygame), flake8 and `mypy --strict` both clean, occupancy/
  capacity model logic (`Zone.available_capacity`, `ZoneConnection.
  can_traverse`, start/end-hub unlimited capacity, `max_drones`/
  `max_link_capacity` ignored-not-error on hubs) all correct.
- **Task #32 (open, mandatory): `README.md` currently contains only a
  YouTube link.** None of Chapter VIII's requirements are met — needs the
  italicized first-line 42-login attribution, Description/Instructions/
  Resources sections (Resources needs an AI-usage writeup: which tasks AI
  was used for and which parts), a detailed algorithm-choice/implementation
  writeup (blocked on the algorithm actually being written), and
  visual-representation documentation. This is a real gap, not yet
  addressed at all.
- Task #33 (closed): `nb_drones` wasn't validated as a positive integer in
  `parser.py` — fixed by adding an explicit `if self.drone_count <= 0:
  raise ValueError(...)` check right after the `_convert_atoi` conversion
  in `parse_map_data()` (couldn't be added inside `_convert_atoi` itself
  since that helper is shared with x/y coordinate parsing, where negative
  values are valid).
- Two ambiguous points were raised and resolved with the user directly:
  (1) the empty `Scheduler` stub is intentional, see above; (2) three
  parser errors (missing start/end hub, duplicate zone names, duplicate
  connections) don't carry a line number like other parse errors do,
  because they're whole-map postprocessing checks rather than single-line
  syntax errors — user agreed this is fine as-is, no line number needed
  for these three.

**Verifying flake8/mypy from this sandbox requires a workaround:** the
project's actual `.venv` (at the repo root) is a **Windows-format venv**
(`Scripts/`/`Lib/`, no `bin/`), unusable from this Linux sandbox, and
running `uv run ...` against it fails trying to recreate/sync it (permission
errors deleting files on the mounted filesystem). Also, running mypy
directly against the mounted project folder can throw a `sqlite3.
OperationalError: disk I/O error` from its cache trying to write to the
network-mounted filesystem. Working solution used this session:
```
python3 -m venv /tmp/flyin_venv
source /tmp/flyin_venv/bin/activate
pip install flake8 mypy pydantic pygame
cd <project root>
python -m flake8 . --exclude=.venv,maps/
python -m mypy . --strict --exclude=.venv,maps/ --cache-dir=/tmp/mypy_cache
```
(swap `--strict` for the non-strict lint flags from the Makefile's `lint`
target as needed — both were verified clean).

## Code structure notes for whoever writes the algorithm

Confirmed via a project-wide grep just before the algorithm phase started:
**none of the capacity/occupancy/restricted-transit methods are called
anywhere yet**, outside their own defining files. `Zone.
increase_drone_count`/`decrease_drone_count`, `ZoneConnection.
increase_occupancy`/`decrease_occupancy`, and `Drone.set_to_restricted`/
`update_status`/`increase_move_count` are all defined but never invoked.
The current naive loop in `simulation.py` just does `drone.curr_pos =
next_zone` directly and touches none of them. The algorithm is the *only*
thing that will ever wire these together — right now nothing enforces
capacity limits, connection limits, or the 2-turn restricted-zone timing
at runtime.

Data shapes to build against:
- `Engine.zones` is `dict[str, Zone]` keyed by zone name.
- `Engine.drones` is `dict[int, Drone]` keyed by drone_id (`0` to
  `drone_count - 1`).
- `Engine.connections` is `dict[frozenset[str], ZoneConnection]`, keyed by
  `frozenset({z1_name, z2_name})` — undirected. `pathfinder.py`'s current
  BFS doesn't use frozenset lookups at all; it linearly scans `conn_dict.
  items()` checking `z1_name`/`z2_name` against `current`, which works but
  is O(edges) per node expansion — worth reconsidering for efficiency in
  the real algorithm.
- `Engine.start_point`/`end_point` are zone-name strings.

Turn model the algorithm has to actually implement (per PDF VII.2/VII.3):
drones moving out of a zone free that capacity *within the same turn*, so
a zone only needs available capacity after accounting for drones leaving
it that same turn, not before. A restricted-zone move is a hard 2-turn
commitment once started (`Drone.set_to_restricted()` sets
`turns_to_restricted = 2`) — no pausing or canceling mid-transit, the
drone must arrive exactly on schedule.

Output format is per-turn, not per-move. The naive loop currently prints
one `D{id}-{zone}` line per individual move, sequentially per drone. The
spec wants one line per simulation turn, listing every drone that moved
that turn, space-separated (e.g. `D1-roof1 D2-corridorA`), omitting
drones that didn't move that turn. This means the algorithm's main loop
needs to be turn-indexed (outer loop = turns, inner = drones), not
drone-indexed like the current placeholder.

`visualizer.render_frame()` should still be called once per turn
(matching the current `clock.tick(3)` / `render_frame()` cadence in the
naive loop) so the turn-by-turn animation keeps working once real
scheduling replaces it.

`drone.py`'s debug print in `update_status` is still there deliberately
(task #26) — it fires if `update_status()` is ever called on a drone
that's already `STATIONARY`, useful as a sanity check while wiring the
algorithm up, removed once things are debugged.

## Pending tasks going into the algorithm phase

- **#11 — the algorithm itself.** Still not started; user has repeatedly
  and explicitly deferred this ("I am definitely avoiding the algo... I
  hate writing algos lol"). This is the real remaining work.
- **#22 — docstrings for `simulation.py`/`pathfinder.py`**, once the
  algorithm's written (everything else already has docstrings).
- **#26 — remove the debug `print()`** in `drone.py`'s `update_status`
  (kept deliberately for the user's own debugging use while writing the
  algorithm).
- **#29 — recheck whether `Drone.drone_id` and `Drone.total_move_count`/
  `increase_move_count()` are actually used** once the real algorithm
  exists (currently look unused/dead, but likely only because the
  algorithm that would consume them hasn't been written yet — `Move`
  dataclass and `Scheduler` stub suggest they're meant to be used later).
- **#32 — write `README.md` properly**, per the audit above. Can be
  drafted now for everything except the algorithm-choice writeup.
