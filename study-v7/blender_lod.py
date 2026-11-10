"""CPU Blender fallback for the reference compiler; geometry only, no rendering."""
import json,os,subprocess
from pathlib import Path
import numpy as np

SCRIPT=r'''import bpy,json,numpy as np,sys
job=json.load(open(sys.argv[sys.argv.index('--')+1]));meta=json.load(open(job['metadata']));raw=np.load(job['source'],allow_pickle=False)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
source=sum(len(raw['f_'+p]) for p in meta['part_ids']);ratio=min(.98,.85*job['max_triangles']/source)
objects=[]
for pid in meta['part_ids']:
 v=raw['v_'+pid];f=raw['f_'+pid];m=bpy.data.meshes.new(pid);m.from_pydata(v.tolist(),[],f.tolist());m.update();o=bpy.data.objects.new(pid,m);bpy.context.collection.objects.link(o);objects.append(o)
 # Dissolve coplanar faces before collapse, protecting small flat features.
 bpy.context.view_layer.objects.active=o;o.select_set(True)
 mod=o.modifiers.new('coplanar','DECIMATE');mod.decimate_type='DISSOLVE';mod.angle_limit=.0001;bpy.ops.object.modifier_apply(modifier=mod.name)
 if len(f)>128:
  mod=o.modifiers.new('budget','DECIMATE');mod.ratio=ratio;mod.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=mod.name)
 o.select_set(False)
output={}
for o in objects:
 m=o.data;m.calc_loop_triangles();output['v_'+o.name]=np.array([v.co[:] for v in m.vertices],dtype=float);output['f_'+o.name]=np.array([t.vertices[:] for t in m.loop_triangles],dtype=np.int32)
np.savez_compressed('/work/visual-blender.npz',**output)
'''

def compile_visual(job):
 Path('lod-blender.py').write_text(SCRIPT);Path('lod-job.json').write_text(json.dumps(job));env=dict(os.environ);env['PYTHONPATH']=''
 p=subprocess.run(['blender','-b','-t','2','--python','lod-blender.py','--','lod-job.json'],capture_output=True,env=env,timeout=20)
 Path('blender-lod.log').write_bytes(p.stdout+p.stderr)
 if p.returncode or not Path('visual-blender.npz').exists():return None
 with np.load('visual-blender.npz',allow_pickle=False) as a:return {p:(np.array(a['v_'+p]),np.array(a['f_'+p])) for p in json.loads(Path(job['metadata']).read_text())['part_ids']}
