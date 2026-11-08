"""Freeze public cases and verify legal library baselines before any model call."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import trimesh

from geometry import probe_set
from proxy_execution import DOCKER, IMAGE, aggregate, evaluate_method, save, sha
from proxy_task import CASES, evaluate

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'study-v5'))
from asset_task import load_source

LIBRARY = '''import sys,coacd,numpy as np
from proxy_sdk import load_job,write_output
j,v,f=load_job(sys.argv[1]);coacd.set_log_level('warn')
_,indices,inverse=np.unique(np.round(v,7),axis=0,return_index=True,return_inverse=True)
v=v[indices];f=inverse[f]
result=coacd.run_coacd(coacd.Mesh(v,f),threshold=.03,max_convex_hull=j['max_hulls'],preprocess_mode='auto',preprocess_resolution=30,resolution=1000,mcts_nodes=10,mcts_iterations=30,mcts_max_depth=2,decimate=True,max_ch_vertex=128,seed=0)
write_output(sys.argv[2],[vertices for vertices,faces in result])
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    image = json.loads(subprocess.check_output([*DOCKER, 'image', 'inspect', IMAGE], text=True))[0]
    save(out / 'image.json', {k: image[k] for k in ['Id', 'Architecture', 'Os', 'Created']})
    rows = []
    for case in CASES:
        folder = ROOT / '.tools/v6-calibration' / case['id']
        folder.mkdir(parents=True, exist_ok=False)
        source = load_source(ROOT / '.tools/v5-inputs' / case['asset'])
        v, f = source['vertices'][case['part']], source['faces'][case['part']]
        np.savez_compressed(folder / 'source.npz', vertices=v, faces=f)
        reference = trimesh.Trimesh(v, f, process=False)
        probes = probe_set(reference, 9 if case['split'] == 'dev' else 11)
        assert len(probes['contact']) and len(probes['free'])
        np.savez_compressed(folder / 'probes.npz', **probes)
        save(folder / 'case.json', case)
        r = evaluate_method(LIBRARY, case, out / case['id'], image['Id'])
        print('LIBRARY_CONTROL', case['id'], r, flush=True)
        assert r['scored'] and r['evaluation']['budget_passed'] and r['evaluation']['score'] > 0, r
        empty = out / (case['id'] + '-empty.json')
        save(empty, {'hulls': []})
        assert evaluate(empty, probes, case)['score'] == 0
        rows.append(r)
    save(out / 'library-results.json', dict(rows=rows, summary=aggregate(rows)))
    save(out / 'cases.json', CASES)
    frozen = {str(p.relative_to(ROOT)): sha(p) for p in (ROOT / '.tools/v6-calibration').rglob('*') if p.is_file()}
    save(out / 'input-hashes.json', frozen)
    save(out / 'verified.json', dict(passed=True, legal_positive_library_cases=len(rows), empty_proxy_zero=True,
                                     source_note='Developer controls only, never the actual model baseline'))
    print('ALL_PROXY_PREFLIGHT_CONTROLS_PASS', flush=True)


if __name__ == '__main__':
    main()
