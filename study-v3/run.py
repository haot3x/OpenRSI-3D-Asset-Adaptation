"""Write-once local screening; no source URDF labels enter model prompts."""
import copy,hashlib,json,sys
from pathlib import Path
import numpy as np
import fcl
from core import ASSETS,ROOT,load_asset,render_parts,save,score,validate_prediction
sys.path.insert(0,str(ROOT/'tools'))
from inference import generate


def controls(asset):
    ref=asset['reference']
    pred=dict(root_id=ref['root_id'],joints=[dict(child=j['child'],parent=j['parent'],type=j['type'],axis_world=j['axis'],pivot_world=j['pivot'],confidence=1.) for j in ref['joints']])
    validate_prediction(pred,asset['input']['parts'])
    assert score(ref,pred,asset['diagonal'])['fraction']==1
    equivalent=copy.deepcopy(pred)
    for j in equivalent['joints']:
        axis=np.array(j['axis_world']);j['axis_world']=(-axis).tolist()
        j['pivot_world']=(np.array(j['pivot_world'])+(axis if j['type']=='revolute' else np.array([3.,4.,5.]))).tolist()
    assert score(ref,equivalent,asset['diagonal'])['fraction']==1
    bad=copy.deepcopy(pred)
    for j in bad['joints']:
        axis=np.array(j['axis_world']);u=np.eye(3)[np.argmin(abs(axis))];orth=np.cross(axis,u);orth/=np.linalg.norm(orth);j['axis_world']=orth.tolist()
    assert score(ref,bad,asset['diagonal'])['fraction']==0
    displaced=copy.deepcopy(pred)
    for j in displaced['joints']:
        if j['type']=='revolute':
            axis=np.array(j['axis_world']);orth=np.cross(axis,np.eye(3)[np.argmin(abs(axis))]);orth/=np.linalg.norm(orth)
            j['pivot_world']=(np.array(j['pivot_world'])+orth*asset['diagonal']).tolist()
    result=score(ref,displaced,asset['diagonal'])
    assert all(not r['passed'] for r,j in zip(result['rows'],ref['joints']) if j['type']=='revolute')
    invalid=copy.deepcopy(pred);invalid['joints'][0]['parent']=invalid['joints'][0]['child']
    try:validate_prediction(invalid,asset['input']['parts'])
    except ValueError:pass
    else:raise AssertionError('Self-cycle accepted')
    return dict(reference_pass=True,axis_sign_invariant=True,unidentifiable_pivot_invariant=True,orthogonal_axis_rejected=True,displaced_rotational_pivot_rejected=True,self_cycle_rejected=True)


def main():
    out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=False)
    a=fcl.CollisionObject(fcl.Box(1,1,1));b=fcl.CollisionObject(fcl.Box(1,1,1),fcl.Transform(np.array([2.,0,0])))
    assert fcl.collide(a,b,fcl.CollisionRequest(),fcl.CollisionResult())==0
    b.setTranslation(np.array([.25,0,0]));assert fcl.collide(a,b,fcl.CollisionRequest(),fcl.CollisionResult())>0
    assets=[load_asset(name) for name in ASSETS]
    save(out/'controls.json',dict(fcl_boxes_pass=True,assets={a['name']:controls(a) for a in assets}))
    frozen={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'study-v3').glob('*')) if p.is_file()}
    save(out/'frozen-source.json',frozen)
    records=[]
    for asset in assets:
        d=out/asset['name'];d.mkdir();render_parts(asset,d/'views')
        save(d/'input.json',asset['input']);save(d/'reference-private.json',asset['reference'])
        prompt='''Recover the kinematic mechanism of this real articulated asset from the supplied images and geometry measurements. Return only the required JSON. Images in order: original closed appearance, original open appearance, then anonymous-part front, side, isometric surface views. Geometry views and numerical coordinates share world +Z up in metres; original reference images have unspecified camera orientation. Infer one root and exactly one joint per other supplied part. Recover parent, fixed/revolute/prismatic type, world-space axis and a point on its axis. Use geometric dimensions to estimate pivot positions; prismatic pivot can be [0,0,0]. Axis sign is irrelevant. Parts are already segmented but IDs carry no semantics. No tools are available. You must infer from inputs, not access any original dataset annotations. Confidence is 0..1.\nDescription:\n'''+(asset['folder']/'prompt.txt').read_text()+'\nGeometry:\n'+json.dumps(asset['input'])
        images=[asset['folder']/'close.png',asset['folder']/'open.png']+[d/'views'/(v+'.png') for v in ['front','side','iso']]
        print('START',asset['name'],flush=True)
        invocation=generate(prompt,images,d/'generation',dict(model='gpt-6-astra',reasoning_effort='max',seconds_per_call=300,schema=ROOT/'study-v3/prediction.schema.json'))
        record=dict(asset=asset['name'],status=invocation['status'],seconds=invocation['wall_seconds'])
        records.append(record)
        if invocation['status']!='completed' or invocation['native_session']['status']!='copied_exact_fresh_session':
            record['scored']=False;save(out/'results.json',records);break
        try:
            prediction=json.loads((d/'generation/response.json').read_text());validate_prediction(prediction,asset['input']['parts'])
            result=score(asset['reference'],prediction,asset['diagonal']);save(d/'score.json',result);record.update(scored=True,result=result)
        except (ValueError,KeyError,TypeError) as error:
            record.update(scored=False,error=str(error));save(out/'results.json',records);break
        save(out/'results.json',records);print('SCORE',asset['name'],result['correct'],result['joint_count'],flush=True)
    print('DONE',len(records),flush=True)


if __name__=='__main__':main()
