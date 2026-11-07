# Study v2 — controlled pose-adapter calibration

This is a short development calibration of one immutable interactive asset,
not a formal OpenRSI workload, success claim or completed RSI trajectory.

The same base GLB must support three model-authored animation adapters:
`UprightRide`, `DuckRide`, `LeftRide`. Scene targets are delivered concretely in
`scenes.json`. The upright and low-clearance requirements are incompatible with
one static pose. The side-window target adds a different spatial interaction.
Seven declared switches test returning to previous states. Repeated visits are
not independent examples, and switching is immediate rather than blended.

## Input and candidate

The candidate receives the original GLB already imported into Blender 4.0.2,
canonical images and measured part/animation metadata. It does not receive the
construction source or developer control adapter. It returns Blender editing
code that creates a rig/animation adapters and exports a single GLB. A fixed
bootstrap delivers only the declared input asset in the existing restricted
CPU container, with no host mount or network. The model's code is unedited.

Mesh roles, mesh-local triangle surface/connectivity, base colors and effective
mesh scales must be preserved. New empty rig nodes and animation channels are
allowed. Static body/bicycle parts stay in place. The neck base stays attached;
its top remains connected to the actual head geometry. The original riding
behavior is independently checked in each selected clip and root transform.

The evaluator selects the model-authored clip, samples it and measures geometry.
It does not solve poses, author clips, synthesize cycling or repair outputs.
Blender is configured to retain constant object-animation tracks; Godot imports
without pruning immutable tracks. These options preserve authored data when
switching clips, rather than substituting a pose. The same options are available
to the model. Positive and no-op adapter controls validate this before sampling.

## Budget and observations

Request `gpt-6-astra`, low reasoning, 180 seconds per call, tools/web disabled,
maximum **two** generation opportunities and no automatic retries. The second,
when needed, gets only its own first code and actual evaluation feedback.
Generation/execution failures consume an opportunity. Service timeouts and
ambiguous infrastructure outcomes are unscored and stop the condition.

**Predeclared ceiling stop:** if the first valid artifact passes all three
scenes and all seven visits, stop immediately and report saturation rather than
spending a second call. If the first is partial, permit one feedback repair.

Report first and selected strict unique-scene success (0/3 through 3/3), return
visit outcomes and individual failure categories. Geometry-invalid or malformed
artifacts are unscored, not invented zero rewards. Missing/wrong animation clips
in an otherwise valid immutable GLB are functional failures. Select among valid
evaluated outputs by unique scenes passed, then visits passed, retaining the
earlier attempt on an exact tie. There is no official reward in this protocol.

## Controls and limits

Before model calls, a developer-authored imported-asset control must pass all
three scenes and seven visits. A no-op adapter with correctly named clips must
pass only the upright scene; a changed-geometry control must be rejected by the
independent mesh check. Controls are not model baselines. Freeze code, source
asset, metadata, scenes, prompt and configuration hashes before generation.

One asset, three public states and one baseline/repair trial cannot establish
method transfer or RSI gains. Local-surface, base-color and transform invariants
do not prove complete visual identity, collision-free motion or game readiness.
There is no unseen parameter/asset-family test or smooth transition metric yet.
Low reasoning is an engineering calibration; any intended formal frontier/max
configuration still needs validation. A first or selected ceiling result leaves
the workload unready as a formal bounded-score research benchmark.
