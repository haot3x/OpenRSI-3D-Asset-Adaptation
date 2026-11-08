"""Pre-sampling feasibility witnesses. Never delivered to the research subject."""
import copy,json,sys,time
from pathlib import Path
import numpy as np
from asset_task import load_source,write_output,preservation,envelope,evaluate
ROOT=Path(__file__).resolve().parents[1]
CONFIGS=[('dev-narrow','medical_cart001',.90,.94,'dev'),('dev-low','medical_cart001',.98,.84,'dev'),('dev-combined','medical_cart001',.88,.86,'dev'),('transfer-cart-a','medical_cart001',.84,.91,'heldout'),('transfer-cart-b','medical_cart001',.93,.80,'heldout'),('transfer-cabinet-a','cabinet_1',.88,.90,'heldout'),('transfer-cabinet-b','cabinet_1',.90,.83,'heldout')]


def witness(source,scales):
    meta=source['meta'];S=np.diag(scales);anchor=np.array(meta['anchor']);t=anchor-S@anchor;vertices={};rig=copy.deepcopy(source['rig']);joints={j['child']:j for j in source['rig']['joints']}
    for p in meta['part_ids']:
        role=meta['roles'][p]
        if role in ['body','drawer']:
            vertices[p]=source['vertices'][p]@S.T+t
            if role=='drawer':vertices[p]=vertices[p]+np.array([0,.012*scales[1],0])
        else:
            pivot=np.array(joints[joints[p]['parent']]['pivot']) if role=='wheel' else np.array(joints[p]['pivot']);delta=S@pivot+t-pivot;vertices[p]=source['vertices'][p]+delta
    for j in rig['joints']:
        p=j['child'];role=meta['roles'][p];oldp=np.array(j['pivot'])
        if role=='wheel':
            parent=np.array(joints[j['parent']]['pivot']);j['pivot']=(oldp+S@parent+t-parent).tolist()
        else:j['pivot']=(S@oldp+t).tolist()
        if role=='drawer':j['pivot'][1]+=.012*scales[1];j['upper']*=scales[1]
    return dict(meta=meta,vertices=vertices,faces=copy.deepcopy(source['faces']),rig=rig)


def main():
    out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=False);cases=[];records=[]
    for id,name,sx,sz,split in CONFIGS:
        source=load_source(ROOT/'.tools/v5-inputs'/name);scales=[sx,1.01/(sx*sz),sz];good=witness(source,scales)
        guard=preservation(source,good);assert guard['passed'],guard
        bounds=envelope(good)
        for phase,(lo,hi) in bounds.items():
            bounds[phase]=[[lo[0]-.024,lo[1]-.024,-.0025],[hi[0]+.024,hi[1]+.024,hi[2]+.024]]
        scene=dict(id=id,split=split,source=name,bounds=bounds)
        output=out/id;output.mkdir();write_output(output/'witness',good['vertices'],good['faces'],good['rig'])
        reference=evaluate(source,good,scene);assert reference['passed'],reference
        tests={};identity=evaluate(source,source,scene);tests['identity']=dict(passed=identity['passed'],failure=identity.get('first_failure'));assert not identity['passed']
        stale=copy.deepcopy(good);stale['rig']=copy.deepcopy(source['rig']);r=evaluate(source,stale,scene);assert not r['passed'];tests['stale_rig']=[i['kind'] for i in r['preservation']['issues']]
        no_capacity=witness(source,[sx,1.,sz]);r=evaluate(source,no_capacity,scene);assert not r['passed'] and any(i['kind']=='drawer_capacity_lost' for i in r['preservation']['issues']);tests['no_capacity_compensation']=True
        uniform=copy.deepcopy(source);uniform['vertices']={p:v*.85 for p,v in source['vertices'].items()};r=evaluate(source,uniform,scene);assert not r['passed'];tests['uniform_shrink']=True
        cases.append(scene);records.append(dict(id=id,split=split,reference_scales=scales,witness=reference,negative_controls=tests));print(id,'witness PASS',reference.get('sampled_frames'),'frames',flush=True)
        (out/(id+'.json')).write_text(json.dumps(records[-1],indent=2)+'\n')
    (out/'cases-private.json').write_text(json.dumps(dict(cases=cases),indent=2)+'\n');(out/'controls.json').write_text(json.dumps(records,indent=2)+'\n');(out/'verified.json').write_text(json.dumps(dict(passed=True,cases=len(cases)))+'\n')
    print('ALL_V5_CONTROLS_PASS',len(cases),flush=True)


if __name__=='__main__':main()
