"""Immutable real-mesh kinematic actor, sampled motion and FCL scene checks."""
import itertools,json,math,sys,time
from pathlib import Path
import fcl
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'study-v3'))
from core import load_asset

Q_NAMES=['drawer_left','drawer_right','holder_left','holder_right']
Q_PARTS=['p05','p01','p07','p12']
Q_MIN=np.array([0.,0.,0.,-math.pi]);Q_MAX=np.array([.3,.3,math.pi,0.])
FIXTURES=json.loads((Path(__file__).parent/'fixtures.json').read_text())


def rz(angle):
    c,s=math.cos(angle),math.sin(angle)
    return np.array([[c,-s,0],[s,c,0],[0.,0.,1.]])


def joint_matrix(joint,amount):
    t=np.eye(4);axis=np.array(joint['axis']);pivot=np.array(joint['pivot'])
    if joint['type']=='prismatic':t[:3,3]=axis*amount
    else:
        x,y,z=axis;c,s=math.cos(amount),math.sin(amount);cross=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
        t[:3,:3]=c*np.eye(3)+(1-c)*np.outer(axis,axis)+s*cross
        t[:3,3]=pivot-t[:3,:3]@pivot
    return t


class Actor:
    def __init__(self):
        self.asset=load_asset('medical_cart001');self.ids=list(self.asset['ids'].values())
        self.points={pid:self.asset['points'][name] for name,pid in self.asset['ids'].items()}
        self.faces={pid:self.asset['faces'][name] for name,pid in self.asset['ids'].items()}
        self.joints={j['child']:j for j in self.asset['reference']['joints']}
        self.root=self.asset['reference']['root_id'];assert self.root=='p00'
        self.wheels=[j['child'] for j in self.joints.values() if j['parent']!='p00']
        self.casters=[self.joints[w]['parent'] for w in self.wheels]
        self.centers=[];self.halves=[];self.objects={}
        for pid in self.ids:
            vertices=self.points[pid];faces=self.faces[pid]
            lo,hi=vertices.min(axis=0),vertices.max(axis=0)
            self.centers.append((lo+hi)/2);self.halves.append((hi-lo)/2)
            mesh=fcl.BVHModel();mesh.beginModel(len(faces),len(vertices));mesh.addSubModel(vertices,faces);mesh.endModel()
            self.objects[pid]=fcl.CollisionObject(mesh)
        self.centers=np.array(self.centers);self.halves=np.array(self.halves)
        # Adjacent rotational joint pairs intentionally overlap at their bearings.
        # Keep body/drawer pairs checked; exclusions are fixed, never candidate-controlled.
        self.excluded={frozenset([j['parent'],j['child']]) for j in self.joints.values() if j['type']=='revolute'}
        self.pairs=[(i,j) for i,j in itertools.combinations(range(len(self.ids)),2) if frozenset([self.ids[i],self.ids[j]]) not in self.excluded]
        self.radii=[];self.wheel_xz=[]
        for wheel in self.wheels:
            p=self.points[wheel]-np.array(self.joints[wheel]['pivot'])
            self.radii.append(float(np.max(np.sqrt(p[:,0]**2+p[:,2]**2))))
            self.wheel_xz.append(p[:,[0,2]])
        # Analytic conservative vertex-speed bounds for interpolation refinement.
        holder_radius=max(float(np.linalg.norm((self.points[p]-np.array(self.joints[p]['pivot']))[:,:2],axis=1).max()) for p in Q_PARTS[2:])
        caster_radius=max(float(np.linalg.norm(self.points[p]-np.array(self.joints[p]['pivot']),axis=1).max()) for p in self.casters)
        wheel_radius=max(float(np.linalg.norm(self.points[w]-np.array(self.joints[w]['pivot']),axis=1).max()) for w in self.wheels)
        self.speed_bounds=dict(root=2.,holder=holder_radius,caster=caster_radius+wheel_radius+0.1,wheel=wheel_radius)

    def metadata(self):
        all_points=np.concatenate(list(self.points.values()))
        return dict(asset='medical_cart001',geometry='immutable source collision triangle meshes',frame='world +Z up, metres; yaw about +Z; drawer fronts face +Y at yaw 0',
            closed_bbox=[all_points.min(axis=0).tolist(),all_points.max(axis=0).tolist()],
            q_order=Q_NAMES,q_min=Q_MIN.tolist(),q_max=Q_MAX.tolist(),
            controls=[dict(name=name,part=pid,axis=self.joints[pid]['axis'],pivot=self.joints[pid]['pivot'],bbox=[self.points[pid].min(axis=0).tolist(),self.points[pid].max(axis=0).tolist()]) for name,pid in zip(Q_NAMES,Q_PARTS)],
            locomotion='Fixed controller steers and rolls all four caster assemblies. Intermediate steering arcs are checked at each segment start; extra steering time is evaluator-owned. Root has x,y,yaw only, no lifting, scaling or mesh edits.',
            self_collision_exclusions=[sorted(p) for p in sorted(self.excluded,key=lambda x:sorted(x))],speed_bounds=self.speed_bounds)

    def transforms(self,frame):
        root,q,steer,roll=map(np.array,[frame['root'],frame['q'],frame['steer'],frame['roll']])
        base=np.eye(4);base[:3,:3]=rz(root[2]);base[:2,3]=root[:2];world={self.root:base}
        amounts=dict(zip(Q_PARTS,q));amounts.update(zip(self.casters,steer));amounts.update(zip(self.wheels,roll))
        pending=dict(self.joints)
        while pending:
            resolved=[pid for pid,j in pending.items() if j['parent'] in world]
            if not resolved:raise ValueError('Unresolved actor tree')
            for pid in resolved:
                j=pending.pop(pid);world[pid]=world[j['parent']]@joint_matrix(j,float(amounts[pid]))
        return np.array([world[pid] for pid in self.ids])

    def floor_minima(self,roll):
        return [float(self.joints[w]['pivot'][2]+np.min(-math.sin(a)*p[:,0]+math.cos(a)*p[:,1])) for w,p,a in zip(self.wheels,self.wheel_xz,roll)]


def validate(candidate):
    if set(candidate)!={'poses','scenes'}:raise ValueError('Unexpected candidate keys')
    poses=candidate['poses'];scenes=candidate['scenes']
    if not 1<=len(poses)<=12 or len(scenes)!=3:raise ValueError('Pose/scene count')
    pose_map={p['id']:np.array(p['q'],dtype=float) for p in poses}
    if len(pose_map)!=len(poses) or any(not isinstance(p['id'],str) or not p['id'] or len(p['id'])>40 or set(p)!={'id','q'} for p in poses):raise ValueError('Invalid pose IDs')
    for q in pose_map.values():
        if q.shape!=(4,) or not np.isfinite(q).all() or np.any(q<Q_MIN-1e-9) or np.any(q>Q_MAX+1e-9):raise ValueError('Joint limits/finite values')
    if {s['id'] for s in scenes}!={s['id'] for s in FIXTURES['scenes']}:raise ValueError('Require each exact scene ID once')
    for scene in scenes:
        if set(scene)!={'id','keyframes'} or not 2<=len(scene['keyframes'])<=64:raise ValueError('Invalid scene/keyframe count')
        previous=-1.;total_distance=0.;last=None
        for k in scene['keyframes']:
            if set(k)!={'time','root','pose'} or k['pose'] not in pose_map:raise ValueError('Invalid keyframe fields/pose')
            t=float(k['time']);root=np.array(k['root'],dtype=float)
            if not math.isfinite(t) or not previous<t<=90 or root.shape!=(3,) or not np.isfinite(root).all() or np.any(abs(root[:2])>3) or abs(root[2])>2*math.pi+1e-9:raise ValueError('Invalid timeline/root')
            if last is not None:total_distance+=np.linalg.norm(root[:2]-last[:2])
            previous=t;last=root
        if scene['keyframes'][0]['time']!=0 or previous<2 or total_distance>12:raise ValueError('Timeline/distance cap')
    return pose_map


def blend(a,b,f):
    return {k:((1-f)*np.array(a[k])+f*np.array(b[k])).tolist() if k!='time' else (1-f)*a[k]+f*b[k] for k in a}


def motion_bound(a,b,actor):
    dr=np.array(b['root'])-np.array(a['root']);dq=abs(np.array(b['q'])-np.array(a['q']))
    return float(np.linalg.norm(dr[:2])+actor.speed_bounds['root']*abs(dr[2])+max(dq[:2])+actor.speed_bounds['holder']*max(dq[2:])+actor.speed_bounds['caster']*max(abs(np.array(b['steer'])-a['steer']))+actor.speed_bounds['wheel']*max(abs(np.array(b['roll'])-a['roll'])))


def sample(scene,poses,actor):
    keys=scene['keyframes'];root=np.array(keys[0]['root'],dtype=float);q=poses[keys[0]['pose']]
    steer=np.zeros(4);roll=np.zeros(4);clock=0.
    frames=[dict(time=clock,root=root.tolist(),q=q.tolist(),steer=steer.tolist(),roll=roll.tolist())]
    bound=FIXTURES['max_surface_step_bound_metres']
    def append(target):
        previous=frames[-1];n=max(1,math.ceil(motion_bound(previous,target,actor)/bound),math.ceil((target['time']-previous['time'])/.1))
        for i in range(1,n+1):frames.append(blend(previous,target,i/n))
        if len(frames)>18000:raise ValueError('Refined trajectory exceeds 18000-frame cap')
    for a,b in zip(keys,keys[1:]):
        ar,br=np.array(a['root']),np.array(b['root']);aq,bq=poses[a['pose']],poses[b['pose']]
        duration=b['time']-a['time'];velocity=(br[:2]-ar[:2])/duration;omega=(br[2]-ar[2])/duration
        moving=float(np.linalg.norm(velocity)+abs(omega))>1e-10
        def directions(yaw,current):
            body=rz(yaw)[:2,:2].T@velocity;values=[];speeds=[]
            for caster,old in zip(actor.casters,current):
                p=np.array(actor.joints[caster]['pivot'][:2]);v=body+omega*np.array([-p[1],p[0]])
                speed=float(np.linalg.norm(v));angle=math.atan2(v[1],v[0]) if speed>1e-10 else old
                angle=old+math.atan2(math.sin(angle-old),math.cos(angle-old));values.append(angle);speeds.append(speed)
            return np.array(values),np.array(speeds)
        if moving:
            desired,_=directions(ar[2],steer);extra=float(np.max(abs(desired-steer))/math.pi)
            if extra>1e-9:
                clock+=extra;append(dict(time=clock,root=ar.tolist(),q=aq.tolist(),steer=desired.tolist(),roll=roll.tolist()));steer=desired
        n=max(1,math.ceil(np.linalg.norm(br[:2]-ar[:2])/.01),math.ceil(abs(br[2]-ar[2])/.01),math.ceil(duration/.1),math.ceil(float(np.max(abs(bq-aq)))/.02))
        for i in range(1,n+1):
            f=i/n;root=(1-f)*ar+f*br;q=(1-f)*aq+f*bq
            if moving:
                steer,speeds=directions(root[2],steer);roll+=speeds*(duration/n)/np.array(actor.radii)
            clock+=duration/n;append(dict(time=clock,root=root.tolist(),q=q.tolist(),steer=steer.tolist(),roll=roll.tolist()))
    if clock>120:raise ValueError('Trajectory including steering exceeds 120 seconds')
    return frames


def root_matches(root,target):
    r=np.array(root);t=np.array(target)
    return bool(np.linalg.norm(r[:2]-t[:2])<=FIXTURES['endpoint_xy_tolerance'] and abs(math.atan2(math.sin(r[2]-t[2]),math.cos(r[2]-t[2])))<=FIXTURES['endpoint_yaw_tolerance'])


def event_sequence(frames,scene):
    found=[];cursor=0
    for event in scene['events']:
        beginning=None;matched=None
        for i in range(cursor,len(frames)):
            f=frames[i];q=np.array(f['q']);ok=root_matches(f['root'],event['root']) and bool(np.all(q>=np.array(event['q_min'])-1e-9) and np.all(q<=np.array(event['q_max'])+1e-9))
            if not ok:beginning=None;continue
            if beginning is None:beginning=i
            if f['time']-frames[beginning]['time']>=FIXTURES['minimum_event_hold_seconds']-1e-9:
                matched=dict(id=event['id'],start=frames[beginning]['time'],end=f['time']);cursor=i+1;break
        if matched is None:return dict(passed=False,completed=found,missing=event['id'])
        found.append(matched)
    return dict(passed=True,completed=found)


def evaluate_scene(candidate_scene,poses,scene,actor,include_frames=False):
    start=time.perf_counter();frames=sample(candidate_scene,poses,actor)
    events=event_sequence(frames,scene);endpoint=bool(root_matches(frames[0]['root'],scene['start']) and root_matches(frames[-1]['root'],scene['goal']) and np.max(abs(np.array(frames[0]['q'])))<=.01 and np.max(abs(np.array(frames[-1]['q'])))<=.01)
    obstacles=[];omin=[];omax=[]
    for o in scene['obstacles']:
        size=np.array(o['size']);center=np.array(o['center']);obstacles.append(fcl.CollisionObject(fcl.Box(*size),fcl.Transform(center)))
        omin.append(center-size/2);omax.append(center+size/2)
    omin,omax=np.array(omin),np.array(omax);clearance=FIXTURES['clearance_metres'];failure=None;verified=0
    # Failure diagnostics short-circuit at the first failed frame; passes check every frame.
    for index,frame in enumerate(frames):
        transforms=actor.transforms(frame);rot=transforms[:,:3,:3];tr=transforms[:,:3,3]
        centers=np.einsum('nij,nj->ni',rot,actor.centers)+tr;half=np.einsum('nij,nj->ni',abs(rot),actor.halves)
        lo,hi=centers-half,centers+half
        floor=actor.floor_minima(frame['roll'])
        if min(floor)<-.0025 or max(floor)>.003:
            failure=dict(kind='wheel_ground_support',frame=index,time=frame['time'],wheel_minima=floor);break
        bounds=np.array(scene['bounds'])
        potentially_out=np.where(np.any(lo<bounds[0]-1e-9,axis=1)|np.any(hi>bounds[1]+1e-9,axis=1))[0]
        for i in potentially_out:
            v=actor.points[actor.ids[i]]@rot[i].T+tr[i]
            if np.any(v<bounds[0]-1e-9) or np.any(v>bounds[1]+1e-9):
                failure=dict(kind='workspace_boundary',frame=index,time=frame['time'],part=actor.ids[i]);break
        if failure:break
        for i,pid in enumerate(actor.ids):actor.objects[pid].setTransform(fcl.Transform(rot[i],tr[i]))
        gaps=np.maximum(np.maximum(omin[None,:,:]-hi[:,None,:],lo[:,None,:]-omax[None,:,:]),0)
        near=np.argwhere(np.linalg.norm(gaps,axis=2)<clearance+1e-9)
        for i,j in near:
            obj=actor.objects[actor.ids[i]];other=obstacles[j]
            if fcl.collide(obj,other,fcl.CollisionRequest(),fcl.CollisionResult()):distance=-1.
            else:distance=float(fcl.distance(obj,other,fcl.DistanceRequest(),fcl.DistanceResult()))
            if distance<clearance-1e-8:
                failure=dict(kind='scene_clearance',frame=index,time=frame['time'],part=actor.ids[i],obstacle=scene['obstacles'][j]['id'],distance_metres=distance,root=frame['root'],q=frame['q']);break
        if failure:break
        for i,j in actor.pairs:
            if np.any(lo[i]>hi[j]) or np.any(lo[j]>hi[i]):continue
            if fcl.collide(actor.objects[actor.ids[i]],actor.objects[actor.ids[j]],fcl.CollisionRequest(),fcl.CollisionResult()):
                failure=dict(kind='non_excluded_self_collision',frame=index,time=frame['time'],parts=[actor.ids[i],actor.ids[j]],q=frame['q']);break
        if failure:break
        verified+=1
    result=dict(scene=scene['id'],passed=bool(endpoint and events['passed'] and failure is None),endpoint_passed=endpoint,events=events,motion_passed=failure is None,first_failure=failure,sampled_frames=len(frames),collision_verified_prefix_frames=verified,actual_duration_seconds=frames[-1]['time'],root_travel_metres=float(sum(np.linalg.norm(np.array(b['root'][:2])-a['root'][:2]) for a,b in zip(frames,frames[1:]))),wall_seconds=round(time.perf_counter()-start,4))
    if include_frames:result['frames']=frames
    return result


def evaluate(candidate,actor=None,include_frames=False):
    actor=actor or Actor();poses=validate(candidate);by_id={s['id']:s for s in candidate['scenes']}
    results=[evaluate_scene(by_id[s['id']],poses,s,actor,include_frames) for s in FIXTURES['scenes']]
    return dict(kind='Three public development fixtures; sampled kinematic function and clearance, not an official reward or RSI gain',passed=sum(r['passed'] for r in results),total=3,fraction=sum(r['passed'] for r in results)/3,scenes=results)
