"""Fixed v2 asset/adapter checks with independent geometry identity validation."""
import json
import os
from pathlib import Path
import subprocess

from geometry import compare,load
ROOT = Path(__file__).resolve().parents[1]


def save(path,data):
    path.write_text(json.dumps(data,indent=2)+'\n')


def metadata(out,godot):
    out.mkdir(parents=True,exist_ok=False)
    save(out/'job.json',dict(asset_path=str(ROOT/'assets/canonical/asset.glb'),spec={},render=False,output=str(out)))
    p = subprocess.run([godot,'--headless','--path',str(ROOT/'runtime'),'--script','res://inspect_v2.gd','--',str(out/'job.json')],capture_output=True,text=True,timeout=40)
    (out/'stdout.log').write_text(p.stdout);(out/'stderr.log').write_text(p.stderr)
    lines=[s[len('V2_METADATA '):] for s in p.stdout.splitlines() if s.startswith('V2_METADATA ')]
    if p.returncode or len(lines)!=1 or 'SCRIPT ERROR' in p.stderr:raise RuntimeError('Metadata inspector failed')
    m=json.loads(lines[0]);doc,_=load(ROOT/'assets/canonical/asset.glb')
    animated={c['target']['node'] for a in doc['animations'] for c in a['channels']}
    parent={child:i for i,node in enumerate(doc['nodes']) for child in node.get('children',[])}
    def moves(index):
        while True:
            if index in animated:return True
            if index not in parent:return False
            index=parent[index]
    upper={'Neck','PelicanHead','Beak','Pouch','EyeLeft','EyeRight'}
    allowed_static={node['name'] for i,node in enumerate(doc['nodes']) if 'mesh' in node and not moves(i) and node['name'] not in upper}
    m['static_meshes']={name:value for name,value in m['meshes'].items() if name in allowed_static}
    m['allowed_upper_meshes']=sorted(upper)
    save(out/'metadata.json',m);return m


def evaluate(asset,out,m,godot,sequence=None):
    out.mkdir(parents=True,exist_ok=False)
    identity=compare(ROOT/'assets/canonical/asset.glb',asset)
    save(out/'identity.json',identity)
    if not identity['passed']:
        result=dict(status='identity_invalid_unscored',identity=identity,scene_fraction=None)
        save(out/'result.json',result);return result
    definitions=json.loads((ROOT/'study-v2/scenes.json').read_text())
    spec=dict(triangle_limit=6000,scenes=definitions['scenes'],sequence=sequence or definitions['switch_sequence'],
              neck_anchor=m['neck_anchor'],static_meshes=m['static_meshes'],meshes=m['meshes'])
    save(out/'job.json',dict(asset_path=str(asset.resolve()),spec=spec,render=False,output=str(out)))
    p=subprocess.run([godot,'--headless','--path',str(ROOT/'runtime'),'--script','res://adapter_v2.gd','--',str(out/'job.json')],capture_output=True,text=True,timeout=100)
    (out/'stdout.log').write_text(p.stdout);(out/'stderr.log').write_text(p.stderr)
    lines=[s[len('ADAPTER_V2_RESULT '):] for s in p.stdout.splitlines() if s.startswith('ADAPTER_V2_RESULT ')]
    if p.returncode or len(lines)!=1 or 'SCRIPT ERROR' in p.stderr or 'ERROR:' in p.stderr:raise RuntimeError('Evaluator infrastructure failure: '+str(out))
    data=json.loads(lines[0]);result=dict(status='evaluated',identity=identity,**data,
        scene_fraction=sum(data['scene_pass'].values())/len(data['scene_pass']),
        switch_visits_passed=sum(v['passed'] for v in data['visits']),switch_visits_total=len(data['visits']))
    save(out/'result.json',result);return result
