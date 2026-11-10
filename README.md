# Continual Cross-Scene Adaptation of Interactive 3D Game Assets

Independent research task direction by **Haotian Xu**, creator of
[AI Game Bench](https://aigamebench.com/).
Discussion: https://github.com/OpenRSI-Foundation/OpenRSI-Index/discussions/324

**Confirmed research direction:** improve a reusable method for adapting an
interactive 3D asset across game scenes, preserving its identity and functionality
while transferring to new constraints and avoiding regressions in prior scenes.
This repository is a public, runnable **engineering prototype**, not an accepted
OpenRSI task, a completed RSI trajectory, or evidence of continual-learning gains.

**Latest completed coupled-asset pilot (v7):** a 28.1-minute tool-using Astra-max
episode improved development **0 → 1** and withheld transfer **0.333333 → 1**.
Development already reached full score on submission two; all nine final
transfer configurations are full score. The subset still saturates and does
**not** justify a 12-hour run. Exact frozen outputs reproduce on Mac/Linux;
the actual generated cart passes 60 Godot transforms and 3,456 collision queries.
See [study-v7/RESULTS.md](study-v7/RESULTS.md). The next planned scope adds module
selection, assembly generation and conflicting game-scene constraints.

**Latest completed bounded convex-proxy study (v6):** one tool-using Astra-max episode
improved development score **0.879604 → 0.996543** and withheld transfer score
**0.955445 → 0.976554**. It generates real compound convex shapes under fixed
hull/vertex budgets. There is a small observed method gain, but the first strong
program is already near the transfer ceiling; a long run is not justified.
Frozen outputs score identically on Mac/Linux, and 1,728 actual model-output
Godot queries pass. See [study-v6/RESULTS.md](study-v6/RESULTS.md).

**Preserved tool-using geometry/rig study (v5):** Astra max wrote and tested a reusable
mesh/rig generator. Both its first submitted and final programs pass 4/4 withheld
transfer cases, including an unseen three-part cabinet. Capacity is preserved at
95%+, rigid functional parts retain size, and generated joint hierarchies import
into Godot. This parametric family still saturates; no RSI gain or long-run
readiness is demonstrated. See [study-v5/RESULTS.md](study-v5/RESULTS.md).

**Preserved functional-motion calibration (v4):** generated behavior adapters move a
real 13-part prop through stockroom pickup, an L-corridor and a service alcove.
Full sampled mesh clearance, operation sequences and previous-scene regression
checks work; the model's first completed candidate still passes 3/3. Its GLB
roundtrip passes 117 transform checks in Godot. This is a saturated development
calibration, not an RSI gain or a formal task. See [study-v4/RESULTS.md](study-v4/RESULTS.md).

**Preserved real-asset screening (v3):** three public articulated assets run on native
Mac CPU geometry/collision infrastructure. Astra at max reasoning recovered all
18 reference movable joints within the frozen structural tolerances. This subset
still saturates; movement-based cross-scene functionality has yet to be tested.
See [study-v3/RESULTS.md](study-v3/RESULTS.md) for predictions, controls, CPU timings
and the limits of this prerequisite screening. No long run was started.

**Preserved adapter calibration (v2):** the model edited an existing GLB without
construction source, preserved its meshes and passed three distinct pose scenes
plus seven switches on its first call. The no-op control passed only the upright
scene. This confirms the controlled-adapter pipeline, but the one-asset workload
still saturates. See [study-v2/RESULTS.md](study-v2/RESULTS.md).

**Preserved development study (v1):** independent and policy-assisted adaptation both
passed all six required fixtures on their first attempts. The workload is
saturated and showed no success-rate gain. The complete eight-call comparison,
audited records and next-study limitations are in
[study-v1/RESULTS.md](study-v1/RESULTS.md). This is a calibration finding; the
current protocol is not ready for a formal long research run.

## Research target

The planned candidate is reusable code producing game-ready mesh variants,
registered articulation, behavior and collision proxies from an input asset and
scene requirements. The scene and evaluator stay fixed. The completed v6 study
isolates compound-convex proxy generation. The new v7 prototype couples visual
topology, proxies and prescribed full-asset motion; the broader task involving
new assemblies, materials and game scenarios remains unimplemented and uncalibrated.
The intended comparison is continually improved reusable adaptation versus
matched-budget independent per-scene adaptation. New-scene success, previous-scene
regressions, asset preservation and adaptation cost are distinct outcomes.
The final primary metric, workload and resource contract remain to be calibrated
and confirmed. See [task-direction.json](task-direction.json).

## Initial pipeline smoke (preserved)

One Codex-generated cycling-pelican asset is tested in two **public development
fixtures**: an open courtyard (3.0 m ceiling) and a low archway (2.05 m ceiling,
2 cm clearance required). Its original 2.29 m height fits only the first fixture.
A separate bounded Codex invocation adapts the existing source. It must preserve
the bicycle and riding animation and keep a visible pelican while reducing the
upper-body envelope. The generated Blender source is executed without human
edits in a restricted container. Both scenes are then evaluated again.

The fixed Godot checker applies inherited animation diagnostics plus a neutral
pose ceiling/floor envelope and simple head/beak/body volume guards. It does not
generate or repair the riding motion. A static-animation negative control must
be rejected. The diagnostic count is correlated and is **not** an official reward
or a count of independent benchmark examples.

This is a small pose/geometry adaptation, not demonstrated continual evolution.
It does not test traversal, full-cycle obstacle clearance, forces, visual style,
complete semantic identity or held-out scene transfer. The original asset's
source and geometry are public; these fixtures are not a hidden test set.

## Run the offline smoke

Requires Python 3.12 and Godot **4.7.2**. No Python packages, model credentials,
Docker, renderer or GPU are required for this offline headless check.

```sh
python3 tools/verify_assets.py
python3 tests/smoke.py --godot /absolute/path/to/godot --out runs/local-001 --include-negative
```

GitHub Actions repeats this check on Ubuntu 24.04 x86_64, using a pinned Godot
archive checksum, and uploads the raw per-scene results and engine logs. That CI
tests Linux headless physics/import/envelope checks; it does not validate the
full official Harbor task, Linux rendering or live model generation.

## Reproduce live adaptation locally

The original adaptation used hosted `gpt-6-astra`, low reasoning, one call with
a 180-second cap and no retries. Fresh native session and CLI event records stay
in ignored `runs/` locally; operator chat histories and credentials are not
published. `tools/adapt_once.py` retains the complete source, images, prompt,
feedback, generated response and container execution records. Its output paths
are write-once, so rerunning on an existing result intentionally refuses to
overwrite it. To repeat generation, use a separate clean worktree and remove
only the tracked `assets/adapted/` outputs there before invoking the script.

Build the Blender image with `docker build -t openrsi-asset-blender:pilot-v0
environment`, provide an authenticated Codex CLI and `GODOT_BIN`, optionally set
`ASSET_DOCKER_HOST`, then run `python3 tools/adapt_once.py`. Candidate code runs
with no network, host mounts, capabilities or privileged mode, limited to 2 CPUs
and 2 GiB RAM. The Dockerfile currently uses Ubuntu packages; each invocation
records the actual image ID. This host-managed Docker path is not an official
Harbor execution contract.

All included code and assets were authored for this independent exploration.
No private company source, reports, assets or earlier gameplay-task results are
included. Nearby work: [ElasticFit](https://arxiv.org/abs/2610.07460),
[Scene Retargeting](https://arxiv.org/abs/2609.36801), and
[Artisan](https://arxiv.org/abs/2610.13947). Novelty remains a hypothesis requiring
example-level comparison; fit-aware insertion or articulated generation alone
is not claimed as new.

## Initial local smoke result

One adaptation call completed in 103.364 seconds. The actual exported geometry
height changed from **2.290 m to 2.014 m**. The original asset passed **1/2** public
scene fixtures; the adapted asset passed **2/2**, retaining the prior courtyard
and animation behavior. The static-animation negative control failed both.
These are engineering fixture outcomes, not benchmark rewards or RSI gains.
See [local smoke notes](reports/local-smoke-notes.json),
[per-scene diagnostics](reports/local-smoke-summary.json) and
[generation provenance](reports/provenance.json).

During local checker calibration, transformed AABBs overestimated rotated-part
height. The final checker measures actual exported mesh vertices. Assets and
the 2.03 m requirement were unchanged; the initial coarse-check record remains
local and the correction is recorded in the smoke notes.
