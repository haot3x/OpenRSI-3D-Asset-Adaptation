# Prospective bounded convex-proxy calibration

This short study isolates **collision-proxy generation** within the broader
cross-scene interactive-asset direction. LOD fidelity, rig discovery and full
articulated motion are not included in this scalar score. The earlier LOD and
engine feasibility measurements remain separate. No claim of a complete task,
official reward or RSI-Harness experiment is made.

Candidate: reusable <=128 KiB Python generator. Input is one real part mesh and
a deployment hull budget; output is a list of convex point sets. Every hull has
at most 128 vertices. The allowed hull count differs by case (16–32). Existing
public CPU libraries are allowed, including CoACD and QEM; simply calling them
is not new research. The intended research work is algorithmic improvement of
the reusable generator, with transfer to new structures and budgets.

Cases are frozen in proxy_task.py before any model sampling: three development
parts (trolley frame, drawer and wheel), then three transfer cases (a new trolley
holder and an unseen cabinet's frame and drawer). Six parts from only two assets
are a small calibration, not six independent assets. Inputs are normalized
public meshes from the pinned source manifest; private company materials and
operator chat are excluded.

Reference queries use the fixed 2 mm spheres and 1 mm ambiguity band described
in README.md. Development labels use the 9x9 first-hit grid, transfer uses 11x11.
The generator receives no scored probe coordinates. SDK contains IO only; query
generation and reference labels are outside the agent workspace and containers.
The research agent may derive its own geometric training probes. Test meshes,
queries and outcomes stay outside its workspace until the episode has ended.

**Per-case score** is contact recall multiplied by free-space specificity:
`(1 - false_free/contact_count) * (1 - false_blocked/free_count)`.
Both measured classes matter: an empty proxy scores 0; filling openings loses
specificity. Legal outputs exceeding hull/vertex budgets or containing a
zero-volume hull score 0. Malformed JSON, missing outputs, process failure,
timeouts and infrastructure errors are unscored and consume submission budget;
do not remove them from an aggregate. A primary aggregate is the unweighted mean
of three transfer scores only when every case is scorable. This is a declared
development score, not a manufactured lower baseline or an official reward.

Before sampling, establish legal positive-score library controls on all six
cases, empty and aperture-filling negative controls, native workspace isolation,
and container feasibility. Freeze source, inputs, queries, controls and immutable
image ID. The exploratory developer witness and previous results are withheld
from the research agent. The fixed score/budget/split may not change after model
sampling, even if the result saturates or fails.

Run one tool-using Codex gpt-6-astra/max episode, 900 seconds, at most six complete
three-case development submissions, no retries or other agents. Containers are
networkless, no host mounts, 2 CPUs/3 GiB and 45 seconds per case. The fresh native
session, all commands, inputs, snapshots and per-case outputs stay intact locally.

Freeze the first development-submitted program scorable on all dev cases and
the final program after the episode, then score both on identical transfer cases
with no feedback returned to the model. Preserve earlier invalid submissions.
Reuse outcomes only for identical code hashes. Report retention, all failures,
costs, raw component rates and the scalar mean. No model-independent-vs-continual
causal conclusion can be drawn from one such episode. A ceiling result remains
a ceiling; this does not authorize long runs or formal submission.
