"""Run the fixed pre-model screen on public inputs; raw derivatives stay local."""
import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

import fast_simplification
import numpy as np
import trimesh

from geometry import clean, make_hulls, probe_set, proxy_report, seed_for, surface_report

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'study-v5'))
from asset_task import load_source


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    record = dict(kind='Pre-model tool feasibility, not an RSI experiment',
                  platform=platform.platform(), python=platform.python_version(),
                  packages={p: importlib.metadata.version(p) for p in
                            ['numpy', 'scipy', 'trimesh', 'rtree', 'coacd', 'fast-simplification', 'networkx']},
                  rows=[], coacd=[])
    record['source_hashes'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted(Path(__file__).parent.glob('*.py'))}
    save(out / 'record.json', record)
    for asset in ['medical_cart001', 'cabinet_1']:
        source_dir = ROOT / '.tools/v5-inputs' / asset
        source = load_source(source_dir)
        record.setdefault('input_hashes', {})[asset] = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source_dir.iterdir() if p.is_file()
        }
        for pid in source['meta']['part_ids']:
            start = time.monotonic()
            folder = out / asset / pid
            folder.mkdir(parents=True)
            reference = trimesh.Trimesh(source['vertices'][pid], source['faces'][pid], process=False)
            mesh = clean(source['vertices'][pid], source['faces'][pid])
            mesh.export(folder / 'cleaned.ply')
            probes = probe_set(reference)
            np.savez_compressed(folder / 'probes.npz', **probes)
            row = dict(asset=asset, part=pid, role=source['meta']['roles'][pid],
                       original_triangles=len(reference.faces), cleaned_triangles=len(mesh.faces), lods=[])
            # Cleaning itself is measured against unmodified reference geometry.
            row['cleaning'] = surface_report(reference, mesh, seed_for(asset, pid))
            for ratio in [.2, .05, .015]:
                target = max(12, int(len(mesh.faces) * ratio))
                vertices, faces = fast_simplification.simplify(
                    mesh.vertices, mesh.faces.astype(np.int32), target_count=target, agg=7.
                )
                candidate = trimesh.Trimesh(vertices, faces, process=False)
                candidate.export(folder / ('lod-' + str(ratio) + '.ply'))
                result = surface_report(reference, candidate, seed_for(asset, pid))
                result.update(ratio=ratio, target_triangles=target)
                row['lods'].append(result)
            row['proxies'] = {}
            for mode, components in [('single_hull', False), ('component_hulls', True)]:
                hulls = make_hulls(mesh, components)
                row['proxies'][mode] = proxy_report(hulls, probes)
                if hulls is not None:
                    raw = {}
                    for i, hull in enumerate(hulls):
                        raw['v_' + str(i)] = hull.vertices
                        raw['f_' + str(i)] = hull.faces
                    np.savez_compressed(folder / (mode + '.npz'), **raw)
            row['wall_seconds'] = round(time.monotonic() - start, 3)
            record['rows'].append(row)
            save(out / 'record.json', record)
            print('PART', asset, pid, 'LODs', [(x['triangles'], round(x['sampled_max_metres'] * 1000, 2)) for x in row['lods']],
                  'proxy', row['proxies'], 'seconds', row['wall_seconds'], flush=True)
        # Bounded library runs are feasibility probes, not candidate submissions.
        selected = ['p01', 'p07'] if asset == 'medical_cart001' else ['p01']
        for pid in selected:
            folder = out / asset / pid
            command = [sys.executable, str(Path(__file__).with_name('try_coacd.py')), str(folder)]
            start = time.monotonic()
            with (folder / 'coacd.log').open('w') as log:
                proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                        env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'})
                try:
                    proc.wait(timeout=60)
                    status = 'completed' if proc.returncode == 0 else 'library_error'
                except subprocess.TimeoutExpired:
                    proc.kill(); proc.wait()
                    status = 'timeout'
            row = dict(asset=asset, part=pid, status=status, cap_seconds=60,
                       wall_seconds=round(time.monotonic() - start, 3))
            if status == 'completed':
                row['measurement'] = json.loads((folder / 'coacd-result.json').read_text())
            record['coacd'].append(row)
            save(out / 'record.json', record)
            print('COACD', row, flush=True)
    print('DONE_PREMODEL_SCREEN', flush=True)


if __name__ == '__main__':
    main()
