"""Verify native subject isolation and real file-exchange/container feedback.

Calls the Codex sandbox executable, but makes no model/provider request.
"""
import argparse
import json
import subprocess
from pathlib import Path

from episode import Broker, workspace
from execution import DOCKER, IMAGE, ROOT, save, sha
from isolation import PROFILE, PYTHON, config_args


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('out', type=Path)
    parser.add_argument('--controls', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    controls = args.controls.resolve()
    assert json.loads((controls / 'verified.json').read_text())['passed']
    for relative, digest in json.loads((controls / 'fixture-hashes.json').read_text()).items():
        assert sha(ROOT / relative) == digest, relative
    manifest = json.loads((controls / 'fixture-manifest.json').read_text())
    cases = manifest['cases']
    dev = [c for c in cases if c['split'] == 'dev' and c['profile'] == 'standard']
    image = json.loads(subprocess.check_output([*DOCKER, 'image', 'inspect', IMAGE], text=True))[0]
    image_record = {k: image[k] for k in ['Id', 'Architecture', 'Os', 'Created']}
    save(out / 'image.json', image_record)
    image_path = controls / 'image.json'
    if image_path.exists():
        assert json.loads(image_path.read_text())['Id'] == image['Id']
    else:
        save(image_path, image_record)
    data, probes = ROOT / manifest['data_root'], ROOT / manifest['probe_root']
    work = workspace(out, dev, cases, data)
    protected = [p.name for p in work.iterdir() if p.name not in ['generator.py', '.tmp']]
    policy = config_args(work, protected)
    command = ['codex', 'sandbox', '-P', PROFILE, '-C', str(work), *policy, '--', str(PYTHON)]
    boundary = subprocess.run([*command, 'check_boundary.py'], cwd=work, capture_output=True,
                              text=True, timeout=30)
    save(out / 'boundary.json', dict(returncode=boundary.returncode, stdout=boundary.stdout, stderr=boundary.stderr))
    assert boundary.returncode == 0 and 'BOUNDARY_OK' in boundary.stdout, boundary.stderr
    # Deliberate legal zero: source visuals plus empty proxies. It must return
    # budget/functional feedback, not crash the broker or fabricate a reward.
    (work / 'generator.py').write_text("""import sys
from asset_sdk import load_job,write_output
job,meta,parts=load_job(sys.argv[1])
write_output(sys.argv[2],parts,{p:[] for p in parts},dict(root_id=meta['root_id'],joints=meta['joints']))
""")
    broker = Broker(work, out, dev, image['Id'], data, probes)
    broker.start()
    try:
        feedback = subprocess.run([*command, 'dev_eval.py', 'generator.py'], cwd=work,
                                  capture_output=True, text=True, timeout=420)
        save(out / 'client.json', dict(returncode=feedback.returncode, stdout=feedback.stdout, stderr=feedback.stderr))
        assert feedback.returncode == 0, feedback.stderr
        response = json.loads(feedback.stdout)
        assert response['summary']['scorable'] and response['summary']['mean_score'] == 0
        assert len(response['cases']) == 3
        assert all('required_collision_part_missing' in r['evaluation']['issues'] for r in response['cases'])
    finally:
        broker.stop.set()
        broker.thread.join(timeout=420)
    assert broker.error is None and not broker.thread.is_alive() and len(broker.records) == 1
    save(out / 'verified.json', dict(passed=True, model_called=False, boundary=True,
                                    broker_submissions=1, scorable_cases=3,
                                    deliberate_control_score=0, image_id=image['Id']))
    print('V7_NATIVE_BOUNDARY_AND_BROKER_PASS; NO MODEL CALLED', flush=True)


if __name__ == '__main__':
    main()
