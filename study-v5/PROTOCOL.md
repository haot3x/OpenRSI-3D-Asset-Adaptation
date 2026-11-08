# Prospective geometry/rig generator study v5

Research target: a fixed-model research agent improves reusable generation code
that produces function-preserving 3D asset variants for new game-scene constraints.
This is a new frozen study. Previous pose/path and structural checks are archived;
none of their full scores or unscored timeouts are relabeled as this baseline.

Candidate: one <=128 KiB portable generator.py. It takes source triangle meshes,
semantic roles, joint tree and scene bounds and outputs actual mesh arrays and
registered rig. The declared family is positive diagonal chassis/drawer
deformation, capacity compensation and bounded seating repair, with rigid wheel,
caster and holder geometry. This is parametric geometry generation and rig repair,
not unrestricted new topology, texture synthesis or new-object reconstruction.
The full public contract is TASK.md and the fixed SDK asset_task.py.

Before any model call, freeze and hash SDK, protocol, source deliveries, all seven
fixtures and controls. Use three development fixtures on one wheeled prop and
four transfer fixtures: two new scene constraints on that prop and two on a
different, unwheeled storage prop. Source meshes come only from the pinned public
manifest in study-v3/sources.json. Axis/datum normalization is recorded; source
closed-pose intersections are not pre-repaired. A bounded drawer seating shift
is an allowed model-generated repair. The developer witness must establish all
seven are feasible before sampling, and identity, universal shrink, lost capacity
and stale-rig controls must fail. Witness code/parameters and transfer fixtures
are withheld from the model's filesystem and tools.

Run one **tool-using Codex gpt-6-astra/max** development episode, at most 900 s and
6 complete development submissions, no automatic retries, extra agents or effort
reduction. All shell/tool events and the exact original fresh native session are
preserved. The public-only workspace has read-only assets, SDK and feedback
responses, no network and no access to other user projects or the held-out files.
Use a verified native permission profile, and a file-exchange development broker
that accepts only code and fixed dev-scene requests. It never exposes transfer
data. Agent commands receive a filtered environment. Candidate code executes in
fresh containers without network/host mounts, 2 CPUs, 3 GiB, 30 s per fixture.
The actual immutable container image ID and architecture are recorded.

Freeze two candidate snapshots **after the agent ends**, before transfer scoring:
the earliest development submission with scorable outputs on all three dev
fixtures, and the final generator.py. Invalid early submissions remain recorded,
unscored, and consume submission budget. Do not choose the best test-performing
snapshot. If code hashes match, execute transfer once and reuse identical results.
Recheck the three dev fixtures on the final snapshot to measure retention.

Primary development-study outcome: unweighted fraction of four transfer scenes
passing capacity/shape/registration guards and full sampled collision/function
tests. Also report familiar-asset and unseen-asset subsets separately, dev results,
all invalid outcomes and candidate/runtime costs. Only report a primary fraction
if all four fixtures are scorable; never drop or normalize away invalid cases.
Candidate-invalid formats, process errors, timeouts and infrastructure outcomes
are unscored; valid but nonfunctional/identity-breaking artifacts receive zero.
No test feedback is returned to the research agent. No thresholds, meshes,
fixtures, split or counted budget may change after model sampling begins.

Compare first and final snapshots with identical per-fixture generation budgets.
Any improvement is preliminary evidence from one short episode and four transfer
cases. It is not a replicated matched-budget independent-vs-continual comparison,
an official reward, Harbor validation, official runner trajectory, long-run
readiness or proof of a 20% expected headroom. A ceiling result is retained as
such; do not manufacture room by weakening the model or changing the score.

Mesh-derived artifacts and original native logs stay local. Public code, hashes,
normalized-source recipes, frozen fixtures after the episode and derived
measurements may be published. No private company data or operator conversation
is input to the model. This episode is separate from any future fresh public-only
proposal-agent session and official private-repository experiment.

The permission configuration follows the [official OpenAI permission-profile
documentation](https://learn.chatgpt.com/docs/permissions). A local cached base
image is extended with checksum-recorded CPU wheels; the actual final image ID
is pinned for all generations. Full official container packaging is still pending.
