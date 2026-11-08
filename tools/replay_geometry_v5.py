"""Offline CPU reproduction from measured affine mesh outputs, without executing code."""
import argparse,json,subprocess,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'study-v5'))
from asset_task import load_source,write_output,evaluate


def main():
    p=argparse.ArgumentParser();p.add_argument('--record',type=Path,default=ROOT/'study-v5/recorded.json');p.add_argument('--out',type=Path,required=True);p.add_argument('--export-example',action='store_true');args=p.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);record=json.loads(args.record.read_text());cases={c['id']:c for c in record['fixtures']};sources={};rows=[];example=None
    for name,snapshot in record['snapshots'].items():
        for item in snapshot['cases']:
            if not item['scored']:
                rows.append(dict(snapshot=name,case=item['case'],scored=False,status=item['status']));continue
            if not item['geometry']['exact_affine_reconstruction_supported']:raise ValueError('Output requires original artifact replay, not affine reconstruction')
            case=cases[item['case']];source_name=case['source']
            if source_name not in sources:sources[source_name]=load_source(ROOT/'.tools/v5-inputs'/source_name)
            source=sources[source_name];geometry=item['geometry'];vertices={p:source['vertices'][p]@np.array(m['linear']).T+np.array(m['translation']) for p,m in geometry['affines'].items()}
            candidate=dict(meta=source['meta'],vertices=vertices,faces=source['faces'],rig=geometry['rig']);actual=evaluate(source,candidate,case);expected=item['evaluation']
            assert actual['passed']==expected['passed'],(name,item['case'],'functional result mismatch')
            assert actual['preservation']['passed']==expected['preservation']['passed']
            assert sorted(i['kind'] for i in actual['preservation']['issues'])==sorted(i['kind'] for i in expected['preservation']['issues'])
            assert (actual.get('first_failure') or {}).get('kind')==(expected.get('first_failure') or {}).get('kind')
            path=out/(name+'-'+item['case']+'.json');path.write_text(json.dumps(actual,indent=2)+'\n');rows.append(dict(snapshot=name,case=item['case'],scored=True,passed=actual['passed']))
            if name=='final' and actual['passed'] and example is None:example=(source_name,candidate)
            print('V5_REPLAY',name,item['case'],actual['passed'],flush=True)
    (out/'summary.json').write_text(json.dumps(dict(kind='Offline recorded affine-output reproduction; no generated code or live model execution',rows=rows,reproduced=True),indent=2)+'\n')
    if args.export_example and example:
        source_name,candidate=example;artifact=out/'example-artifact';write_output(artifact,candidate['vertices'],candidate['faces'],candidate['rig'])
        subprocess.run([sys.executable,str(ROOT/'tools/export_geometry_v5.py'),'--source',str(ROOT/'.tools/v5-inputs'/source_name),'--artifact',str(artifact),'--out',str(out/'export')],check=True)


if __name__=='__main__':main()
