# Study v2: controlled adapters work, baseline still saturates

**Codex/Astra low passed all three scenes and all seven switches on its first
attempt. The mesh-preservation check passed. The predeclared ceiling stop saved
the second call. This is not evidence of RSI improvement or adequate research
headroom.**

The candidate received an imported canonical GLB, images and measured metadata,
without its original construction source. It authored an adapter script creating
`UprightRide`, `DuckRide` and `LeftRide` clips. A fixed evaluator selected and
sampled those authored clips; it supplied no poses, IK or cycling repair.

| Artifact | Upright interaction | Low tunnel | Side interaction | Passing switch visits |
| --- | --- | --- | --- | --- |
| Developer feasibility control | Pass | Pass | Pass | 7/7 |
| Developer no-op control | Pass | Fail | Fail | 3/7 |
| Codex first output | Pass | Pass | Pass | 7/7 |

The two developer controls are not model baselines. A separate changed-vertex
control was rejected as geometry-invalid and remained unscored.

One model call completed in **98.981 seconds**, under the frozen 180-second cap,
with no retries or human source edits. The original native session, CLI events,
response, exact candidate, fixed input bootstrap, GLB and engine results are
retained locally with integrity hashes. Published evaluated assets, adapter code,
manifest and outcome records are in [fixtures/](fixtures/) and
[the audited summary](../reports/study-v2-summary.json).

## What changed from v1

The three pose requirements are incompatible with one static pose. The no-op
control demonstrates that difference. Mesh-local triangle surfaces/connectivity,
base colors, effective mesh scales, static component transforms, neck attachment,
head connection and riding behavior are checked. Actual clip switching includes
returning to prior states. The model worked with an existing GLB, rather than
editing the asset's construction program.

Before model sampling, control calibration established the required constant
animation-channel settings in Blender and disabled immutable-track pruning in
Godot. Both preserve authored channels across switches; they do not solve the
candidate's poses. The same export settings were supplied to the model. Earlier
engineering-control records are retained locally, separate from model results.
The final controls, inputs, evaluator and protocol were frozen before the call;
no threshold was changed after observing it.

## Interpretation and next research boundary

This removes v1's static-pose shortcut, but the stronger single-asset adapter
problem remains solvable in one short call. The output samples the existing
animation, plans rigid upper-part transforms and bakes per-scene clips while
preserving geometry. Increasing only numerical tightness or running this same
three-state workload longer would not establish improvement space.

A useful next study must test reusable adaptation across multiple genuinely
different assets and previously unseen scene constraints, with explicit asset
identity and physical-validity requirements. It must distinguish improvements
to a reusable method from authoring a few declared clips for one known asset.
Those broader requirements are not implemented or claimed by this v2 smoke.

This prototype does not measure complete self-collision, smooth transition
blending, arbitrary scene generalization or asset-family transfer. The low-effort
calibration is not the intended formal frontier/max validation, a Harbor task
validation, an official reward or a runner-native RSI trajectory. The formal
task contract remains unresolved; this workload should not enter a long run.
