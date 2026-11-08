"""Known game-like aperture fixture: prevent measuring only triangle reduction."""
import argparse
import json
from pathlib import Path

import numpy as np
import trimesh

from geometry import make_hulls, probe_set, proxy_hits, proxy_report, surface_report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('out', type=Path)
    out = parser.parse_args().out
    out.mkdir(parents=True, exist_ok=False)
    parts = []
    for extent, center in [([.02, .1, .12], [-.05, 0, .06]),
                           ([.02, .1, .12], [.05, 0, .06]),
                           ([.12, .1, .02], [0, 0, .01])]:
        mesh = trimesh.creation.box(extent)
        mesh.apply_translation(center)
        parts.append(mesh)
    reference = trimesh.util.concatenate(parts)
    probes = probe_set(reference)
    component = make_hulls(reference, True)
    single = make_hulls(reference, False)
    a, b = proxy_report(component, probes), proxy_report(single, probes)
    assert a['exact_sampled_agreement'], a
    assert b['false_blocked'] > 0, b
    assert not proxy_hits(component, np.array([[0., 0., .07]]))[0]
    assert proxy_hits(single, np.array([[0., 0., .07]]))[0]
    assert proxy_hits(component, np.array([[.05, 0., .07]]))[0]
    empty = proxy_report([], probes)
    assert empty['false_free'] == empty['contact_count'] > 0, empty
    unchanged = surface_report(reference, reference, 0)
    moved = reference.copy()
    moved.apply_translation([.03, 0, 0])
    shifted = surface_report(reference, moved, 0)
    assert unchanged['sampled_max_metres'] < 1e-10
    assert shifted['sampled_max_metres'] >= .029
    record = dict(passed=True, reference_triangles=len(reference.faces),
                  proper_compound=a, single_hull_fills_aperture=b,
                  empty_proxy=empty, unchanged=unchanged, shifted=shifted)
    (out / 'controls.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
