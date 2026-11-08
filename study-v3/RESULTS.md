# Real-asset mechanism screening — 2026-11-08

**Decision: local CPU execution and the bounded model-probe pipeline work. This
mechanism-recovery subset still saturates and does not justify a long RSI run.**
The intended research direction remains cross-scene adaptation of interactive
game assets. This screening checks one prerequisite, not the complete task.

Three public ArtVIP assets were selected and the protocol, model configuration,
scorer and controls frozen before sampling. One fresh Codex structured-output
probe per asset used `gpt-6-astra`, **max** reasoning, a 300-second cap, zero
retries and no tools. All three completed; all three exact original native
sessions were recovered and hash-verified locally. This is a bounded fixed-model
probe, not a tool-using Codex agent or an official runner-native trajectory.

| Asset | Parts | Movable joints passing | Correct root | Call seconds |
|---|---:|---:|---|---:|
| Two-drawer cabinet | 3 | 2 / 2 | yes | 19.695 |
| Compound microscope | 5 | 4 / 4 | yes | 197.910 |
| Medical trolley | 13 | 12 / 12 | yes | 177.105 |

All three per-asset agreement fractions are 1.0 (macro-average 1.0); 18 / 18
reference movable joints pass. These are agreement diagnostics under the
predeclared thresholds, not physical functionality scores or official rewards.
There was no adaptation iteration or measured RSI gain.

The maximum microscope axis error is 3.828 degrees and rotational pivot-line
error is 7.854 mm. The trolley's maximum pivot-line error is 2.671 mm. These pass
the predeclared 15-degree and max(5 mm, 2% of asset diagonal) tolerances. Their
effect on actual interaction clearance has not been measured. Thresholds were
not changed after seeing outputs; unidentifiable prismatic pivots were excluded.

## What the model received

Original closed/open reference images and operation descriptions; anonymous
part IDs; world-space geometric measurements and three neutral surface-sampled
views. The trusted loader assembles collision meshes using reference zero-state
forward kinematics. Part segmentation and zero-pose placement are supplied.
The model does not recover segmentation and receives no reference joint tree,
axes, pivots, semantic link names, URDF file or evaluator source.

These inputs already provide substantial help. The descriptions specify the
expected kinds of operations, and the delivered joints have mostly simple axes.
Public benchmark familiarity cannot be excluded. Perfect agreement here does
not establish robust mechanism recovery from arbitrary game meshes.

## Mac CPU feasibility

Native macOS ARM64, Python 3.12.13, Codex CLI 0.166.0; pinned dependencies are in
requirements.txt. Model inference used the hosted Codex service; model weights
did not run on the laptop. Dataset selection downloaded 33 files, 60,123,574
bytes. Full upstream GPU training/rendering dependencies were not installed.

| Asset | Triangles | Load seconds | FCL BVH build seconds | Zero-pose pair queries |
|---|---:|---:|---:|---:|
| Cabinet | 1,052 | 0.004 | 0.002 | 3 |
| Microscope | 372,335 | 0.848 | 1.003 | 10 |
| Trolley | 81,254 | 0.188 | 0.176 | 78 |

Each asset's complete zero-pose pair-query pass took under 1 ms on this machine.
This is one local feasibility measurement, not a full dynamic simulation or
performance guarantee. Adjacent-link contact is expected, so these queries are
not interpreted as pass/fail functionality measurements. Positive/negative box
collision controls, exact-reference joint controls, equivalent-axis invariance,
wrong-axis/pivot rejection and self-cycle rejection all passed.

## What must precede a long run

Build movement-based game interaction tests on these real mechanisms: open and
reach into drawers, turn and roll caster assemblies, actuate linked parts through
a trajectory, and measure scene collisions and usable clearance. Cross-scene
variants must impose competing spatial and resource constraints and test returns
to prior scenes. Validate that checks reject broken functionality and allow valid
alternative constructions; reference-URDF similarity alone is insufficient.

Then freeze the functional scoring contract and a development/transfer split,
test the intended strong baseline, and evaluate whether a reusable adaptation
method has improvement and retention headroom. No long-run readiness, Harbor
validation, official submission or acceptance is claimed by this screening.

## Reproduce

From the repository root, use Python 3.12:

```sh
python3.12 -m venv .tools/physics-venv
.tools/physics-venv/bin/pip install -r study-v3/requirements.txt
.tools/physics-venv/bin/python tools/fetch_screening_assets.py
.tools/physics-venv/bin/python tools/replay_v3.py study-v3/recorded.json
.tools/physics-venv/bin/python tools/profile_geometry_v3.py --out runs/cpu-profile-new.json
```

To make three new hosted model calls, authenticate Codex CLI and use a fresh
write-once output directory:

```sh
.tools/physics-venv/bin/python study-v3/run.py runs/v3-screening-new
```

Raw assets and native transcripts stay local in ignored directories. Source
links and hashes are in sources.json; derived predictions, component errors,
environment and controls are in recorded.json. Original inputs come from the
immutable [Artisan Benchmark snapshot](https://huggingface.co/datasets/mastercai/Artisan-Benchmark/tree/17d219e8abea0a5489e2280bf713748aa1e0f6b9/ArtVIP),
whose subset is attributed to [ArtVIP](https://huggingface.co/datasets/X-Humanoid/ArtVIP).
Our screening does not reproduce the official Artisan evaluator. No Mopan
source, assets or reports are used.
