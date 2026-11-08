"""At most two bounded, fresh model probes with unchanged full-scene replay."""
import argparse,hashlib,importlib.metadata,json,platform,subprocess,sys
from pathlib import Path
from PIL import Image,ImageDraw
from motion import Actor,FIXTURES,ROOT,evaluate,validate
sys.path.insert(0,str(ROOT/'tools'))
from inference import generate


def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def maps(folder,actor):
    folder.mkdir();paths=[]
    for scene in FIXTURES['scenes']:
        im=Image.new('RGB',(760,760),'white');draw=ImageDraw.Draw(im)
        lower,upper=scene['bounds'];scale=min(620/(upper[i]-lower[i]) for i in [0,1])
        def xy(p):return (65+(p[0]-lower[0])*scale,695-(p[1]-lower[1])*scale)
        def rectangle(lo,hi,**kwargs):
            a,b=xy(lo),xy(hi);draw.rectangle((min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1])),**kwargs)
        rectangle(lower,upper,outline='black',width=2)
        for o in scene['obstacles']:
            c,s=o['center'],o['size'];rectangle([c[i]-s[i]/2 for i in range(2)],[c[i]+s[i]/2 for i in range(2)],fill='#bbbbbb',outline='#555555')
            draw.text(xy(c),o['id'],fill='black')
        for index,e in enumerate(scene['events']):
            x,y=xy(e['root']);draw.ellipse((x-7,y-7,x+7,y+7),outline='orange',width=2);draw.text((x+10,y+14*index),str(index+1)+': '+e['id'],fill='#9b4800')
        for label,color in [('start','green'),('goal','blue')]:
            p=scene[label];x,y=xy(p);draw.ellipse((x-4,y-4,x+4,y+4),fill=color);draw.text((x+8,y-18 if label=='start' else y+8),label,fill=color)
        draw.text((20,15),scene['id']+' / top view / +X right, +Y up / metres',fill='black')
        draw.text((20,35),'Grey: solid obstacles. Orange: interaction checkpoints. No solution path shown.',fill='black')
        path=folder/(scene['id']+'.png');im.save(path);paths.append(path)
    return paths


def main():
    parser=argparse.ArgumentParser();parser.add_argument('out',type=Path);parser.add_argument('--controls',type=Path,required=True);parser.add_argument('--seconds-per-call',type=int,choices=[300,600],default=300);args=parser.parse_args()
    verified=json.loads((args.controls/'verified.json').read_text())
    assert verified['all_functional_controls_passed'] and verified['mesh_box_separation_distance_intersection_and_enclosure_passed']
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);actor=Actor()
    save(out/'run-config.json',dict(model='gpt-6-astra',reasoning_effort='max',seconds_per_call=args.seconds_per_call,maximum_attempts=2,automatic_retries=0,tools=False,capacity_amendment=args.seconds_per_call==600))
    save(out/'controls-verification.json',verified);save(out/'actor-metadata.json',actor.metadata());save(out/'fixtures.json',FIXTURES)
    source=list((ROOT/'study-v4').glob('*'))+[ROOT/'study-v3/core.py',ROOT/'study-v3/sources.json',ROOT/'tools/inference.py']
    save(out/'frozen-source.json',{str(p.relative_to(ROOT)):sha(p) for p in sorted(source) if p.is_file()})
    save(out/'environment.json',dict(python=platform.python_version(),platform=platform.platform(),codex_cli=subprocess.check_output(['codex','--version'],text=True).strip(),packages={p:importlib.metadata.version(p) for p in ['numpy','scipy','trimesh','python-fcl','Pillow']}))
    images=[actor.asset['folder']/'close.png']+maps(out/'maps',actor)
    base='''Create reusable behavior/animation adapters for this existing articulated 3D game prop across all three fixed scenes. Return only the required JSON. You control a shared pose bank and one piecewise-linear root/pose keyframe program per scene. No tools or filesystem access are available. No code executes from your response.

Each pose q is [left drawer metres, right drawer metres, left ring-holder radians, right ring-holder radians]. Pose IDs may be reused across scenes; define 1..12 distinct IDs. There must be exactly one program for each declared scene ID, with 2..64 keyframes. Each keyframe has time, root=[x,y,yaw radians], pose ID. Time starts at 0, strictly increases and ends within 90 seconds. Root x,y stay within +/-3 m, yaw within +/-2*pi, root travel <=12 m. The fixed controller adds caster-steering time; total must remain <=120 s. Do not add scale, geometry, obstacles, executable code or other fields. Meshes and rig cannot change.

Every scene must start at its start root and finish at its goal root, with all four q values stowed (zero) at both ends. Root tolerance is 0.02 m and 0.035 rad. Each fixture's events must be performed IN ORDER. At each event, match its root and all four q_min..q_max ranges simultaneously for at least 0.4 seconds continuously; use explicit repeated pose/root keyframes for holds. Events can require different poses even at the same location. Leaving out an event fails the scene.

All INTERMEDIATE states are evaluated, including simultaneous changes of root yaw and joints. Root, all parts, drawers and deployed holders must maintain >=0.008 m clearance from every solid obstacle and remain within workspace bounds. Source mesh surfaces are checked, not a point-robot path. In-place turns sweep the entire prop. Fold deployed parts before narrow passages and provide room before opening drawers. All prior scenes are re-evaluated after any shared-bank change. The goal is 3/3 complete functional scenes, not merely good-looking endpoints. There is no special reward for speed; use enough time to hold every event.

Original appearance image comes first, followed by one top-view obstacle/checkpoint map per scene. Exact geometry/interface metadata and fixtures below are authoritative. Witness solutions and evaluator code are not provided.
ASSET INTERFACE:\n'''+json.dumps(actor.metadata())+'\nFIXTURES:\n'+json.dumps(FIXTURES)
    records=[];previous=None;feedback=None
    for number in range(1,3):
        d=out/('attempt-'+str(number).zfill(3));d.mkdir()
        prompt=base
        if previous is not None:prompt+='\nYour unchanged previous candidate:\n'+json.dumps(previous)+'\nEvaluator feedback for ALL scenes:\n'+json.dumps(feedback)+'\nRevise the shared bank and scene programs to repair failures while retaining all previous successes.'
        print('START ATTEMPT',number,flush=True)
        try:invocation=generate(prompt,images,d/'generation',dict(model='gpt-6-astra',reasoning_effort='max',seconds_per_call=args.seconds_per_call,schema=ROOT/'study-v4/prediction.schema.json'))
        except Exception as error:
            records.append(dict(attempt=number,scored=False,status='invocation_infrastructure_failure',error=repr(error)));save(out/'results.json',records);break
        record=dict(attempt=number,status=invocation['status'],seconds=invocation['wall_seconds']);records.append(record)
        if invocation['status']!='completed' or invocation['native_session']['status']!='copied_exact_fresh_session':
            record['scored']=False;save(out/'results.json',records);break
        try:
            candidate=json.loads((d/'generation/response.json').read_text());validate(candidate)
        except (ValueError,KeyError,TypeError) as error:
            record.update(scored=False,status='candidate_invalid',error=str(error));save(out/'results.json',records);break
        save(d/'candidate.json',candidate)
        try:result=evaluate(candidate,actor,include_frames=True)
        except ValueError as error:
            record.update(scored=False,status='candidate_sampling_cap_or_invalid',error=str(error));save(out/'results.json',records);break
        except Exception as error:
            record.update(scored=False,status='evaluator_infrastructure_failure',error=repr(error));save(out/'results.json',records);break
        for scene in result['scenes']:save(d/(scene['scene']+'.frames.json'),scene.pop('frames'))
        save(d/'evaluation.json',result);record.update(scored=True,evaluation=result);save(out/'results.json',records)
        print('SCORE',number,result['passed'],'/',result['total'],flush=True)
        if result['passed']==3:print('STOP CEILING',flush=True);break
        previous=candidate;feedback=result
    print('DONE',flush=True)


if __name__=='__main__':main()
