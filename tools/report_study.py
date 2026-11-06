"""Audit original study records, then emit a public-safe result summary."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def compact_trial(trial):
    return dict(status=trial['status'], maximum_calls=trial['maximum_calls'], model_calls=trial['model_calls'],
                selected_attempt=trial['selected_attempt'], selected=trial['selected'],
                attempts=[dict(attempt=r['attempt'], status=r['status'], model_seconds=r['invocation']['wall_seconds'],
                    source_sha256=r.get('source_sha256'),
                    target_success=r.get('evaluation', {}).get('target_success'),
                    retained_success=r.get('evaluation', {}).get('retained_success'),
                    retained_total=r.get('evaluation', {}).get('retained_total'),
                    strict_scene_fraction=r.get('evaluation', {}).get('strict_scene_fraction')) for r in trial['rows']])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    run = args.run.resolve()
    summary = json.loads((run / 'summary.json').read_text())
    integrity = json.loads((run / 'integrity.json').read_text())['sha256']
    for relative, expected in integrity.items():
        assert sha(run / relative) == expected, relative
    source = json.loads((run / 'source-manifest.json').read_text())
    for relative, expected in source['source_sha256'].items():
        assert sha(run / 'frozen' / relative) == expected, relative
    invocations = [p for p in run.rglob('invocation.json') if 'frozen' not in p.parts]
    threads = []
    for path in invocations:
        i = json.loads(path.read_text())
        assert i['model_requested'] == 'gpt-6-astra' and i['reasoning_effort'] == 'low'
        assert i['timeout_seconds'] == 180 and i['automatic_retries'] == 0
        assert sha(path.with_name('events.jsonl')) == i['events_sha256']
        native = i['native_session']
        assert native['status'] == 'copied_exact_fresh_session', path
        assert sha(path.with_name('native-session.jsonl')) == native['sha256']
        metadata = json.loads(path.with_name('native-session.jsonl').read_text().splitlines()[0])
        assert metadata['payload']['id'] == native['thread_id']
        threads.append(native['thread_id'])
        script = path.with_name('candidate.py')
        if script.exists():
            assert script.read_text() == json.loads(path.with_name('response.json').read_text())['script']
    assert len(threads) == len(set(threads))
    frozen = json.loads((run / 'policy-freeze.json').read_text())
    policy = (run / 'policy.txt').read_text()
    assert sha(run / 'policy.txt') == frozen['sha256']
    assert policy == json.loads((run / 'method-call/response.json').read_text())['instructions']
    first = run / 'independent/attempt-1'
    second = run / 'policy-assisted/attempt-1'
    assert (second / 'prompt.txt').read_text() == (first / 'prompt.txt').read_text() + '\nReusable learned adaptation method:\n' + policy
    a, b = [json.loads((f / 'invocation.json').read_text()) for f in [first, second]]
    assert a['images'] == b['images']
    stamp = datetime.datetime.fromisoformat(frozen['frozen_utc'])
    assert all(stamp < datetime.datetime.fromisoformat(i['started_utc']) for i in [a, b])
    definitions = json.loads((run / 'frozen/study-v1/scenes.json').read_text())
    target = definitions['transfer'][0]
    old = definitions['prior'] + definitions['development']
    dominates = all(target['ceiling_height']-target['clearance_margin'] <= s['ceiling_height']-s['clearance_margin']
                    and target['triangle_limit'] <= s['triangle_limit']
                    and ('inner_width' not in s or target['inner_width']/2-target['side_margin'] <= s['inner_width']/2-s['side_margin'])
                    and (not s.get('dock') or target.get('dock') and target['dock_socket'] == s['dock_socket']) for s in old)
    report = dict(kind=summary['kind'], status=summary['status'], wall_seconds=summary['wall_seconds'],
                  model_calls=len(invocations), asset_calls=len(invocations)-1, method_calls=1,
                  model='gpt-6-astra', reasoning_effort='low', seconds_per_call=180,
                  native_sessions_verified=len(threads), integrity_files_verified=len(integrity),
                  policy_characters=len(policy), policy_sha256=frozen['sha256'],
                  policy_frozen_before_transfer=True, matched_first_prompts_except_policy=True,
                  target_constraints_subsume_retention=dominates,
                  development={s['condition']:compact_trial(s) for s in summary['development']},
                  independent=compact_trial(summary['independent']), policy_assisted=compact_trial(summary['policy_assisted']),
                  official_reward=None, formal_task_ready=False,
                  limitations=['One canonical asset and one new compound scene; no unseen asset-family evaluation.',
                      'The compound target subsumes prior fixture constraints; retention here does not demonstrate nontrivial adaptation tradeoffs.',
                      'One method update and one sequential transfer pair; provider/model sampling is uncontrolled.',
                      'Calls and deadlines are matched for transfer; context tokens differ and development cost is separate.',
                      'Retained-scene success is requirement satisfaction; a failure is a regression only if prior support was verified.',
                      'Low reasoning is exploratory; the intended formal configuration still needs calibration.',
                      'Sampled geometry and support rays do not establish continuous traversal or complete semantic identity.'])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists():
        raise FileExistsError(args.out)
    args.out.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','model_calls','native_sessions_verified','integrity_files_verified']}))
    for name in ['independent','policy_assisted']:
        print(name, json.dumps(report[name]['selected']))


if __name__ == '__main__':
    main()
