# Functional LOD feasibility and bounded convex-proxy calibration (v6)

**Completed short-study result:** development score 0.879604 → 0.996543;
withheld transfer score 0.955445 → 0.976554. There is a small observed gain, but
the first strong-model program is already near the transfer ceiling. This is
**not ready for a long run**. See [RESULTS.md](RESULTS.md).

This is a new development study with a **pre-model engineering feasibility screen**
and a separately specified bounded convex-proxy model calibration. It does not relabel
v5's saturated geometry/rig result, is not a formal task, and does not claim an
RSI gain. Original studies and native trajectories remain intact.

The target is a reusable program that generates **new topology** and separate
compound-convex collision proxies for interactive game assets at different
viewing distances/resource budgets. Visual shape, openings and collision response
must survive. A whole-part convex hull may fill a drawer or holder opening;
triangle reduction alone is insufficient.

This first screen measures existing public tools on the pinned public trolley
and cabinet, on the Mac CPU. It reports sampled bidirectional surface distances,
triangle counts, compound-convex complexity, and sphere-probe collision response.
It does not yet define a single benchmark reward. Native source geometry can
contain thin/open or duplicate surfaces, so arbitrary interior occupancy is not
treated as ground truth. Reference free probes have clear line-of-sight from
outside the part and sampled clearance from its surface; contact probes overlap
an actual first-hit surface. These are geometric query checks, not a rigid-body
simulation or continuous proof of collision equivalence.

## Fixed pre-model screen

- Assets: the same pinned public `medical_cart001` and `cabinet_1` sources used
  by v5; no private assets or reports. Source normalization is unchanged.
- QEM LOD candidates retain 20%, 5%, or 1.5% of each cleaned part's triangles,
  with a minimum of 12 per part. Topology/vertex positions may change.
- Visualization distances 2, 6 and 12 metres, vertical 60-degree field of view,
  1080 pixels. Report geometric error in approximate pixel units using
  `metres_per_pixel = 2 * distance * tan(30 degrees) / 1080`. This is a geometric
  approximation, not rendered perceptual fidelity. No pass tolerance or polygon
  budget is chosen after observing a model.
- Test the single-convex-hull baseline and connected-component hull baseline.
  Run bounded CoACD on representative concave parts to check laptop practicality.
- Surface metrics use deterministic area-weighted barycentric samples plus every
  cleaned source vertex; measured maxima are **sampled**, not Hausdorff bounds.
- Sphere probes use a fixed 2 mm radius, with 1 mm clearance ambiguity excluded.
  Axis-aligned first-hit rays create contact queries and outside-visible free
  queries, including apertures reached before a first hit. Report false-free
  and false-blocked counts separately. The full reference and proxy arrays stay
  local; only code, hashes and derived measurements are publishable.

The first model calibration isolates convex-proxy generation under explicit shape/vertex
budgets. See [PROXY_PROTOCOL.md](PROXY_PROTOCOL.md) and [TASK.md](TASK.md).
A formal combined LOD/interaction boundary, actual device budgets, full joint-motion
checks and broader reference feasibility still need validation before this can
become a task. Merely replacing QEM with another
algorithm is not a novelty claim; the research hypothesis concerns method
improvement and transfer under coupled interaction and deployment constraints.

## Sources and tools

- Meshes: `study-v3/sources.json` and `study-v5/prepare.py`.
- QEM: https://pyvista.github.io/fast-simplification/ (MIT).
- Convex decomposition: https://github.com/SarahWeiii/CoACD (MIT).
- Game-engine requirement: https://docs.godotengine.org/en/stable/tutorials/physics/collision_shapes_3d.html
- Existing mesh optimization: https://meshoptimizer.org/ — LOD generation itself
  is established; broader novelty remains to be assessed.

On 2026-11-08, the current OpenRSI main tree and the latest 100 Discussion titles
were checked; no other interactive-asset LOD/convex-proxy topic was found in that
limited inventory. This is not an exhaustive literature or proposal review.

## Local reproduction

Install `requirements.txt` into a Python 3.12 environment; source fetching and
normalization follow v5. Use fresh output paths:

```sh
python study-v6/controls.py runs/v6-controls-new
python study-v6/screen.py runs/v6-screen-new
python study-v6/witness.py runs/v6-witness-new
python study-v6/engine_job.py runs/v6-witness-new runs/v6-engine-new
/path/to/godot --headless --path runtime --script res://inspect_proxies_v6.gd -- /absolute/path/to/runs/v6-engine-new/job.json /absolute/path/to/runs/v6-engine-new/result.json
```

The exploratory developer witness uses development free probes to partition
triangle coverage, then checks a denser 11x11 grid. That grid is a small
correlated validation, not unseen-asset evidence or a continuous guarantee.
Its 64-hull-per-part allowance differs from the separately frozen model-study
budgets; never compare its scalar result as the model baseline.

The model generator runs in a CPU Linux container built from the v5 base and
`Dockerfile`, using public wheels in `runtime-wheels.json`. Every generation
pins the actual image ID. Native agent isolation is for the Mac host; Linux
scoring alone does not validate Linux agent isolation or official Harbor packaging.
