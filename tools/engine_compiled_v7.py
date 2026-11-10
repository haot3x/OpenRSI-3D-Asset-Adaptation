"""Actual compiled proxies at three rig states for independent Godot queries.

Each part is queried separately. This checks representation/pose transfer;
whole-assembly clearance remains the separate sampled FCL evaluator's job.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'study-v7'))
from evaluator import load_artifact, load_source, proxy_hits, rig_guard, transforms


def main():
    parser = argparse.ArgumentParser()
    for name in ['source', 'artifact', 'probes', 'out']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    _, meta = load_source(args.source)
    _, hulls, rig = load_artifact(args.artifact, meta)
    assert not rig_guard(meta, rig)
    rest, deployed = meta['knots'][0], meta['knots'][-2]
    midpoint = {p: (rest[p] + deployed[p]) / 2 for p in rest}
    jobs = []
    for state, q in [('rest', rest), ('midpoint', midpoint), ('deployed', deployed)]:
        world = transforms(meta, q, rig)
        for part in meta['part_ids']:
            points, labels = [], []
            with np.load(args.probes / (part + '.npz'), allow_pickle=False) as probes:
                for category, blocked in [('free', False), ('contact', True)]:
                    cloud = probes[category]
                    selected = np.linspace(0, len(cloud) - 1, min(24, len(cloud)), dtype=int)
                    points.extend(cloud[selected])
                    labels.extend([blocked] * len(selected))
            points = np.asarray(points)
            expected = proxy_hits(hulls[part], points)
            t = world[part]
            def apply(v):
                return np.asarray(v) @ t[:3, :3].T + t[:3, 3]
            jobs.append(dict(asset=meta['family'] + ':' + state, part=part,
                             hulls=[apply(h.vertices).tolist() for h in hulls[part]],
                             queries=[dict(point=p.tolist(), proxy_blocked=bool(a), source_blocked=b)
                                      for p, a, b in zip(apply(points), expected, labels)]))
    (args.out / 'job.json').write_text(json.dumps(dict(radius=.002, jobs=jobs)))
    print('V7_COMPILED_ENGINE_JOB', len(jobs), 'posed parts,',
          sum(len(j['queries']) for j in jobs) * 2, 'queries', flush=True)


if __name__ == '__main__':
    main()
