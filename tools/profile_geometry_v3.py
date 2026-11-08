"""CPU feasibility only: real-mesh BVHs and zero-pose pair queries, no reward."""
import argparse,itertools,json,platform,sys,time
from pathlib import Path
import fcl
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'study-v3'))
from core import ASSETS,load_asset

parser=argparse.ArgumentParser();parser.add_argument('--out',required=True,type=Path);args=parser.parse_args()
if args.out.exists():raise FileExistsError(args.out)
records=[]
for name in ASSETS:
    start=time.perf_counter();asset=load_asset(name);loaded=time.perf_counter();objects=[]
    for link in asset['ids']:
        vertices=asset['points'][link];triangles=asset['faces'][link];mesh=fcl.BVHModel()
        mesh.beginModel(len(triangles),len(vertices));mesh.addSubModel(vertices,triangles);mesh.endModel()
        objects.append(fcl.CollisionObject(mesh))
    built=time.perf_counter();pairs=list(itertools.combinations(objects,2))
    for a,b in pairs:fcl.collide(a,b,fcl.CollisionRequest(),fcl.CollisionResult())
    end=time.perf_counter()
    row=dict(asset=name,parts=len(objects),triangles=sum(len(f) for f in asset['faces'].values()),load_seconds=loaded-start,bvh_build_seconds=built-loaded,zero_pose_pairs=len(pairs),pair_queries_seconds=end-built)
    records.append(row);print(json.dumps(row),flush=True)
args.out.parent.mkdir(parents=True,exist_ok=True)
args.out.write_text(json.dumps(dict(kind='Native CPU feasibility; pair queries include expected adjacent contacts and are not functionality scores',machine=platform.machine(),cases=records),indent=2)+'\n')
