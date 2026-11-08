# Candidate next direction: functional LOD and collision-proxy generation

The affine geometry/rig family is solved by the first strong-model program in
this pilot. More instances of the same three-scale problem would mostly enlarge
the test set. Keep its implementation and observations as infrastructure and
calibration, rather than treating a 12-hour repeat as a new scientific result.

A more substantial candidate is **cross-scene generation of interactive-asset
topology, LODs and collision proxies**. One reusable program would produce game-
ready variants for different triangle/runtime budgets, close-view fidelity and
interaction requirements. Wheels, drawers, hinges and holder openings would have
to remain functional through complete motion tests.

The candidate should be allowed to generate new vertices, faces, decomposition
and proxy meshes, rather than selecting only affine dimensions. Proposed fixed
checks include bidirectional surface fidelity to the source, critical-feature
and aperture preservation, actual triangle/resource budgets, and scene/part
collisions over unchanged interaction tests. Generating a static low-poly shape
would not be sufficient. CPU Blender/mesh processing and FCL are plausible local
tools, subject to measured validation on the laptop and Linux.

Before treating this as a task:

1. Check overlap with current OpenRSI tasks and existing mesh-optimization work.
2. Establish developer witnesses that jointly satisfy fidelity, budgets and
   interactions. Derive numerical tolerances from game-use requirements before
   model sampling; do not select thresholds to lower a previously seen score.
3. Freeze the generator API, permitted edits, failure handling, dataset split,
   resource budget and continuous/discrete primary outcome.
4. Test the intended full tool-using model, including local development before
   its first scored submission. Confirm reproducible headroom and improvement
   potential across new assets and scene requirements.
5. Only then prepare a fresh public-only proposal-agent session and formal
   submission. The current pilot is not a proposal or official runner trajectory.

Exact quality thresholds, polygon budgets and primary score are unresolved.
This document describes a candidate direction, not an implemented v6 benchmark.
