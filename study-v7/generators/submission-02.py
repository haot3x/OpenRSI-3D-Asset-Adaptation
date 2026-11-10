"""Complete-asset compiler: geometric LOD and resource-aware solid proxies."""
import os
os.environ.setdefault('OMP_NUM_THREADS', '2')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
import sys, time, math, heapq
import numpy as np
import trimesh, fast_simplification
from scipy.spatial import ConvexHull, cKDTree
from asset_sdk import load_job, write_output
from legacy_proxy import generate, limited_hull, planar_decompose


def clean_mesh(v, f):
    m = trimesh.Trimesh(v, f, process=True)
    m.update_faces(m.unique_faces() & m.nondegenerate_faces())
    m.remove_unreferenced_vertices()
    return m


def extrusion(m):
    """Recover an exact two-plane extrusion, including holes and concave rims."""
    v = np.asarray(m.vertices)
    if len(v) < 8:
        return None
    keys, inv = np.unique(np.round(m.face_normals, 6), axis=0, return_inverse=True)
    weights = np.bincount(inv, weights=m.area_faces)
    candidates = keys[np.argsort(weights)[::-1][:256]]
    scale = max(float(np.max(m.extents)), 1e-3)
    eps = max(1e-8, scale * 2e-7)
    for axis in candidates:
        if np.linalg.norm(axis) < .5:
            continue
        axis = axis / np.linalg.norm(axis)
        z = v @ axis;lo, hi = z.min(), z.max()
        if hi - lo < eps * 10 or np.max(np.minimum(z-lo, hi-z)) > eps:
            continue
        capface = np.flatnonzero(np.max(z[m.faces]-lo, axis=1) < eps)
        if len(capface) < 2:
            continue
        axis = -np.asarray(m.face_normals[capface[0]])
        z = v @ axis;lo, hi = z.min(), z.max()
        if np.max(np.minimum(z-lo, hi-z)) > eps:
            continue
        u = np.cross(axis, np.eye(3)[np.argmin(abs(axis))]);u /= np.linalg.norm(u)
        w = np.cross(axis, u)
        uv = np.column_stack((v @ u, v @ w))
        labels = (z > (lo+hi)*.5).astype(int)
        q, first, ids = np.unique(np.round(uv / eps).astype(np.int64), axis=0, return_index=True, return_inverse=True)
        xy = uv[first]
        if len(np.unique(ids[labels == 0])) != len(xy) or len(np.unique(ids[labels == 1])) != len(xy):
            continue
        cap = ids[m.faces[np.max(z[m.faces]-lo, axis=1) < eps]]
        edges = np.sort(np.concatenate((cap[:,[0,1]],cap[:,[1,2]],cap[:,[2,0]])), axis=1)
        edges, count = np.unique(edges, axis=0, return_counts=True);edges = edges[count == 1]
        adjacent = {}
        for a,b in edges:
            adjacent.setdefault(int(a), []).append(int(b));adjacent.setdefault(int(b), []).append(int(a))
        if not adjacent or any(len(ns) != 2 for ns in adjacent.values()):
            continue
        unseen = set(adjacent);loops = []
        while unseen:
            a = min(unseen);loop = [a];prev = -1;cur = a
            while True:
                ns = adjacent[cur];nxt = ns[0] if ns[0] != prev else ns[1]
                if nxt == a:break
                if nxt in loop:return None
                loop.append(nxt);prev,cur = cur,nxt
            unseen.difference_update(loop);loops.append(np.array(loop,dtype=int))
        return dict(axis=axis,u=u,w=w,lo=lo,hi=hi,xy=xy,ids=ids,labels=labels,loops=loops,cap=cap)
    return None


def segment_error(points, a, b):
    d = b-a;t = np.clip((points-a) @ d / max(float(d@d), 1e-30), 0, 1)
    return float(np.max(np.linalg.norm(points-a-t[:,None]*d, axis=1)))


def simplify_loop(xy, loop, tolerance):
    n = len(loop);alive = list(range(n));original = xy[loop]
    while len(alive) > 4:
        best = None
        for j,k in enumerate(alive):
            a,b = alive[j-1],alive[(j+1)%len(alive)]
            seq = np.arange(a, b+1 if b>a else b+1+n) % n
            err = segment_error(original[seq], original[a], original[b])
            if best is None or err < best[0]:best = err,j
        if best[0] > tolerance:break
        alive.pop(best[1])
    mapping = {}
    for j,a in enumerate(alive):
        b = alive[(j+1)%len(alive)];seq = np.arange(a, b if b>a else b+n) % n
        for k in seq:
            mapping[int(loop[k])] = int(loop[a] if np.linalg.norm(original[k]-original[a]) <= np.linalg.norm(original[k]-original[b]) else loop[b])
    return mapping


def extruded_visual(m, ex, tolerance):
    remap = np.arange(len(ex['xy']))
    for loop in ex['loops']:
        for a,b in simplify_loop(ex['xy'],loop,tolerance).items():remap[a] = b
    xy = ex['xy'][remap[ex['ids']]];z = np.where(ex['labels'],ex['hi'],ex['lo'])
    v = xy[:,0,None]*ex['u'] + xy[:,1,None]*ex['w'] + z[:,None]*ex['axis']
    return clean_mesh(v, m.faces)


def cap_decomposition(ex, limit):
    """Merge adjacent cap triangles only when their union remains convex."""
    xy = ex['xy'];polys = {};edge_owner = {};heap = [];serial = 0
    def put(poly):
        nonlocal serial
        idx=serial;serial+=1;polys[idx]=poly
        for a,b in zip(poly,np.roll(poly,-1)):
            edge=tuple(sorted((int(a),int(b))))
            for other in edge_owner.get(edge,()):
                if other in polys:heapq.heappush(heap,(len(poly)+len(polys[other]),idx,other))
            edge_owner.setdefault(edge,set()).add(idx)
        return idx
    for tri in ex['cap']:
        p=xy[tri]
        if abs(np.cross(p[1]-p[0],p[2]-p[0])) > 1e-15:put(np.asarray(tri))
    while heap:
        _,a,b=heapq.heappop(heap)
        if a not in polys or b not in polys:continue
        pa,pb=polys[a],polys[b];vertices=np.unique(np.concatenate((pa,pb)))
        try:
            h=ConvexHull(xy[vertices]);ha=ConvexHull(xy[pa]).volume;hb=ConvexHull(xy[pb]).volume
        except Exception:continue
        poly=vertices[h.vertices]
        if len(poly)*2 > limit or h.volume > ha+hb+max(1e-13,(ha+hb)*1e-8):continue
        del polys[a];del polys[b];put(poly)
    result=[]
    for poly in polys.values():
        p=xy[poly,0,None]*ex['u']+xy[poly,1,None]*ex['w']+ex['lo']*ex['axis']
        result.append(np.concatenate((p,p+(ex['hi']-ex['lo'])*ex['axis'])))
    return result


def surface_error(source, target, seed=19):
    rng=np.random.default_rng(seed)
    def samples(m, count):
        v=np.asarray(m.vertices);vv=v if len(v)<=600 else v[np.linspace(0,len(v)-1,600,dtype=int)]
        ii=rng.choice(len(m.faces),min(count,len(m.faces)),replace=False,p=m.area_faces/m.area)
        return np.concatenate((vv,np.asarray(m.triangles_center)[ii]))
    try:
        a=trimesh.proximity.closest_point(target,samples(source,700))[1]
        b=trimesh.proximity.closest_point(source,samples(target,400))[1]
        return max(float(np.max(a)),float(np.max(b)))
    except Exception:return float('inf')


def visual_lod(records, budget, tolerance, deadline):
    for rec in records:
        m=rec['mesh'];rec['cache']={};rec['selected']=m
        if rec['ex'] is None and len(m.faces)>128:
            candidates=[]
            for n in sorted(set([32,64,100,160,256,400,640,1000,1600,2600,len(m.faces)])):
                if n >= len(m.faces):candidates.append((0.,m));break
                v,f=fast_simplification.simplify(m.vertices,m.faces.astype(np.int32),target_count=n,agg=7.)
                out=trimesh.Trimesh(v,f,process=False);err=surface_error(m,out);candidates.append((err,out))
                if err < tolerance*.32 or time.monotonic()>deadline:break
            rec['candidates']=candidates
    def choose(error):
        total=0
        for rec in records:
            m=rec['mesh']
            if rec['ex'] is not None and len(m.faces)>32:
                key=round(error,10)
                if key not in rec['cache']:rec['cache'][key]=extruded_visual(m,rec['ex'],error)
                out=rec['cache'][key]
            elif 'candidates' in rec:
                accepted=[out for e,out in rec['candidates'] if e<=error]
                out=min(accepted,key=lambda m:len(m.faces)) if accepted else min(rec['candidates'],key=lambda x:x[0])[1]
            else:out=m
            rec['selected']=out;total+=len(out.faces)
        return total
    low=tolerance*.32;high=tolerance*.65;total=choose(high)
    if total>budget:
        while total>budget and high < 1.:high*=1.6;total=choose(high)
        for _ in range(7):
            mid=(low+high)/2
            if choose(mid)>budget:low=mid
            else:high=mid
        choose(high)
    total=sum(len(r['selected'].faces) for r in records)
    while total>budget:
        options=[r for r in records if len(r['selected'].faces)>12]
        if not options:break
        r=max(options,key=lambda r:len(r['selected'].faces));m=r['selected'];count=max(4,len(m.faces)-(total-budget)-2)
        v,f=fast_simplification.simplify(m.vertices,m.faces.astype(np.int32),target_count=count,agg=10.)
        if len(f)>=len(m.faces):break
        r['selected']=trimesh.Trimesh(v,f,process=False);total=sum(len(r['selected'].faces) for r in records)


def compile_asset(job,meta,parts):
    start=time.monotonic();deadline=start+float(job.get('generation_seconds',90))-6;records=[]
    for p,(v,f) in parts.items():
        m=clean_mesh(v,f)
        for c in m.split(only_watertight=False,repair=False):records.append(dict(pid=p,mesh=c,ex=extrusion(c)))
    visual_lod(records,int(job['max_triangles']),float(job['visual_tolerance_m']),start+25)
    visual={}
    for p in meta['part_ids']:
        m=trimesh.util.concatenate([r['selected'] for r in records if r['pid']==p]);visual[p]=(m.vertices,m.faces)
    limit=int(job['max_vertices_per_hull']);hull_budget=int(job['max_hulls']);proxies={p:[] for p in meta['part_ids']};pending=[]
    for rec in records:
        m=rec['mesh'];p=rec['pid']
        try:h=ConvexHull(m.vertices);convex=abs(m.volume)/h.volume>.99999
        except Exception:convex=False
        if convex:proxies[p].append(np.asarray(m.vertices)[h.vertices])
        elif rec['ex'] is not None:proxies[p].extend(cap_decomposition(rec['ex'],limit))
        else:pending.append(rec)
    for i,rec in enumerate(pending):
        left=len(pending)-i;used=sum(len(hs) for hs in proxies.values());alloc=max(1,(hull_budget-used)//left)
        seconds=max(1.,(deadline-time.monotonic())/left);m=rec['mesh']
        hs=generate(dict(max_hulls=alloc,max_vertices_per_hull=limit,generation_seconds=seconds),m.vertices,m.faces)
        proxies[rec['pid']].extend(hs)
    all_hulls=[(p,limited_hull(h,limit)) for p,hs in proxies.items() for h in hs]
    total=sum(len(h) for p,h in all_hulls)
    if total>job['max_proxy_vertices']:
        cap=next((k for k in range(limit,3,-1) if sum(min(len(h),k) for p,h in all_hulls)<=job['max_proxy_vertices']),4)
        all_hulls=[(p,limited_hull(h,cap)) for p,h in all_hulls]
    proxies={p:[] for p in meta['part_ids']}
    for p,h in all_hulls:proxies[p].append(h)
    return visual,proxies,dict(root_id=meta['root_id'],joints=meta['joints'])


if __name__=='__main__':
    job,meta,parts=load_job(sys.argv[1]);write_output(sys.argv[2],*compile_asset(job,meta,parts))
