# Compile complete interactive assets under joint quality/resource constraints

Implement one reusable `generator.py`, invoked as:

```
python3 generator.py job.json output_folder
```

`asset_sdk.load_job` returns `(job, metadata, parts)`. Each part is `(vertices,
triangle_indices)` in the common rest-world metre frame, +Z up. Write changed
visual topology, compound convex proxies and the registered rig using
`asset_sdk.write_output(folder, parts, proxies, rig)`. The archive/JSON filenames
are handled by the SDK. Every required part must remain present. Each proxy is
a list of at least four noncoplanar points; its convex hull is solid.

The job fixes maximum total triangles, hull count, total convex vertices and
vertices per hull. Read and respect them. It also supplies visual_tolerance_m
and a 90-second complete-asset generation limit. Runtime is fresh Linux ARM64,
2 CPUs / 3 GiB, no network or host mounts. NumPy, SciPy, trimesh, FCL, CoACD,
fast_simplification, rtree, networkx and CPU Blender are available. Code is
limited to 128 KiB and must produce bounded regular output files.

Metadata supplies semantic parts, original joint tree/axes/limits/pivots and
required sequential and simultaneous motion clips. This integration study
requires that existing graph and motion ranges be preserved. Pivot registration
may differ by at most 0.5 mm; axes remain fixed. This particular prototype is a
complete-asset compiler, not new joint discovery or unrestricted assembly.

The coupled per-case quality is the worst required part's:

```
min(1, visual_tolerance_m / sampled_bidirectional_surface_error)
  * contact_recall * free_space_specificity
```

Contact/free queries use 2 mm spheres, including oblique views, and omit a
1 mm reference ambiguity band. Actual scored samples/queries are not supplied.
Any budget/rig/missing-proxy/inverted-solid violation, ground penetration or
nonadjacent solid collision anywhere in the fixed sampled motion clips scores
zero. Immediate fixed/rotational attachment neighbours allow bearing contacts;
sliding pairs remain tested. Format errors, candidate crashes and timeouts are
unscored failures and consume submission budget; they cannot be dropped from an
aggregate. Different deployment profiles change budgets and camera-derived
visual tolerances. Scores are averaged by asset family, not by the number of
individual probes or motion samples. The developer reference shows score 1 is
feasible; it is withheld from this workspace.

You have the strongest preserved v6 proxy code in `legacy_proxy.py` and a
component-aware QEM starter in `starter.py`. Both are allowed research tools.
Improve global resource allocation, remeshing/topology, decomposition and other
reusable algorithms; do not hard-code case answers, part dimensions or geometry
for particular source names. Generate from the actual input geometry.

The workspace has three development families and all their deployment briefs.
Authoritative `./python dev_eval.py generator.py` scores the three STANDARD
profiles only for fast feedback. At most eight submissions in a 1,800-second
short calibration. You may run your own local geometry tests. Transfer uses
new complete mechanism families and all three deployment profiles. No test
geometry or feedback is supplied before the episode ends. Leave your final
program ready and finish normally before the deadline.

First run `./python check_boundary.py` and stop if it fails. Do not read outside
this workspace, request escalation, use networks or spawn other agents.
