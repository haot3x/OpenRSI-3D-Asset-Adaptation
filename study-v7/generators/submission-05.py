"""Complete-asset compiler: geometric LOD and resource-aware solid proxies."""
import os
os.environ.setdefault('OMP_NUM_THREADS', '2')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
import sys, time, math, heapq
import numpy as np
import trimesh, fast_simplification
from scipy.spatial import ConvexHull, cKDTree
from asset_sdk import load_job, write_output
from legacy_proxy import generate, limited_hull, split_surface


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
    keys, first_normal, inv = np.unique(np.round(m.face_normals, 6), axis=0, return_index=True, return_inverse=True)
    weights = np.bincount(inv, weights=m.area_faces)
    candidates = np.asarray(m.face_normals)[first_normal[np.argsort(weights)[::-1][:256]]]
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
    n = len(loop);original = xy[loop]
    previous=(np.arange(n)-1)%n;following=(np.arange(n)+1)%n
    live=np.ones(n,dtype=bool);version=np.zeros(n,dtype=int);heap=[]
    def enqueue(k):
        a,b=previous[k],following[k]
        seq=np.arange(a,b+1 if b>a else b+1+n)%n
        err=segment_error(original[seq],original[a],original[b])
        heapq.heappush(heap,(err,int(k),int(version[k])))
    for k in range(n):enqueue(k)
    count=n
    while heap and count>4:
        err,k,ver=heapq.heappop(heap)
        if not live[k] or ver!=version[k]:continue
        if err>tolerance:break
        a,b=previous[k],following[k];live[k]=False;count-=1
        following[a]=b;previous[b]=a
        for i in (a,b):version[i]+=1;enqueue(i)
    alive=np.flatnonzero(live).tolist()
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


def qem(m, count):
    v,f=fast_simplification.simplify(m.vertices,m.faces.astype(np.int32),target_count=count,agg=7.)
    if len(f)>count*1.1+4:
        # Flat and very slender triangles can lock the collapse normal test.
        # An affine conditioning pass changes the metric, then world-space
        # surface validation decides whether the candidate is worth retaining.
        center=m.bounds.mean(0);scale=np.maximum(m.extents,1e-7)
        vv,ff=fast_simplification.simplify((m.vertices-center)/scale,m.faces.astype(np.int32),target_count=count,agg=7.)
        if len(ff)<len(f):v,f=vv*scale+center,ff
    return trimesh.Trimesh(v,f,process=False)


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
                out=qem(m,n);err=surface_error(m,out);candidates.append((err,out))
                if err < tolerance*.32 or time.monotonic()>deadline:break
            if candidates[-1][1] is not m:candidates.append((0.,m))
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
    low=0.;high=tolerance*.65;total=choose(high)
    if total>budget:
        while total>budget and high < 1.:high*=1.6;total=choose(high)
    # Minimize the worst geometric error across the entire asset. Unused
    # triangles buy tolerance margin for small, visually important parts too.
    for _ in range(9):
        mid=(low+high)/2
        if choose(mid)>budget:low=mid
        else:high=mid
    choose(high)
    # Fill gaps between the coarse QEM ladder rungs with actual candidates.
    # This prevents one dense component from stranding a shared resource pool.
    for _ in range(2):
        room=budget-sum(len(r['selected'].faces) for r in records)
        curved=[r for r in records if 'candidates' in r and len(r['selected'].faces)<len(r['mesh'].faces)]
        if not curved or room<16*len(curved) or time.monotonic()>deadline:break
        share=room//len(curved);added=False
        for r in curved:
            if time.monotonic()>deadline:break
            n=min(len(r['mesh'].faces),len(r['selected'].faces)+share)
            out=qem(r['mesh'],n)
            if len(out.faces)>len(r['selected'].faces)+share:continue
            err=surface_error(r['mesh'],out)
            r['candidates'].append((err,out));added=True
        if not added:break
        low=0.
        for _ in range(8):
            mid=(low+high)/2
            if choose(mid)>budget:low=mid
            else:high=mid
        choose(high)
    total=sum(len(r['selected'].faces) for r in records)
    while total>budget:
        options=[r for r in records if len(r['selected'].faces)>12]
        if not options:break
        r=max(options,key=lambda r:len(r['selected'].faces));m=r['selected'];count=max(4,len(m.faces)-(total-budget)-2)
        out=qem(m,count)
        if len(out.faces)>=len(m.faces):break
        r['selected']=out;total=sum(len(r['selected'].faces) for r in records)


def hull_ladder(points, limit):
    """Nested inscribed approximations with measured support-plane error."""
    p=np.unique(points,axis=0)
    h=ConvexHull(p);p=p[h.vertices]
    if len(p)<=4:return [(0.,p)]
    a=int(np.argmin(p[:,0]));b=int(np.argmax(np.sum((p-p[a])**2,axis=1)))
    cross=np.cross(p[b]-p[a],p-p[a]);c=int(np.argmax(np.sum(cross**2,axis=1)))
    normal=np.cross(p[b]-p[a],p[c]-p[a]);d=int(np.argmax(abs((p-p[a])@normal)))
    chosen=[a,b,c,d];result=[]
    for count in range(4,min(limit,len(p))+1):
        h=ConvexHull(p[chosen]);ds=np.max(p@h.equations[:,:3].T+h.equations[:,3],axis=1)
        err=max(0.,float(ds.max()));result.append((err,p[chosen].copy()))
        if count==limit or count==len(p) or err<1e-10:break
        ds[chosen]=-np.inf;chosen.append(int(np.argmax(ds)))
    return result


def allocate_vertices(hulls, total_budget, limit):
    # Exact boxes and flat contacts compete on geometric error, not the same
    # arbitrary vertex cap as every curved piece.
    ladders=[]
    for p,h in hulls:
        h=limited_hull(h,max(limit,len(h)))
        if h is not None:ladders.append((p,h))
    if sum(len(h) for p,h in ladders)<=total_budget and all(len(h)<=limit for p,h in ladders):return ladders
    ladders=[(p,hull_ladder(h,limit)) for p,h in ladders]
    def choose(error):
        result=[]
        for p,ladder in ladders:
            feasible=[(e,h) for e,h in ladder if e<=error]
            h=min(feasible,key=lambda eh:len(eh[1]))[1] if feasible else ladder[-1][1]
            result.append((p,h))
        return result
    low=0.;high=.00005;out=choose(high)
    while sum(len(h) for p,h in out)>total_budget:
        high*=2;out=choose(high)
        if high>10:break
    for _ in range(16):
        mid=(low+high)/2;candidate=choose(mid)
        if sum(len(h) for p,h in candidate)>total_budget:low=mid
        else:high=mid;out=candidate
    return out


def merge_hulls_to_budget(proxies, budget):
    """Preserve all solids if an unusually tight job requires coalescing them."""
    while sum(len(hs) for hs in proxies.values())>budget:
        best=None
        for p,hs in proxies.items():
            if len(hs)<2:continue
            centers=np.array([h.mean(0) for h in hs]);tree=cKDTree(centers)
            pairs=tree.query(centers,k=min(5,len(hs)))[1]
            seen=set()
            for i,neighbors in enumerate(pairs):
                for j in np.atleast_1d(neighbors):
                    j=int(j)
                    if i==j or tuple(sorted((i,j))) in seen:continue
                    seen.add(tuple(sorted((i,j))))
                    a,b=hs[i],hs[j];joined=np.concatenate((a,b))
                    try:
                        ha,hb,h=ConvexHull(a),ConvexHull(b),ConvexHull(joined)
                    except Exception:continue
                    gap=np.linalg.norm(np.maximum(np.maximum(a.min(0)-b.max(0),b.min(0)-a.max(0)),0))
                    cost=gap+max(0.,h.volume-ha.volume-hb.volume)/max(h.area,1e-15)
                    if best is None or cost<best[0]:best=(cost,p,i,j,joined[h.vertices])
        if best is None:break
        _,p,i,j,h=best;proxies[p][i]=h;proxies[p].pop(j)


def refine_large_convex(proxies, hull_budget, vertex_budget, limit, deadline):
    """Spend spare resources on curved convex bodies without expanding them."""
    cache={}
    for _ in range(64):
        count=sum(len(hs) for hs in proxies.values())
        cost=sum(min(len(h),limit) for hs in proxies.values() for h in hs)
        if count>=hull_budget or cost+limit>vertex_budget or time.monotonic()>deadline:break
        best=None
        for p,hs in proxies.items():
            for i,h in enumerate(hs):
                if len(h)<=limit:continue
                key=id(h)
                if key not in cache:
                    approx=limited_hull(h,limit);ch=ConvexHull(approx)
                    ds=h@ch.equations[:,:3].T+ch.equations[:,3]
                    j,k=np.unravel_index(np.argmax(ds),ds.shape)
                    cache[key]=(float(ds[j,k]),ch.equations[k,:3])
                error,normal=cache[key]
                if error>.00035 and (best is None or error>best[0]):best=(error,p,i,normal)
        if best is None:break
        _,p,i,normal=best;h=proxies[p][i]
        mesh=trimesh.Trimesh(h,ConvexHull(h).simplices,process=True).convex_hull
        offset=float(h.mean(0)@normal)
        a,b=split_surface(np.asarray(mesh.triangles),normal,offset)
        children=[]
        for tri in (a,b):
            points=np.unique(tri.reshape(-1,3),axis=0)
            try:children.append(points[ConvexHull(points).vertices])
            except Exception:pass
        if len(children)!=2:cache[id(h)]=(0.,normal);continue
        proxies[p][i]=children[0];proxies[p].append(children[1])


def compile_asset(job,meta,parts):
    start=time.monotonic();deadline=start+float(job.get('generation_seconds',90))-6;records=[]
    for p,(v,f) in parts.items():
        m=clean_mesh(v,f)
        for c in m.split(only_watertight=False,repair=False):records.append(dict(pid=p,mesh=c,ex=extrusion(c)))
    visual_lod(records,int(job['max_triangles']),float(job['visual_tolerance_m']),start+25)
    visual={}
    for p in meta['part_ids']:
        m=trimesh.util.concatenate([r['selected'] for r in records if r['pid']==p]);visual[p]=(m.vertices,m.faces)
    limit=int(job['max_vertices_per_hull']);hull_budget=min(int(job['max_hulls']),int(job['max_proxy_vertices'])//4);proxies={p:[] for p in meta['part_ids']};pending=[];extrusions=[]
    for rec in records:
        m=rec['mesh'];p=rec['pid']
        try:h=ConvexHull(m.vertices);convex=abs(m.volume)/h.volume>.99999
        except Exception:convex=False
        if convex:proxies[p].append(np.asarray(m.vertices)[h.vertices])
        elif rec['ex'] is not None:extrusions.append(rec)
        else:pending.append(rec)
    # Reserve curved components before spending the shared budget on exact
    # extrusion tessellation. Small contour errors release many redundant cuts.
    demands=[max(8,min(80,int(math.ceil(math.pi*math.sqrt(max(r['mesh'].extents)/.0016))))) for r in pending]
    reserve=sum(demands)
    fixed_hulls=sum(len(hs) for hs in proxies.values());fixed_vertices=sum(len(h) for hs in proxies.values() for h in hs)
    extrusion_hulls=[]
    for epsilon in (0.,.00006,.00012,.00024,.0004):
        extrusion_hulls=[]
        for rec in extrusions:
            ex=rec['ex']
            if epsilon:
                reduced=extruded_visual(rec['mesh'],ex,epsilon)
                recovered=extrusion(reduced)
                if recovered is not None and reduced.is_watertight:ex=recovered
            extrusion_hulls.extend((rec['pid'],h) for h in cap_decomposition(ex,limit))
        if fixed_hulls+len(extrusion_hulls)+reserve<=hull_budget and fixed_vertices+sum(len(h) for p,h in extrusion_hulls)+reserve*32<=job['max_proxy_vertices']:break
        if time.monotonic()>deadline-10:break
    for p,h in extrusion_hulls:proxies[p].append(h)
    for i,rec in enumerate(pending):
        left=len(pending)-i;used=sum(len(hs) for hs in proxies.values())
        alloc=max(1,1+int(max(0,hull_budget-used-left)*demands[i]/max(1,sum(demands[i:]))))
        seconds=max(1.,(deadline-time.monotonic())/left);m=rec['mesh']
        hs=generate(dict(max_hulls=alloc,max_vertices_per_hull=limit,generation_seconds=seconds),m.vertices,m.faces)
        proxies[rec['pid']].extend(hs)
    merge_hulls_to_budget(proxies,hull_budget)
    refine_large_convex(proxies,hull_budget,int(job['max_proxy_vertices']),limit,deadline-2)
    all_hulls=allocate_vertices([(p,h) for p,hs in proxies.items() for h in hs],int(job['max_proxy_vertices']),limit)
    proxies={p:[] for p in meta['part_ids']}
    for p,h in all_hulls:proxies[p].append(h)
    return visual,proxies,dict(root_id=meta['root_id'],joints=meta['joints'])


if __name__=='__main__':
    job,meta,parts=load_job(sys.argv[1]);write_output(sys.argv[2],*compile_asset(job,meta,parts))
