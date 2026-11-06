"""Reproduce recorded asset outcomes offline; this does not rerun inference."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'study-v1'))
from check import evaluate, save


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--godot', required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=False)
    fixture_root = ROOT / 'study-v1/fixtures'
    manifest = json.loads((fixture_root / 'manifest.json').read_text())
    assert hashlib.sha256((ROOT / 'study-v1/scenes.json').read_bytes()).hexdigest() == manifest['scenes_sha256']
    definitions = json.loads((ROOT / 'study-v1/scenes.json').read_text())
    scenes = {s['id']:s for group in ['prior','development','transfer'] for s in definitions[group]}
    reproduced = []
    for candidate in manifest['candidates']:
        asset = fixture_root / candidate['file']
        assert hashlib.sha256(asset.read_bytes()).hexdigest() == candidate['sha256']
        for expected in candidate['outcomes']:
            scene = scenes[expected['scene_id']]
            row = evaluate(asset, scene, args.out / candidate['name'] / scene['id'], args.godot)
            # Compare observed behavior, including real candidate failures.
            # A passing replay means reproducibility, not that every asset succeeds.
            assert sorted(row['failed_checks']) == sorted(expected['failed_checks']), (candidate['name'], scene['id'], row['failed_checks'], expected['failed_checks'])
            assert row['triangle_count'] == expected['triangle_count']
            reproduced.append(dict(candidate=candidate['name'],scene=scene['id'], all_checks_pass=row['all_checks_pass'],failed_checks=row['failed_checks']))
    save(args.out / 'summary.json', dict(kind='offline record reproduction; not live model rerun or official reward',
                                      reproduced=True, observations=reproduced))
    print('STUDY_REPLAY_OK',len(reproduced),'recorded observations')


if __name__ == '__main__':
    main()
