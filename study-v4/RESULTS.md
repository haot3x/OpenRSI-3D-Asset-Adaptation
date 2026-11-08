# Real-mesh functional-motion calibration v4 — 2026-11-08

**The functional engineering pipeline works on Mac. The first completed Astra
candidate passes all three public scenes, so this workload still saturates and
does not justify a long RSI run.** No research improvement or official acceptance
is claimed. The original immutable real mesh has 13 parts and 81,254 triangles.

## Completed model result

The model generated a shared six-pose bank and three scene-specific motion
programs. The existing mesh, rig, dimensions, scene walls, targets and evaluator
were fixed. The model produced root motion and drawer/holder actuation;
the trusted controller supplied caster steering and wheel-roll channels.

| Scene | Result | Refined motion frames | Evaluation seconds |
|---|---|---:|---:|
| Stockroom: left/right pickup operations, then return stowed | pass | 2,825 | 4.245 |
| L-corridor: turn and deliver using the right drawer | pass | 3,057 | 4.554 |
| Narrow alcove: prepare outside, service inside, release outside | pass | 3,299 | 4.300 |

The development fraction is **3/3 = 1.0**. All 9,181 refined frames were checked
for scene clearance, workspace bounds, ground support and non-excluded sampled
self-collisions. Initial/final states and ordered operation holds also passed.
This is the first completed candidate, with no feedback-repair iteration.

The configuration was hosted Codex `gpt-6-astra`, **max** reasoning, no tools,
one fresh structured-output call with a **600-second cap**, zero automatic
retries. It completed in **200.339 s**, using 18,248 input and 6,086 output tokens
(5,002 reasoning-output tokens). The predeclared ceiling stop skipped the optional
second call. A tool-using research agent was not tested by this probe.

An earlier separate **300-second** run timed out before producing a complete
candidate. It is unscored: there was no evaluator submission and no zero reward.
Both original native sessions, invocation records, frozen source bytes, source
hashes and full model-generated motion frames are preserved locally. The
capacity amendment was recorded before the 600-second invocation. The successful
600-second-cap call is not relabeled as a 300-second experiment, even though its
observed duration was below 300 seconds. No timeout-to-success RSI gain is claimed.

## Controls establish that the evaluator can fail

Controls were validated before any model call and were not shown to the model.

| Developer control | Scenes passing | Intended observation |
|---|---:|---|
| Known feasible full-motion witness | 3/3 | Every scene is solvable |
| Well-formed static no-op | 0/3 | Interaction and travel cannot be omitted |
| Diagonal shortcut through the L-corner | 2/3 | Valid endpoints/events still fail on the intervening sweep |
| Universal deployment carried into the alcove | 2/3 | Reusing the wrong deployment collides with a wall |
| Changed shared left-pickup pose | 1/3 | Previously working scene functions regress |

An attempted scale field is rejected. Native mesh/box controls verify separated
distance, near-but-not-intersecting clearance, intersection, and a mesh enclosed
inside a solid box. Bounding boxes only prune expensive queries; actual FCL mesh
queries decide obstacle collision/clearance. A height-only case was removed
during engineering, before model sampling, because this rig has no height-
changing controls. It would not have provided a meaningful adaptation test.

## A runnable animated game-asset artifact

The unedited model candidate was exported locally as a **7,303,212-byte GLB** with
13 meshes and three named clips. Godot **4.7.2** imported it and checked all 13
node transforms at three sample times in each clip: **117/117 passed**, maximum
matrix-element error **0.00000418** against the source kinematics. The 81,254
triangles and all three clips survived import. Local paths:

```text
runs/v4-capacity-002/attempt-001/candidate.json
runs/v4-capacity-002/attempt-001/*.frames.json
runs/v4-model-export-001/adapted-motion.glb
runs/v4-model-export-001/godot.log
```

The GLB is a behavior-adapted preview of existing collision meshes, not newly
generated mesh geometry, textures or a model-authored rig. Raw third-party mesh
derivatives remain local; CI publishes only derived evaluation/import summaries.

## What these checks do and do not establish

Operations mean reaching declared drawer travel and holder posture at fixed
gameplay checkpoints. Hand reach, object grasping and payload contact are not
simulated. The actor is kinematic: no rigid-body contact forces, friction, tire
slip, motor dynamics or caster-trail dynamics. Ten fixed adjacent rotational
bearing pairs are excluded from self-collision because they intentionally touch;
their penetration is not certified. Other self-collisions are sampled, without a
continuous-collision proof. Fixture and joint details are supplied in the input.

All three scenes are public development fixtures on one supplied rig. No
held-out scenes/assets, independent-vs-reusable method comparison or research
agent's evolving generator was evaluated. The result validates the engineering
checks, not sufficient difficulty, method transfer, RSI gain or long-run readiness.

The next scientific step must go beyond choosing poses and planar waypoints:
evaluate a reusable **geometry/rig/behavior adaptation generator** on fixed
cross-scene functional constraints and held-out asset/scene combinations, using
the intended tool-using agent and matched budgets. Preserve functional part
dimensions/capacity and measure the complete motion after permitted geometry
changes. Calibrate actual headroom before any formal long run. These are design
requirements for the next study, not results already achieved here.

## Reproduce locally without model calls

Use Python 3.12 and the pinned CPU environment from study-v3/requirements.txt:

```sh
.tools/physics-venv/bin/python tools/fetch_screening_assets.py
.tools/physics-venv/bin/python study-v4/controls.py runs/v4-controls-new
.tools/physics-venv/bin/python tools/replay_motion_v4.py --out runs/v4-replay-new --export-latest
/absolute/path/to/godot --headless --path runtime --script res://inspect_motion_v4.gd -- /absolute/path/to/runs/v4-replay-new/export/roundtrip-job.json
```

Evaluate a new candidate without inference:

```sh
.tools/physics-venv/bin/python tools/evaluate_motion_v4.py candidate.json --out runs/candidate-evaluation-new --frames
```

To repeat the hosted capacity-calibration configuration with an authenticated
Codex CLI, use a fresh output directory (up to two chargeable model calls):

```sh
.tools/physics-venv/bin/python study-v4/run.py runs/v4-capacity-new --controls runs/v4-controls-new --seconds-per-call 600
```

Inputs are pinned in [the public source manifest](../study-v3/sources.json),
using [ArtVIP meshes delivered in Artisan Benchmark](https://huggingface.co/datasets/mastercai/Artisan-Benchmark/tree/17d219e8abea0a5489e2280bf713748aa1e0f6b9/ArtVIP/medical_cart001).
The [prospective protocol](PROTOCOL.md), [capacity amendment](CAPACITY-AMENDMENT.md)
and [derived record](recorded.json) separate completed scores, developer controls
and the unscored earlier timeout. No private company material is included.
