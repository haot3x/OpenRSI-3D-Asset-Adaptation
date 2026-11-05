"""One bounded Codex adaptation. Native transcripts remain in ignored local runs/."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
sys.path.insert(0, str(ROOT / 'tests'))
from container_runtime import execute
from inference import generate
from smoke import evaluate


def save(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def main():
    import os
    out = ROOT / 'runs/adaptation-001'
    out.mkdir(parents=True, exist_ok=False)
    source = (ROOT / 'assets/canonical/source.py').read_text()
    scenes = json.loads((ROOT / 'scenes.json').read_text())['scenes']
    environment = {'godot': os.environ['GODOT_BIN']}
    before = [evaluate(ROOT / 'assets/canonical/asset.glb', scene, out / 'before' / scene['id'], environment['godot']) for scene in scenes]
    assert before[0]['all_checks_pass']
    assert not before[1]['checks']['ceiling_clearance']
    assert before[1]['checks']['ride_animation']
    prompt = '''Adapt this existing interactive 3D game asset for a second scene, while preserving the original scene's functionality and asset identity. It is a white low-poly pelican riding a turquoise bicycle, with a baked two-second Ride animation. The attached four images show the existing base asset, not a target to copy unchanged.

The open courtyard has a 3.0 metre roof. The new low archway has a 2.05 metre roof, and every visible part must remain at or below 2.03 metres in Blender +Z. The current asset's head extends too high. Fold/crouch the neck and reposition/reorient the head, eyes, beak and pouch as a coherent connected bird assembly so it fits. Preserve visible pelican identity and avoid obvious head/body interpenetration. Keep the main body and ALL bicycle, wheel, crank, hip, leg, foot and pedal geometry and animation unchanged. Do not globally scale or translate the asset, delete parts, make them invisible, reduce their geometry to proxies, change units, or replace the whole asset with an unrelated new one. Keep the head, beak and body volumes; only their allowed rigid pose and the neck geometry may change. All previous foot-contact, constant-leg-length, wheel/crank, loop and playback behavior must remain intact.

Use Blender 4.0.2, bpy/mathutils and Python standard library only. Return complete self-contained Blender Python in FINAL JSON fields script and design_notes. Export /output/asset.glb using the original animation export settings. No network, external resources, filesystem reads, tools or execution. A fixed runner executes the script in isolation. This is one call, no retries. Preserve the original unmodified code where adaptation is unnecessary. Return FINAL JSON directly.

Original complete source:
''' + source + '\nMeasured fixed pre-adaptation diagnostics:\n' + json.dumps([dict(scene=r['scene_id'], geometry=r['geometry']) for r in before])
    snapshots = [p for p in ROOT.rglob('*') if p.is_file() and not any(part in ['runs', '.git', '__pycache__', '.godot'] for part in p.relative_to(ROOT).parts)]
    hashes = {}
    for path in snapshots:
        relative = path.relative_to(ROOT)
        destination = out / 'frozen' / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        hashes[str(relative)] = hashlib.sha256(path.read_bytes()).hexdigest()
    save(out / 'source-manifest.json', hashes)
    images = [ROOT / 'assets/canonical' / (v + '.png') for v in ['front', 'side', 'top', 'iso']]
    folder = out / 'call-1'
    invocation = generate(prompt, images, folder, {'model': 'gpt-6-astra', 'reasoning_effort': 'low', 'seconds_per_call': 180})
    if invocation['status'] != 'completed':
        save(out / 'summary.json', dict(status=invocation['status'], official_reward=None, retry_count=0))
        raise SystemExit('Adaptation incomplete; original record preserved, no score')
    response = json.loads((folder / 'response.json').read_text())
    ast.parse(response['script'])
    script = folder / 'candidate.py'
    script.write_text(response['script'])
    result = execute(script, folder / 'execution')
    if result['status'] != 'completed':
        save(out / 'summary.json', dict(status=result['status'], official_reward=None, execution=result))
        raise SystemExit('Generated asset failed; original record preserved')
    for source, destination in [(script, ROOT / 'assets/adapted/source.py'), (folder / 'execution/asset.glb', ROOT / 'assets/adapted/asset.glb')]:
        if destination.exists():
            raise FileExistsError(destination)
        shutil.copyfile(source, destination)
    save(out / 'summary.json', dict(status='generated_pending_cross_scene_regression', official_reward=None,
                                   model_calls=1, invocation=invocation, execution=result))
    print('ADAPTATION_GENERATED', flush=True)


if __name__ == '__main__':
    main()
