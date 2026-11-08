"""Bounded CoACD CPU probe, called in a separate killable process."""
import json
import sys
from pathlib import Path

import coacd
import numpy as np
import trimesh

from geometry import hull_mesh, proxy_report

folder = Path(sys.argv[1])
mesh = trimesh.load(folder / 'cleaned.ply', process=False)
coacd.set_log_level('warn')
parts = coacd.run_coacd(
    coacd.Mesh(np.asarray(mesh.vertices), np.asarray(mesh.faces)), threshold=.03,
    max_convex_hull=32, preprocess_mode='auto', preprocess_resolution=30,
    resolution=1000, mcts_nodes=10, mcts_iterations=30, mcts_max_depth=2,
    decimate=True, max_ch_vertex=64, seed=0,
)
hulls = [hull_mesh(vertices)[0] for vertices, _ in parts]
with np.load(folder / 'probes.npz', allow_pickle=False) as p:
    probes = {k: p[k] for k in p.files}
result = proxy_report(hulls, probes)
raw = {}
for i, mesh in enumerate(hulls):
    raw['v_' + str(i)] = mesh.vertices
    raw['f_' + str(i)] = mesh.faces
np.savez_compressed(folder / 'coacd-hulls.npz', **raw)
(folder / 'coacd-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result), flush=True)
