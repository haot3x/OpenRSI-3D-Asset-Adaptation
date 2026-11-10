"""Fixed CPU coupled visual/proxy/kinematic integration evaluator.

A finite sampled verifier, not continuous collision or force simulation.
Original fixture parameters and witnesses must stay outside a subject workspace.
"""
import itertools,json,math,time,zipfile
from pathlib import Path
import fcl
import numpy as np
import trimesh
from scipy.spatial import ConvexHull,QhullError


def read_json(path,cap=16*1024**2):
 p=Path(path)
 if p.is_symlink() or not p.is_file() or p.stat().st_size>cap:raise ValueError('Missing, linked or oversized JSON')
 return json.loads(p.read_text(),parse_constant=lambda s:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))

def read_meshes(path,ids):
 p=Path(path)
 if p.is_symlink() or not p.is_file() or p.stat().st_size>64*1024**2:raise ValueError('Missing, linked or oversized mesh archive')
 with zipfile.ZipFile(p) as z:
  if len(z.infolist())!=2*len(ids) or sum(f.file_size for f in z.infolist())>96*1024**2:raise ValueError('Mesh archive shape/size violation')
 with np.load(p,allow_pickle=False) as a:
  if set(a.files)!={'v_'+p for p in ids}|{'f_'+p for p in ids}:raise ValueError('Require every semantic part exactly once')
  meshes={}
  for pid in ids:
   v,f=a['v_'+pid],a['f_'+pid]
   if v.ndim!=2 or v.shape[1]!=3 or not 4<=len(v)<=1000000 or f.ndim!=2 or f.shape[1]!=3 or not 4<=len(f)<=1000000 or not np.issubdtype(f.dtype,np.integer):raise ValueError('Malformed mesh arrays')
   if not np.isfinite(v).all() or np.any(abs(v)>10) or np.min(f)<0 or np.max(f)>=len(v):raise ValueError('Out of bounds or nonfinite mesh')
   meshes[pid]=trimesh.Trimesh(v,f,process=False)
 return meshes

def load_source(folder):
 folder=Path(folder);meta=read_json(folder/'metadata.json');return read_meshes(folder/'source.npz',meta['part_ids']),meta

def load_artifact(folder,meta):
 folder=Path(folder);meshes=read_meshes(folder/'visual.npz',meta['part_ids']);raw=read_json(folder/'proxies.json');rig=read_json(folder/'rig.json',256*1024)
 if not isinstance(raw,dict) or set(raw)!=set(meta['part_ids']):raise ValueError('Proxy semantic part set mismatch')
 proxies={}
 for pid,arrays in raw.items():
  if not isinstance(arrays,list) or len(arrays)>512:raise ValueError('Malformed or excessive proxy list')
  proxies[pid]=[]
  for points in arrays:
   v=np.asarray(points,dtype=float)
   if v.ndim!=2 or v.shape[1]!=3 or not 4<=len(v)<=4096 or not np.isfinite(v).all() or np.any(abs(v)>10):raise ValueError('Malformed convex point set')
   try:
    strict=ConvexHull(v)
    if not math.isfinite(strict.volume) or strict.volume<=1e-15:raise ValueError('Non-volumetric convex hull')
    points=v[strict.vertices];strict=ConvexHull(points);faces=strict.simplices.copy()
    normals=np.cross(points[faces[:,1]]-points[faces[:,0]],points[faces[:,2]]-points[faces[:,0]])
    reverse=np.einsum('ij,ij->i',normals,strict.equations[:,:3])<0
    faces[reverse]=faces[reverse][:,[0,2,1]]
    hull=trimesh.Trimesh(points,faces,process=False)
   except (QhullError,ValueError) as e:raise ValueError('Non-volumetric proxy') from e
   proxies[pid].append(hull)
 return meshes,proxies,rig

def transforms(meta,q,rig=None):
 rig=rig or meta;root=rig['root_id'];world={root:np.eye(4)};pending={j['child']:j for j in rig['joints']}
 for _ in range(len(pending)+1):
  ready=[pid for pid,j in pending.items() if j['parent'] in world]
  for pid in ready:
   j=pending.pop(pid);amount=q.get(pid,0.);t=np.eye(4);axis=np.array(j['axis']);p=np.array(j['pivot'])
   if j['type']=='prismatic':t[:3,3]=axis*amount
   elif j['type']!='fixed':
    x,y,z=axis;c,s=math.cos(amount),math.sin(amount);cross=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
    r=c*np.eye(3)+(1-c)*np.outer(axis,axis)+s*cross;t[:3,:3]=r;t[:3,3]=p-r@p
   world[pid]=world[j['parent']]@t
  if not pending:return world
 raise ValueError('Unresolved joint tree')

def motion_frames(meta):
 joints={j['child']:j for j in meta['joints']};result=[]
 for a,b in zip(meta['knots'],meta['knots'][1:]):
  n=max([1]+[math.ceil(abs(b[p]-a[p])/(.01 if joints[p]['type']=='prismatic' else .05)) for p in a])
  for i in range(n+1):result.append({p:a[p]+(b[p]-a[p])*i/n for p in a})
 return result

def rig_guard(meta,rig):
 issues=[]
 if not isinstance(rig,dict) or set(rig)!={'root_id','joints'} or rig['root_id']!=meta['root_id']:return ['rig_schema_or_root']
 if not isinstance(rig['joints'],list) or len(rig['joints'])!=len(meta['joints']):return ['rig_joint_count']
 actual={j.get('child'):j for j in rig['joints'] if isinstance(j,dict)}
 if set(actual)!={j['child'] for j in meta['joints']}:return ['rig_child_set']
 for j in meta['joints']:
  c=actual[j['child']]
  if set(c)!=set(j):issues.append('rig_fields');continue
  if any(c[k]!=j[k] for k in ['parent','type','lower','upper']):issues.append('required_motion_changed')
  for k in ['pivot','axis']:
   try:v=np.array(c[k],dtype=float)
   except (ValueError,TypeError):issues.append('rig_vector');continue
   if v.shape!=(3,) or not np.isfinite(v).all() or np.max(abs(v-j[k]))>(.0005 if k=='pivot' else 1e-8):issues.append('rig_registration')
 return sorted(set(issues))

def convex_object(mesh):
 faces=np.c_[np.full(len(mesh.faces),3),np.asarray(mesh.faces)].astype(np.int32).ravel()
 geom=fcl.Convex(np.asarray(mesh.vertices,dtype=float),len(mesh.faces),faces)
 return fcl.CollisionObject(geom)

def check_motion(meta,meshes,proxies,rig):
 ids=meta['part_ids'];objects={p:[convex_object(m) for m in proxies[p]] for p in ids}
 # Bearing/attachment contacts between immediate joint neighbours are legitimate.
 # Other part pairs are tested as solid unions; no parent/child containment claim.
 excluded={frozenset([j['child'],j['parent']]) for j in meta['joints'] if j['type']!='prismatic'}
 pairs=[(a,b) for a,b in itertools.combinations(ids,2) if frozenset([a,b]) not in excluded]
 vertices={p:np.asarray(meshes[p].vertices) for p in ids};proxy_bounds={p:[m.bounds for m in proxies[p]] for p in ids}
 total=motion_frames(meta);checked=0;part_cache={};pair_cache={}
 for index,q in enumerate(total):
  world=transforms(meta,q,rig);bounds={};hull_bounds={}
  for p in ids:
   t=world[p];key=t.tobytes()
   if p in part_cache and part_cache[p][0]==key:
    hull_bounds[p]=part_cache[p][1];bounds[p]=part_cache[p][2];continue
   v=vertices[p]@t[:3,:3].T+t[:3,3]
   if v[:,2].min()<-.002:return dict(passed=False,kind='visual_ground_penetration',part=p,frame=index,min_z=float(v[:,2].min()),frames=len(total),verified=checked)
   lo,hi=v.min(0),v.max(0);bounds[p]=(lo,hi);hull_bounds[p]=[]
   for m,obj in zip(proxies[p],objects[p]):
    obj.setTransform(fcl.Transform(t[:3,:3],t[:3,3]));w=m.vertices@t[:3,:3].T+t[:3,3];a,b=w.min(0),w.max(0)
    if a[2]<-.002:return dict(passed=False,kind='proxy_ground_penetration',part=p,frame=index,min_z=float(a[2]),frames=len(total),verified=checked)
    hull_bounds[p].append((a,b))
   bounds[p]=(np.min([b[0] for b in hull_bounds[p]],axis=0),np.max([b[1] for b in hull_bounds[p]],axis=0))
   part_cache[p]=(key,hull_bounds[p],bounds[p])
  for a,b in pairs:
   key=(world[a].tobytes(),world[b].tobytes())
   if pair_cache.get((a,b))==key:continue
   if np.any(bounds[a][0]>bounds[b][1]+1e-9) or np.any(bounds[b][0]>bounds[a][1]+1e-9):
    pair_cache[(a,b)]=key;continue
   # Proxy bounds can extend beyond visible geometry, so use actual hull bounds.
   for i,(alo,ahi) in enumerate(hull_bounds[a]):
    for j,(blo,bhi) in enumerate(hull_bounds[b]):
     if np.any(alo>bhi+1e-9) or np.any(blo>ahi+1e-9):continue
     if fcl.collide(objects[a][i],objects[b][j],fcl.CollisionRequest(),fcl.CollisionResult()):return dict(passed=False,kind='nonadjacent_solid_collision',parts=[a,b],frame=index,frames=len(total),verified=checked)
   pair_cache[(a,b)]=key
  checked+=1
 return dict(passed=True,frames=len(total),verified=checked,nonadjacent_pairs=len(pairs))

def surface_distances(mesh,points):
 ds=[]
 for i in range(0,len(points),256):ds.append(trimesh.proximity.closest_point(mesh,points[i:i+256])[1])
 result=np.concatenate(ds)
 if not np.isfinite(result).all():raise ValueError('Nonfinite geometric measurement')
 return result

def surface_samples(mesh,seed,count=512):
 p,_=trimesh.sample.sample_surface(mesh,count,seed=seed);v=np.unique(mesh.vertices,axis=0);idx=np.linspace(0,len(v)-1,min(256,len(v)),dtype=int)
 return np.vstack([p,v[idx]])

def proxy_hits(hulls,points):
 hit=np.zeros(len(points),dtype=bool)
 for m in hulls:
  eq=ConvexHull(m.vertices).equations;hit|=np.all(points@eq[:,:3].T+eq[:,3]<=1e-10,axis=1)
  lo,hi=m.bounds;gap=np.maximum(np.maximum(lo-points,points-hi),0);idx=np.flatnonzero((~hit)&(np.linalg.norm(gap,axis=1)<=.002))
  if len(idx):hit[idx]|=surface_distances(m,points[idx])<=.002+1e-10
 return hit

def probe_set(reference):
 # Axis and oblique grids. Outside-visible reference free space only.
 from scipy.spatial.transform import Rotation
 free=[];contact=[]
 for rotation in [np.eye(3),Rotation.from_euler('xyz',[.43,.67,.31]).as_matrix()]:
  local=reference.copy();local.vertices=local.vertices@rotation.T;lo,hi=local.bounds
  for axis in range(3):
   others=[k for k in range(3) if k!=axis];g=np.meshgrid(*[np.linspace(lo[k]+.04*(hi[k]-lo[k]),hi[k]-.04*(hi[k]-lo[k]),7) for k in others])
   for sign in [-1.,1.]:
    origins=np.zeros((49,3));dirs=np.zeros_like(origins);dirs[:,axis]=sign
    for k,v in zip(others,g):origins[:,k]=v.ravel()
    origins[:,axis]=lo[axis]-.01 if sign>0 else hi[axis]+.01
    hits,rays,_=local.ray.intersects_location(origins,dirs,multiple_hits=False);ends=np.full(len(origins),hi[axis]-lo[axis]+.02)
    for point,index in zip(hits,rays):
     ends[index]=float((point-origins[index])@dirs[index]);contact.append((point-dirs[index]*.001)@rotation);free.append((point-dirs[index]*.004)@rotation)
    for fraction in [.3,.6,.85]:free.extend((origins+dirs*(ends*fraction)[:,None])@rotation)
 free=np.unique(np.round(free,10),axis=0);contact=np.unique(np.round(contact,10),axis=0)
 free=free[surface_distances(reference,free)>.003];contact=contact[surface_distances(reference,contact)<.00175]
 if not len(free) or not len(contact):raise ValueError('Empty contact/free reference class')
 return dict(free=free,contact=contact)

def evaluate(source_dir,artifact_dir,case,probe_dir=None):
 start=time.monotonic();source,meta=load_source(source_dir);visual,proxies,rig=load_artifact(artifact_dir,meta);issues=rig_guard(meta,rig)
 counts=dict(triangles=sum(len(m.faces) for m in visual.values()),hulls=sum(map(len,proxies.values())),proxy_vertices=sum(len(m.vertices) for hs in proxies.values() for m in hs))
 if any(not math.isfinite(float(m.volume)) or m.volume<=0 for m in visual.values()):issues.append('nonpositive_or_inverted_visual_solid')
 for field,limit in [('triangles','max_triangles'),('hulls','max_hulls'),('proxy_vertices','max_proxy_vertices')]:
  if counts[field]>case[limit]:issues.append(limit)
 if any(len(m.vertices)>case['max_vertices_per_hull'] for hs in proxies.values() for m in hs):issues.append('max_vertices_per_hull')
 if any(not proxies[p] for p in meta['part_ids']):issues.append('required_collision_part_missing')
 if issues:return dict(status='evaluated',score=0.,guards_passed=False,issues=sorted(set(issues)),counts=counts,wall_seconds=round(time.monotonic()-start,3))
 rows=[]
 for i,p in enumerate(meta['part_ids']):
  d=np.r_[surface_distances(visual[p],surface_samples(source[p],100+i)),surface_distances(source[p],surface_samples(visual[p],200+i))];error=float(np.max(d));visual_quality=min(1.,case['visual_tolerance_m']/max(error,1e-15))
  if probe_dir is None:probes=probe_set(source[p])
  else:
   with np.load(Path(probe_dir)/(p+'.npz'),allow_pickle=False) as a:probes={k:a[k] for k in a.files}
  false_free=int(np.sum(~proxy_hits(proxies[p],probes['contact'])));false_blocked=int(np.sum(proxy_hits(proxies[p],probes['free'])))
  collision_quality=(1-false_free/len(probes['contact']))*(1-false_blocked/len(probes['free']))
  rows.append(dict(part=p,visual_max_error_m=error,visual_quality=visual_quality,proxy_quality=collision_quality,contact_count=len(probes['contact']),free_count=len(probes['free']),false_free=false_free,false_blocked=false_blocked,quality=visual_quality*collision_quality))
 motion=check_motion(meta,visual,proxies,rig);score=min(r['quality'] for r in rows) if motion['passed'] else 0.
 return dict(status='evaluated',score=float(score),guards_passed=True,counts=counts,parts=rows,motion=motion,wall_seconds=round(time.monotonic()-start,3))
