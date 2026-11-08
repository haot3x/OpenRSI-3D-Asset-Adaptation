"""Local engine-query job from measured real-asset proxies; no raw publication."""
import argparse
import json
from pathlib import Path

import numpy as np
import trimesh

from geometry import proxy_hits


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('witness', type=Path)
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    jobs = []
    for file in sorted(args.witness.glob('*/*/hulls.npz')):
        folder = file.parent
        with np.load(file, allow_pickle=False) as raw:
            hulls = [trimesh.Trimesh(raw['v_' + str(i)], raw['f_' + str(i)], process=False)
                     for i in range(len(raw.files) // 2)]
        with np.load(folder / 'validation-probes.npz', allow_pickle=False) as raw:
            points, labels = [], []
            for category, limit, blocked in [('free', 96, False), ('contact', 48, True)]:
                selected = np.linspace(0, len(raw[category]) - 1, min(limit, len(raw[category])), dtype=int)
                points.extend(raw[category][selected])
                labels.extend([blocked] * len(selected))
        points = np.asarray(points)
        expected = proxy_hits(hulls, points)
        jobs.append(dict(asset=folder.parent.name, part=folder.name,
                         hulls=[m.vertices.tolist() for m in hulls],
                         queries=[dict(point=p.tolist(), proxy_blocked=bool(a), source_blocked=b)
                                  for p, a, b in zip(points, expected, labels)]))
    (args.out / 'job.json').write_text(json.dumps(dict(radius=.002, jobs=jobs)))
    print('Local convex engine job:', len(jobs), 'parts,', sum(len(j['queries']) for j in jobs) * 2, 'posed queries')


if __name__ == '__main__':
    main()
