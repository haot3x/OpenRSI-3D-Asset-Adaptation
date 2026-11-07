"""Roundtrip, feasible multi-pose, no-op and altered-geometry controls."""
import argparse
import json
import os
from pathlib import Path
import struct
from check import metadata,evaluate,save
from execute import execute
from geometry import load
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    m=metadata(out/'metadata',os.environ['GODOT_BIN'])
    results={}
    for name,noop in [('positive',False),('noop',True)]:
        script=out/(name+'.py');script.write_text('CONTROL_NOOP='+repr(noop)+'\n'+(ROOT/'study-v2/control_adapter.py').read_text())
        delivered=execute(script,out/name)
        if delivered['execution']['status']!='completed':raise RuntimeError(name+' did not export')
        results[name]=evaluate(out/name/'container/asset.glb',out/(name+'-evaluation'),m,os.environ['GODOT_BIN'])
    # Mutate one vertex, without changing the container or scene, to ensure
    # geometry preservation is an actual independent check.
    raw=bytearray((out/'positive/container/asset.glb').read_bytes());doc,_=load(out/'positive/container/asset.glb')
    n=struct.unpack_from('<I',raw,12)[0]
    a=doc['accessors'][doc['meshes'][0]['primitives'][0]['attributes']['POSITION']]
    v=doc['bufferViews'][a['bufferView']]
    at=28+n+v.get('byteOffset',0)+a.get('byteOffset',0)
    struct.pack_into('<f',raw,at,struct.unpack_from('<f',raw,at)[0]+.05)
    altered=out/'altered-geometry.glb';altered.write_bytes(raw)
    results['altered_geometry']=evaluate(altered,out/'altered-evaluation',m,os.environ['GODOT_BIN'])
    passed=(results['positive'].get('scene_fraction')==1 and results['positive']['switch_visits_passed']==7
        and results['noop'].get('scene_pass')=={'upright_kiosk':True,'low_tunnel':False,'side_window':False}
        and results['altered_geometry']['status']=='identity_invalid_unscored')
    save(out/'summary.json',dict(passed=passed,kind='developer-authored feasibility/negative controls, not model scores',results=results))
    print(json.dumps({name:{k:value.get(k) for k in ['status','scene_pass','scene_fraction','switch_visits_passed']} for name,value in results.items()},indent=2))
    print('CONTROLS_PASSED',passed)
    if not passed:raise SystemExit(1)


if __name__=='__main__':main()
