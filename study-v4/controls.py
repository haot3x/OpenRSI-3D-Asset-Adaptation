"""Developer witnesses and negative controls, excluded from model inputs."""
import copy,json,math,sys
from pathlib import Path
import fcl
import numpy as np
import trimesh
from motion import Actor,FIXTURES,evaluate,validate


def witness():
    poses=[dict(id='stowed',q=[0,0,0,0]),dict(id='pick_left',q=[.28,0,math.pi,0]),dict(id='pick_right',q=[0,.28,0,-math.pi]),dict(id='deliver',q=[0,.28,0,0]),dict(id='service',q=[0,.28,0,-math.pi/2]),dict(id='release',q=[0,0,math.pi,0])]
    def k(t,root,p='stowed'):return dict(time=t,root=root,pose=p)
    outside=[0,-1.05,0];dock=[0,0,0];corner_start=[0,-1.1,0];turn=[0,0,math.pi/2];end=[1.2,0,math.pi/2]
    return dict(poses=poses,scenes=[
        dict(id='stockroom_pickup',keyframes=[k(0,outside),k(1,outside),k(5,dock),k(7,dock,'pick_left'),k(8,dock,'pick_left'),k(10,dock),k(12,dock,'pick_right'),k(13,dock,'pick_right'),k(15,dock),k(19,outside),k(20,outside)]),
        dict(id='corner_delivery',keyframes=[k(0,corner_start),k(1,corner_start),k(5,dock),k(8,turn),k(12,end),k(14,end,'deliver'),k(15,end,'deliver'),k(17,end),k(18,end)]),
        dict(id='alcove_service',keyframes=[k(0,outside),k(2,outside,'pick_left'),k(3,outside,'pick_left'),k(5,outside),k(9,dock),k(11,dock,'service'),k(12,dock,'service'),k(14,dock),k(18,outside),k(20,outside,'release'),k(21,outside,'release'),k(23,outside),k(24,outside)])])


def variants():
    good=witness();noop=copy.deepcopy(good)
    for scene,fixture in zip(noop['scenes'],FIXTURES['scenes']):
        scene['keyframes']=[dict(time=t,root=fixture['start'],pose='stowed') for t in [0,2]]
    shortcut=copy.deepcopy(good);corner=shortcut['scenes'][1]
    corner['keyframes']=[corner['keyframes'][0]]+corner['keyframes'][4:]
    carry=copy.deepcopy(good)
    for key in carry['scenes'][2]['keyframes']:
        if key['pose']=='service':key['pose']='pick_left'
    regression=copy.deepcopy(good)
    next(p for p in regression['poses'] if p['id']=='pick_left')['q'][2]=math.pi/2
    return dict(witness=good,static_noop=noop,diagonal_shortcut=shortcut,universal_deployment=carry,shared_pose_regression=regression)


def main():
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False);actor=Actor();records=[]
    cube=trimesh.creation.box();mesh=fcl.BVHModel();mesh.beginModel(len(cube.faces),len(cube.vertices));mesh.addSubModel(cube.vertices,cube.faces);mesh.endModel()
    obj=fcl.CollisionObject(mesh);box=fcl.CollisionObject(fcl.Box(1,1,1),fcl.Transform(np.array([2.,0,0])))
    assert not fcl.collide(obj,box,fcl.CollisionRequest(),fcl.CollisionResult())
    assert abs(fcl.distance(obj,box,fcl.DistanceRequest(),fcl.DistanceResult())-1)<1e-7
    box.setTranslation(np.array([1.005,0,0]))
    assert not fcl.collide(obj,box,fcl.CollisionRequest(),fcl.CollisionResult())
    assert 0<fcl.distance(obj,box,fcl.DistanceRequest(),fcl.DistanceResult())<.008
    box.setTranslation(np.array([.25,0,0]));assert fcl.collide(obj,box,fcl.CollisionRequest(),fcl.CollisionResult())
    enclosing=fcl.CollisionObject(fcl.Box(2,2,2));assert fcl.collide(obj,enclosing,fcl.CollisionRequest(),fcl.CollisionResult())
    (out/'actor-metadata.json').write_text(json.dumps(actor.metadata(),indent=2)+'\n')
    for name,candidate in variants().items():
        (out/(name+'.candidate.json')).write_text(json.dumps(candidate,indent=2)+'\n')
        result=evaluate(candidate,actor);(out/(name+'.result.json')).write_text(json.dumps(result,indent=2)+'\n')
        print(name,result['passed'],[(r['scene'],r['first_failure'],r['events'].get('missing'),r['sampled_frames'],r['wall_seconds']) for r in result['scenes']],flush=True)
        records.append(dict(name=name,result=result))
    (out/'all.json').write_text(json.dumps(records,indent=2)+'\n')
    by_name={r['name']:r['result'] for r in records}
    assert by_name['witness']['passed']==3
    assert by_name['static_noop']['passed']==0
    bad=by_name['diagonal_shortcut']['scenes'][1]
    assert bad['endpoint_passed'] and bad['events']['passed'] and not bad['motion_passed']
    assert not by_name['universal_deployment']['scenes'][2]['motion_passed']
    assert not by_name['shared_pose_regression']['scenes'][0]['passed']
    invalid=witness();invalid['scale']=.5
    try:validate(invalid)
    except ValueError:pass
    else:raise AssertionError('Unexpected scale field accepted')
    (out/'verified.json').write_text(json.dumps(dict(all_functional_controls_passed=True,mesh_box_separation_distance_intersection_and_enclosure_passed=True),indent=2)+'\n')
    print('All functional controls passed',flush=True)


if __name__=='__main__':main()
