"""Record the supplied standard compiler; never a substitute for model calibration."""
import argparse
import json
import subprocess
from pathlib import Path

from execution import DOCKER, IMAGE, ROOT, aggregate, evaluate_method, save, sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('out', type=Path)
    parser.add_argument('--controls', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    assert json.loads((args.controls / 'verified.json').read_text())['passed']
    for relative, digest in json.loads((args.controls / 'fixture-hashes.json').read_text()).items():
        assert sha(ROOT / relative) == digest, relative
    manifest = json.loads((args.controls / 'fixture-manifest.json').read_text())
    image = json.loads(subprocess.check_output([*DOCKER, 'image', 'inspect', IMAGE], text=True))[0]
    save(out / 'image.json', {k: image[k] for k in ['Id', 'Architecture', 'Os', 'Created']})
    code = (Path(__file__).resolve().parent / 'standard_pipeline.py').read_text()
    rows = []
    for case in manifest['cases']:
        if case['profile'] != 'standard':
            continue
        print('START', case['id'], flush=True)
        rows.append(evaluate_method(code, case, out / case['id'], image['Id'],
                                    ROOT / manifest['data_root'], ROOT / manifest['probe_root']))
        save(out / 'summary.json', dict(kind='Standard compiler, not frontier-model baseline',
                                        rows=rows, summary=aggregate(rows)))
        r = rows[-1]
        print('RESULT', r['case'], r['status'], r.get('evaluation', {}).get('score'),
              r.get('evaluation', {}).get('issues'), flush=True)
    print('ALL', aggregate(rows), flush=True)


if __name__ == '__main__':
    main()
