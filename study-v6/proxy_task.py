"""Host-only fixed proxy calibration; all scalar metrics are development metrics."""
import json
from pathlib import Path

import numpy as np
from scipy.spatial import QhullError

from geometry import hull_mesh, proxy_report

CASES = [
    dict(id='dev-frame', asset='medical_cart001', part='p00', split='dev', max_hulls=32),
    dict(id='dev-drawer', asset='medical_cart001', part='p01', split='dev', max_hulls=32),
    dict(id='dev-wheel', asset='medical_cart001', part='p02', split='dev', max_hulls=16),
    dict(id='transfer-holder', asset='medical_cart001', part='p07', split='heldout', max_hulls=24),
    dict(id='transfer-cabinet-frame', asset='cabinet_1', part='p01', split='heldout', max_hulls=32),
    dict(id='transfer-cabinet-drawer', asset='cabinet_1', part='p00', split='heldout', max_hulls=24),
]
MAX_VERTICES = 128


def evaluate(path, probes, case):
    p = Path(path)
    if p.is_symlink() or not p.is_file() or p.stat().st_size > 8 * 1024 ** 2:
        raise ValueError('Missing, linked or oversized output')
    data = json.loads(p.read_text(), parse_constant=lambda s: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    if not isinstance(data, dict) or set(data) != {'hulls'} or not isinstance(data['hulls'], list) or len(data['hulls']) > 512:
        raise ValueError('Output must be {hulls: list of point arrays}, capped at 512')
    hulls, budget_errors = [], []
    for vertices in data['hulls']:
        v = np.asarray(vertices, dtype=float)
        if v.ndim != 2 or v.shape[1:] != (3,) or not 4 <= len(v) <= 4096 or not np.isfinite(v).all() or np.any(abs(v) > 5):
            raise ValueError('Malformed or unbounded convex point array')
        if len(v) > MAX_VERTICES:
            budget_errors.append('per-hull vertex budget exceeded')
        try:
            mesh, _ = hull_mesh(v)
        except QhullError:
            budget_errors.append('zero-volume hull is not deployable')
            continue
        hulls.append(mesh)
    if len(data['hulls']) > case['max_hulls']:
        budget_errors.append('convex shape budget exceeded')
    if budget_errors:
        return dict(status='evaluated', score=0., budget_passed=False,
                    budget_errors=sorted(set(budget_errors)), hulls=len(data['hulls']))
    m = proxy_report(hulls, probes)
    score = (1 - m['false_free_fraction']) * (1 - m['false_blocked_fraction'])
    return dict(status='evaluated', score=float(score), budget_passed=True, measurement=m)
