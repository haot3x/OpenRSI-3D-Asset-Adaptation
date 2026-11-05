"""Offline cross-scene regression: no model, Docker, keys, rendering or GPU needed."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate(asset, scene, out, godot):
    out.mkdir(parents=True, exist_ok=False)
    spec = json.loads((ROOT / 'protocol/base-case.json').read_text())
    spec.update(scene_id=scene['id'], ceiling_height=scene['ceiling_height'],
                clearance_margin=scene['clearance_margin'])
    job = out / 'job.json'
    job.write_text(json.dumps(dict(asset_path=str(asset.resolve()), spec=spec, render=False, output=str(out.resolve()))))
    command = [str(godot), '--headless', '--path', str(ROOT / 'runtime'), '--script',
               'res://cross_scene.gd', '--', str(job.resolve())]
    process = subprocess.run(command, capture_output=True, text=True, timeout=40)
    (out / 'stdout.log').write_text(process.stdout)
    (out / 'stderr.log').write_text(process.stderr)
    marker = 'BLENDER_ASSET_RESULT '
    diagnostics = 'CROSS_SCENE_DIAGNOSTICS '
    lines = [s[len(marker):] for s in process.stdout.splitlines() if s.startswith(marker)]
    extra = [s[len(diagnostics):] for s in process.stdout.splitlines() if s.startswith(diagnostics)]
    if process.returncode or len(lines) != 1 or len(extra) != 1 or 'SCRIPT ERROR' in process.stderr or 'ERROR:' in process.stderr:
        raise RuntimeError('Evaluator infrastructure failure; inspect ' + str(out))
    row = dict(asset_sha256=sha(asset), scene_id=scene['id'], **json.loads(lines[0]),
               geometry=json.loads(extra[0]))
    (out / 'result.json').write_text(json.dumps(row, indent=2) + '\n')
    return row


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--godot', type=Path, default=os.environ.get('GODOT_BIN'))
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--canonical', type=Path, default=ROOT / 'assets/canonical/asset.glb')
    p.add_argument('--adapted', type=Path, default=ROOT / 'assets/adapted/asset.glb')
    p.add_argument('--include-negative', action='store_true')
    args = p.parse_args()
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=False)
    if not args.godot:
        raise ValueError('Supply --godot or GODOT_BIN')
    version = subprocess.check_output([str(args.godot), '--version'], text=True).strip()
    if not version.startswith('4.7.2'):
        raise ValueError('Expected Godot 4.7.2, got ' + version)
    scenes = json.loads((ROOT / 'scenes.json').read_text())['scenes']
    rows = {}
    artifacts = [('canonical', args.canonical), ('adapted', args.adapted)]
    if args.include_negative:
        artifacts.append(('negative_static', ROOT / 'assets/negative-static.glb'))
    for name, asset in artifacts:
        rows[name] = [evaluate(asset, scene, args.out / name / scene['id'], args.godot) for scene in scenes]
    canonical_open, canonical_low = rows['canonical']
    adapted_open, adapted_low = rows['adapted']
    prior_checks = lambda r: all(value for key, value in r['checks'].items() if not key.startswith(('ceiling_', 'ground_', 'metric_', 'identity_')))
    passed = (canonical_open['all_checks_pass'] and not canonical_low['checks']['ceiling_clearance']
              and prior_checks(canonical_low) and adapted_open['all_checks_pass'] and adapted_low['all_checks_pass'])
    if args.include_negative:
        passed = passed and all(not row['checks']['ride_animation'] and not row['all_checks_pass'] for row in rows['negative_static'])
    summary = dict(kind='offline two-scene smoke; not official reward, generalization evidence or RSI trajectory',
                   passed=passed, engine=version, source_manifest_sha256=sha(ROOT / 'scenes.json'), rows=rows)
    (args.out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(dict(passed=passed, per_asset={name: [dict(scene=r['scene_id'], passed=r['passed_checks'], total=r['total_checks'], all_pass=r['all_checks_pass'], peak=r['geometry']['peak_height_metres']) for r in values] for name, values in rows.items()}), indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
