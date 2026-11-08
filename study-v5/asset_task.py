"""Public portable geometry/rig SDK and fixed CPU functional development evaluator."""
import copy,itertools,json,math,zipfile
from pathlib import Path
import fcl
import numpy as np

CLEARANCE=.008
AFFINE_TOLERANCE=1e-5
MIN_CAPACITY_RATIO=.95


def json_read(path):
    return json.loads(Path(path).read_text(),parse_constant=lambda x:(_ for _ in ()).throw(ValueError('Nonfinite JSON value')))


def read_arrays(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size>32*1024**2:raise ValueError('Missing, linked or oversized mesh archive')
    with zipfile.ZipFile(path) as z:
        if len(z.infolist())>64 or sum(i.file_size for i in z.infolist())>32*1024**2:raise ValueError('Oversized decompressed mesh archive')
    with np.load(path,allow_pickle=False) as a:return {k:a[k] for k in a.files}


def load_source(folder):
    folder=Path(folder);meta=json_read(folder/'metadata.json');arrays=read_arrays(folder/'canonical.npz')
    return dict(meta=meta,vertices={p:arrays['v_'+p] for p in meta['part_ids']},faces={p:arrays['f_'+p] for p in meta['part_ids']},rig=dict(root_id=meta['root_id'],joints=copy.deepcopy(meta['joints'])))


def write_output(folder,vertices,faces,rig):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(folder/'mesh.npz',**{**{'v_'+p:v for p,v in vertices.items()},**{'f_'+p:f for p,f in faces.items()}})
    (folder/'rig.json').write_text(json.dumps(rig,indent=2,allow_nan=False)+'\n')


def read_output(folder,source):
    folder=Path(folder);rigpath=folder/'rig.json'
    if rigpath.is_symlink() or not rigpath.is_file() or rigpath.stat().st_size>128*1024:raise ValueError('Missing, linked or oversized rig')
    rig=json_read(rigpath);a=read_arrays(folder/'mesh.npz');ids=source['meta']['part_ids']
    if set(a)!={'v_'+p for p in ids}|{'f_'+p for p in ids}:raise ValueError('Require every exact source part')
    for p in ids:
        v,f=a['v_'+p],a['f_'+p]
        if v.shape!=source['vertices'][p].shape or f.ndim!=2 or f.shape[1]!=3 or len(f)>500000 or not np.issubdtype(f.dtype,np.integer):raise ValueError('Malformed geometry shape or face indices')
        if not np.isfinite(v).all() or np.any(abs(v)>5) or (f.size and (f.min()<0 or f.max()>=len(v))):raise ValueError('Nonfinite or out-of-bounds geometry')
    if set(rig)!={'root_id','joints'} or not isinstance(rig['root_id'],str) or len(rig['joints'])!=len(ids)-1:raise ValueError('Malformed rig root/joint count')
    for j in rig['joints']:
        if set(j)!={'child','parent','type','axis','pivot','lower','upper'} or j['type'] not in ['prismatic','revolute','continuous','fixed']:raise ValueError('Malformed joint fields')
        if not isinstance(j['child'],str) or not isinstance(j['parent'],str):raise ValueError('Malformed joint IDs')
        for k in ['axis','pivot']:
            v=np.asarray(j[k],dtype=float)
            if v.shape!=(3,) or not np.isfinite(v).all():raise ValueError('Malformed joint vector')
        for k in ['lower','upper']:
            if j[k] is not None and (not isinstance(j[k],(int,float)) or not math.isfinite(j[k])):raise ValueError('Malformed joint limit')
    return dict(meta=source['meta'],vertices={p:a['v_'+p] for p in ids},faces={p:a['f_'+p] for p in ids},rig=rig)


def affine_fit(before,after):
    index=np.linspace(0,len(before)-1,min(len(before),512),dtype=int);a=np.c_[before[index],np.ones(len(index))]
    fitted=np.linalg.lstsq(a,after[index],rcond=None)[0];linear=fitted[:3].T;shift=fitted[3]
    error=float(np.max(abs(before@linear.T+shift-after)))
    return linear,shift,error


def preservation(source,candidate):
    meta=source['meta'];issues=[];fits={}
    def issue(kind,part=None,**extra):issues.append(dict(kind=kind,**({'part':part} if part else {}),**extra))
    for pid in meta['part_ids']:
        if not np.array_equal(source['faces'][pid],candidate['faces'][pid]):issue('source_topology_changed',pid)
        linear,shift,error=affine_fit(source['vertices'][pid],candidate['vertices'][pid]);fits[pid]=(linear,shift)
        if error>AFFINE_TOLERANCE:issue('outside_declared_affine_family',pid,max_error=error)
        if np.max(abs(linear-np.diag(np.diag(linear))))>AFFINE_TOLERANCE:issue('shear_or_rotation_not_permitted',pid)
        if np.any(np.diag(linear)<=0):issue('non_positive_scale',pid)
    body=meta['root_id'];body_linear,body_t=fits[body];scales=np.diag(body_linear);capacity=float(np.linalg.det(body_linear));anchor=np.array(meta['anchor'])
    if np.any(scales<.70) or np.any(scales>np.array([1.15,1.75,1.15])):issue('chassis_scale_out_of_bounds',body,scales=scales.tolist())
    if np.max(abs(body_linear@anchor+body_t-anchor))>.001:issue('chassis_datum_moved',body)
    if capacity<MIN_CAPACITY_RATIO-1e-6:issue('drawer_capacity_lost',ratio=capacity)
    original={j['child']:j for j in source['rig']['joints']};new={j['child']:j for j in candidate['rig']['joints']}
    if candidate['rig']['root_id']!=body or set(new)!=set(original) or len(new)!=len(candidate['rig']['joints']):issue('rig_roles_or_root_changed')
    expected_delta={};seat={}
    for pid in meta['part_ids']:
        role=meta['roles'][pid];linear,t=fits[pid]
        if role=='body':continue
        if role=='drawer':
            if np.max(abs(linear-body_linear))>5e-5:issue('drawer_cavity_scaling_mismatch',pid)
            delta=t-body_t;seat[pid]=float(delta[1]);depth=float(np.ptp(candidate['vertices'][pid][:,1]));limit=min(.025,.06*depth)
            if max(abs(delta[0]),abs(delta[2]))>.001 or not -.001<=delta[1]<=limit+.001:issue('drawer_seating_offset_out_of_bounds',pid,offset=delta.tolist(),limit=limit)
            expected_delta[pid]=delta
        else:
            if np.max(abs(linear-np.eye(3)))>AFFINE_TOLERANCE:issue('rigid_functional_part_scaled',pid,role=role)
    # Registration comes from original attachment geometry, independent of the submitted rig.
    for pid,j in original.items():
        role=meta['roles'][pid];oldp=np.array(j['pivot'])
        if role=='wheel':
            parent=j['parent'];pj=original[parent];delta=body_linear@np.array(pj['pivot'])+body_t-np.array(pj['pivot']);expected_pivot=oldp+delta
        elif role=='drawer':expected_pivot=body_linear@oldp+body_t+expected_delta.get(pid,np.zeros(3));delta=None
        else:expected_pivot=body_linear@oldp+body_t;delta=expected_pivot-oldp
        if role not in ['drawer'] and np.max(abs(fits[pid][1]-delta))>.001:issue('rigid_part_attachment_geometry_mismatch',pid)
        if pid not in new:continue
        actual=new[pid]
        if actual['parent']!=j['parent'] or actual['type']!=j['type']:issue('joint_topology_or_type_changed',pid)
        if np.max(abs(np.array(actual['pivot'])-expected_pivot))>.001:issue('joint_pivot_not_registered_to_mesh',pid)
        if np.max(abs(np.array(actual['axis'])-j['axis']))>1e-5:issue('joint_axis_changed',pid)
        if role=='drawer':
            expected_upper=j['upper']*scales[1]
            if actual['lower'] is None or abs(actual['lower'])>1e-6 or actual['upper'] is None or not .95*expected_upper<=actual['upper']<=1.05*expected_upper:issue('drawer_functional_stroke_not_adapted',pid,expected=expected_upper)
        elif actual['lower']!=j['lower'] or actual['upper']!=j['upper']:issue('rotational_range_changed',pid)
    return dict(passed=not issues,issues=issues,body_scales=scales.tolist(),capacity_ratio=capacity,seating_offsets=seat,affines={p:dict(linear=fits[p][0].tolist(),translation=fits[p][1].tolist()) for p in fits})


def joint_transform(j,q):
    matrix=np.eye(4);axis=np.array(j['axis']);p=np.array(j['pivot'])
    if j['type']=='prismatic':matrix[:3,3]=axis*q
    else:
        x,y,z=axis;c,s=math.cos(q),math.sin(q);cross=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
        matrix[:3,:3]=c*np.eye(3)+(1-c)*np.outer(axis,axis)+s*cross;matrix[:3,3]=p-matrix[:3,:3]@p
    return matrix


class Actor:
    def __init__(self,artifact):
        self.artifact=artifact;self.meta=artifact['meta'];self.ids=self.meta['part_ids'];self.points=artifact['vertices'];self.faces=artifact['faces'];self.root=artifact['rig']['root_id'];self.joints={j['child']:j for j in artifact['rig']['joints']}
        self.objects={};self.centers=[];self.halves=[]
        for p in self.ids:
            v=self.points[p];f=self.faces[p];lo,hi=v.min(axis=0),v.max(axis=0);self.centers.append((lo+hi)/2);self.halves.append((hi-lo)/2)
            m=fcl.BVHModel();m.beginModel(len(f),len(v));m.addSubModel(v,f);m.endModel();self.objects[p]=fcl.CollisionObject(m)
        self.centers=np.array(self.centers);self.halves=np.array(self.halves)
        self.bound_points={p:np.unique(self.points[p],axis=0) for p in self.ids}
        excluded={frozenset([j['parent'],j['child']]) for j in self.joints.values() if j['type']!='prismatic'}
        self.pairs=[(a,b) for a,b in itertools.combinations(range(len(self.ids)),2) if frozenset([self.ids[a],self.ids[b]]) not in excluded]

    def transforms(self,q):
        world={self.root:np.eye(4)};pending=dict(self.joints)
        while pending:
            ready=[p for p,j in pending.items() if j['parent'] in world]
            if not ready:raise ValueError('Unresolved rig')
            for p in ready:
                j=pending.pop(p);world[p]=world[j['parent']]@joint_transform(j,q.get(p,0.))
        return np.array([world[p] for p in self.ids])

    def floor(self,q,transforms):
        support=[p for p in self.ids if self.meta['roles'][p]=='wheel'] or [self.root];values=[]
        for p in support:
            i=self.ids.index(p);t=transforms[i];values.append(float(np.min(self.bound_points[p]@t[2,:3]+t[2,3])))
        return min(values)>=-.0025 and max(values)<=.003


def frames(artifact):
    meta=artifact['meta'];joints={j['child']:j for j in artifact['rig']['joints']};q={p:0. for p in joints};result=[]
    def move(target,phase):
        nonlocal q
        count=max([1]+[math.ceil(abs(target[p]-q[p])/(.003 if joints[p]['type']=='prismatic' else .0125)) for p in q])
        for i in range(count+1):result.append(dict(phase=phase,q={p:q[p]+(target[p]-q[p])*i/count for p in q}))
        q=target.copy()
    caster=[p for p,r in meta['roles'].items() if r=='caster'];wheels=[p for p,r in meta['roles'].items() if r=='wheel']
    if caster:
        target=q.copy();target.update({p:2*math.pi for p in caster});move(target,'transport')
        q.update({p:0. for p in caster});target=q.copy();target.update({p:math.pi/2 for p in caster});move(target,'transport')
        target=q.copy();target.update({p:2*math.pi for p in wheels});move(target,'transport');q.update({p:0. for p in wheels})
        target=q.copy();target.update({p:0. for p in caster});move(target,'transport')
    else:result.append(dict(phase='transport',q=q.copy()))
    for p in joints:
        if meta['roles'][p] not in ['drawer','holder']:continue
        target=q.copy();j=joints[p];target[p]=j['upper'] if abs(j['upper'] or 0)>=abs(j['lower'] or 0) else j['lower'];move(target,'interaction');target[p]=0.;move(target,'interaction')
    return result


def envelope(artifact):
    actor=Actor(artifact);bounds={};cache={}
    for frame in frames(artifact):
        t=actor.transforms(frame['q']);lo=[];hi=[]
        for i,p in enumerate(actor.ids):
            key=t[i].tobytes()
            if p not in cache or cache[p][0]!=key:
                if np.max(abs(t[i,:3,:3]-np.eye(3)))<1e-12:a,b=actor.centers[i]-actor.halves[i]+t[i,:3,3],actor.centers[i]+actor.halves[i]+t[i,:3,3]
                else:
                    v=actor.bound_points[p]@t[i,:3,:3].T+t[i,:3,3];a,b=v.min(axis=0),v.max(axis=0)
                cache[p]=(key,a,b)
            lo.append(cache[p][1]);hi.append(cache[p][2])
        a,b=np.min(lo,axis=0),np.max(hi,axis=0);phase=frame['phase']
        if phase not in bounds:bounds[phase]=[a,b]
        else:bounds[phase]=[np.minimum(bounds[phase][0],a),np.maximum(bounds[phase][1],b)]
    return {phase:[a.tolist(),b.tolist()] for phase,(a,b) in bounds.items()}


def walls(bounds):
    lo,hi=np.array(bounds);out=[]
    for axis in [0,1,2]:
        for side in [0,1]:
            if axis==2 and side==0:continue
            size=hi-lo+1.;size[axis]=.1;center=(lo+hi)/2;center[axis]=(lo[axis]-.05) if side==0 else (hi[axis]+.05)
            out.append(dict(id=('xyz'[axis]+('min' if side==0 else 'max')),center=center,size=size,object=fcl.CollisionObject(fcl.Box(*size),fcl.Transform(center)),lo=center-size/2,hi=center+size/2))
    return out


def evaluate(source,candidate,scene):
    guard=preservation(source,candidate)
    if not guard['passed']:return dict(status='evaluated',passed=False,score=0.,preservation=guard,motion_checked=False)
    actor=Actor(candidate);motions=frames(candidate);wall_sets={k:walls(v) for k,v in scene['bounds'].items()};verified=0;failure=None
    for index,frame in enumerate(motions):
        transforms=actor.transforms(frame['q']);rot=transforms[:,:3,:3];tr=transforms[:,:3,3]
        centers=np.einsum('nij,nj->ni',rot,actor.centers)+tr;half=np.einsum('nij,nj->ni',abs(rot),actor.halves);lo,hi=centers-half,centers+half
        if not actor.floor(frame['q'],transforms):failure=dict(kind='ground_support',frame=index,phase=frame['phase']);break
        for i,p in enumerate(actor.ids):actor.objects[p].setTransform(fcl.Transform(rot[i],tr[i]))
        for wall in wall_sets[frame['phase']]:
            gaps=np.maximum(np.maximum(wall['lo']-hi,lo-wall['hi']),0);near=np.where(np.linalg.norm(gaps,axis=1)<CLEARANCE+1e-9)[0]
            for i in near:
                a,b=actor.objects[actor.ids[i]],wall['object']
                d=-1. if fcl.collide(a,b,fcl.CollisionRequest(),fcl.CollisionResult()) else float(fcl.distance(a,b,fcl.DistanceRequest(),fcl.DistanceResult()))
                if d<CLEARANCE-1e-8:failure=dict(kind='scene_clearance',frame=index,phase=frame['phase'],part=actor.ids[i],wall=wall['id'],distance=d);break
            if failure:break
        if failure:break
        for i,j in actor.pairs:
            if np.any(lo[i]>hi[j]) or np.any(lo[j]>hi[i]):continue
            if fcl.collide(actor.objects[actor.ids[i]],actor.objects[actor.ids[j]],fcl.CollisionRequest(),fcl.CollisionResult()):failure=dict(kind='self_collision',frame=index,phase=frame['phase'],parts=[actor.ids[i],actor.ids[j]]);break
        if failure:break
        verified+=1
    return dict(status='evaluated',passed=failure is None,score=1. if failure is None else 0.,preservation=guard,motion_checked=True,sampled_frames=len(motions),verified_prefix_frames=verified,first_failure=failure)
