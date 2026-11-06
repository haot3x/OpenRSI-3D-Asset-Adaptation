"""Fixed study-v1 engine evaluation and prospectively declared selection."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def save(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def evaluate(asset, scene, out, godot):
    out.mkdir(parents=True, exist_ok=False)
    spec = json.loads((ROOT / 'protocol/base-case.json').read_text())
    spec.update(scene)
    spec['scene_id'] = scene['id']
    save(out / 'job.json', dict(asset_path=str(asset.resolve()), spec=spec, render=False, output=str(out.resolve())))
    command = [godot, '--headless', '--path', str(ROOT / 'runtime'), '--script', 'res://study_v1.gd', '--', str(out / 'job.json')]
    process = subprocess.run(command, capture_output=True, text=True, timeout=50)
    (out / 'stdout.log').write_text(process.stdout)
    (out / 'stderr.log').write_text(process.stderr)
    markers = ['BLENDER_ASSET_RESULT ', 'STUDY_V1_DIAGNOSTICS ']
    lines = [[s[len(m):] for s in process.stdout.splitlines() if s.startswith(m)] for m in markers]
    if process.returncode or any(len(s) != 1 for s in lines) or 'SCRIPT ERROR' in process.stderr or 'ERROR:' in process.stderr:
        raise RuntimeError('Evaluator infrastructure failure: ' + str(out))
    result = dict(scene_id=scene['id'], asset_sha256=hashlib.sha256(asset.read_bytes()).hexdigest(),
                  **json.loads(lines[0][0]), metrics=json.loads(lines[1][0]))
    result['failed_checks'] = [name for name, passed in result['checks'].items() if not passed]
    save(out / 'result.json', result)
    return result


def measure(asset, current, retained, out, godot):
    scenes = [current] + [s for s in retained if s['id'] != current['id']]
    rows = [evaluate(asset, s, out / s['id'], godot) for s in scenes]
    return dict(target_success=rows[0]['all_checks_pass'], retained_success=sum(r['all_checks_pass'] for r in rows[1:]),
                retained_total=len(rows)-1, strict_success_count=sum(r['all_checks_pass'] for r in rows),
                required_scene_count=len(rows), strict_scene_fraction=sum(r['all_checks_pass'] for r in rows)/len(rows), rows=rows)


def selection(row):
    result = row.get('evaluation')
    if not result:
        return (-1, -1, -1)
    return (result['strict_success_count'], int(result['target_success']),
            sum(r['passed_checks']/r['total_checks'] for r in result['rows'])/len(result['rows']))
