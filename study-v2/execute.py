"""Deliver only the immutable input GLB, then run unmodified model adapter code."""
import base64
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'lib'))
from container_runtime import execute as isolated_execute


def execute(candidate, out):
    out = Path(out)
    out.mkdir(parents=True,exist_ok=False)
    asset = ROOT/'assets/canonical/asset.glb'
    # Fixed bootstrap provides the one declared file inside the isolated
    # container, with no host mount or private data access.
    bootstrap = "import base64,bpy\nfrom pathlib import Path\n"
    bootstrap += "Path('/tmp/canonical.glb').write_bytes(base64.b64decode("+repr(base64.b64encode(asset.read_bytes()).decode())+"))\n"
    bootstrap += "bpy.ops.wm.read_factory_settings(use_empty=True)\nbpy.ops.import_scene.gltf(filepath='/tmp/canonical.glb')\n"
    bootstrap += 'exec(compile('+repr(Path(candidate).read_text())+",'model_adapter.py','exec'))\n"
    path = out/'bootstrap.py';path.write_text(bootstrap)
    info = isolated_execute(path,out/'container')
    record = dict(kind='fixed input delivery plus unmodified candidate execution',input_sha256=hashlib.sha256(asset.read_bytes()).hexdigest(),
                  candidate_sha256=hashlib.sha256(Path(candidate).read_bytes()).hexdigest(),bootstrap_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),execution=info)
    (out/'delivery.json').write_text(json.dumps(record,indent=2)+'\n')
    return record
