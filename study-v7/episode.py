"""One isolated tool-using model episode and post-episode transfer calibration."""
import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import threading
import time
from pathlib import Path

from isolation import PROFILE, PYTHON, config_args
from execution import DOCKER, IMAGE, aggregate, evaluate_method, save, sha

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent


class Broker:
    def __init__(self, work, out, cases, image, data_root, probe_root):
        self.work, self.out, self.cases, self.image = work, out, cases, image
        self.data_root, self.probe_root = data_root, probe_root
        self.stop = threading.Event()
        self.records, self.seen, self.error = [], set(), None

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        try:
            while not self.stop.is_set():
                for path in sorted((self.work / '.exchange/requests').glob('*.json')):
                    if self.stop.is_set():
                        break
                    if path.name in self.seen or not re.fullmatch(r'[a-f0-9]{32}\.json', path.name) or path.is_symlink():
                        continue
                    self.seen.add(path.name)
                    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
                    try:
                        info = os.fstat(fd)
                        if not stat.S_ISREG(info.st_mode) or info.st_size > 256 * 1024:
                            continue
                        raw = os.read(fd, 256 * 1024 + 1)
                    finally:
                        os.close(fd)
                    try:
                        request = json.loads(raw)
                        code = request['code']
                        assert request['id'] == path.stem and isinstance(code, str) and len(code.encode()) <= 128 * 1024
                    except (ValueError, KeyError, AssertionError, TypeError):
                        continue
                    if len(self.records) >= 8:
                        response = dict(status='submission_budget_exhausted', remaining=0)
                    else:
                        number = len(self.records) + 1
                        folder = self.out / ('dev-' + str(number).zfill(2))
                        folder.mkdir()
                        (folder / 'generator.py').write_text(code)
                        print('DEV_SUBMISSION', number, hashlib.sha256(code.encode()).hexdigest(), flush=True)
                        rows = [evaluate_method(code, c, folder / c['id'], self.image, self.data_root, self.probe_root) for c in self.cases]
                        response = dict(status='evaluated', submission=number, remaining=8 - number,
                                        generator_sha256=sha(folder / 'generator.py'),
                                        summary=aggregate(rows), cases=rows)
                        save(folder / 'feedback.json', response)
                        self.records.append(dict(folder=str(folder.relative_to(self.out)), **response))
                        save(self.out / 'dev-ledger.json', self.records)
                        print('DEV_RESULT', number, response['summary'], flush=True)
                    # Counts/rates only: no exact reference test or dev coordinates.
                    response = copy.deepcopy(response)
                    with (self.work / '.exchange/responses' / path.name).open('x') as f:
                        f.write(json.dumps(response, indent=2) + '\n')
                self.stop.wait(.2)
        except BaseException as error:
            self.error = repr(error)
            save(self.out / 'broker-error.json', dict(error=self.error))


def native_session(events, out):
    ids = {e['thread_id'] for e in events if e.get('type') == 'thread.started'}
    if len(ids) != 1:
        return dict(status='missing_or_ambiguous_thread')
    identity = next(iter(ids))
    root = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'sessions'
    matches = list(root.glob('**/*' + identity + '*.jsonl'))
    if len(matches) != 1:
        return dict(status='missing_native_session')
    if json.loads(matches[0].read_text().splitlines()[0]).get('payload', {}).get('id') != identity:
        return dict(status='native_identity_mismatch')
    shutil.copyfile(matches[0], out / 'native-session.jsonl')
    return dict(status='copied_exact_fresh_session', thread_id=identity, sha256=sha(out / 'native-session.jsonl'))


def workspace(out, cases, all_cases, data_root):
    work = out / 'workspace'
    work.mkdir()
    for name in ['.exchange/requests', '.exchange/responses', '.tmp', 'assets']:
        (work / name).mkdir(parents=True)
    for name in ['asset_sdk.py', 'blender_lod.py', 'primitive_fit.py', 'dev_eval.py', 'TASK.md']:
        shutil.copyfile(HERE / name, work / name)
    shutil.copyfile(HERE / 'standard_pipeline.py', work / 'starter.py')
    shutil.copyfile(HERE / 'standard_pipeline.py', work / 'generator.py')
    shutil.copyfile(ROOT / 'study-v6/generators/final.py', work / 'legacy_proxy.py')
    shutil.copyfile(ROOT / 'study-v6/proxy_sdk.py', work / 'proxy_sdk.py')
    dev = []
    for family in sorted({c['family'] for c in cases}):
        folder = work / 'assets' / family
        folder.mkdir()
        shutil.copyfile(data_root / family / 'source.npz', folder / 'source.npz')
        meta = json.loads((data_root / family / 'metadata.json').read_text())
        meta.pop('family', None)
        save(folder / 'metadata.json', meta)
    for c in all_cases:
        if c['split'] != 'dev':
            continue
        job = {k:c[k] for k in ['max_triangles','max_hulls','max_proxy_vertices','max_vertices_per_hull','visual_tolerance_m','generation_seconds']}
        job.update(id=c['id'], source='assets/'+c['family']+'/source.npz', metadata='assets/'+c['family']+'/metadata.json')
        dev.append(job)
    save(work / 'dev-cases.json', dev)
    (work / 'python').write_text('#!/bin/sh\nexec '+repr(str(PYTHON))+' "$@"\n')
    (work / 'python').chmod(0o755)
    sentinel=out/'outside-sentinel.txt';sentinel.write_text('Public nonsecret boundary sentinel')
    probe = """import pathlib,socket
try:pathlib.Path(%r).read_text()
except PermissionError:pass
else:raise AssertionError('Outside read permitted')
for path in ['asset_sdk.py','.exchange/responses/forbidden.txt']:
 try:pathlib.Path(path).write_text('probe')
 except PermissionError:pass
 else:raise AssertionError('Protected write permitted')
s=socket.socket()
try:s.connect(('127.0.0.1',9))
except PermissionError:pass
except OSError as e:raise AssertionError('Network not denied by policy: '+str(e))
else:raise AssertionError('Network permitted')
print('BOUNDARY_OK: outside reads, protected writes and network denied')
""" % str(sentinel)
    (work/'check_boundary.py').write_text(probe)
    return work


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('out', type=Path)
    parser.add_argument('--controls', type=Path, required=True)
    parser.add_argument('--preflight-only', action='store_true')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    assert json.loads((args.controls / 'verified.json').read_text())['passed']
    original = json.loads((args.controls / 'fixture-hashes.json').read_text())
    for p, h in original.items():
        assert sha(ROOT / p) == h
    manifest=json.loads((args.controls/'fixture-manifest.json').read_text())
    all_cases=manifest['cases'];data_root=ROOT/manifest['data_root'];probe_root=ROOT/manifest['probe_root']
    dev=[c for c in all_cases if c['split']=='dev' and c['profile']=='standard']
    test=[c for c in all_cases if c['split']=='heldout']
    image = json.loads(subprocess.check_output([*DOCKER, 'image', 'inspect', IMAGE], text=True))[0]
    image_id = image['Id']
    assert image_id == json.loads((args.controls / 'image.json').read_text())['Id']
    save(out / 'image.json', {k: image[k] for k in ['Id', 'Architecture', 'Os', 'Created']})
    work = workspace(out, dev, all_cases, data_root)
    protected = ['assets', 'asset_sdk.py', 'blender_lod.py', 'primitive_fit.py', 'proxy_sdk.py', 'legacy_proxy.py', 'starter.py', 'dev_eval.py', 'TASK.md', 'dev-cases.json',
                 'python', 'check_boundary.py', '.exchange']
    policy = config_args(work, protected)
    save(out / 'permission-config.json', policy)
    preflight = subprocess.run(['codex', 'sandbox', '-P', PROFILE, '-C', str(work), *policy,
                                '--', str(PYTHON), str(work / 'check_boundary.py')],
                               cwd=work, capture_output=True, text=True, timeout=30)
    save(out / 'boundary-preflight.json', dict(returncode=preflight.returncode, stdout=preflight.stdout, stderr=preflight.stderr))
    assert preflight.returncode == 0 and 'BOUNDARY_OK' in preflight.stdout, preflight.stderr
    if args.preflight_only:
        print('BOUNDARY_PREFLIGHT_PASS; NO MODEL CALLED', flush=True)
        return
    frozen = {str(p.relative_to(ROOT)): sha(p) for p in HERE.iterdir() if p.is_file()}
    frozen.update(original)
    frozen.update({str(p.relative_to(ROOT)): sha(p)
                   for p in args.controls.resolve().rglob('*') if p.is_file()})
    frozen['study-v6/generators/final.py']=sha(ROOT/'study-v6/generators/final.py')
    frozen['study-v6/proxy_sdk.py']=sha(ROOT/'study-v6/proxy_sdk.py')
    save(out / 'frozen-source-and-inputs.json', frozen)
    save(out / 'frozen-cases.json', all_cases)
    for relative in frozen:
        target = out / 'frozen-source-copy' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    readonly = {str(p.relative_to(work)): sha(p) for p in work.rglob('*') if p.is_file() and p.relative_to(work).as_posix()!='generator.py'}
    save(out / 'initial-workspace-hashes.json', readonly)
    prompt = ('Read TASK.md and improve the reusable complete-asset compiler generator.py, initialized from starter.py. '
              'First run ./python check_boundary.py and stop if it fails. You have 1800 seconds total and '
              'at most 8 authoritative dev submissions via ./python dev_eval.py generator.py. '
              'All three development families and all their deployment briefs are provided. Broker feedback '
              'scores their standard profiles only; held-out evaluation uses new mechanisms at all profiles. '
              'Inspect the meshes and improve visual topology/LOD, global resource allocation and solid '
              'collision proxies while retaining every part and required articulated motion. The preserved '
              'v6 proxy algorithm and installed public libraries are available. Finish normally before '
              'the deadline with the final generator.py ready. Do not access other projects, network, '
              'request escalation, spawn agents, hard-code geometry answers or invent test results.')
    (out / 'prompt.txt').write_text(prompt)
    command = ['codex', 'exec', '--skip-git-repo-check', '--ignore-user-config', '--ignore-rules', *policy,
               '-c', 'model_reasoning_effort="max"', '-c', 'web_search="disabled"',
               '-c', 'project_doc_max_bytes=0', '-c', 'mcp_servers={}']
    for feature in ['apps', 'plugins', 'memories', 'multi_agent', 'multi_agent_v2', 'hooks', 'goals',
                    'browser_use', 'computer_use', 'image_generation']:
        command += ['-c', 'features.' + feature + '=false']
    command += ['--model', 'gpt-6-astra', '--json', '--color', 'never', '-C', str(work),
                '--output-last-message', str(out / 'last-message.txt'), '-']
    run = dict(command=command, model='gpt-6-astra', reasoning_effort='max', tools=True,
               seconds=1800, automatic_retries=0, max_dev_submissions=8,
               codex_cli=subprocess.check_output(['codex', '--version'], text=True).strip(),
               prompt_sha256=sha(out / 'prompt.txt'))
    save(out / 'invocation.json', run)
    broker = Broker(work, out, dev, image_id, data_root, probe_root)
    broker.start()
    started = time.monotonic()
    print('START_V7_TOOL_USING_AGENT', flush=True)
    with (out / 'events.jsonl').open('wb') as stdout, (out / 'stderr.log').open('wb') as stderr:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, start_new_session=True)
        run['process_pid']=process.pid
        save(out / 'invocation.json', run)
        try:
            process.communicate(prompt.encode(), timeout=1800)
            run['status'] = 'completed' if process.returncode == 0 else 'cli_or_provider_error'
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
            run['status'] = 'incomplete_deadline'
    broker.stop.set()
    broker.thread.join(timeout=420)
    events = [json.loads(line) for line in (out / 'events.jsonl').read_text().splitlines()]
    run.update(returncode=process.returncode, wall_seconds=round(time.monotonic() - started, 3),
               dev_submissions=len(broker.records), broker_error=broker.error,
               native_session=native_session(events, out),
               usage=[e.get('usage') for e in events if e.get('type') == 'turn.completed'],
               completed_item_counts={t: sum(e.get('type') == 'item.completed' and e.get('item', {}).get('type') == t for e in events)
                                      for t in ['command_execution', 'file_change']})
    save(out / 'invocation.json', run)
    print('AGENT_END', run['status'], run['wall_seconds'], 'dev submissions', len(broker.records), flush=True)
    if run['status'] != 'completed' or broker.error or broker.thread.is_alive() or run['native_session']['status'] != 'copied_exact_fresh_session':
        return
    for relative, digest in readonly.items():
        assert sha(work / relative) == digest, 'Protected workspace changed: ' + relative
    final = work / 'generator.py'
    assert final.is_file() and not final.is_symlink() and final.stat().st_size <= 128 * 1024
    snapshots = out / 'frozen-candidates'
    snapshots.mkdir()
    shutil.copyfile(final, snapshots / 'final.py')
    first = next((r for r in broker.records if r['summary']['scorable']), None)
    if first:
        shutil.copyfile(out / first['folder'] / 'generator.py', snapshots / 'first.py')
    results, cache = {}, {}
    for name in (['first'] if first else []) + ['final']:
        path = snapshots / (name + '.py')
        code, digest = path.read_text(), sha(path)
        rows = []
        for case in test:
            key = (digest, case['id'])
            if key not in cache:
                folder = out / ('transfer-' + name) / case['id']
                folder.parent.mkdir(exist_ok=True)
                print('TRANSFER', name, case['id'], flush=True)
                cache[key] = evaluate_method(code, case, folder, image_id, data_root, probe_root)
            rows.append(cache[key])
        results[name] = dict(generator_sha256=digest, summary=aggregate(rows), cases=rows)
        save(out / 'transfer-results.json', results)
        print('TRANSFER_RESULT', name, results[name]['summary'], flush=True)
    digest = sha(snapshots / 'final.py')
    existing = next((r for r in broker.records if r['generator_sha256'] == digest), None)
    if existing:
        retention = dict(reused_exact_code_submission=existing['submission'], summary=existing['summary'], cases=existing['cases'])
    else:
        folder = out / 'final-dev'
        folder.mkdir()
        rows = [evaluate_method((snapshots / 'final.py').read_text(), c, folder / c['id'], image_id, data_root, probe_root) for c in dev]
        retention = dict(summary=aggregate(rows), cases=rows)
    save(out / 'retention.json', retention)
    for relative, digest in frozen.items():
        assert sha(ROOT / relative) == digest, 'Frozen study changed: ' + relative
    inventory = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file()}
    save(out / 'integrity.json', inventory)
    print('DONE_JOINT_V7', flush=True)


if __name__ == '__main__':
    main()
