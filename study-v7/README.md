# Coupled complete-asset compiler: v7 development pilot

This is the first implementation stage of a broader game-asset generation
task. A single reusable program compiles full articulated assets into visual
LODs and compound convex collision proxies under joint budgets, preserving
required motion and transferring to new mechanism families. It is not yet a
formal OpenRSI task or evidence of 12-hour difficulty.

The six original mechanisms include articulated bridges, workbenches, carts,
telescoping platforms, lamps and chests. Coherent fluted supports, scalloped
openings and noncircular curved handles require more than circular primitive
fitting. Three camera/resource profiles yield 18 configurations, not 18
independent assets. Fixtures and algorithms use no company data or private
assets. The exact geometry constructors are developer-only during calibration.

The evaluator couples visual surface fidelity, contact recall, free-space
specificity, triangle/hull/vertex limits, rig registration and full **sampled**
kinematic clearance. A case is limited by its worst required part. Legal
functional/budget failures score zero; process/format failures remain unscored
and invalidate an aggregate. There is no artificial score cap or rescaling.
The evaluator is not a continuous collision proof or force simulation.

Before a model run, all 18 constructive reference artifacts must score 1, and
the failure controls must catch lost detail, empty proxies, filled apertures,
changed rigs/ranges, inverted winding, solid containment and intermediate
collisions with clear endpoints. These are feasibility checks, not a model
baseline or a demonstration of learning.

## Reproduce feasibility on CPU

Python 3.12; macOS ARM64 or Linux. No GPU, model access or Blender is needed
for these evaluator/reference checks. Install the pinned requirements in a
virtual environment, then use new output paths:

```sh
python -m pip install -r study-v7/requirements.txt
python study-v7/assets.py .tools/v7-fixtures
python study-v7/controls.py .tools/v7-fixtures runs/v7-controls
python tools/export_compiled_v7.py \
  --source .tools/v7-fixtures/service_cart \
  --artifact .tools/v7-fixtures/service_cart/reference-standard \
  --out runs/v7-export
```

The exporter creates a visual GLB with real hierarchy and animated motion;
it does not embed physics proxies. Godot 4.7.2 can independently check the
exported geometry, parent relationships and sampled transforms:

```sh
godot --headless --path runtime --script res://inspect_geometry_v5.gd -- \
  "$PWD/runs/v7-export/roundtrip-job.json"
```

## Prospective model calibration

The subject is Codex gpt-6-astra at max reasoning, with the best preserved v6
proxy method and a component-aware QEM/Blender starter available. It may edit
its reusable program and run development tests. First and final programs are
frozen before transfer scoring. Native logs, every submitted source, generated
artifact and feedback are retained locally with integrity hashes.

The controller expects the repository's existing immutable Linux generation
image, a Docker daemon and native Codex permissions supporting this profile.
On this Mac, Docker runs inside Lima; `ASSET_DOCKER_HOST` points to its socket.
Generation runs in fresh networkless, mount-free 2-CPU/3-GiB containers, with
90 seconds per complete asset. CPU Blender is optional inside that image.
Model tools have no Docker socket or access to developer fixtures/evaluator.

```sh
python study-v7/preflight.py runs/v7-native-preflight --controls runs/v7-controls
python study-v7/baseline.py runs/v7-standard-baseline --controls runs/v7-controls
# Only after preflight, reference controls and a review/freeze of this version:
python study-v7/episode.py runs/v7-agent --controls runs/v7-controls
```

The first model episode is capped at 30 minutes and eight development
submissions. It is **not** the planned two-hour difficulty stress test or a
12-hour official runner trajectory. A poor starter or early score proves
nothing about sustained headroom. If the strong model rapidly saturates, save
that result and broaden the genuine problem before spending a longer budget.

This pilot retains the provided joint graph and part count. New assemblies,
module-count changes, materials/textures, forces, live gameplay and broader
real-asset coverage remain future work. See [PROTOCOL.md](PROTOCOL.md) for the
fixed score, split, failure semantics and limitations.
