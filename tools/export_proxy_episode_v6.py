"""Local-only engine job for exact frozen model outputs, never raw publication."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'study-v6'))
from geometry import hull_mesh, proxy_hits
from proxy_task import CASES


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('episode', type=Path)
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    jobs = []
    for output in sorted(args.episode.glob('transfer-*/*/output.json')):
        case = next(c for c in CASES if c['id'] == output.parent.name)
        data = json.loads(output.read_text())
        hulls = [hull_mesh(np.array(v))[0] for v in data['hulls']]
        with np.load(ROOT / '.tools/v6-calibration' / case['id'] / 'probes.npz', allow_pickle=False) as a:
            points, labels = [], []
            for name, count, blocked in [('free', 96, False), ('contact', 48, True)]:
                indices = np.linspace(0, len(a[name]) - 1, min(count, len(a[name])), dtype=int)
                points.extend(a[name][indices])
                labels.extend([blocked] * len(indices))
        points = np.asarray(points)
        expected = proxy_hits(hulls, points)
        jobs.append(dict(asset=output.parent.parent.name + '/' + case['asset'], part=case['part'],
                         hulls=[h.vertices.tolist() for h in hulls],
                         queries=[dict(point=p.tolist(), proxy_blocked=bool(h), source_blocked=b)
                                  for p, h, b in zip(points, expected, labels)]))
    assert jobs
    (args.out / 'job.json').write_text(json.dumps(dict(radius=.002, jobs=jobs)))
    print('Actual frozen model engine job:', len(jobs), 'outputs,', sum(len(j['queries']) for j in jobs) * 2, 'posed queries')


if __name__ == '__main__':
    main()
