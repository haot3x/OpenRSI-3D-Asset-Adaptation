"""Offline replay of v2 controls/model assets; no live inference or Docker."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'study-v2'))
from check import metadata,evaluate,save


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--godot',required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    root=ROOT/'study-v2/fixtures';manifest=json.loads((root/'manifest.json').read_text())
    assert hashlib.sha256((ROOT/'study-v2/scenes.json').read_bytes()).hexdigest()==manifest['scenes_sha256']
    m=metadata(out/'canonical-metadata',args.godot);rows=[]
    for item in manifest['assets']:
        asset=root/item['file'];assert hashlib.sha256(asset.read_bytes()).hexdigest()==item['sha256']
        result=evaluate(asset,out/item['name'],m,args.godot)
        assert result['status']==item['expected_status'],item['name']
        if result['status']=='evaluated':
            assert result['scene_pass']==item['scene_pass'],(item['name'],result['scene_pass'],item['scene_pass'])
            for actual,expected in zip(result['visits'],item['visits']):
                assert actual['scene']==expected['scene']
                assert sorted(actual['failed_checks'])==sorted(expected['failed_checks']),(item['name'],actual['scene'],actual['failed_checks'],expected['failed_checks'])
        rows.append(dict(asset=item['name'],status=result['status'],scene_pass=result.get('scene_pass'),switch_visits_passed=result.get('switch_visits_passed')))
    save(out/'summary.json',dict(kind='offline adapter-record reproduction; not a live model rerun or official task reward',reproduced=True,rows=rows))
    print('ADAPTER_V2_REPLAY_OK',len(rows),'assets')


if __name__=='__main__':main()
