# Tool-using geometry/rig generator pilot v5 — 2026-11-08

**Geometry generation, rig adaptation and unseen-asset execution work. The first
and final generators both pass all four transfer cases, so this declared family
still saturates. No transfer improvement or RSI gain was observed.**

This is a completed short development study, not an accepted task, official
reward, Harbor validation or official RSI-Harness trajectory. The experiment's
frozen implementation is commit `118e72f`; complete source/input hashes are in
the [derived record](recorded.json). Earlier studies remain archived separately.

## What changed in this study

The candidate is **executable reusable Python**, not a list of poses or routes.
It receives a source mesh/rig and a new scene specification and writes actual
mesh vertices/triangles and an adapted rig. Chassis and drawers deform, rigid
wheels/casters/holders keep their dimensions, drawer capacity must remain at
least 95%, and attachment pivots, seating and drawer stroke must remain usable.
Fixed motion probes test generated geometry and rig together.

The research agent received three development scenes on one 13-part trolley.
Four transfer cases were withheld until its code and native episode were frozen:
two new requirements on that trolley and two on an unseen 3-part cabinet.
The cabinet's delivered closed-rest contact requires permissible seating repair;
the source geometry was not manually pre-repaired for the model. Neither the
cabinet input nor transfer fixtures were in the agent's public-only workspace.

## Preregistered first-versus-final comparison

| Frozen generator | Dev scenes | New trolley scenes | Unseen cabinet scenes | Primary transfer fraction |
|---|---:|---:|---:|---:|
| First scorable development-submitted program | 3/3 | 2/2 | 2/2 | **4/4 = 1.0** |
| Final program | 3/3 | 2/2 | 2/2 | **4/4 = 1.0** |

The primary difference is **0**. These are the same four cases tested on two
snapshots, not eight independent test examples. There were no invalid or timeout
outcomes in the primary transfer evaluations. The final dev check reused the
authoritative submission with an identical code hash; it is not a new replicate.

The first and final code hashes differ, but both produce effectively identical
chassis scales on these cases. The capacity ratios are approximately **0.950002**
in every case. Wheels, caster forks and holders retain rigid geometry; the
registered pivots and scaled drawer strokes pass the fixed checks.

| Transfer case | Final chassis scale X / Y / Z | Checked motion frames | Result |
|---|---|---:|---|
| Trolley A | 0.89172 / 1.14696 / 0.92885 | 2,738 | pass |
| Trolley B | 0.98172 / 1.18176 / 0.81885 | 2,754 | pass |
| Cabinet A | 0.94260 / 1.05414 / 0.95609 | 429 | pass |
| Cabinet B | 0.96260 / 1.11379 / 0.88609 | 453 | pass |

## Actual research-agent execution

One fresh **tool-using Codex gpt-6-astra/max** episode completed normally in
**740.255 seconds** within its 900-second cap. It made **24 completed shell
commands**, **2 file-change operations** and **2 authoritative development
submissions** out of six permitted. The first and second dev submissions both
passed all three scenes. The agent also ran its own local robustness tests;
these are not additional held-out observations.

The agent could inspect public source geometry, use NumPy/FCL and modify its
generator. An OS-enforced permission profile denied other project files and
network access and kept SDK, source inputs and feedback responses read-only.
Both an independent preflight and the agent's actual first tool check passed.
A code-only development broker evaluated fixed dev scenes; it never returned
transfer inputs or feedback. Its authoritative snapshots and feedback are
preserved outside the agent's writable workspace.

Every generated candidate ran in a fresh **networkless Linux ARM64 container**,
2 CPUs, 3 GiB, 30-second cap, no host mounts, reduced privileges and bounded
outputs. The final image ID is recorded. Generation used Python 3.12 and pinned
NumPy 2.4.4, SciPy 1.17.1 and python-fcl 0.7.0.11. Physics/shape checking ran
on the Mac CPU; hosted model inference did not run on laptop GPU hardware.

The complete original fresh native session, tool-event stream, every submitted
program, per-case generated mesh/rig and evaluation logs remain in ignored local
`runs/v5-agent-001/`, with a SHA-256 inventory. Public records contain hashes,
programs and derived measurements, not the private operator conversation.

## Feasibility, failure controls and asset delivery

Before the model ran, developer witnesses passed all **7** dev/transfer fixtures.
Identity/no-adaptation, universal shrinking, capacity loss and stale-rig controls
failed. The first generated program is the actual model baseline; a deliberately
weak developer control is not substituted for it.

The final generated trolley and cabinet were exported locally as GLBs with their
**actual parent/child joint hierarchies**, local pivot frames and two test clips.
Godot 4.7.2 verifies all hierarchy edges, counts and sampled node transforms:

| Generated asset | Parts | Triangles | Joint edges | Transform checks |
|---|---:|---:|---:|---:|
| Trolley A | 13 | 81,254 | 12 | 78/78 pass |
| Cabinet A | 3 | 1,052 | 2 | 15/15 pass |

The cabinet transport clip is a static envelope check because it has no wheels;
its interaction clip opens/closes both drawers. GLB previews retain neutral
collision-mesh appearance, not newly synthesized textures. Raw mesh derivatives
stay local. The exporter independently verifies serialized vertex/index arrays;
Godot verifies hierarchy and animated transforms.

## Interpretation and limits

This confirms that a strong model can write a generic geometry/rig adaptation
program that transfers to these new constraints and source geometry. It does
not show recursive improvement: both snapshots already achieve the ceiling.

The allowed design space is still small: three chassis scales, affine-derived
attachment displacements and bounded seating repairs, with semantic roles and
the original joint tree supplied. A general geometric solver can cover the
family quickly. The current results suggest that adding more affine instances
alone is unlikely to produce sufficient research headroom; this is an inference
from a small pilot, not a claim about unrestricted 3D generation.

No new topology, joint-tree discovery, retopology, textures, grasping, rigid-body
forces or broad game-level transfer were tested. Adjacent rotational bearing
pairs are excluded from sampled self-collision, and sampled tests are not a
continuous-collision proof. The source meshes are existing public assets. The
capacity measurement is exact for the declared affine cavity deformation;
it is not a fluid or payload simulation.

**Do not start a long run on this saturated family.** The next candidate direction
is topology/LOD and collision-proxy co-generation with fixed functional/fidelity
constraints; it needs its own feasible witnesses, novelty check and frozen strong
baseline calibration. See [NEXT.md](NEXT.md). That future task is not claimed to
be implemented or validated here.

## Reproduce offline

Use Python 3.12 with `study-v3/requirements.txt`, then:

```sh
python tools/fetch_screening_assets.py
python study-v5/prepare.py
python tools/replay_geometry_v5.py --out runs/v5-replay-new --export-example
/absolute/path/to/godot --headless --path runtime --script res://inspect_geometry_v5.gd -- /absolute/path/to/runs/v5-replay-new/export/roundtrip-job.json
```

Normalization is write-once; skip prepare.py if the verified inputs already exist.
The replay reconstructs measured affine outputs from fetched source geometry and
the recorded rig and repeats the real CPU evaluator. It executes neither the
submitted program nor live model calls. Original output archives are separately
hash-recorded; the reconstruction residual is verified below 1e-8 m.

To reproduce **generation**, build `environment/Dockerfile` as
`openrsi-asset-blender:pilot-v0`, download the pinned Linux CPython-3.12 wheels
and pip 25.0.1 into a build context's `wheels/`, and build the v5 Dockerfile as
`openrsi-asset-generator:v5`. It supports the existing CPU Docker VM; the exact
local image ID is recorded rather than claiming a published immutable registry
image. Official Harbor packaging and reproducible image distribution remain
pending. Set `ASSET_DOCKER_HOST` when using a non-default Docker socket.

A new live episode uses an authenticated Codex CLI, a Mac public-only workspace,
the v5 image and passing controls:

```sh
python study-v5/controls.py runs/v5-controls-new
python study-v5/agent.py runs/v5-agent-new --controls runs/v5-controls-new
```

After this episode, a defensive runtime-path portability guard was added. The
recorded Mac permission configuration remains byte-identical; no metric, fixture,
input or generation rule changed. Linux agent isolation is not claimed validated
by offline Linux scoring CI.

Sources: [pinned public mesh manifest](../study-v3/sources.json),
[prospective protocol](PROTOCOL.md), [generator interface](TASK.md),
[first program](generators/first.py), [final program](generators/final.py).
No private company source, reports, assets or credentials were used.
