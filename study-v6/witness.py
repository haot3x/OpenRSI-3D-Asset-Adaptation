"""Exploratory developer witness; never substituted for a model baseline.

Partition source triangle coverage into convex pieces using development free
probes, then check a separately generated denser query grid. This establishes
feasibility/complexity tradeoffs, not proof of continuous collision equivalence.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial import QhullError

from geometry import clean, hull_mesh, probe_set, proxy_hits, proxy_report

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'study-v5'))
from asset_task import load_source


def node(mesh, faces, free):
    vertices = mesh.vertices[np.unique(mesh.faces[faces])]
    try:
        hull = hull_mesh(vertices)[0]
    except QhullError:
        # At most 0.1 mm extrusion of a planar/linear patch, below the fixed
        # 1 mm reference ambiguity band. No source contact is removed.
        offsets = np.vstack([np.eye(3), -np.eye(3)]) * .0001
        hull = hull_mesh((vertices[:, None] + offsets).reshape(-1, 3))[0]
    return dict(faces=faces, hull=hull, bad=proxy_hits([hull], free))


def partition(mesh, probes, max_hulls=64):
    components = trimesh.graph.connected_components(mesh.face_adjacency, nodes=np.arange(len(mesh.faces)), min_len=1)
    leaves = [node(mesh, np.asarray(faces), probes['free']) for faces in components]
    if len(leaves) > max_hulls:
        leaves = [node(mesh, np.arange(len(mesh.faces)), probes['free'])]
    centers = mesh.triangles_center
    while len(leaves) < max_hulls:
        editable = [i for i, n in enumerate(leaves) if n['bad'].any() and len(n['faces']) > 1]
        if not editable:
            break
        index = max(editable, key=lambda i: int(leaves[i]['bad'].sum()))
        current = leaves[index]
        ids = current['faces']
        choices = []
        for axis in range(3):
            order = np.argsort(centers[ids, axis], kind='stable')
            if np.ptp(centers[ids, axis]) < 1e-8:
                continue
            left, right = np.split(ids[order], [len(ids) // 2])
            children = [node(mesh, left, probes['free']), node(mesh, right, probes['free'])]
            union_bad = children[0]['bad'] | children[1]['bad']
            # Prefer fewer false blocks, then fewer redundant overlapping hits.
            cost = (int(union_bad.sum()), sum(int(c['bad'].sum()) for c in children))
            choices.append((cost, children))
        if not choices:
            current['bad'][:] = False
            continue
        _, children = min(choices, key=lambda x: x[0])
        leaves[index:index + 1] = children
    return [n['hull'] for n in leaves]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    record = dict(kind='Exploratory developer feasibility witness, not a model experiment',
                  max_hulls_per_part=64, train_grid=9, validation_grid=11, rows=[])
    for asset in ['medical_cart001', 'cabinet_1']:
        source = load_source(ROOT / '.tools/v5-inputs' / asset)
        for pid in source['meta']['part_ids']:
            start = time.monotonic()
            folder = out / asset / pid
            folder.mkdir(parents=True)
            reference = trimesh.Trimesh(source['vertices'][pid], source['faces'][pid], process=False)
            mesh = clean(source['vertices'][pid], source['faces'][pid])
            train = probe_set(reference, 9)
            hulls = partition(mesh, train)
            validation = probe_set(reference, 11)
            row = dict(asset=asset, part=pid, role=source['meta']['roles'][pid],
                       development=proxy_report(hulls, train), validation=proxy_report(hulls, validation),
                       wall_seconds=round(time.monotonic() - start, 3))
            raw = {}
            for i, hull in enumerate(hulls):
                raw['v_' + str(i)] = hull.vertices
                raw['f_' + str(i)] = hull.faces
            np.savez_compressed(folder / 'hulls.npz', **raw)
            np.savez_compressed(folder / 'validation-probes.npz', **validation)
            record['rows'].append(row)
            (out / 'record.json').write_text(json.dumps(record, indent=2) + '\n')
            print('WITNESS', asset, pid, row, flush=True)
    print('DONE_DEVELOPER_WITNESS', flush=True)


if __name__ == '__main__':
    main()
