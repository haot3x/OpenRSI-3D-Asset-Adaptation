"""Offline replay of functional-motion diagnostics; never calls a model."""
import argparse,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'study-v4'))
from motion import Actor,evaluate


def main():
    p=argparse.ArgumentParser();p.add_argument('--record',type=Path,default=ROOT/'study-v4/recorded.json');p.add_argument('--out',type=Path,required=True);p.add_argument('--export-latest',action='store_true');args=p.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);record=json.loads(args.record.read_text());actor=Actor();rows=[];latest=None
    for attempt in record['attempts']:
        if not attempt['scored']:
            rows.append(dict(attempt=attempt['attempt'],scored=False,status=attempt['status']));continue
        result=evaluate(attempt['candidate'],actor);expected=attempt['evaluation']
        assert result['passed']==expected['passed']
        for actual,wanted in zip(result['scenes'],expected['scenes']):
            for key in ['scene','passed','endpoint_passed','motion_passed']:assert actual[key]==wanted[key],(attempt['attempt'],key)
            assert actual['events']['passed']==wanted['events']['passed']
            assert [e['id'] for e in actual['events']['completed']]==[e['id'] for e in wanted['events']['completed']]
            assert (actual['first_failure'] or {}).get('kind')==(wanted['first_failure'] or {}).get('kind')
        (out/('attempt-'+str(attempt['attempt'])+'.evaluation.json')).write_text(json.dumps(result,indent=2)+'\n')
        rows.append(dict(attempt=attempt['attempt'],scored=True,passed=result['passed'],total=result['total']));latest=attempt['candidate']
        print('MOTION_V4_REPLAY',attempt['attempt'],result['passed'],'/',result['total'],flush=True)
    (out/'summary.json').write_text(json.dumps(dict(kind='Offline recorded-output reproduction, not new inference or official validation',reproduced=True,rows=rows),indent=2)+'\n')
    if args.export_latest and latest is not None:
        path=out/'latest-candidate.json';path.write_text(json.dumps(latest,indent=2)+'\n')
        subprocess.run([sys.executable,str(ROOT/'tools/export_motion_v4.py'),str(path),'--out',str(out/'export')],check=True)


if __name__=='__main__':main()
