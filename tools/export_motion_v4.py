"""Local-only GLB preview from unchanged real meshes and sampled candidate motion.

Format: https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html
Raw third-party mesh derivatives stay in ignored runs/, not the public repository.
"""
import argparse,json,math,struct,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'study-v4'))
from motion import Actor,FIXTURES,evaluate,sample,validate


def main():
    p=argparse.ArgumentParser();p.add_argument('candidate',type=Path);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    actor=Actor();candidate=json.loads(args.candidate.read_text());poses=validate(candidate)
    binary=bytearray();views=[];accessors=[];meshes=[];nodes=[dict(name='SourceZUpToGameYUp',rotation=[-math.sqrt(.5),0,0,math.sqrt(.5)],children=list(range(1,14)))];animations=[];expected=[]
    def add(array,kind,component=5126,target=None):
        array=np.asarray(array,dtype='<f4' if component==5126 else '<u4');binary.extend(b'\0'*((-len(binary))%4));offset=len(binary);raw=array.tobytes();binary.extend(raw)
        view=dict(buffer=0,byteOffset=offset,byteLength=len(raw))
        if target:view['target']=target
        views.append(view);flat=array.reshape((len(array),-1))
        accessors.append(dict(bufferView=len(views)-1,componentType=component,count=len(array),type=kind,min=flat.min(axis=0).tolist(),max=flat.max(axis=0).tolist()))
        return len(accessors)-1
    colors=[[.78,.8,.83,1],[.65,.7,.75,1],[.13,.16,.2,1],[.55,.6,.65,1]]
    materials=[dict(name='neutral_'+str(i),doubleSided=True,pbrMetallicRoughness=dict(baseColorFactor=c,metallicFactor=.15,roughnessFactor=.7)) for i,c in enumerate(colors)]
    for pid in actor.ids:
        material=2 if pid in actor.wheels else 1 if pid in ['p01','p05'] else 3 if pid in ['p07','p12'] else 0
        pos=add(actor.points[pid],'VEC3',target=34962);index=add(actor.faces[pid].reshape(-1),'SCALAR',5125,34963)
        meshes.append(dict(name=pid,primitives=[dict(attributes=dict(POSITION=pos),indices=index,material=material,mode=4)]))
        nodes.append(dict(name=pid,mesh=len(meshes)-1))
    conversion=np.array([[1,0,0,0],[0,0,1,0],[0,-1,0,0],[0,0,0,1.]])
    scene_map={s['id']:s for s in candidate['scenes']}
    for fixture in FIXTURES['scenes']:
        frames=sample(scene_map[fixture['id']],poses,actor);times=np.array([f['time'] for f in frames],dtype='<f4')
        if not np.all(np.diff(times)>0):raise ValueError('Float32 animation timestamps are not distinct; raw candidate unchanged')
        transforms=np.array([actor.transforms(f) for f in frames]);input_index=add(times,'SCALAR');samplers=[];channels=[]
        for i,pid in enumerate(actor.ids):
            translations=transforms[:,i,:3,3];quaternions=Rotation.from_matrix(transforms[:,i,:3,:3]).as_quat()
            for j in range(1,len(quaternions)):
                if quaternions[j-1]@quaternions[j]<0:quaternions[j]*=-1
            for kind,values,typ in [('translation',translations,'VEC3'),('rotation',quaternions,'VEC4')]:
                output=add(values,typ);samplers.append(dict(input=input_index,output=output,interpolation='LINEAR'));channels.append(dict(sampler=len(samplers)-1,target=dict(node=i+1,path=kind)))
        animations.append(dict(name=fixture['id'],samplers=samplers,channels=channels))
        for index in [0,len(frames)//2,len(frames)-1]:
            values=conversion[None,:,:]@transforms[index]
            expected.append(dict(clip=fixture['id'],time=float(times[index]),nodes={pid:values[i].tolist() for i,pid in enumerate(actor.ids)}))
    doc=dict(asset=dict(version='2.0',generator='OpenRSI local behavior-adapter preview; raw source meshes retained locally'),scene=0,scenes=[dict(nodes=[0])],nodes=nodes,meshes=meshes,materials=materials,animations=animations,buffers=[dict(byteLength=len(binary))],bufferViews=views,accessors=accessors)
    raw=json.dumps(doc,separators=(',',':')).encode();raw+=b' '*((-len(raw))%4);binary.extend(b'\0'*((-len(binary))%4))
    length=12+8+len(raw)+8+len(binary)
    glb=struct.pack('<III',0x46546c67,2,length)+struct.pack('<II',len(raw),0x4e4f534a)+raw+struct.pack('<II',len(binary),0x004e4942)+binary
    (out/'adapted-motion.glb').write_bytes(glb)
    (out/'roundtrip-job.json').write_text(json.dumps(dict(asset_path=str(out/'adapted-motion.glb'),mesh_count=13,triangle_count=sum(len(f) for f in actor.faces.values()),samples=expected),indent=2)+'\n')
    (out/'export.json').write_text(json.dumps(dict(kind='Local animation preview; export/import does not imply functional success',bytes=len(glb),mesh_count=13,triangle_count=sum(len(f) for f in actor.faces.values()),clips=[a['name'] for a in animations],transform_samples=len(expected)),indent=2)+'\n')
    print('GLB_EXPORTED',len(glb),'bytes;',len(animations),'clips;',len(expected),'sample poses')


if __name__=='__main__':main()
