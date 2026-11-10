"""Transparent integration baseline: QEM plus the preserved v6 final proxy method.

This is a traceable developer baseline, never substituted for a strong agent's
first or final program. No fixture constructor or reference proxy is available.
"""
import sys,time,math
import numpy as np
import trimesh,fast_simplification
from asset_sdk import load_job,write_output
from legacy_proxy import generate,limited_hull
from blender_lod import compile_visual
from primitive_fit import cylinder_fit

def compile_asset(job,meta,parts):
 start=time.monotonic();clean={}
 for p,(v,f) in parts.items():
  m=trimesh.Trimesh(v,f,process=True);m.update_faces(m.unique_faces()&m.nondegenerate_faces());m.remove_unreferenced_vertices();clean[p]=m
 components={p:list(m.split(only_watertight=False,repair=False)) for p,m in clean.items()}
 # Keep already-small components intact, rather than flattening a housing to
 # pay for an unrelated dense handle. This is part of the hardened reference.
 fixed=sum(len(c.faces) for cs in components.values() for c in cs if len(c.faces)<=128)
 dense=sum(len(c.faces) for cs in components.values() for c in cs if len(c.faces)>128)
 ratio=min(.98,max(0.,(.92*job['max_triangles']-fixed)/max(dense,1)))
 visual={}
 for p,cs in components.items():
  result=[]
  for c in cs:
   recovered=cylinder_fit(c,job['visual_tolerance_m'])
   if recovered is not None:result.append(recovered);continue
   if len(c.faces)<=128:result.append(c);continue
   count=max(12,int(len(c.faces)*ratio));v,f=fast_simplification.simplify(c.vertices,c.faces.astype(np.int32),target_count=count,agg=7.)
   result.append(trimesh.Trimesh(v,f,process=False))
  m=trimesh.util.concatenate(result);visual[p]=(m.vertices,m.faces)
 if sum(len(f) for v,f in visual.values())>job['max_triangles']:
  alternative=compile_visual(job)
  if alternative is not None and sum(len(f) for v,f in alternative.values())<sum(len(f) for v,f in visual.values()):visual=alternative
 weights=np.array([math.sqrt(len(clean[p].faces))*(1.4 if meta['roles'][p] in ['aperture','storage','grasp'] else 1.) for p in meta['part_ids']]);extra=max(0,job['max_hulls']-len(clean));raw=extra*weights/weights.sum();alloc=np.floor(raw).astype(int)+1
 for i in np.argsort(raw-np.floor(raw))[::-1][:job['max_hulls']-int(alloc.sum())]:alloc[i]+=1
 limit=job['max_vertices_per_hull']
 proxies={}
 for i,p in enumerate(meta['part_ids']):
  remaining=len(clean)-i;seconds=max(.5,(job['generation_seconds']-5-(time.monotonic()-start))/remaining)
  v,f=parts[p];proxies[p]=generate(dict(max_hulls=int(alloc[i]),max_vertices_per_hull=limit,generation_seconds=seconds),v,f)
 total=sum(len(v) for hs in proxies.values() for v in hs)
 if total>job['max_proxy_vertices']:
  cap=next(k for k in range(limit,3,-1) if sum(min(len(v),k) for hs in proxies.values() for v in hs)<=job['max_proxy_vertices'])
  proxies={p:[limited_hull(v,cap) for v in hs] for p,hs in proxies.items()}
 return visual,proxies,dict(root_id=meta['root_id'],joints=meta['joints'])

if __name__=='__main__':
 job,meta,parts=load_job(sys.argv[1]);write_output(sys.argv[2],*compile_asset(job,meta,parts))
