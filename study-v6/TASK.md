# Generate reusable collision proxies for interactive game assets

Implement `generator.py`. Invocation:

```
python3 generator.py job.json output.json
```

Use `proxy_sdk.load_job(path)` to get `(job, vertices, faces)` and
`proxy_sdk.write_output(path, list_of_vertex_arrays)` to emit compound convex
shapes. Each array represents a solid convex hull of its points, not a triangle
mesh. Coordinates are metres in the supplied mesh frame. New hull topology and
decomposition are allowed. Preserve contact surfaces and accessible openings.

The job contains `mesh`, `max_hulls`, `max_vertices_per_hull` (128), and
`generation_seconds` (45). Each hull needs at least four noncoplanar points and
no more than the allowed vertices. Hull-count and vertex-budget violations are
scorable zeros. Malformed data, crashes and timeouts are unscored failures.
Runtime is a fresh networkless CPU Linux container, 2 CPUs/3 GiB, no host mounts.
Installed packages include NumPy, SciPy, trimesh, CoACD, fast_simplification,
rtree and networkx. Output must be a regular JSON file; code <=128 KiB.

The case score is contact recall multiplied by free-space specificity, using
fixed source-surface contact and outside-visible free sphere queries. Radius
is 2 mm, with a 1 mm ambiguity band. Scored query coordinates are not supplied.
Empty proxy => 0; a single hull may fill openings and lose specificity. All
development-case scores are averaged; the final program must generalize to
different real parts and deployment budgets. No texture/LOD generation or
physics force simulation is required in this short calibration.

Inspect `assets/` and `dev-cases.json`. You may use the local Python runtime via
`./python`, derive your own geometry tests, and use installed libraries. The
input shape, not any particular vertex order/part name, should drive the method.
Authoritative feedback: `./python dev_eval.py generator.py`. At most six complete
development submissions are permitted; local reasoning/tests are allowed within
the 900-second episode. Submit early enough to inspect actual feedback and leave
your final `generator.py` ready before the deadline.

First execute `./python check_boundary.py`; stop if it fails. Assets, SDK and
feedback directories are read-only. Do not access other projects, networks,
credentials, held-out data or spawn other agents. Only public data is provided.
