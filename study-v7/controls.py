"""Feasible full-asset witnesses and meaningful coupled failure controls."""
import argparse,copy,json,shutil,time
from pathlib import Path
import fcl,numpy as np,trimesh
from assets import write_artifact
from evaluator import evaluate,load_source,load_artifact,check_motion,convex_object,probe_set

def save(path,r):path.write_text(json.dumps(r,indent=2)+'\n')

def main():
 p=argparse.ArgumentParser();p.add_argument('data',type=Path);p.add_argument('out',type=Path);p.add_argument('--probe-cache',type=Path);a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);cases=json.loads((a.data/'cases.json').read_text());records=[];start=time.monotonic()
 probes=a.probe_cache or out/'probes'
 if a.probe_cache is None:
  for f in sorted({c['family'] for c in cases}):
   source,meta=load_source(a.data/f);folder=probes/f;folder.mkdir(parents=True)
   for pid,m in source.items():np.savez_compressed(folder/(pid+'.npz'),**probe_set(m))
 for c in cases:
  result=evaluate(a.data/c['family'],a.data/c['family']/('reference-'+c['profile']),c,probes/c['family']);save(out/(c['id']+'.json'),result)
  assert result['guards_passed'] and result['motion']['passed'] and abs(result['score']-1)<1e-12,(c,result)
  records.append(dict(case=c['id'],family=c['family'],profile=c['profile'],evaluation=result));print('FEASIBLE',c['id'],result['score'],result['motion']['frames'],result['wall_seconds'],flush=True)
 c=next(c for c in cases if c['family']=='supply_chest' and c['profile']=='standard');folder=a.data/c['family'];source,meta=load_source(folder);visual,proxy,rig=load_artifact(folder/'reference-standard',meta);negatives={}
 def run(name,v,hs,r):
  dest=out/name;write_artifact(dest,v,hs,{**meta,'root_id':r['root_id'],'joints':r['joints']});result=evaluate(folder,dest,c,probes/c['family']);save(out/(name+'.json'),result);negatives[name]=result;return result
 r=run('no_lod',source,proxy,rig);assert r['score']==0 and 'max_triangles' in r['issues']
 r=run('missing_proxy',visual,{p:[] for p in proxy},rig);assert r['score']==0 and 'required_collision_part_missing' in r['issues']
 boxes={p:[trimesh.creation.box(m.extents,transform=trimesh.transformations.translation_matrix(m.bounds.mean(0)))] for p,m in source.items()}
 r=run('filled_apertures',visual,boxes,rig);assert r['score']<.95,r
 stale=copy.deepcopy(rig);stale['joints'][0]['pivot'][0]+=.02;r=run('misregistered_rig',visual,proxy,stale);assert r['score']==0 and 'rig_registration' in r['issues']
 noop=copy.deepcopy(rig)
 for j in noop['joints']:j['lower']=j['upper']=0.
 r=run('disabled_motion',visual,proxy,noop);assert r['score']==0 and 'required_motion_changed' in r['issues']
 inverted={p:trimesh.Trimesh(m.vertices,m.faces[:,::-1],process=False) for p,m in visual.items()}
 r=run('inverted_winding',inverted,proxy,rig);assert r['score']==0 and 'nonpositive_or_inverted_visual_solid' in r['issues']
 planar=out/'planar_proxy';shutil.copytree(folder/'reference-standard',planar)
 raw=json.loads((planar/'proxies.json').read_text());raw['base']=[[[0,0,0],[1,0,0],[0,1,0],[1,1,0]]];save(planar/'proxies.json',raw)
 try:load_artifact(planar,meta)
 except ValueError:pass
 else:raise AssertionError('Planar proxy incorrectly accepted as solid')
 # Solid containment is caught, including when no surfaces intersect.
 outer=convex_object(trimesh.creation.box([1,1,1]));inner=convex_object(trimesh.creation.box([.1,.1,.1]));assert fcl.collide(outer,inner,fcl.CollisionRequest(),fcl.CollisionResult())
 # A rod's endpoints clear the obstacle, but its intermediate sweep hits it.
 meshes={'root':trimesh.creation.box([.05,.05,.05],transform=trimesh.transformations.translation_matrix([-.2,0,.5])),
 'rod':trimesh.creation.box([1.,.035,.035],transform=trimesh.transformations.translation_matrix([.5,0,.5])),
 'obstacle':trimesh.creation.box([.08,.08,.08],transform=trimesh.transformations.translation_matrix([.5,0,.5]))}
 joints=[dict(child='rod',parent='root',type='revolute',pivot=[0,0,.5],axis=[0,0,1],lower=-np.pi/2,upper=np.pi/2),dict(child='obstacle',parent='root',type='fixed',pivot=[.5,0,.5],axis=[0,0,1],lower=0.,upper=0.)]
 m=dict(root_id='root',part_ids=list(meshes),joints=joints,knots=[dict(rod=-np.pi/2,obstacle=0.),dict(rod=np.pi/2,obstacle=0.)]);rig=dict(root_id='root',joints=joints);hs={p:[v.convex_hull] for p,v in meshes.items()}
 endpoints=[]
 for q in m['knots']:
  check=check_motion({**m,'knots':[q,q]},meshes,hs,rig);assert check['passed'];endpoints.append(check)
 sweep=check_motion(m,meshes,hs,rig);assert not sweep['passed'] and sweep['kind']=='nonadjacent_solid_collision' and sweep['verified']>0
 save(out/'intermediate_collision.json',dict(endpoints=endpoints,sweep=sweep))
 save(out/'verified.json',dict(passed=True,feasible_cases=len(records),families=len({c['family'] for c in cases}),profiles=len({c['profile'] for c in cases}),negative_controls=list(negatives),solid_containment=True,intermediate_collision=True,wall_seconds=round(time.monotonic()-start,3)))
 import hashlib
 root=Path(__file__).resolve().parents[1]
 files=[p for p in a.data.resolve().rglob('*') if p.is_file()]+[p for p in probes.resolve().rglob('*') if p.is_file()]
 save(out/'fixture-hashes.json',{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
 save(out/'fixture-manifest.json',dict(data_root=str(a.data.resolve().relative_to(root)),probe_root=str(probes.resolve().relative_to(root)),cases=cases))
 save(out/'summary.json',dict(kind='Developer controls only; not model baseline or difficulty proof',references=records,negative_controls=negatives))
 print('ALL_V7_COUPLED_CONTROLS_PASS',flush=True)

if __name__=='__main__':main()
