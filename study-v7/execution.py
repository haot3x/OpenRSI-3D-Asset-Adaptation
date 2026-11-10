"""Isolated generation of complete asset artifacts; host owns fixed evaluation."""
import base64,hashlib,io,json,os,subprocess,tarfile,time,uuid
from pathlib import Path
from evaluator import evaluate
ROOT=Path(__file__).resolve().parents[1];HERE=Path(__file__).resolve().parent
DOCKER=['docker']+(['--host',os.environ['ASSET_DOCKER_HOST']] if os.environ.get('ASSET_DOCKER_HOST') else [])
IMAGE='openrsi-asset-proxy:v6'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,data):Path(path).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')

def evaluate_method(code,case,out,image_id,data_root,probes_root):
 out=Path(out);out.mkdir(parents=True,exist_ok=False);source=Path(data_root)/case['family']
 job={k:case[k] for k in ['max_triangles','max_hulls','max_proxy_vertices','max_vertices_per_hull','visual_tolerance_m','generation_seconds']};job.update(source='source.npz',metadata='metadata.json')
 metadata=json.loads((source/'metadata.json').read_text());metadata.pop('family',None)
 files={'generator.py':code.encode(),'blender_lod.py':(HERE/'blender_lod.py').read_bytes(),'primitive_fit.py':(HERE/'primitive_fit.py').read_bytes(),'asset_sdk.py':(HERE/'asset_sdk.py').read_bytes(),'source.npz':(source/'source.npz').read_bytes(),'metadata.json':json.dumps(metadata).encode(),'job.json':json.dumps(job).encode(),
        'legacy_proxy.py':(ROOT/'study-v6/generators/final.py').read_bytes(),'proxy_sdk.py':(ROOT/'study-v6/proxy_sdk.py').read_bytes()}
 payload=io.BytesIO()
 with tarfile.open(fileobj=payload,mode='w') as tar:
  for name,raw in files.items():
   entry=tarfile.TarInfo(name);entry.size=len(raw);entry.mode=0o644;tar.addfile(entry,io.BytesIO(raw))
 name='openrsi-joint-v7-'+uuid.uuid4().hex[:12];timeout=case['generation_seconds']
 wrapper=f'tar -xf - -C /work; cd /work; ulimit -f 65536; ulimit -t {timeout}; python3 generator.py job.json output; task_rc=$?; echo "$task_rc" > .exitcode; sleep 180'
 command=[*DOCKER,'run','--name',name,'--network','none','--read-only','--user','1000:1000','--cap-drop','ALL','--security-opt','no-new-privileges','--cpus','2','--memory','3g','--memory-swap','3g','--pids-limit','64','--tmpfs','/work:rw,nosuid,size=192m,uid=1000,gid=1000','--tmpfs','/tmp:rw,nosuid,size=64m,uid=1000,gid=1000','--workdir','/work','--entrypoint','/bin/sh','-i',image_id,'-c',wrapper]
 record=dict(command=command,image_id=image_id,case=case['id'],generator_sha256=hashlib.sha256(code.encode()).hexdigest(),source_sha256=sha(source/'source.npz'),metadata_sha256=sha(source/'metadata.json'),payload_sha256=hashlib.sha256(payload.getvalue()).hexdigest())
 save(out/'execution.json',record);(out/'generator.py').write_text(code);start=time.monotonic();proc=None;rc=None
 try:
  with (out/'stdout.log').open('wb') as stdout,(out/'stderr.log').open('wb') as stderr:
   proc=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr);proc.stdin.write(payload.getvalue());proc.stdin.close()
   while time.monotonic()-start<timeout:
    poll=subprocess.run([*DOCKER,'exec',name,'cat','/work/.exitcode'],capture_output=True,text=True,timeout=5)
    if poll.returncode==0:rc=int(poll.stdout.strip());break
    if proc.poll() is not None:break
    time.sleep(.25)
   record.update(status='generated' if rc==0 else 'candidate_process_failure' if rc is not None else 'timeout_or_infrastructure',exit_code=rc)
   if rc==0:
    reader="import os,stat,base64,json;d={};\nfor n,c in [('visual.npz',67108864),('proxies.json',16777216),('rig.json',262144)]:\n p='/work/output/'+n;s=os.lstat(p);assert stat.S_ISREG(s.st_mode) and s.st_size<=c;d[n]=base64.b64encode(open(p,'rb').read()).decode()\nprint(json.dumps(d))"
    r=subprocess.run([*DOCKER,'exec',name,'python3','-c',reader],capture_output=True,timeout=20)
    if r.returncode:record.update(status='candidate_output_invalid',error=r.stderr.decode(errors='replace')[-1500:])
    else:
     folder=out/'output';folder.mkdir()
     for filename,raw in json.loads(r.stdout).items():
      if filename not in ['visual.npz','proxies.json','rig.json']:raise ValueError('Unexpected output name')
      (folder/filename).write_bytes(base64.b64decode(raw))
     record['output_hashes']={p.name:sha(p) for p in folder.iterdir()}
 finally:
  cleanup=subprocess.run([*DOCKER,'rm','--force',name],capture_output=True);record['container_removed']=cleanup.returncode==0
  if proc is not None:
   try:proc.wait(timeout=10)
   except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=5)
  record['generation_wall_seconds']=round(time.monotonic()-start,3);save(out/'execution.json',record)
 result=dict(case=case['id'],family=case['family'],profile=case['profile'],scored=False,generator_sha256=record['generator_sha256'],status=record['status'])
 if record['status']=='generated':
  try:r=evaluate(source,out/'output',case,Path(probes_root)/case['family'])
  except (ValueError,KeyError,TypeError) as error:result.update(status='candidate_invalid',error=str(error))
  else:result.update(status='evaluated',scored=True,evaluation=r)
 save(out/'result.json',result);return result

def aggregate(rows):
 valid=bool(rows) and all(r['scored'] for r in rows);families=sorted({r['family'] for r in rows});scores={}
 if valid:
  for f in families:
   values=[r['evaluation']['score'] for r in rows if r['family']==f];scores[f]=sum(values)/len(values)
 return dict(scorable=valid,cases=len(rows),families=len(families),family_scores=scores,mean_score=sum(scores.values())/len(scores) if valid else None)
