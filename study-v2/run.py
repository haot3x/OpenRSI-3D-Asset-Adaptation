"""Short v2 calibration, with immutable inputs, one repair and a ceiling stop."""
import argparse
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from inference import generate
from execute import execute
from check import evaluate,save


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--controls',type=Path,required=True);args=p.parse_args()
    out=args.out.resolve();controls=args.controls.resolve()
    control=json.loads((controls/'summary.json').read_text())
    if not control['passed']:raise ValueError('Passing v2 controls required')
    m=json.loads((controls/'metadata/metadata.json').read_text())
    scenes=json.loads((ROOT/'study-v2/scenes.json').read_text())
    out.mkdir(parents=True,exist_ok=False)
    save(out/'canonical-metadata.json',m)
    godot_version=subprocess.check_output([os.environ['GODOT_BIN'],'--version'],text=True).strip()
    if not godot_version.startswith('4.7.2'):raise ValueError('Godot version changed')
    # Model exposure is measured canonical metadata, not the control's rig,
    # angles, code, generated clips, or the original construction program.
    exposed=dict(neck_anchor_godot=m['neck_anchor'],
                 upper_meshes={name:m['meshes'][name] for name in m['allowed_upper_meshes']},
                 static_mesh_names=sorted(m['static_meshes']),
                 animation='Ride, two seconds; imported active actions and NLA may share the same action; inspect/normalize the imported frame range to frames 0..48 at 24 fps exactly once per action')
    base='''You are adapting an existing interactive 3D game asset across three scenes. The canonical GLB has ALREADY been imported into a fresh Blender 4.0.2 scene by a fixed bootstrap. The four images show that immutable base asset. Do not clear the scene or regenerate it. You may inspect/edit the loaded bpy scene and, if needed, read only the assigned /tmp/canonical.glb file. You are not given its construction source.

Return complete Blender ADAPTER code as final JSON fields script and design_notes. Use only bpy, mathutils and Python standard library. No tools, network, external resources, subprocesses or other file reads. Code executes in an isolated fixed runner. Export /output/asset.glb.

Author THREE named two-second clips: UprightRide, DuckRide, LeftRide. Each must retain the original bicycle/leg Ride motion. The fixed evaluator selects your clips and samples them; it does not solve head poses, synthesize cycling or compensate for missing channels. It switches among them seven times, so one static pose is insufficient. Preserve all original meshes, their names, mesh-local surface coordinates, connectivity and base colors. Mesh scale must remain unchanged in every state. New EMPTY rig nodes, transform keyframes and parenting changes are allowed. Do not apply object transforms into mesh geometry, deform meshes, delete parts, globally resize/translate the asset or replace it. All unanimated body/bike components outside the six upper-head meshes must retain canonical transforms.

Allowed upper assembly: Neck, PelicanHead, EyeLeft, EyeRight, Beak, Pouch. The actual neck base must remain at its original attachment (tolerance .015 m), and its top must stay within .04 m of the actual head center. Measurements use real geometry, not candidate-added markers. Keep the riding wheel/crank/pedal/hip interfaces, foot contacts, leg lengths, rod collisions, cycle seam and playback speeds. You can author a coherent upper rig to meet the different scene targets without changing mesh vertices.

Units are metres. Scene targets/metadata below use Godot axes: +Y up; convert to Blender as [x,-godot_z,godot_y]. The beak tip is the actual original Beak mesh endpoint, not a new empty. Upright and side targets apply throughout sampled clip phases; low-tunnel clearance applies to actual surface vertices. Head/base are canonical geometry, so meaningful connection must be maintained.

Export authoring requirements: frames 0..48 at 24 fps, 2-second duration; keep original imported action timing and loop behavior correctly normalized. For multiple NLA clips, keep the intended track names consistent across participating objects and clear active actions as needed. Blender 4.0.2 can omit constant pose tracks unless export_optimize_animation_keep_anim_object=True. Use export_animations=True, export_animation_mode='NLA_TRACKS', export_nla_strips=True, export_frame_range=True, export_force_sampling=True, export_optimize_animation_size=False, export_optimize_animation_keep_anim_object=True, export_yup=True, export_format='GLB'. Godot will retain authored constant channels. These are export settings, not pose solutions.

No progress text or tool use. Return final JSON directly.

Scene requirements and switch sequence:
'''+json.dumps(scenes)+'\nCanonical measured metadata:\n'+json.dumps(exposed)
    (out/'base-prompt.txt').write_text(base)
    files=list((ROOT/'study-v2').glob('*.py'))+list((ROOT/'study-v2').glob('*.md'))+list((ROOT/'study-v2').glob('*.json'))
    files += [ROOT/'tools/inference.py',ROOT/'lib/container_runtime.py',ROOT/'protocol/output.schema.json']
    files += list((ROOT/'runtime').glob('*v2.gd'))+list((ROOT/'assets/canonical').glob('*.png'))+[ROOT/'assets/canonical/asset.glb',ROOT/'runtime/project.godot']
    manifest={}
    for path in files:
        relative=path.relative_to(ROOT);dest=out/'frozen'/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest);manifest[str(relative)]=sha(path)
    save(out/'freeze.json',dict(started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_sha256=manifest,
         prompt_sha256=sha(out/'base-prompt.txt'),controls_summary_sha256=sha(controls/'summary.json'),maximum_calls=2,
         metadata_sha256=sha(out/'canonical-metadata.json'),godot_version=godot_version,
         cli_version=subprocess.check_output(['codex','--version'],text=True).strip(),
         model='gpt-6-astra',reasoning_effort='low',seconds_per_call=180,automatic_retries=0))
    images=[ROOT/'assets/canonical'/(v+'.png') for v in ['front','side','top','iso']]
    prompt=base;rows=[];status='completed';fatal=None
    try:
        for index in [1,2]:
            print('CALL',index,flush=True);folder=out/('attempt-'+str(index))
            invocation=generate(prompt,images,folder,dict(model='gpt-6-astra',reasoning_effort='low',seconds_per_call=180))
            row=dict(attempt=index,invocation=invocation);rows.append(row)
            if invocation['status']!='completed':row['status']='generation_incomplete_unscored';status='incomplete_unscored';break
            response=json.loads((folder/'response.json').read_text());source=response['script'];script=folder/'adapter.py';script.write_text(source)
            row.update(source_sha256=sha(script),human_source_edits=False)
            try:ast.parse(source)
            except SyntaxError as error:row.update(status='generated_python_invalid_unscored',error=str(error))
            else:
                delivery=execute(script,folder/'delivery');row['delivery']=delivery
                if delivery['execution']['status']=='completed':
                    result=evaluate(folder/'delivery/container/asset.glb',folder/'evaluation',m,os.environ['GODOT_BIN'])
                    row.update(status=result['status'],evaluation=result)
                else:row['status']=delivery['execution']['status']
            save(out/'progress.json',rows)
            print('OUTCOME',index,row['status'],row.get('evaluation',{}).get('scene_pass'),flush=True)
            result=row.get('evaluation',{})
            if result.get('scene_fraction')==1 and result.get('switch_visits_passed')==7:
                status='saturated_first_attempt' if index==1 else 'selected_ceiling_after_repair';break
            if row['status'] in ['execution_incomplete','asset_retrieval_error']:
                status='incomplete_unscored';break
            brief=dict(status=row['status'],identity=result.get('identity'),scene_pass=result.get('scene_pass'),
                       visits=result.get('visits'),error=row.get('error'))
            if row.get('delivery') and row['delivery']['execution']['status']!='completed':
                brief['blender_error']=(folder/'delivery/container/blender.stderr.log').read_text()[-3000:]+(folder/'delivery/container/blender.stdout.log').read_text()[-1500:]
            prompt=base+'\nYour previous full adapter code:\n'+source+'\nActual fixed evaluation feedback:\n'+json.dumps(brief)+'\nUse the remaining opportunity to return complete corrected adapter code. Preserve what works.'
    except Exception as error:
        status='infrastructure_or_orchestration_error_unscored';fatal=type(error).__name__+': '+str(error)
        raise
    finally:
        valid=[r for r in rows if r.get('evaluation',{}).get('status')=='evaluated']
        selected=max(valid,key=lambda r:(r['evaluation']['scene_fraction'],r['evaluation']['switch_visits_passed'])) if valid else None
        save(out/'summary.json',dict(kind='v2 adapter short calibration; not RSI improvement or official reward',status=status,
              model_calls=len(rows),selected_attempt=selected['attempt'] if selected else None,
              selected_scene_fraction=selected['evaluation']['scene_fraction'] if selected and status in ['completed','saturated_first_attempt','selected_ceiling_after_repair'] else None,
              official_reward=None,error=fatal,rows=rows))
        changed=[name for name,expected in manifest.items() if sha(ROOT/name)!=expected]
        save(out/'integrity.json',dict(source_changed=changed,sha256={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name!='integrity.json' and 'empty-workspace' not in p.parts}))
    print('CALIBRATION_DONE',status,flush=True)


if __name__=='__main__':main()
