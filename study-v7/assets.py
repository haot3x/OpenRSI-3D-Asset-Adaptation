"""Original procedural game mechanisms for joint compiler integration tests.

This source is an evaluator/developer fixture generator, not subject input.
No company or third-party geometry is used. All geometry is in metres, +Z up.
"""
import copy,hashlib,json,math
from functools import lru_cache
from convex_partition import partition
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial.transform import Rotation

FAMILIES=['folding_bridge','telescoping_platform','folding_workbench','inspection_lamp','service_cart','supply_chest']
PROFILES={
 'inspection':dict(sections=48,tube_sections=16,distance_m=.8,pixel_error=2.,budget_slack=1.12),
 'standard':dict(sections=32,tube_sections=12,distance_m=1.5,pixel_error=2.,budget_slack=1.12),
 'mobile':dict(sections=24,tube_sections=10,distance_m=3.,pixel_error=2.,budget_slack=1.12),
}

def frame(center,rot=None):
 m=np.eye(4);m[:3,3]=center
 if rot is not None:m[:3,:3]=Rotation.from_euler('xyz',rot).as_matrix()
 return m.tolist()
def box(size,center,rot=None):return dict(kind='box',size=size,transform=frame(center,rot))
def cylinder(radius,height,center,rot=None):return dict(kind='cylinder',radius=radius,height=height,transform=frame(center,rot))
def ring(inner,outer,height,center,rot=None):return dict(kind='ring',inner=inner,outer=outer,height=height,transform=frame(center,rot))
def torus(major,minor,center,rot=None):return dict(kind='torus',major=major,minor=minor,transform=frame(center,rot))

def _radial(theta, radius, kind, inner=False):
 if kind=='cylinder':return radius*(1+.14*np.cos(5*theta)+.035*np.sin(3*theta))
 if kind=='ring':return radius*(1+.13*np.cos(3*theta)+.045*np.sin(5*theta))
 return radius*(1+.12*np.cos(3*theta)+.04*np.sin(5*theta))

def _solid_loft(spec,sections):
 # Designed flutes/scallops are coherent shape features, not stochastic noise.
 kind=spec['kind'];theta=np.arange(sections)*2*math.pi/sections;height=spec['height'];vertices=[];faces=[]
 if kind=='cylinder':
  for z in [-height/2,height/2]:
   r=_radial(theta,spec['radius'],kind);vertices.extend(np.c_[r*np.cos(theta),r*np.sin(theta),np.full(sections,z)])
  vertices.extend([[0,0,-height/2],[0,0,height/2]])
  for i in range(sections):
   j=(i+1)%sections;faces.extend([[i,j,sections+j],[i,sections+j,sections+i],[2*sections,j,i],[2*sections+1,sections+i,sections+j]])
 else:
  for z,radius in [(-height/2,spec['inner']),(-height/2,spec['outer']),(height/2,spec['inner']),(height/2,spec['outer'])]:
   r=_radial(theta,radius,kind);vertices.extend(np.c_[r*np.cos(theta),r*np.sin(theta),np.full(sections,z)])
  for i in range(sections):
   j=(i+1)%sections
   faces.extend([[i,2*sections+j,j],[i,2*sections+i,2*sections+j],
                 [sections+i,sections+j,3*sections+j],[sections+i,3*sections+j,3*sections+i],
                 [i,j,sections+j],[i,sections+j,sections+i],
                 [2*sections+i,3*sections+j,2*sections+j],[2*sections+i,3*sections+i,3*sections+j]])
 mesh=trimesh.Trimesh(vertices,faces,process=False)
 if mesh.volume<0:mesh.invert()
 return mesh

def _torus_points(spec,angles,around):
 result=[]
 for a in angles:
  major=float(_radial(a,spec['major'],'torus'));rise=.08*spec['major']*math.sin(2*a)
  for b in around:
   radius=spec['minor']*(1+.08*math.cos(4*b));result.append([(major+radius*math.cos(b))*math.cos(a),(major+radius*math.cos(b))*math.sin(a),rise+radius*math.sin(b)])
 return np.asarray(result)

def primitive(spec,sections=96,tube_sections=32):
 k=spec['kind']
 if k=='box':m=trimesh.creation.box(spec['size'])
 elif k in ['cylinder','ring']:m=_solid_loft(spec,sections)
 elif k=='torus':
  angles=np.arange(sections)*2*math.pi/sections;around=np.arange(tube_sections)*2*math.pi/tube_sections;vertices=_torus_points(spec,angles,around);faces=[]
  for i in range(sections):
   for j in range(tube_sections):
    a=i*tube_sections+j;b=((i+1)%sections)*tube_sections+j;c=((i+1)%sections)*tube_sections+(j+1)%tube_sections;d=i*tube_sections+(j+1)%tube_sections;faces.extend([[a,b,c],[a,c,d]])
  m=trimesh.Trimesh(vertices,faces,process=False)
  if m.volume<0:m.invert()
 else:raise ValueError(k)
 m.apply_transform(np.array(spec['transform']));return m

@lru_cache(maxsize=8)
def _cylinder_partition(sections):
 theta=np.arange(2*sections)*math.pi/sections;r=_radial(theta,1.,'cylinder');return partition(np.c_[r*np.cos(theta),r*np.sin(theta)])

def proxy_pieces(spec,sections=48,tube_sections=12):
 k=spec['kind'];transform=np.array(spec['transform'])
 if k=='box':return [primitive(spec).convex_hull]
 if k=='cylinder':
  result=[]
  for poly in _cylinder_partition(sections):
   v=np.array([[p[0]*spec['radius'],p[1]*spec['radius'],z] for z in [-spec['height']/2,spec['height']/2] for p in poly]);m=trimesh.convex.convex_hull(v);m.apply_transform(transform);result.append(m)
  return result
 result=[]
 for i in range(sections):
  angles=np.array([i,i+.5,i+1])*2*math.pi/sections
  if k in ['ring','cylinder']:
   z=np.array([-1,1])*spec['height']/2
   if k=='cylinder':
    v=np.array([[float(_radial(a,spec['radius'],k))*math.cos(a),float(_radial(a,spec['radius'],k))*math.sin(a),height] for a in angles for height in z]+[[0,0,height] for height in z])
   else:v=np.array([[float(_radial(a,radius,k))*math.cos(a),float(_radial(a,radius,k))*math.sin(a),height] for a in angles for radius in [spec['inner'],spec['outer']] for height in z])
  else:v=_torus_points(spec,angles,np.arange(tube_sections)*2*math.pi/tube_sections)
  m=trimesh.convex.convex_hull(v);m.apply_transform(transform);result.append(m)
 return result

def mechanism(family):
 parts={};joints=[];qmax={}
 def add(pid,role,shapes,parent=None,kind='fixed',pivot=(0,0,0),axis=(0,0,1),target=0.):
  parts[pid]=dict(role=role,primitives=shapes)
  if parent is not None:
   joints.append(dict(child=pid,parent=parent,type=kind,pivot=list(pivot),axis=list(axis),lower=min(0.,target),upper=max(0.,target)))
   qmax[pid]=target
 if family=='folding_bridge':
  add('base','anchor',[box([.24,.5,.16],[-.15,0,.45]),ring(.035,.055,.025,[-.05,0,.6],(math.pi/2,0,0))])
  add('deck_a','walkable',[box([.7,.42,.035],[.35,0,.6]),cylinder(.018,.7,[.35,-.23,.66],(0,math.pi/2,0)),cylinder(.018,.7,[.35,.23,.66],(0,math.pi/2,0))],'base','revolute',(0,0,.6),(0,1,0),-.9)
  add('deck_b','walkable',[box([.7,.42,.035],[1.05,0,.6]),cylinder(.018,.7,[1.05,-.23,.66],(0,math.pi/2,0)),cylinder(.018,.7,[1.05,.23,.66],(0,math.pi/2,0))],'deck_a','revolute',(.7,0,.6),(0,1,0),-1.8)
  add('ring_handle','grasp',[torus(.055,.012,[1.35,0,.66])],'deck_b',pivot=(1.35,0,.66))
 elif family=='telescoping_platform':
  add('base','anchor',[box([.3,.45,.15],[0,0,.4]),cylinder(.04,.55,[.22,-.16,.54],(0,math.pi/2,0)),cylinder(.04,.55,[.22,.16,.54],(0,math.pi/2,0))])
  add('carriage','slider',[box([.55,.35,.035],[.4,0,.62]),ring(.03,.045,.04,[.35,0,.68])],'base','prismatic',(0,0,.62),(1,0,0),.38)
  add('panel','deployable',[box([.42,.3,.025],[.68,0,.66]),torus(.045,.01,[.8,0,.7])],'carriage','revolute',(.47,0,.66),(0,1,0),-1.05)
 elif family=='folding_workbench':
  add('base','work_surface',[box([.9,.55,.045],[0,0,.9]),ring(.045,.064,.025,[.35,.12,.94])])
  add('leg_a','support',[cylinder(.026,.43,[-.32,-.17,.66]),torus(.043,.01,[-.32,-.17,.45])],'base','revolute',(-.32,-.17,.875),(0,1,0),-.8)
  add('leg_b','support',[cylinder(.026,.43,[.32,.17,.66]),torus(.043,.01,[.32,.17,.45])],'base','revolute',(.32,.17,.875),(0,1,0),.8)
  add('tray','storage',[box([.36,.3,.02],[0,.05,.81]),box([.02,.3,.07],[-.18,.05,.84]),box([.02,.3,.07],[.18,.05,.84]),box([.36,.02,.07],[0,-.1,.84])],'base','prismatic',(0,0,.81),(0,1,0),.3)
 elif family=='inspection_lamp':
  add('base','anchor',[cylinder(.13,.08,[0,0,.12]),ring(.025,.045,.025,[0,0,.185]),cylinder(.024,.27,[0,0,.315])])
  add('arm_a','link',[cylinder(.024,.36,[.18,0,.45],(0,math.pi/2,0)),ring(.028,.05,.035,[0,0,.45],(math.pi/2,0,0))],'base','revolute',(0,0,.45),(0,1,0),.45)
  add('arm_b','link',[cylinder(.021,.3,[.51,0,.45],(0,math.pi/2,0)),ring(.026,.047,.03,[.36,0,.45],(math.pi/2,0,0))],'arm_a','revolute',(.36,0,.45),(0,1,0),-.9)
  add('shade','aperture',[ring(.055,.075,.075,[.7,0,.45],(0,math.pi/2,0)),torus(.074,.009,[.745,0,.45],(0,math.pi/2,0))],'arm_b',pivot=(.7,0,.45))
 elif family=='service_cart':
  add('base','frame',[box([.55,.44,.025],[0,0,.36]),box([.55,.44,.025],[0,0,.77])]+[cylinder(.018,.39,[x,y,.565]) for x in [-.26,.26] for y in [-.2,.2]])
  for i,z in enumerate([.46,.63]):
   add('drawer_'+str(i),'storage',[box([.43,.3,.015],[0,0,z]),box([.015,.3,.08],[-.215,0,z+.04]),box([.015,.3,.08],[.215,0,z+.04]),box([.43,.015,.08],[0,-.15,z+.04]),torus(.035,.008,[0,.17,z+.04],(math.pi/2,0,0))],'base','prismatic',(0,0,z),(0,1,0),.26)
  for i,(x,y) in enumerate([(x,y) for x in [-.26,.26] for y in [-.2,.2]]):
   add('caster_'+str(i),'caster',[box([.07,.045,.015],[x,y,.32]),box([.015,.045,.06],[x-.035,y,.285]),box([.015,.045,.06],[x+.035,y,.285])],'base','continuous',(x,y,.32),(0,0,1),math.pi/2)
   add('wheel_'+str(i),'wheel',[cylinder(.052,.035,[x,y,.245],(0,math.pi/2,0))],'caster_'+str(i),'continuous',(x,y,.245),(1,0,0),2*math.pi)
  add('holder','aperture',[ring(.055,.075,.025,[.39,0,.7]),box([.15,.025,.025],[.32,0,.68])],'base','revolute',(.32,0,.7),(0,0,1),1.2)
 elif family=='supply_chest':
  add('base','housing',[box([.6,.44,.025],[0,0,.3]),box([.025,.44,.35],[-.3,0,.475]),box([.025,.44,.35],[.3,0,.475]),box([.6,.025,.35],[0,-.22,.475])])
  add('lid','cover',[box([.61,.45,.025],[0,0,.67]),torus(.055,.012,[0,.05,.72],(math.pi/2,0,0))],'base','revolute',(0,-.22,.67),(1,0,0),1.1)
  add('tray','storage',[box([.5,.36,.015],[0,0,.4]),box([.015,.36,.07],[-.25,0,.435]),box([.015,.36,.07],[.25,0,.435]),box([.5,.015,.07],[0,-.18,.435])],'base','prismatic',(0,0,.4),(0,1,0),.28)
 else:raise ValueError(family)
 root=next(iter(parts));zero={p:0. for p in qmax};knots=[zero]
 # Separate movements and simultaneous deployment expose cross-part conflicts.
 for p,target in qmax.items():
  if target:knots.extend([{**zero,p:target},zero.copy()])
 knots.extend([qmax.copy(),zero.copy()])
 return dict(family=family,root_id=root,parts=parts,joints=joints,knots=knots)

def build(family,profile='source'):
 spec=mechanism(family);params=dict(sections=96,tube_sections=32) if profile=='source' else PROFILES[profile]
 meshes={};proxies={}
 for p,part in spec['parts'].items():
  meshes[p]=trimesh.util.concatenate([primitive(s,params['sections'],params['tube_sections']) for s in part['primitives']])
  if profile!='source':proxies[p]=[h for s in part['primitives'] for h in proxy_pieces(s,48,16)]
 meta={k:copy.deepcopy(spec[k]) for k in ['family','root_id','joints','knots']};meta['roles']={p:v['role'] for p,v in spec['parts'].items()};meta['part_ids']=list(meshes)
 return meshes,proxies,meta

def write_meshes(path,meshes):
 np.savez_compressed(path,**{**{'v_'+p:np.asarray(m.vertices) for p,m in meshes.items()},**{'f_'+p:np.asarray(m.faces,dtype=np.int32) for p,m in meshes.items()}})

def write_artifact(folder,meshes,proxies,meta):
 folder=Path(folder);folder.mkdir(parents=True,exist_ok=False);write_meshes(folder/'visual.npz',meshes)
 (folder/'rig.json').write_text(json.dumps(dict(root_id=meta['root_id'],joints=meta['joints']),indent=2)+'\n')
 (folder/'proxies.json').write_text(json.dumps({p:[m.vertices.tolist() for m in hs] for p,hs in proxies.items()})+'\n')

def prepare(root):
 root=Path(root);root.mkdir(parents=True,exist_ok=False);cases=[]
 for family in FAMILIES:
  source,_,meta=build(family);folder=root/family;folder.mkdir();write_meshes(folder/'source.npz',source);(folder/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
  for profile,p in PROFILES.items():
   meshes,proxies,_=build(family,profile);write_artifact(folder/('reference-'+profile),meshes,proxies,meta)
   # Budgets derive from a functional low-complexity witness, not model scores.
   tri=sum(len(m.faces) for m in meshes.values());hulls=sum(map(len,proxies.values()));verts=sum(len(h.vertices) for hs in proxies.values() for h in hs)
   case=dict(id=family+'--'+profile,family=family,profile=profile,split='dev' if family in ['folding_bridge','folding_workbench','service_cart'] else 'heldout',max_triangles=math.ceil(tri*p['budget_slack']),max_hulls=math.ceil(hulls*p['budget_slack']),max_proxy_vertices=math.ceil(verts*p['budget_slack']),max_vertices_per_hull=64,visual_tolerance_m=2*p['distance_m']*math.tan(math.pi/6)/1080*p['pixel_error'],generation_seconds=90)
   cases.append(case)
 (root/'cases.json').write_text(json.dumps(cases,indent=2)+'\n');return cases

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();cases=prepare(a.out)
 for c in cases:print(c['id'],c['max_triangles'],c['max_hulls'],c['max_proxy_vertices'])
