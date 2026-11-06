"""Fresh bounded asset-generation invocation; original native sessions stay local."""
import datetime,hashlib,json,os,shutil,signal,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def generate(prompt, images, out, spec):
    out.mkdir(parents=True, exist_ok=False)
    cwd = out / 'empty-workspace'
    cwd.mkdir()
    (out / 'prompt.txt').write_text(prompt)
    args = ['codex', 'exec', '--skip-git-repo-check', '--ignore-user-config', '--ignore-rules',
            '--sandbox', 'read-only', '-c', 'model_reasoning_effort="' + spec['reasoning_effort'] + '"',
            '-c', 'web_search="disabled"', '-c', 'project_doc_max_bytes=0']
    for feature in ['shell_tool', 'apps', 'plugins', 'memories', 'multi_agent', 'hooks', 'goals',
                    'browser_use', 'computer_use', 'image_generation']:
        args += ['-c', 'features.' + feature + '=false']
    schema = Path(spec.get('schema', ROOT / 'protocol/output.schema.json'))
    args += ['--model', spec['model'], '--json', '--color', 'never', '--output-schema',
             str(schema), '-C', str(cwd),
             '--output-last-message', str(out / 'response.json')]
    for image in images:
        args += ['--image', str(image)]
    args += ['-']
    invocation = dict(started_utc=now(), command=args, model_requested=spec['model'],
                      reasoning_effort=spec['reasoning_effort'], timeout_seconds=spec['seconds_per_call'],
                      prompt_sha256=sha(out / 'prompt.txt'), schema_sha256=sha(schema),
                      images=[dict(path=str(p), sha256=sha(p)) for p in images], automatic_retries=0,
                      native_session_ephemeral=False)
    save(out / 'invocation.json', invocation)
    start = time.monotonic()
    with (out / 'events.jsonl').open('wb') as stdout, (out / 'stderr.log').open('wb') as stderr:
        proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            proc.communicate(prompt.encode(), timeout=spec['seconds_per_call'])
            status = 'completed' if proc.returncode == 0 and (out / 'response.json').exists() else 'cli_or_provider_error'
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=5)
            status = 'incomplete_local_deadline'
    events = [json.loads(line) for line in (out / 'events.jsonl').read_text().splitlines()]
    types = sorted({e['item'].get('type', '') for e in events if 'item' in e})
    if any(t not in ['agent_message', 'reasoning'] for t in types):
        status = 'unexpected_tool_activity_no_execution'
    threads = {e['thread_id'] for e in events if e.get('type') == 'thread.started'}
    native = dict(status='not_found', reason='exact thread identity required')
    if len(threads) == 1:
        thread = next(iter(threads))
        home = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))
        matches = list((home / 'sessions').glob('**/*' + thread + '*.jsonl'))
        if len(matches) == 1:
            metadata = json.loads(matches[0].read_text().splitlines()[0])
            if metadata.get('payload', {}).get('id') == thread:
                shutil.copyfile(matches[0], out / 'native-session.jsonl')
                native = dict(status='copied_exact_fresh_session', thread_id=thread,
                              sha256=sha(out / 'native-session.jsonl'))
    invocation.update(status=status, returncode=proc.returncode, wall_seconds=round(time.monotonic() - start, 3),
                      item_types=types, usage=[e.get('usage') for e in events if e.get('type') == 'turn.completed'],
                      events_sha256=sha(out / 'events.jsonl'), native_session=native)
    save(out / 'invocation.json', invocation)
    print('GENERATION', status, invocation['wall_seconds'], native['status'], flush=True)
    return invocation
