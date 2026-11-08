"""Execute untrusted proxy generation only in isolated CPU Linux containers."""
import base64
import hashlib
import io
import json
import os
import subprocess
import tarfile
import time
import uuid
from pathlib import Path

import numpy as np

from proxy_task import evaluate

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DOCKER = ['docker'] + (['--host', os.environ['ASSET_DOCKER_HOST']] if os.environ.get('ASSET_DOCKER_HOST') else [])
IMAGE = 'openrsi-asset-proxy:v6'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def evaluate_method(code, case, out, image_id):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    source = ROOT / '.tools/v6-calibration' / case['id']
    job = dict(mesh='source.npz', max_hulls=case['max_hulls'], max_vertices_per_hull=128, generation_seconds=45)
    files = {'generator.py': code.encode(), 'proxy_sdk.py': (HERE / 'proxy_sdk.py').read_bytes(),
             'source.npz': (source / 'source.npz').read_bytes(), 'job.json': json.dumps(job).encode()}
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w') as archive:
        for name, raw in files.items():
            entry = tarfile.TarInfo(name)
            entry.size = len(raw)
            entry.mode = 0o644
            archive.addfile(entry, io.BytesIO(raw))
    payload = buffer.getvalue()
    name = 'openrsi-proxy-v6-' + uuid.uuid4().hex[:12]
    wrapper = 'tar -xf - -C /work; cd /work; ulimit -f 16384; ulimit -t 45; python3 generator.py job.json output.json; proxy_rc=$?; echo "$proxy_rc" > .exitcode; sleep 120'
    command = [*DOCKER, 'run', '--name', name, '--network', 'none', '--read-only', '--user', '1000:1000',
               '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--cpus', '2', '--memory', '3g',
               '--memory-swap', '3g', '--pids-limit', '64', '--tmpfs', '/work:rw,nosuid,size=192m,uid=1000,gid=1000',
               '--tmpfs', '/tmp:rw,nosuid,size=64m,uid=1000,gid=1000', '--workdir', '/work',
               '--entrypoint', '/bin/sh', '-i', image_id, '-c', wrapper]
    record = dict(image_id=image_id, container=name, command=command,
                  generator_sha256=hashlib.sha256(code.encode()).hexdigest(),
                  source_sha256=sha(source / 'source.npz'), payload_sha256=hashlib.sha256(payload).hexdigest(), job=job)
    (out / 'generator.py').write_text(code)
    save(out / 'execution.json', record)
    result = dict(case=case['id'], scored=False, generator_sha256=record['generator_sha256'])
    started = time.monotonic()
    process = None
    rc = None
    try:
        with (out / 'stdout.log').open('wb') as stdout, (out / 'stderr.log').open('wb') as stderr:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr)
            process.stdin.write(payload)
            process.stdin.close()
            while time.monotonic() - started < 45:
                poll = subprocess.run([*DOCKER, 'exec', name, 'cat', '/work/.exitcode'], capture_output=True, text=True, timeout=5)
                if poll.returncode == 0:
                    rc = int(poll.stdout.strip())
                    break
                if process.poll() is not None:
                    break
                time.sleep(.25)
            record.update(exit_code=rc, status='generated' if rc == 0 else 'process_error' if rc is not None else 'timeout_or_infrastructure')
            if rc == 0:
                reader = "import os,stat,base64;p='/work/output.json';s=os.lstat(p);assert stat.S_ISREG(s.st_mode) and s.st_size<=8388608;print(base64.b64encode(open(p,'rb').read()).decode())"
                read = subprocess.run([*DOCKER, 'exec', name, 'python3', '-c', reader], capture_output=True, timeout=15)
                if read.returncode:
                    record.update(status='output_missing_or_invalid', error=read.stderr.decode(errors='replace')[-1000:])
                else:
                    (out / 'output.json').write_bytes(base64.b64decode(read.stdout))
                    record['output_sha256'] = sha(out / 'output.json')
    finally:
        cleanup = subprocess.run([*DOCKER, 'rm', '--force', name], capture_output=True)
        record['container_removed'] = cleanup.returncode == 0
        if process is not None:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=5)
        record['wall_seconds'] = round(time.monotonic() - started, 3)
        save(out / 'execution.json', record)
    if record['status'] == 'generated':
        with np.load(source / 'probes.npz', allow_pickle=False) as a:
            probes = {k: a[k] for k in a.files}
        try:
            evaluation = evaluate(out / 'output.json', probes, case)
        except (ValueError, TypeError, KeyError) as error:
            result.update(status='candidate_invalid', error=str(error))
        else:
            result.update(status='evaluated', scored=True, evaluation=evaluation)
    else:
        result['status'] = record['status']
    save(out / 'result.json', result)
    return result


def aggregate(rows):
    valid = bool(rows) and all(r['scored'] for r in rows)
    return dict(scorable=valid, cases=len(rows),
                mean_score=sum(r['evaluation']['score'] for r in rows) / len(rows) if valid else None,
                budget_passes=sum(bool(r.get('evaluation', {}).get('budget_passed')) for r in rows))
