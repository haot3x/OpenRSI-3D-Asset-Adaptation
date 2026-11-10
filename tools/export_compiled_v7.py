"""Local GLB delivery of compiled v7 meshes, joint hierarchy and required motion."""
import argparse,json,math,struct,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'study-v7'))
from evaluator import load_source,load_artifact,rig_guard,motion_frames,transforms

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--artifact',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 source,meta=load_source(a.source);meshes,proxies,rig=load_artifact(a.artifact,meta);assert not rig_guard(meta,rig)
 ids=meta['part_ids'];index={pid:i+1 for i,pid in enumerate(ids)};joints={j['child']:j for j in rig['joints']};pivots={pid:np.array(joints[pid]['pivot']) if pid in joints else np.zeros(3) for pid in ids}
 blob=bytearray();views=[];accessors=[];nodes=[dict(name='ZUpToYUp',rotation=[-math.sqrt(.5),0,0,math.sqrt(.5)],children=[index[meta['root_id']]])];gltf_meshes=[]
 def add(values,kind,component=5126,target=None):
  values=np.asarray(values,dtype='<f4' if component==5126 else '<u4');blob.extend(b'\0'*((-len(blob))%4));start=len(blob);raw=values.tobytes();blob.extend(raw);view=dict(buffer=0,byteOffset=start,byteLength=len(raw))
  if target:view['target']=target
  views.append(view);v=values.reshape(len(values),-1);accessors.append(dict(bufferView=len(views)-1,componentType=component,count=len(values),type=kind,min=v.min(0).tolist(),max=v.max(0).tolist()));return len(accessors)-1
 colors=[[.65,.72,.8,1],[.18,.55,.65,1],[.9,.55,.15,1],[.12,.14,.17,1]]
 materials=[dict(name='role_'+str(i),doubleSided=True,pbrMetallicRoughness=dict(baseColorFactor=c,metallicFactor=.15,roughnessFactor=.5)) for i,c in enumerate(colors)]
 for pid in ids:
  mesh=meshes[pid];pos=add(mesh.vertices-pivots[pid],'VEC3',target=34962);face=add(mesh.faces.ravel(),'SCALAR',5125,34963);role=meta['roles'][pid];material=3 if role=='wheel' else 2 if role in ['grasp','aperture'] else 1 if role in ['storage','deployable','walkable'] else 0
  gltf_meshes.append(dict(name=pid,primitives=[dict(attributes=dict(POSITION=pos),indices=face,material=material,mode=4)]));parent=joints[pid]['parent'] if pid in joints else None
  node=dict(name=pid,mesh=len(gltf_meshes)-1,translation=(pivots[pid]-pivots[parent] if parent else np.zeros(3)).tolist(),extras=dict(role=role));children=[index[j['child']] for j in joints.values() if j['parent']==pid]
  if children:node['children']=children
  nodes.append(node)
 frames=motion_frames(meta);times=np.arange(len(frames))/60;time_index=add(times,'SCALAR');samplers=[];channels=[]
 for pid in ids:
  if pid not in joints:translations=np.zeros((len(frames),3));quaternions=np.tile([0,0,0,1.],(len(frames),1))
  else:
   j=joints[pid];q=np.array([f[pid] for f in frames]);translations=np.tile(pivots[pid]-pivots[j['parent']],(len(frames),1));axis=np.array(j['axis'])
   if j['type']=='prismatic':translations+=q[:,None]*axis;quaternions=np.tile([0,0,0,1.],(len(frames),1))
   elif j['type']=='fixed':quaternions=np.tile([0,0,0,1.],(len(frames),1))
   else:quaternions=Rotation.from_rotvec(q[:,None]*axis).as_quat()
   for k in range(1,len(quaternions)):
    if quaternions[k-1]@quaternions[k]<0:quaternions[k]*=-1
  for path,values,kind in [('translation',translations,'VEC3'),('rotation',quaternions,'VEC4')]:
   value_index=add(values,kind);samplers.append(dict(input=time_index,output=value_index,interpolation='LINEAR'));channels.append(dict(sampler=len(samplers)-1,target=dict(node=index[pid],path=path)))
 document=dict(asset=dict(version='2.0',generator='Original OpenRSI v7 integration compiler',copyright='Original procedural fixtures; no third-party or company geometry'),scene=0,scenes=[dict(nodes=[0])],nodes=nodes,meshes=gltf_meshes,materials=materials,animations=[dict(name='required_interactions',samplers=samplers,channels=channels)],buffers=[dict(byteLength=len(blob))],bufferViews=views,accessors=accessors)
 raw=json.dumps(document,separators=(',',':')).encode();raw+=b' '*((-len(raw))%4);blob.extend(b'\0'*((-len(blob))%4));size=12+8+len(raw)+8+len(blob)
 (a.out/'compiled.glb').write_bytes(struct.pack('<III',0x46546c67,2,size)+struct.pack('<II',len(raw),0x4e4f534a)+raw+struct.pack('<II',len(blob),0x004e4942)+blob)
 C=np.array([[1,0,0,0],[0,0,1,0],[0,-1,0,0],[0,0,0,1.]])
 selected=sorted(set([0,len(frames)//4,len(frames)//2,3*len(frames)//4,len(frames)-1]));samples=[]
 for k in selected:
  world=transforms(meta,frames[k],rig);expected={}
  for pid in ids:
   pivot=np.eye(4);pivot[:3,3]=pivots[pid];expected[pid]=(C@world[pid]@pivot).tolist()
  samples.append(dict(clip='required_interactions',time=float(times[k]),nodes=expected))
 job=dict(asset_path=str((a.out/'compiled.glb').resolve()),mesh_count=len(ids),triangle_count=sum(len(m.faces) for m in meshes.values()),parents={pid:j['parent'] for pid,j in joints.items()},samples=samples)
 (a.out/'roundtrip-job.json').write_text(json.dumps(job,indent=2)+'\n');(a.out/'export.json').write_text(json.dumps(dict(family=meta['family'],parts=len(ids),triangles=job['triangle_count'],frames=len(frames),hierarchy_edges=len(joints),sampled_transforms=len(samples)*len(ids),glb_bytes=size,proxy_hulls=sum(map(len,proxies.values()))),indent=2)+'\n');print('V7_COMPILED_GLB',meta['family'],size,'bytes',len(frames),'frames')

if __name__=='__main__':main()
