"""Execute only generated Blender code inside a fresh resource-limited container."""
import json
import os
import struct
import subprocess
import time
import uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
DOCKER=['docker'] + (['--host',os.environ['ASSET_DOCKER_HOST']] if os.environ.get('ASSET_DOCKER_HOST') else [])
IMAGE='openrsi-asset-blender:pilot-v0'

def validate_glb(path):
 path=Path(path)
 if path.is_symlink() or not path.is_file() or not 20<=path.stat().st_size<=32*1024*1024:raise ValueError('missing, linked or oversized GLB')
 raw=path.read_bytes(); magic,version,size=struct.unpack_from('<4sII',raw)
 if magic!=b'glTF' or version!=2 or size!=len(raw):raise ValueError('invalid GLB header')
 length,kind=struct.unpack_from('<II',raw,12)
 if kind!=0x4e4f534a or length>len(raw)-20:raise ValueError('missing JSON chunk')
 data=json.loads(raw[20:20+length])
 for item in data.get('buffers',[])+data.get('images',[]):
  if 'uri' in item:raise ValueError('external or data URI resources are not accepted')
 if len(data.get('nodes',[]))>256 or len(data.get('meshes',[]))>128:raise ValueError('scene is beyond pilot bounds')
 if any(a.get('count',0)>100000 for a in data.get('accessors',[])):raise ValueError('oversized accessor')
 return dict(byte_count=len(raw),nodes=len(data.get('nodes',[])),meshes=len(data.get('meshes',[])))

def execute(script,output,timeout=90):
 output=Path(output);output.mkdir(parents=True,exist_ok=True)
 image=json.loads(subprocess.check_output([*DOCKER,'image','inspect',IMAGE],text=True))[0]
 name='openrsi-3d-pilot-'+uuid.uuid4().hex[:12]
 wrapper='cat > /tmp/candidate.py; blender --background --factory-startup --disable-autoexec --threads 2 --python-exit-code 42 --python /tmp/candidate.py; rsi_blender_rc=$?; printf "%s" "$rsi_blender_rc" > /output/.exitcode; sleep 120'
 command=[*DOCKER,'run','--name',name,'--network','none','--read-only','--user','1000:1000','--cap-drop','ALL','--security-opt','no-new-privileges','--cpus','2','--memory','2g','--memory-swap','2g','--pids-limit','128','--tmpfs','/tmp:rw,nosuid,size=256m,uid=1000,gid=1000','--tmpfs','/output:rw,noexec,nosuid,size=64m,uid=1000,gid=1000','--env','HOME=/tmp','--env','OMP_NUM_THREADS=2','--env','OPENBLAS_NUM_THREADS=1','--entrypoint','/bin/sh','-i',image['Id'],'-c',wrapper]
 info=dict(image_id=image['Id'],image_architecture=image['Architecture'],container_name=name,command=command,timeout_seconds=timeout)
 (output/'execution.json').write_text(json.dumps(info,indent=2)+'\n')
 start=time.monotonic();code=None;p=None
 try:
  with (output/'blender.stdout.log').open('wb') as stdout,(output/'blender.stderr.log').open('wb') as stderr:
   p=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr)
   p.stdin.write(Path(script).read_bytes());p.stdin.close()
   while time.monotonic()-start<timeout:
    done=subprocess.run([*DOCKER,'exec',name,'cat','/output/.exitcode'],capture_output=True,text=True,timeout=5)
    if done.returncode==0:
     code=int(done.stdout.strip());break
    if p.poll() is not None:break
    time.sleep(.5)
   info['blender_exit_code']=code
   info['status']='completed' if code==0 else 'generated_script_failed' if code is not None else 'execution_incomplete'
   state=subprocess.run([*DOCKER,'inspect','--format','{{json .State}}',name],capture_output=True,text=True)
   info['container_state']=json.loads(state.stdout) if state.returncode==0 else None
   if code==0:
    # Docker's archive/cp endpoint cannot retrieve this tmpfs mount. Read the
    # bounded regular file through an exec inside the still-running container.
    reader='import os,sys; p="/output/asset.glb"; ok=os.path.isfile(p) and not os.path.islink(p) and 20<=os.path.getsize(p)<=33554432; sys.exit(3) if not ok else None; sys.stdout.buffer.write(open(p,"rb").read())'
    copy=subprocess.run([*DOCKER,'exec',name,'python3','-c',reader],capture_output=True,timeout=10)
    if copy.returncode!=0:info.update(status='generated_asset_missing' if copy.returncode==3 else 'asset_retrieval_error',copy_error=copy.stderr.decode(errors='replace'))
    else:
     (output/'asset.glb').write_bytes(copy.stdout)
     try:info['glb_validation']=validate_glb(output/'asset.glb')
     except (ValueError,KeyError,TypeError) as e:info.update(status='invalid_generated_asset',error=str(e))
 finally:
  cleanup=subprocess.run([*DOCKER,'rm','--force',name],capture_output=True,text=True)
  info['container_removed']=cleanup.returncode==0
  if p is not None:
   try:p.wait(timeout=10)
   except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=5)
  info['wall_seconds']=round(time.monotonic()-start,3)
  (output/'execution.json').write_text(json.dumps(info,indent=2)+'\n')
 return info
