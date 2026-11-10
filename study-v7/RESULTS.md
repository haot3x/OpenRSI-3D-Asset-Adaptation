# v7: a complete-asset compiler still saturates in a short calibration

**The expanded prototype is runnable, but it is not ready for a 12-hour research
run.** Codex/Astra max reached full development score on its second submission.
Its actual final program also scores **1.0 on all nine withheld transfer
configurations**. The low initial score came from a starter's triangle-budget
violations; it is not evidence of sustained research difficulty.

## Frozen experiment

One fresh tool-using Codex **gpt-6-astra / max** episode ran for **1,686.401
seconds** (28.1 minutes), with a 1,800-second cap, six of eight allowed
development submissions, 49 completed commands and 14 file-change events.
It finished normally. There was no operator feedback, rule adjustment or
automatic model retry during the episode. Experiment source:
[`9b2c8f0`](https://github.com/haot3x/OpenRSI-3D-Asset-Adaptation/tree/9b2c8f0b3a13c4e838f7041177199878bf97f3d4).

The subject improved one reusable program producing changed visual topology
and compound convex proxies for **complete moving assemblies**, preserving the
supplied rig, required parts and motion. It received the strongest preserved
v6 proxy algorithm plus the hardened component-aware QEM/Blender starter.
Generation used fresh networkless, mount-free Linux ARM64 containers with
**2 CPUs / 3 GiB**, no GPU and a 90-second per-asset limit. Final transfer
generation wall times, including container handling, were **6.923–9.159 s**.

The six original procedural mechanism families have 30 parts in total. Three
families were available for development; three were withheld until the first
and actual final programs were frozen. Each family has three camera/resource
profiles. These are six constructed archetypes, **not 18 independent real-world
assets**, and the profiles do not measure actual device frame rates.

## Results

| Outcome | First submitted program | Actual final program |
|---|---:|---:|
| Development: three standard configurations | 0.000000 | 1.000000 |
| Transfer: nine configurations, balanced across three families | 0.333333 | 1.000000 |
| Final-program development retention | — | 1.000000 |

Development submission scores were **0, 1, 1, 1, 1, 1**. The first program was
the supplied starter; its three development zeros were valid triangle-budget
failures, not process errors. The final program is submission six, selected by
the subject before transfer feedback. No intermediate program was chosen by
test score. Every transfer case was scored; no failed case was omitted.

| Withheld family | First mean across profiles | Final mean across profiles |
|---|---:|---:|
| Telescoping platform | 0.0 | 1.0 |
| Inspection lamp | 0.0 | 1.0 |
| Supply chest | 1.0 | 1.0 |

The final program recovers concave extrusion contours, simplifies them by
geometric error, partitions caps into convex solids and allocates visual and
proxy resources globally. It also retains general curved-component fallbacks.
It contains no branches for the named benchmark families. This is a useful
general compiler improvement, but the repeated extrusion/sweep structure is
still easy for a strong agent to cover with one reusable method.

## Verification and preserved evidence

All **18 constructive reference configurations** score 1 under the same rules.
Controls reject no-LOD, empty collision geometry, filled apertures, stale rigs,
disabled motion and inverted winding. Separate controls verify solid
containment, planar-proxy rejection and a collision during a sweep whose
endpoints are clear. These are developer feasibility checks, not model results.

All **21 exact frozen outputs**—nine first, nine final and three final-development
outputs—were rescored on Linux ARM64. Their scores match the original Mac
measurements exactly; discrete outcomes/counts match, with tiny tolerances only
for geometric floating-point diagnostics. No generated Python is executed by
this replay. The original data, cached probes and outputs are hash-checked.

The final program's actual service cart also passes **60 GLB hierarchy/animation
transform checks** in Godot 4.7.2 and **3,456 convex sphere queries** with zero
analytic mismatches. Queries cover three registered rig states, each under two
body transforms. Parts are queried separately; whole-assembly sampled clearance
is checked by FCL. These query/transform counts are diagnostics, not independent
benchmark examples or dynamics/stability tests. The visual GLB does not embed
the collision proxies.

The exact fresh native session and **562 original files** were verified against
their SHA-256 inventory. Original native logs remain local; this public release
contains programs, frozen original geometry and derived measurements. It does
not publish the operator conversation and is not an official proposal-agent or
12-hour runner trajectory. See [recorded.json](recorded.json),
[verification.json](verification.json), [PROTOCOL.md](PROTOCOL.md) and
[the programs](generators/).

```sh
python -m pip install -r study-v7/requirements.txt
python tools/replay_compiled_v7.py study-v7/recorded.json --out runs/v7-replay
```

## Consequence for the broader task

Do **not** spend two or twelve hours on this frozen subset as a difficulty
validation. Preserve the result and reuse its compiler in the next stage.
The planned substantive expansion is **module selection, assembly/joint-graph
generation and operation scheduling under conflicting game-scene requirements**:
transport through a doorway/aisle, unfold in a constrained workspace, and retain
usable storage, support and interaction surfaces under shared budgets.

That expanded stage is not implemented or difficulty-validated by this study.
It needs feasible references and failure controls, then a new strong-model
preflight and a two-hour stress calibration before an official long run.
This pilot retains the provided graph/part count and does not evaluate new
assembly synthesis, textures/materials, live gameplay or force dynamics.
