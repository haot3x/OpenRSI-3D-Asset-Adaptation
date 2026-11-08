# Bounded convex-proxy calibration v6 — 2026-11-08

**A tool-using Astra-max episode improved transfer score from 0.955445 to
0.976554 (+2.11 percentage points). The first program already has only 4.46
points of ceiling headroom. This subset is still not suitable for a long RSI
run, despite the real development improvement.**

This is a short development study, not an accepted task, official reward,
Harbor validation or official RSI-Harness trajectory. Its frozen experimental
source is `0009fd0169eaf5cffca74176204f3d3f60c7eda9`. Prior studies remain
preserved separately; their scores are not this baseline.

## What this study tests

The model writes a **reusable executable algorithm** that generates new compound
convex collision geometry for public interactive-game asset parts. It receives
an input triangle mesh and a deployment budget, then emits convex point sets.
The evaluator tests whether the generated solids preserve contact surfaces and
free openings, including drawer/holder cavities.

This expands beyond v5's affine mesh/rig family. It isolates collision-proxy
generation; visual LOD quality, rig discovery, whole-asset joint interactions,
rendering and dynamics are **not** in this scalar score. Separate QEM/LOD and
game-engine feasibility measurements are recorded in [feasibility.json](feasibility.json).

The declared per-case score is:

`contact recall * free-space specificity`

The reference uses 2 mm sphere probes, a 1 mm clearance ambiguity band, actual
first-hit surface contacts and outside-visible free positions. It does not
assign arbitrary interior occupancy to thin/open source meshes. Hull budgets
are 16–32 per case, at most 128 vertices per hull. An empty proxy scores zero;
filling openings reduces specificity. Valid but over-budget or zero-volume
outputs score zero; malformed outputs, process errors and timeouts are unscored.

The three development parts are a trolley frame, drawer and wheel. Transfer
contains a new trolley holder and an unseen cabinet's frame and drawer. Data,
queries, budgets and score were frozen before sampling. The agent received no
transfer meshes, scored probe coordinates, test feedback, developer witness
or earlier experiment results. Development uses a 9x9 ray grid; transfer uses
11x11. These are six parts from **two assets**, not six independent assets.

## First versus final frozen programs

| Snapshot | Dev mean | New trolley holder | Unseen cabinet mean | Primary transfer mean |
|---|---:|---:|---:|---:|
| First scorable dev-submitted program | 0.879604 | 1.000000 | 0.933168 | **0.955445** |
| Final program | 0.996543 | 1.000000 | 0.964831 | **0.976554** |

The primary mean equally weights the three transfer cases. All six
snapshot/case evaluations were scorable and met the declared budgets. There
were no process/format/timeout exclusions. Repeated snapshots on the same
three cases are not six independent test examples.

| Transfer case | First score | Final score | First → final false-blocked queries | Free-query count |
|---|---:|---:|---:|---:|
| Trolley holder | 1.000000 | 1.000000 | 0 → 0 | 1,456 |
| Cabinet frame | 0.994592 | 0.994592 | 13 → 13 | 2,404 |
| Cabinet drawer | 0.871743 | 0.935070 | 320 → 162 | 2,495 |

Contact queries were 226, 718 and 626 respectively, with **zero missed contacts**
for both snapshots. Improvement is in the cabinet drawer's free-space response.
Its proxy also uses **6 hulls / 165 vertices**, versus the first program's
**24 hulls / 1,066 vertices**. More free-space correctness did not require more
proxy geometry on that case.

Development submissions, in actual order:

| Submission | Dev mean |
|---|---:|
| 1 | 0.879604 |
| 2 | 0.996543 |
| 3 | 0.992593 |
| 4 | 0.992593 |
| 5 | 0.992593 |

The model restored submission 2 before ending, using its **development feedback**.
The operator did not pick a program by test performance. First and final programs
were frozen after the agent ended, before any transfer evaluation. Final dev
retention reuses the exact hash-matching submission 2, not a new replicate.

## Actual agent and algorithm changes

One fresh **Codex gpt-6-astra / max, tools enabled** episode completed normally
in **864.938 seconds**, within its 900-second cap. It made **41 completed shell
commands**, **6 file changes** and **5 authoritative dev submissions**, out of six
permitted. There were no automatic retries or other agents.

The first program cleans triangle soups, identifies disconnected components,
uses existing CoACD for concavities, limits hull vertices with support-point
selection, and merges nearby hulls when necessary. The final program adds
planar surface cutting for open thin-wall parts, handles coplanar faces on their
solid side, and disables inappropriate CoACD preprocessing. This is generated
algorithmic code, not a manual edit to the test asset. QEM and CoACD themselves
are established tools; algorithmic or benchmark novelty is not claimed here.

Candidate generation ran in fresh Linux ARM64 containers, 2 CPUs / 3 GiB /
45 seconds per case, no network or host mounts. The actual image ID, wheel
hashes, source/query hashes, every program and each generated output hash are
recorded. The native agent workspace denied outside-project reads, network and
protected writes. Both a production-policy preflight and a three-container
broker smoke passed before the model call; the agent's own boundary check also
passed. Its workspace contained public data only.

Complete original native logs, tool events, all five programs, generated hulls
and feedback remain in local `runs/v6-agent-001/`, with a verified **277-file
SHA-256 inventory**. The public [recorded.json](recorded.json) contains derived
metrics/hashes and the exact [first](generators/first.py) and
[final](generators/final.py) programs. No operator conversation, credentials,
private company material or third-party mesh/hull coordinates are published.
This episode is not the future fresh proposal-agent session or official runner.

## Scoring and engine verification

The **same six frozen model outputs and exact query arrays** were scored on the
Mac and in the Linux ARM64 container. All budget decisions, counts and scalar
scores match exactly. No generator was rerun in this check. It distinguishes
score portability from variability in a new decomposition run.

The actual model-generated proxies were also instantiated as compound
`ConvexPolygonShape3D` children of frozen `RigidBody3D`s in Godot 4.7.2.
**1,728 sphere queries**, across identity and rotated/translated poses, match
the analytic proxy predictions with **zero disagreements**. These are posed
collision queries, not force integration or a complete jointed-gameplay test.

[Linux engineering CI](https://github.com/haot3x/OpenRSI-3D-Asset-Adaptation/actions/runs/42474793869)
passes aperture/empty/shift controls, the developer partition witness, and
**4,608** posed engine queries. The same 4,608 checks also pass on the Mac.
That hosted CI does not run the live model or these frozen submitted programs.
Some newly regenerated developer witness decompositions differ by platform;
those measurements are published separately. For example, cabinet validation
false blocks are 129/7,397 on the Mac versus 32/7,397 on Linux. Both engines
agree with their respective proxy geometry. The frozen-output scoring check
above has no such differences; do not substitute one platform's regenerated
proxy metrics for the original experiment's scores.

## Scientific conclusion and next step

There is an observed improvement in a reusable generated method, including
transfer to a new asset. This one small episode does **not** establish a causal
RSI advantage over matched-budget independent adaptation, broad generalization
or a replicated expected reward. No thresholds or cases were changed after
sampling; all intermediate regressions remain recorded.

The first program's **transfer score is already 95.5%**, even though its dev
score was 88.0%. A low development or library-control score cannot be used to
claim adequate research headroom. The final 15-minute program's **97.7%**
transfer result is closer to the first formal Judge attempt than the early dev
submission would be. Extending runtime on this subset would repeat the
previous saturation problem.

**Do not start a long run on v6.** The next candidate needs genuinely harder
coverage and coupled requirements: nonplanar/curved articulated assets,
visual LOD fidelity under real resource budgets, and full joint-motion/free-space
checks on generated visual meshes and proxies together. Verify feasible
references and the final strong tool-using short-run transfer result before
formal submission. Do not change tolerances to lower an already observed score.
The broader task's resource/quality contract and novelty remain unresolved.

## Reproduction

See [README.md](README.md), [PROXY_PROTOCOL.md](PROXY_PROTOCOL.md),
[TASK.md](TASK.md), [runtime-wheels.json](runtime-wheels.json) and the Dockerfile.
The initial tool screen preceded the model. A later confirmation repeated it
with the same settings and a nonfinite-result guard; original raw runs remain
local. This did not alter any frozen model metric, fixture or budget.

For a new live episode, build `openrsi-asset-proxy:v6`, use the existing pinned
public source fetch/normalization, then choose fresh output paths:

```sh
python study-v6/proxy_controls.py runs/v6-proxy-controls-new
python study-v6/episode.py runs/v6-boundary-new --controls runs/v6-proxy-controls-new --preflight-only
python study-v6/episode.py runs/v6-agent-new --controls runs/v6-proxy-controls-new
```

The case cache is write-once; run preflight/control creation in a clean checkout
or retain the verified cache and controls rather than overwriting them. Set
`ASSET_DOCKER_HOST` for a non-default Docker socket. Native agent isolation is
validated on the Mac; offline Linux scoring/CI does not establish Linux agent
isolation, deterministic regeneration across platforms, an immutable published
registry image, official Harbor packaging or formal acceptance.
