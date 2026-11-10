# Coupled complete-asset compiler integration pilot v7

This implements the first coupled evaluator stage of the broader approved
interactive game-asset generation direction. The six original procedural
mechanisms are folding bridge, telescoping platform, folding workbench,
inspection lamp, service cart and supply chest. Each has inspection, standard
and mobile deployment briefs, yielding 18 family/profile configurations. These
are six constructed mechanism archetypes, not 18 independent real-world assets.
The source is owned by this benchmark; no company or third-party geometry is
used in these fixtures.

The current corpus uses coherent fluted extrusions, scalloped apertures and
noncircular handles with ridged tube sections, rather than only smooth circular
primitives. Reference fluted extrusions use convex partitions of the actual
cross-section. Every reference still has to pass the same motion and fidelity
checks; procedural detail alone is not a difficulty result.

The candidate compiles existing complete assemblies into new visual topology
and compound-convex collision geometry while preserving provided rig, roles and
motion. Graph synthesis, changing module count, textures, visual material
optimization, gravity/stability, force dynamics and new assembly discovery are
not yet implemented. No claim is made that the full broader task is complete,
that procedural complexity alone proves long-run difficulty, or that v7 is an
accepted OpenRSI task.

## Primary outcome and fixed constraints

Each case uses its fixed total triangle/hull/convex-vertex budgets, max 64
vertices per hull and the supplied camera-derived metre tolerance (2 projected
pixels at a declared distance, 1080 pixels, 60 degree vertical field of view).
The deployment settings and reference budgets must be fixed before any model
call. Budgets come from a feasible lower-complexity developer artifact with
12% slack, never from an observed model score. There is no score-rescaling cap.

Every required semantic part and joint/range must be retained. Pivot deviation
is at most 0.5 mm. Input and output stay in the same metre frame. Proxy geometry
is interpreted as solid convex hull unions. Visual parts must have positive
signed volume; orientation inversion/flattening is not a legal optimization.

After budget and rig guards, part quality is saturated geometric fidelity times
contact recall times free-space specificity. Fidelity is
`min(1, tolerance / max(sampled_bidirectional_error, 1e-15))`.
Source and candidate sampling each uses 512 seeded area samples plus up to 256
unique deterministic vertices; it is a sampled diagnostic, not a Hausdorff
bound. Collision probes include axis-aligned and oblique first-hit rays, 2 mm
spheres and a 1 mm reference ambiguity exclusion. Empty reference classes or
nonfinite measurements are evaluator failures, not silently removed examples.

A full case scores its worst required part quality, gated to zero by any
budget/rig/missing-proxy/orientation failure, ground penetration or nonadjacent
solid collision at any sampled frame. Sliding parent-child pairs are checked;
immediate rotational/fixed attachment neighbours are excluded for legitimate
bearing contacts. The clips test each required movement and simultaneous
deployment, with at most 1 cm prismatic and 0.05 rad angular interpolation steps.
They are finite kinematic tests, not continuous collision proofs or force
simulation. The cache uses exact transform byte identity only; it changes
runtime, not tested configurations or collision tolerances.

Primary transfer score averages the three deployment profiles within each
transfer family, then equally averages the three families. This is a mean over
fixed deployment settings, not a continuous AUC across interchangeable budgets.
Candidate-invalid formats/process failures/timeouts are unscored, consume
submission budget and invalidate a whole aggregate; valid functional/guard
failures are scored zeros. Infrastructure stays separately unscored. No failed
case may be omitted.

## Controls and baseline

Before a model call, all 18 developer artifacts must achieve exactly 1, and the
no-LOD, empty proxy, filled aperture, stale rig, disabled motion and inverted
winding controls must fail as declared. Separate solid-containment and
endpoint-clear/intermediate-collision fixtures must exercise the motion guard.
These developers' reference artifacts are not the model baseline.

The traceable standard pipeline combines per-connected-component QEM, protected
small components, proportional resource allocation and the frozen best v6 proxy
method. Record its actual results without substituting its possibly low score
for a frontier-model baseline. Both QEM and the full preserved v6 method are
provided to the research subject, including in generation containers.

## First short calibration

One fresh tool-using Codex gpt-6-astra/max episode, 1,800-second cap, at most
8 authoritative three-case development submissions and no automatic retry or
other agents. The subject gets folding_bridge, folding_workbench and
service_cart source meshes/rigs and all their deployment briefs. For faster
feedback, the broker scores only their standard profiles. The subject may derive
its own geometric tests. Read-only asset/SDK/feedback policy and no-network
boundary must pass native preflight and actual broker smoke first.

Transfer families telescope/platform, inspection lamp and supply chest are
withheld until both first and final programs are frozen after the episode ends.
They are scored at all three deployment profiles. Freeze the earliest submitted
program scorable on all three dev cases and the actual final program; retain
all intermediate errors/regressions. Select neither snapshot by test score.
Reuse identical-hash evaluations only. Report dev retention separately.

Freeze/hash code, all six source deliveries, cases, cached probes, developer
controls and immutable Linux image ID. Generated code executes in fresh
networkless, mount-free 2 CPU / 3 GiB containers, max 90 seconds per asset case.
The evaluator runs separately and never loads generated Python into its own
process. Native model logs, every command, every submitted source/output and
all feedback are retained with an integrity inventory. Publish code and derived
measurements; keep operator conversation and original native logs local until a
proper official private-repository upload exists.

## Difficulty decision

A low standard-pipeline or early development score is insufficient. Assess the
actual final strong-model transfer result and feasible remaining improvements.
This 30-minute calibration is not the planned two-hour stress calibration or a
12-hour run. If it saturates, preserve it as such and extend the genuine action
space/coverage in a new frozen version. Never change this run's score, budgets
or cases after model sampling. The official proposal/Harbor/runner steps and
full broader corpus remain pending.
