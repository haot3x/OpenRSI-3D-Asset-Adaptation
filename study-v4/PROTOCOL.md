# Functional-motion development calibration v4

The research direction remains continual cross-scene adaptation of interactive
3D game assets. This prototype tests generated **behavior/animation adapters** on
one existing articulated game prop. New mesh generation, broad generalization,
method transfer and RSI gain are not measured by this short calibration.

## Fixed candidate and workload

Use the immutable ArtVIP medical_cart001 collision triangle meshes and delivered
joint frames from the pinned source manifest in study-v3/sources.json. The rig
is supplied for this adaptation stage; the model does not reconstruct it. Four
scene-adaptable controls are two prismatic drawers and two rotating ring holders.
The candidate is a JSON shared pose bank plus three root/pose-keyframe programs.
No candidate code executes. Meshes, dimensions, source rig, walls, targets,
sampler, evaluator and limits cannot be changed by the candidate.

Three public development scenes: stockroom pickup with left/right operations;
L-corridor turn and right-drawer delivery; a narrow service alcove with outside
preparation, different inside deployment and outside release. A height-only scene
was discarded during engineering because this rig's controls do not affect
height. The same actor geometry is used in every scene.

The root is planar x/y/yaw. Keyframes interpolate root and joint values linearly.
A fixed kinematic controller generates the four caster steering and wheel-roll
channels. It inserts checked steering arcs at segment starts and integrates
rolling with the delivered wheel radius. This supplies game-prop locomotion
animation; tire contact forces, no-slip dynamics and caster-trail dynamics are
not simulated. Extra steering time is evaluator-owned. Keyframes end by 90 s,
total animation by 120 s, at most 64 keyframes per scene, 12 shared poses, 12 m
root travel, and 18,000 refined frames per scene.

## Fixed development diagnostic

A scene passes only if the initial and final root match the fixture within 2 cm
and 0.035 rad, the first/final articulated states are stowed within 0.01, every
ordered interaction event holds for at least 0.4 s, ground support is preserved,
all sampled real-mesh environment clearances are at least 8 mm, and no checked
self-collision occurs. World bounds use actual vertices when a conservative
broad-phase box could be outside. AABBs only prune collision queries; they never
alone establish a collision failure.

The sampler refines motions with a conservative per-vertex displacement bound
of 4 mm per interval. The ground guard uses actual wheel vertices (minimum z
between -2.5 mm and +3 mm). FCL computes triangle-mesh/box distances and mesh/mesh
intersections. The fixed ten adjacent rotational bearing pairs are excluded from
self-collision; body/drawer and all other pairs remain checked. These exclusions
mean adjacent-link penetration is not certified. Self-collision is sampled, not
a continuous-collision proof. Failure checks short-circuit at the first failed
frame; every refined frame of a passing trajectory must be checked.

Report each scene separately and the unweighted fraction passing out of three.
It is a public development diagnostic, **not an official reward**. Candidate
format, unknown fields, geometry-changing fields, limits, and resource-cap
violations are unscored. A well-formed but nonfunctional motion program receives
its actual finite scene-success fraction, including zero. Provider, timeout,
missing native session or evaluator infrastructure failure is unscored.

## Controls, sampling and stopping

Before model sampling, a developer witness must pass 3/3; a valid static no-op
must pass 0/3; a diagonal shortcut with valid endpoints/events must fail collision;
universal deployment must collide in the alcove; changing a shared pose must
show earlier-scene regression. Reject a scale override. Geometry/clearance
controls check separated, near and intersecting mesh/box placements. Witness
solutions and negative-control trajectories are never included in model input.

Use one fresh Codex structured-output invocation per attempt: gpt-6-astra, max
reasoning, 300-second cap, no tools, zero automatic retries. First attempt gets
only the declared interface, rig metadata, fixtures and public appearance/maps.
If it scores below 3/3, one fresh repair invocation gets its unchanged complete
candidate and evaluator feedback; re-evaluate **all** scenes to expose regressions.
Stop at 3/3, after two completed attempts, or at the first provider/CLI/timeout,
missing-native or candidate-invalid outcome. Never manually repair model output,
lower reasoning effort, change scenes/thresholds after sampling, or recast an
incomplete outcome as low model capability.

This two-attempt feedback loop is not a matched-budget independent-vs-reusable
method study, nor a held-out transfer experiment. Long-run readiness requires a
broader frozen functional workload with baseline headroom, actual method-transfer
and retention evaluation, and the separate official validator/runner contract.
All original fresh native sessions and input hashes are preserved locally.
No private company material is used; raw third-party assets remain local.
