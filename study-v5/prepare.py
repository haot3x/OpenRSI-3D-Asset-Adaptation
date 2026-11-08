"""Normalize pinned public mesh inputs; never pre-repair their contact geometry."""
import hashlib,json,math,sys,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'study-v3'))
from core import load_asset


def prepare(name,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    source=load_asset(name);xml=ET.parse(next((source['folder']/'urdf').glob('*.urdf'))).getroot()
    limits={source['ids'][j.find('child').get('link')]:j.find('limit').attrib for j in xml.findall('joint') if j.get('type')!='fixed'}
    joints=json.loads(json.dumps(source['reference']['joints']));drawers=[j for j in joints if j['type']=='prismatic']
    opening=np.array(drawers[0]['axis'])*(1 if float(limits[drawers[0]['child']]['upper'])>0 else -1)
    angle=math.pi/2-math.atan2(opening[1],opening[0]);c,s=math.cos(angle),math.sin(angle);rotation=np.array([[c,-s,0],[s,c,0],[0.,0,1.]])
    vertices={pid:source['points'][name]@rotation.T for name,pid in source['ids'].items()};faces={pid:source['faces'][name] for name,pid in source['ids'].items()}
    body=source['reference']['root_id'];v=vertices[body];allv=np.concatenate(list(vertices.values()))
    shift=np.array([-(v[:,0].min()+v[:,0].max())/2,-v[:,1].max(),-allv[:,2].min()])
    for pid in vertices:vertices[pid]+=shift
    roles={pid:'body' if pid==body else 'drawer' for pid in vertices}
    wheels=[j['child'] for j in joints if j['parent']!=body];casters=[next(j['parent'] for j in joints if j['child']==w) for w in wheels]
    for pid in wheels:roles[pid]='wheel'
    for pid in casters:roles[pid]='caster'
    for j in joints:
        pid=j['child'];j['pivot']=(rotation@np.array(j['pivot'])+shift).tolist();axis=rotation@np.array(j['axis'])
        lower,upper=float(limits[pid]['lower']),float(limits[pid]['upper'])
        if j['type']=='prismatic':
            sign=1 if upper>0 else -1;axis*=sign;lower,upper=0.,max(abs(lower),abs(upper))
        elif j['parent']==body and pid not in casters:roles[pid]='holder'
        j['axis']=axis.tolist();j['lower']=lower if math.isfinite(lower) else None;j['upper']=upper if math.isfinite(upper) else None
    anchor_z=float(np.mean([j['pivot'][2] for j in joints if j['child'] in casters])) if casters else 0.
    parts=[dict(id=p,role=roles[p],bbox=[vertices[p].min(axis=0).tolist(),vertices[p].max(axis=0).tolist()],vertices=len(vertices[p]),triangles=len(faces[p])) for p in vertices]
    meta=dict(schema='geometry-rig-v5',asset_key=hashlib.sha256(name.encode()).hexdigest()[:12],root_id=body,part_ids=list(vertices),roles=roles,joints=joints,anchor=[0.,0.,anchor_z],parts=parts,coordinate_frame='+Z up; drawer opening +Y; chassis front plane Y=0, centered on X; floor Z=0',
        normalization=dict(rotation=rotation.tolist(),translation=shift.tolist()),source_note='Pinned public meshes, normalized only; closed-pose source contacts are not repaired')
    np.savez_compressed(output/'canonical.npz',**{**{'v_'+p:v for p,v in vertices.items()},**{'f_'+p:f for p,f in faces.items()}})
    (output/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
    return meta


if __name__=='__main__':
    for name in ['medical_cart001','cabinet_1']:
        out=ROOT/'.tools/v5-inputs'/name;meta=prepare(name,out);print(name,len(meta['part_ids']),'parts',meta['anchor'])
