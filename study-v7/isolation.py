"""Native Codex permission profile for public-only agent/method workspaces."""
import json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PROFILE='openrsi_v7'
PYTHON=ROOT/'.tools/physics-venv/bin/python'


def toml(value):
    if isinstance(value,dict):return '{'+','.join(json.dumps(k)+'='+toml(v) for k,v in value.items())+'}'
    return json.dumps(value)


def config_args(workspace,protected=()):
    workspace=Path(workspace).resolve();(workspace/'.tmp').mkdir(exist_ok=True)
    runtime_root=PYTHON.resolve().parents[2]
    if runtime_root==Path('/'):runtime_root=PYTHON.resolve().parents[1]
    filesystem={':root':'deny',':minimal':'read',':slash_tmp':'deny',':tmpdir':'deny',str(ROOT/'.tools/physics-venv'):'read',str(runtime_root):'read'}
    if Path('/opt/homebrew').exists():filesystem['/opt/homebrew']='read'
    if protected:filesystem[':workspace_roots']={'.':'write',**{str(p):'read' for p in protected},'.exchange/requests':'write'}
    policy=dict(extends=':workspace',filesystem=filesystem,network=dict(enabled=False))
    values={'default_permissions':PROFILE,'permissions.'+PROFILE:policy,'approval_policy':'never','shell_environment_policy.inherit':'none','shell_environment_policy.set':dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(workspace/'.tmp'))}
    args=[]
    for k,v in values.items():args+=['-c',k+'='+toml(v)]
    return args


def execute(command,workspace,timeout=30):
    args=['codex','sandbox','-P',PROFILE,'-C',str(Path(workspace).resolve()),*config_args(workspace),'--',*map(str,command)]
    return subprocess.run(args,cwd=workspace,capture_output=True,text=True,timeout=timeout)
