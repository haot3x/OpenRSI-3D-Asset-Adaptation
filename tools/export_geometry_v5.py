"""Local-only GLB: model-generated meshes, actual joint hierarchy and test clips."""
import argparse,json,math,struct,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'study-v5'))
from asset_task import load_source,read_output,preservation,Actor,frames


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--artifact',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);source=load_source(args.source);artifact=read_output(args.artifact,source);guard=preservation(source,artifact)
    if not guard['passed']:raise ValueError('Geometry/rig preservation failed; do not export as a validated asset')
    actor=Actor(artifact);meta=artifact['meta'];ids=meta['part_ids'];index={p:i+1 for i,p in enumerate(ids)};joints={j['child']:j for j in artifact['rig']['joints']};root=meta['root_id'];pivots={p:np.array(joints[p]['pivot']) if p in joints else np.zeros(3) for p in ids}
    binary=bytearray();views=[];accessors=[];meshes=[];nodes=[dict(name='SourceZUpToGameYUp',rotation=[-math.sqrt(.5),0,0,math.sqrt(.5)],children=[index[root]])];animations=[];expected=[]
    def add(values,kind,component=5126,target=None):
        a=np.asarray(values,dtype='<f4' if component==5126 else '<u4');binary.extend(b'\0'*((-len(binary))%4));start=len(binary);raw=a.tobytes();binary.extend(raw);view=dict(buffer=0,byteOffset=start,byteLength=len(raw))
        if target:view['target']=target
        views.append(view);flat=a.reshape((len(a),-1));accessors.append(dict(bufferView=len(views)-1,componentType=component,count=len(a),type=kind,min=flat.min(axis=0).tolist(),max=flat.max(axis=0).tolist()));return len(accessors)-1
    materials=[dict(name='neutral_'+str(i),doubleSided=True,pbrMetallicRoughness=dict(baseColorFactor=c,metallicFactor=.1,roughnessFactor=.7)) for i,c in enumerate([[.72,.76,.82,1],[.55,.62,.7,1],[.12,.14,.18,1]])]
    for pid in ids:
        positions=artifact['vertices'][pid]-pivots[pid];pos=add(positions,'VEC3',target=34962);faces=add(artifact['faces'][pid].reshape(-1),'SCALAR',5125,34963)
        role=meta['roles'][pid];material=2 if role=='wheel' else 1 if role=='drawer' else 0;meshes.append(dict(name=pid,primitives=[dict(attributes=dict(POSITION=pos),indices=faces,material=material,mode=4)]))
        parent=joints[pid]['parent'] if pid in joints else None;node=dict(name=pid,mesh=len(meshes)-1,translation=(pivots[pid]-pivots[parent] if parent else np.zeros(3)).tolist(),extras=dict(role=role))
        children=[index[j['child']] for j in joints.values() if j['parent']==pid]
        if children:node['children']=children
        if pid in joints:node['extras']['joint']=joints[pid]
        nodes.append(node)
    C=np.array([[1,0,0,0],[0,0,1,0],[0,-1,0,0],[0,0,0,1.]])
    motion=frames(artifact)
    for phase in ['transport','interaction']:
        selected=[f for f in motion if f['phase']==phase]
        if len(selected)==1:selected=selected*2
        times=np.arange(len(selected),dtype=float)/60.;time_index=add(times,'SCALAR');samplers=[];channels=[]
        for pid in ids:
            if pid==root:translations=np.zeros((len(selected),3));quaternions=np.tile([0,0,0,1.],(len(selected),1))
            else:
                j=joints[pid];base=pivots[pid]-pivots[j['parent']];axis=np.array(j['axis']);amount=np.array([f['q'].get(pid,0.) for f in selected]);translations=np.tile(base,(len(selected),1))
                if j['type']=='prismatic':translations+=amount[:,None]*axis;quaternions=np.tile([0,0,0,1.],(len(selected),1))
                else:quaternions=Rotation.from_rotvec(amount[:,None]*axis).as_quat()
                for k in range(1,len(quaternions)):
                    if quaternions[k-1]@quaternions[k]<0:quaternions[k]*=-1
            for path,values,typ in [('translation',translations,'VEC3'),('rotation',quaternions,'VEC4')]:
                output=add(values,typ);samplers.append(dict(input=time_index,output=output,interpolation='LINEAR'));channels.append(dict(sampler=len(samplers)-1,target=dict(node=index[pid],path=path)))
        animations.append(dict(name=phase,samplers=samplers,channels=channels))
        for k in sorted(set([0,len(selected)//2,len(selected)-1])):
            matrices=actor.transforms(selected[k]['q']);values={}
            for i,pid in enumerate(ids):
                placement=np.eye(4);placement[:3,3]=pivots[pid];values[pid]=(C@matrices[i]@placement).tolist()
            expected.append(dict(clip=phase,time=float(times[k]),nodes=values))
    document=dict(asset=dict(version='2.0',generator='OpenRSI v5 local parametric geometry/rig preview',copyright='Source meshes: ArtVIP through pinned Artisan-Benchmark snapshot; see source manifest'),scene=0,scenes=[dict(nodes=[0])],nodes=nodes,meshes=meshes,materials=materials,animations=animations,buffers=[dict(byteLength=len(binary))],bufferViews=views,accessors=accessors)
    raw=json.dumps(document,separators=(',',':')).encode();raw+=b' '*((-len(raw))%4);binary.extend(b'\0'*((-len(binary))%4));size=12+8+len(raw)+8+len(binary)
    glb=struct.pack('<III',0x46546c67,2,size)+struct.pack('<II',len(raw),0x4e4f534a)+raw+struct.pack('<II',len(binary),0x004e4942)+binary;(out/'adapted-geometry.glb').write_bytes(glb)
    # Independent existing GLB reader checks actual serialized vertex/index data.
    sys.path.insert(0,str(ROOT/'study-v2'))
    from geometry import load,accessor
    parsed,blob=load(out/'adapted-geometry.glb');vertex_error=0.
    for node in parsed['nodes']:
        if 'mesh' not in node:continue
        pid=node['name'];primitive=parsed['meshes'][node['mesh']]['primitives'][0]
        actual=np.array(accessor(parsed,blob,primitive['attributes']['POSITION']));wanted=artifact['vertices'][pid]-pivots[pid]
        vertex_error=max(vertex_error,float(np.max(abs(actual-wanted))))
        index_values=np.array(accessor(parsed,blob,primitive['indices'])).reshape(-1,3)
        assert np.array_equal(index_values,artifact['faces'][pid]),'GLB triangle indices changed'
    assert vertex_error<1e-6,'GLB vertex serialization changed geometry'
    parents={pid:j['parent'] for pid,j in joints.items()};job=dict(asset_path=str(out/'adapted-geometry.glb'),mesh_count=len(ids),triangle_count=sum(len(v) for v in artifact['faces'].values()),parents=parents,samples=expected)
    (out/'roundtrip-job.json').write_text(json.dumps(job,indent=2)+'\n');(out/'export.json').write_text(json.dumps(dict(kind='Local generated geometry/rig preview; export alone is not functional acceptance',bytes=size,meshes=len(ids),triangles=job['triangle_count'],clips=[a['name'] for a in animations],sampled_transforms=sum(len(v['nodes']) for v in expected),joint_edges=len(parents),capacity_ratio=guard['capacity_ratio'],body_scales=guard['body_scales'],serialized_vertex_max_error=vertex_error,triangle_indices_exact=True),indent=2)+'\n');print('GEOMETRY_V5_EXPORTED',size,'bytes',len(parents),'joint edges')


if __name__=='__main__':main()
