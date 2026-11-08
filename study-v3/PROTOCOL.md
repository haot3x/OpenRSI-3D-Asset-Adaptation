# Real-asset mechanism screening, version 3

Prospective scope: screen cabinet_1, microscope001 and medical_cart001, selected
before model outputs, from the immutable public source manifest in sources.json.
This tests the mechanism-recovery prerequisite for cross-scene adaptation. It is
not the completed cross-scene task, physical functionality evaluation, official
Artisan reproduction, or a formal RSI runner trajectory.

Inputs: original closed/open reference images and description; three neutral
surface-sampled views with anonymous part IDs; world-space bounding boxes,
centroids, principal axes and triangle counts. The trusted loader uses reference
zero-state forward kinematics to assemble meshes. The model does not receive the
URDF, link names, reference hierarchy, joint axes, joint pivots or evaluator.
Already segmented parts make this easier than recovering segmentation from a
single raw mesh. Public benchmark familiarity cannot be excluded.

One fresh structured-output Codex invocation per asset, gpt-6-astra, max reasoning,
300 seconds each, no retries or tool access. This is a bounded model probe rather
than a full tool-using Codex agent. Stop remaining probes on provider/CLI failure,
timeout, missing original native session or invalid output. Incomplete cases are
unscored; they are never counted as capability failures. Preserve all artifacts
locally. Do not silently reduce reasoning effort or increase the budget.

Predict one rooted kinematic tree over all anonymous parts. Primary diagnostic:
fraction of reference movable joints with correct parent, type, undirected axis
within 15 degrees, and, for rotational joints, pivot-line perpendicular distance
within max(5 mm, 2% of asset bounding-box diagonal). Prismatic pivot location is
unidentifiable and not scored. Continuous and revolute types are equivalent;
axis sign and translation along a rotational axis are equivalent. Macro-average
the three per-asset fractions only if all three completed. Root accuracy and each
component are reported separately. No inferred limits, mass or dynamics scoring.
Alternative valid mechanisms and annotation ambiguities require manual review.

Before sampling, verify exact-reference positive controls, sign/along-axis
invariance, orthogonal-axis and displaced-rotational-pivot negatives, graph
validation, and native CPU FCL separated/intersecting-box controls. FCL controls
demonstrate backend availability only; no actual asset functionality is measured.

Decision: do not start a long run from a ceiling result or an unresolved input or
scoring ambiguity. Non-ceiling agreement alone is insufficient: inspect the
errors and then add executable actuation, collision, reachability and retention
tests before claiming an RSI improvement task. No after-output score changes.

Raw third-party assets remain local; source links, hashes and our derived code
can be shared. Dataset and upstream license claims require separate delivery
checks before redistributing raw meshes. No Mopan material is used.
