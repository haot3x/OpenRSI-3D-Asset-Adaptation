"""Developer-authored feasibility controls; never scored as model results."""
import argparse
import json
import os
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
from container_runtime import execute
from check import evaluate, save


def mutate(path, destination, kind):
    raw = path.read_bytes()
    length = struct.unpack_from('<I', raw, 12)[0]
    doc = json.loads(raw[20:20+length])
    if kind == 'static':
        assert doc.pop('animations')
    else:
        for node in doc['nodes']:
            if node.get('name') == 'DockSocket':
                node['name'] = 'RemovedDockSocket'
    encoded = json.dumps(doc, separators=(',', ':')).encode()
    encoded += b' '*(-len(encoded)%4)
    body = struct.pack('<II', len(encoded), 0x4e4f534a) + encoded + raw[20+length:]
    destination.write_bytes(struct.pack('<4sII', b'glTF', 2, len(body)+12) + body)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    source = (ROOT / 'assets/adapted/source.py').read_text()
    edit = '''
# Developer-authored feasibility changes, not a model-generated solution.
for name in ['Neck','PelicanHead','EyeLeft','EyeRight','Beak','Pouch']:
    bpy.data.objects[name].location.z -= .06
bpy.context.view_layer.update()
for name in ['PelicanBody','Breast','FoldedWingLeft','FoldedWingRight','Handlebar','FootLeft','FootRight','PedalLeft','PedalRight','Saddle']:
    o=bpy.data.objects[name]
    transform=o.matrix_world.copy();inverse=transform.inverted()
    for vertex in o.data.vertices:
        world=transform @ vertex.co
        world.x=max(-.25,min(.25,world.x))
        vertex.co=inverse @ world
for o in list(scene.objects):
    if o.type=='MESH' and len(o.data.polygons)>24:
        bpy.context.view_layer.objects.active=o
        mod=o.modifiers.new('ControlLOD','DECIMATE');mod.ratio=.32
        bpy.ops.object.modifier_apply(modifier=mod.name)
empty('DockSocket',(0,-1.2,1.12))
box('DockPlate',(0,-1.2,1.105),(.30,.24,.03),turquoise)
for x in [-.11,.11]:rod('RackSupport'+str(x),(x,-.85,.7),(x,-1.2,1.09),.018,silver)
'''
    marker="os.makedirs('/output',exist_ok=True)"
    assert source.count(marker) == 1
    script = out / 'positive-control.py'
    script.write_text(source.replace(marker, edit+'\n'+marker))
    execution = execute(script, out / 'execution')
    if execution['status'] != 'completed':
        raise RuntimeError('Feasibility control failed to export')
    asset = out / 'execution/asset.glb'
    scenes = json.loads((ROOT / 'study-v1/scenes.json').read_text())
    all_scenes = scenes['prior'] + scenes['development'] + scenes['transfer']
    positive = [evaluate(asset, s, out / 'positive' / s['id'], os.environ['GODOT_BIN']) for s in all_scenes]
    negative = []
    for kind in ['static', 'missing_dock']:
        mutated = out / (kind+'.glb')
        mutate(asset, mutated, kind)
        negative.append(evaluate(mutated, scenes['transfer'][0], out / 'negative' / kind, os.environ['GODOT_BIN']))
    passed = all(r['all_checks_pass'] for r in positive) and all(not r['all_checks_pass'] for r in negative)
    save(out / 'summary.json', dict(kind='developer-authored checker feasibility, not model scores', passed=passed,
                                    positive=positive, negative=negative))
    print(json.dumps(dict(passed=passed, positive=[dict(scene=r['scene_id'], triangles=r['triangle_count'], failed=r['failed_checks']) for r in positive],
                         negative=[r['failed_checks'] for r in negative]), indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
