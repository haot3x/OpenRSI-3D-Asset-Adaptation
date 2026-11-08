# Generate reusable, function-preserving 3D asset variants

Write **generator.py** as a reusable, deterministic Python program. It receives a JSON job path
and output directory as its two arguments. Each job supplies `asset_dir` and
`scene`. Read the delivered mesh/rig using `asset_task.load_source(asset_dir)` and
write actual adapted vertices, faces and rig with `asset_task.write_output`.
The SDK's implementation contains the exact fixed geometric/function checks.

The job's `scene.bounds` defines transport and interaction workspaces in metres.
The actor must remain at least **8 mm** from their sides, back/front and ceiling.
The floor is Z=0. Transport tests swivel and roll all caster assemblies. The
interaction test opens/closes each drawer and deploys/retracts each holder using
the generated rig. The evaluator supplies these fixed motion probes; you cannot
replace them with an easier route or animation.

Input assets use +Z up and +Y drawer opening. The chassis front plane is Y=0 and
its center is X=0. Source joint limits have already been normalized to positive
drawer travel. Inputs can be wheeled or unwheeled storage props, with arbitrary
part IDs and part counts. Use the supplied **roles and joint tree**, not hardcoded
IDs, object names, fixture IDs or remembered scenes. The same frozen program will
later receive unobserved scene requirements and unobserved input geometry, with
no additional model inference or human edits.

## What may change

- Chassis mesh vertices may undergo one positive diagonal affine deformation.
  X/Z scale ranges are 0.70..1.15, Y is 0.70..1.75. Its provided `anchor` must stay
  fixed within 1 mm; this anchors the front/center and support datum.
- Drawer meshes must share the chassis's linear deformation, keeping each
  drawer cavity compatible with the resized chassis. Their extra seating shift
  is along +Y only, between 0 and min(25 mm, 6% of their adapted depth), with the
  SDK's 1 mm registration tolerance. Some delivered source meshes may have
  shallow closed-rest overlap; permissible seating shifts can repair it.
- Preserve **at least 95% of source drawer volume/capacity**. For this affine
  family, the deformation determinant is the exact volume ratio. Narrowing and
  lowering can require compensating depth; global shrinking loses capacity.
- Wheels, caster forks and ring holders are **rigid**: no rescaling, rotation,
  shearing, simplification or deletion of their mesh-local shape. Translate
  each to its resized chassis attachment. Wheel geometry follows its caster's
  attachment displacement, retaining its relative axle location.
- Update joint pivots so that the rig is registered to the adapted meshes.
  Chassis-attached pivots follow the chassis deformation; wheel pivots follow
  the rigid caster displacement. Drawer pivots also follow their seating shift.
- Preserve all parent/child relationships, joint types and oriented axes. Keep
  rotational ranges unchanged. Drawer travel must be 95%..105% of its source
  travel multiplied by chassis Y scale, with lower limit zero. A shorter stroke
  cannot be used to avoid a scene collision.
- Keep the exact source part IDs, vertex counts, triangle indices/connectivity
  and topology. No per-frame deformation, extra meshes or source geometry leaks.

The output is `mesh.npz` containing `v_<id>` and `f_<id>` arrays plus `rig.json`
with exactly `root_id` and `joints`. Copy the input rig's joint-field schema.
Helpers make the format straightforward:

```python
import json, sys
from asset_task import load_source, write_output
job = json.load(open(sys.argv[1]))
source = load_source(job['asset_dir'])
# Produce vertices, faces and rig from source and job['scene'].
write_output(sys.argv[2], vertices, faces, rig)
```

## Development tools and budget

First run `./python check_boundary.py`; stop and report if it fails. It tests the
actual tool sandbox using public sentinels. Work only in this public workspace.
The shell is enabled; network, other project files, memories, apps, plugins and
subagents are disabled. Do not request broader permissions or inspect unrelated
paths. `./python` is the provided scientific Python interpreter.

Run `./python dev_eval.py generator.py` for authoritative feedback on all three
development scenes. This submits your code to fresh Linux containers and returns
fixed-evaluator results. You have **at most 6 development submissions** within a
**900-second** agent episode. All original code snapshots and native tool calls
are recorded. Each per-scene generator execution has 2 CPU cores, 3 GiB RAM,
30 seconds, no network or host mounts. NumPy 2.4.4, SciPy 1.17.1 and python-fcl
0.7.0.11 are installed. The portable SDK is also available in the container.

Development success is diagnostic, not the transfer score. After your episode,
the first scorable development-submitted program and your final generator.py
will be frozen and separately evaluated on four precommitted transfer cases.
Those cases and their results are unavailable during your development. They
include new scene requirements on familiar geometry and different input
geometry. Do not merely fit the three examples; inspect the supplied geometric
and rig rules and implement a robust generator for the declared family.

Missing/malformed output, process failures and timeouts are unscored. A valid
artifact that loses capacity, scales a rigid part, has a stale rig or collides
gets a real functional failure (zero for that scene). No manual output repair.

Leave the completed program at generator.py. You may use public SDK math and
inspect source geometry, but cannot edit the read-only SDK, assets or feedback
service. Finish with a brief description of the generator and observed **dev**
feedback; do not invent transfer scores. This is a short development study,
not an official Harbor/RSI-Harness run.
