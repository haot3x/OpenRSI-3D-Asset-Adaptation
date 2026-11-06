"""One prospectively frozen development/method/transfer study; never overwrite."""
import argparse
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'study-v1'
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'lib'))
from inference import generate
from container_runtime import execute
from check import measure, selection, save


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    files = list(HERE.glob('*.py')) + list(HERE.glob('*.md')) + list(HERE.glob('*.json'))
    files += list((ROOT / 'runtime').glob('*.gd')) + [ROOT / 'runtime/project.godot', ROOT / 'tools/inference.py',
              ROOT / 'lib/container_runtime.py', ROOT / 'protocol/base-case.json', ROOT / 'protocol/output.schema.json']
    files += list((ROOT / 'assets/canonical').glob('*'))
    return sorted(set(files))


def feedback(result):
    return dict(target_success=result['target_success'], retained_success=result['retained_success'],
                retained_total=result['retained_total'], strict_scene_fraction=result['strict_scene_fraction'],
                scenes=[dict(scene=r['scene_id'], metrics=r['metrics'], failed_checks=r['failed_checks']) for r in result['rows']])


def brief(current, retained):
    source = (ROOT / 'assets/canonical/source.py').read_text()
    return '''Adapt this existing interactive 3D asset to a new game scene, while preserving its identity and required functionality in retained scenes. The existing asset is a low-poly white pelican riding a turquoise bicycle; four images show the canonical asset. Return a complete self-contained Blender 4.0.2 script in final JSON fields script and design_notes. Export /output/asset.glb with the original animation export settings.

The target and retained requirements below are fixed. Produce ONE shared asset satisfying them simultaneously. All dimensions are metres in the asset's metric frame. No global translation, rescaling, deleted/invisible required parts, marker-only substitutes, changed units or evaluator changes. The roof requires peak height <= ceiling_height-clearance_margin. Aisle geometry requires abs(X) <= inner_width/2-side_margin throughout sampled riding poses. triangle_limit counts every exported triangle. Keep head, bill and body meaningful visible meshes; bounding volumes must remain >.02, >.008 and >.15 cubic metres respectively. These are minimum guards, not permission to erase the character. Preserve the original wheel, hip, crank and pedal interfaces, leg segment lengths, actual rod collisions and exported Ride motion. You may reduce tessellation, revise static posture/shape and add a rack while preserving these functions.

For a scene with dock=true: create a visible mesh DockPlate supporting a DockSocket marker at Godot [0,1.12,1.2], equivalently Blender [0,-1.2,1.12]. Its top must be horizontal at that height, covering support probes at X=+/- .10 and Godot Z=1.2+/- .08. Real rays must hit DockPlate there with an upward normal. Add coherent visible support geometry; a disconnected marker is insufficient. Scenes without dock=true do not require docking, but all retained requirements still apply.

Use only bpy, mathutils and Python standard library; no external resources, network, filesystem reads or subprocesses. Do not use tools or execute code. A separate runner validates all outputs. Return final JSON directly, with no progress messages.

Target requirements:
''' + json.dumps(current) + '\nRetained requirements:\n' + json.dumps(retained) + '\nOriginal complete source:\n' + source


def trial(out, current, retained, calls, policy, godot):
    out.mkdir(parents=True, exist_ok=False)
    save(out / 'contract.json', dict(current=current, retained=retained, maximum_calls=calls,
                                   policy_sha256=hashlib.sha256(policy.encode()).hexdigest() if policy else None))
    base = brief(current, retained) + ('\nReusable learned adaptation method:\n'+policy if policy else '')
    prompt = base
    rows = []
    images = [ROOT / 'assets/canonical' / (v+'.png') for v in ['front', 'side', 'top', 'iso']]
    for index in range(1, calls+1):
        print('CALL', out.name, index, flush=True)
        folder = out / ('attempt-'+str(index))
        invocation = generate(prompt, images, folder, dict(model='gpt-6-astra', reasoning_effort='low', seconds_per_call=180))
        row = dict(attempt=index, invocation=invocation)
        rows.append(row)
        if invocation['status'] != 'completed':
            row['status'] = 'generation_incomplete_unscored'
            save(out / 'progress.json', rows)
            break
        response = json.loads((folder / 'response.json').read_text())
        source = response.get('script')
        if not isinstance(source, str):
            row['status'] = 'invalid_response_unscored'
            save(out / 'progress.json', rows)
            break
        script = folder / 'candidate.py'
        script.write_text(source)
        row.update(source_sha256=sha(script), human_source_edits=False)
        try:
            ast.parse(source)
        except SyntaxError as error:
            row.update(status='generated_python_invalid_unscored', error=str(error))
        else:
            execution = execute(script, folder / 'execution')
            row['execution'] = execution
            if execution['status'] == 'completed':
                try:
                    evaluation = measure(folder / 'execution/asset.glb', current, retained, folder / 'evaluation', godot)
                except (RuntimeError, subprocess.TimeoutExpired) as error:
                    row.update(status='evaluator_infrastructure_error', error=str(error))
                else:
                    row.update(status='evaluated', evaluation=evaluation)
            else:
                row['status'] = execution['status']
        save(out / 'progress.json', rows)
        print('RESULT', out.name, index, row['status'], feedback(row['evaluation']) if row.get('evaluation') else '', flush=True)
        if row['status'] in ['evaluator_infrastructure_error', 'execution_incomplete', 'asset_retrieval_error']:
            break
        result = feedback(row['evaluation']) if row.get('evaluation') else dict(status=row['status'], error=row.get('error'))
        if row.get('execution') and row['execution']['status'] != 'completed':
            result['blender_error'] = (folder / 'execution/blender.stderr.log').read_text()[-2500:] + (folder / 'execution/blender.stdout.log').read_text()[-1000:]
        prompt = base+'\nPrevious complete source:\n'+source+'\nActual fixed evaluation feedback:\n'+json.dumps(result)+'\nUse the remaining generation opportunity to return complete corrected source. Preserve working requirements.'
    valid = [row for row in rows if row.get('evaluation')]
    selected = max(valid, key=selection) if valid else None
    complete = len(rows) == calls and all(r['invocation']['status'] == 'completed' and r['status'] not in ['evaluator_infrastructure_error', 'execution_incomplete', 'asset_retrieval_error'] for r in rows)
    result = dict(condition=out.name, status='complete' if complete else 'incomplete_unscored',
                  model_calls=len(rows), maximum_calls=calls, selected_attempt=selected['attempt'] if selected else None,
                  selected=feedback(selected['evaluation']) if complete and selected else None, rows=rows, official_reward=None)
    save(out / 'summary.json', result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--controls', type=Path, required=True)
    args = p.parse_args()
    out = args.out.resolve()
    control = args.controls.resolve()
    if not json.loads((control / 'summary.json').read_text())['passed']:
        raise ValueError('Passing feasibility controls required')
    godot = os.environ['GODOT_BIN']
    version = subprocess.check_output([godot, '--version'], text=True).strip()
    if not version.startswith('4.7.2'):
        raise ValueError('Godot version changed')
    out.mkdir(parents=True, exist_ok=False)
    manifest = {}
    for path in sources():
        relative = path.relative_to(ROOT)
        destination = out / 'frozen' / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        manifest[str(relative)] = sha(path)
    save(out / 'source-manifest.json', dict(started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
         source_sha256=manifest, godot_version=version, controls_summary_sha256=sha(control / 'summary.json'),
         settings=dict(model='gpt-6-astra', reasoning_effort='low', seconds_per_call=180, automatic_retries=0)))
    scenes = json.loads((HERE / 'scenes.json').read_text())
    study = dict(kind='one-method-update exploratory study, not official RSI trajectory', development=[], official_reward=None)
    start = time.monotonic()
    try:
        for scene in scenes['development']:
            result = trial(out / 'development' / scene['id'], scene, scenes['prior'], 1, '', godot)
            study['development'].append(result)
            save(out / 'progress.json', study)
        examples = []
        for result in study['development']:
            directory = out / 'development' / result['condition']
            examples.append(dict(brief=json.loads((directory / 'contract.json').read_text()),
                attempts=[dict(status=row['status'], feedback=feedback(row['evaluation']) if row.get('evaluation') else None,
                    source=(directory / ('attempt-'+str(row['attempt'])) / 'candidate.py').read_text() if row.get('source_sha256') else None) for row in result['rows']]))
        prompt = '''Write a reusable adaptation method for a fixed model that modifies interactive 3D assets across game scenes. Learn only from the supplied development attempts, including failures. Return JSON instructions of at most 2500 characters. The method should guide geometry/constraint planning, preserve old functions, manage triangle budgets and validate real interfaces. Do not claim results, hard-code a future scene, repeat the entire asset source or prescribe particular unseen thresholds. No tools or code execution; final JSON directly. Development evidence:\n'''+json.dumps(examples)
        print('METHOD_WRITE', flush=True)
        invocation = generate(prompt, [], out / 'method-call', dict(model='gpt-6-astra', reasoning_effort='low', seconds_per_call=180, schema=HERE/'policy.schema.json'))
        study['method_invocation'] = invocation
        if invocation['status'] != 'completed':
            raise RuntimeError('Method incomplete; no matched transfer comparison started')
        policy = json.loads((out / 'method-call/response.json').read_text())['instructions']
        if not isinstance(policy, str) or not 0 < len(policy) <= 2500:
            raise ValueError('Method invalid; no silent format repair')
        (out / 'policy.txt').write_text(policy)
        save(out / 'policy-freeze.json', dict(sha256=sha(out / 'policy.txt'), characters=len(policy),
              frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), transfer_started_at_freeze=False))
        retained = scenes['prior'] + scenes['development']
        current = scenes['transfer'][0]
        study['independent'] = trial(out / 'independent', current, retained, 2, '', godot)
        save(out / 'progress.json', study)
        study['policy_assisted'] = trial(out / 'policy-assisted', current, retained, 2, policy, godot)
        study['status'] = 'completed' if all(study[c]['status'] == 'complete' and study[c]['selected'] for c in ['independent', 'policy_assisted']) else 'completed_with_unscored_conditions'
    except Exception as error:
        study.update(status='incomplete_or_failed', error=type(error).__name__+': '+str(error))
        raise
    finally:
        study['wall_seconds'] = round(time.monotonic()-start, 3)
        save(out / 'summary.json', study)
        if any(sha(ROOT / relative) != expected for relative, expected in manifest.items()):
            save(out / 'source-changed.json', dict(error='Frozen study source changed while running'))
        files = [p for p in out.rglob('*') if p.is_file() and p.name != 'integrity.json' and 'empty-workspace' not in p.parts]
        save(out / 'integrity.json', dict(sha256={str(p.relative_to(out)):sha(p) for p in files}))
    print('STUDY_COMPLETE', study['status'], flush=True)


if __name__ == '__main__':
    main()
