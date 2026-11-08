"""Compare Mac records with Linux scoring of identical frozen hulls and queries.

Runs only trusted evaluator code, not any submitted generator. Geometry/probes
remain inside local host/VM; publish counts/hashes only.
"""
import argparse
import io
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'study-v6'))
from proxy_execution import DOCKER, save, sha
from proxy_task import CASES


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('episode', type=Path)
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    episode = args.episode.resolve()
    image = json.loads((episode / 'image.json').read_text())['Id']
    records = []
    for result_file in sorted(episode.glob('transfer-*/*/result.json')):
        expected = json.loads(result_file.read_text())
        if not expected['scored']:
            continue
        case = next(c for c in CASES if c['id'] == expected['case'])
        queries = ROOT / '.tools/v6-calibration' / case['id'] / 'probes.npz'
        runner = "import json,numpy as np;from proxy_task import evaluate\na=np.load('probes.npz',allow_pickle=False);probes={k:a[k] for k in a.files};print(json.dumps(evaluate('output.json',probes,json.load(open('case.json'))),allow_nan=False))\n"
        files = {'output.json': result_file.with_name('output.json').read_bytes(),
                 'probes.npz': queries.read_bytes(), 'case.json': json.dumps(case).encode(),
                 'runner.py': runner.encode(),
                 'proxy_task.py': (ROOT / 'study-v6/proxy_task.py').read_bytes(),
                 'geometry.py': (ROOT / 'study-v6/geometry.py').read_bytes()}
        payload = io.BytesIO()
        with tarfile.open(fileobj=payload, mode='w') as tar:
            for name, raw in files.items():
                entry = tarfile.TarInfo(name)
                entry.size = len(raw)
                entry.mode = 0o644
                tar.addfile(entry, io.BytesIO(raw))
        command = [*DOCKER, 'run', '--rm', '--network', 'none', '--read-only', '--user', '1000:1000',
                   '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--cpus', '2', '--memory', '3g',
                   '--pids-limit', '64', '--tmpfs', '/work:rw,nosuid,size=64m,uid=1000,gid=1000',
                   '--tmpfs', '/tmp:rw,nosuid,size=64m,uid=1000,gid=1000', '--workdir', '/work',
                   '--entrypoint', '/bin/sh', '-i', image, '-c', 'tar -xf - -C /work && python3 runner.py']
        r = subprocess.run(command, input=payload.getvalue(), capture_output=True, timeout=60)
        label = result_file.parent.parent.name + '-' + case['id']
        (args.out / (label + '.stdout.log')).write_bytes(r.stdout)
        (args.out / (label + '.stderr.log')).write_bytes(r.stderr)
        r.check_returncode()
        actual = json.loads(r.stdout)
        row = dict(snapshot=result_file.parent.parent.name, case=case['id'],
                   output_sha256=sha(result_file.with_name('output.json')), probes_sha256=sha(queries),
                   identical=actual == expected['evaluation'], mac=expected['evaluation'], linux=actual)
        records.append(row)
        save(args.out / 'record.json', dict(image_id=image, rows=records))
        print(label, 'identical=', row['identical'], flush=True)
    assert records and all(r['identical'] for r in records), 'Frozen-output scoring differs; inspect record'
    print('FROZEN_OUTPUT_SCORING_MATCHES', len(records), 'cases', flush=True)


if __name__ == '__main__':
    main()
