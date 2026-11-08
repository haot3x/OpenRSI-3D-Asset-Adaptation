"""Fresh networkless CPU containers for generated mesh/rig code; no host mounts."""
import base64,hashlib,io,json,os,subprocess,tarfile,time,uuid
from pathlib import Path
from asset_task import load_source,read_output,evaluate
ROOT=Path(__file__).resolve().parents[1]
DOCKER=['docker']+(['--host',os.environ['ASSET_DOCKER_HOST']] if os.environ.get('ASSET_DOCKER_HOST') else [])
IMAGE='openrsi-asset-generator:v5'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,data):Path(path).write_text(json.dumps(data,indent=2)+'\n')


def execute(code,source_dir,scene,out,image_id,timeout=30):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);source_dir=Path(source_dir)
    job=dict(asset_dir='asset',scene=dict(bounds=scene['bounds'],clearance=.008))
    files={'generator.py':code.encode(),'asset_task.py':(Path(__file__).parent/'asset_task.py').read_bytes(),'asset/canonical.npz':(source_dir/'canonical.npz').read_bytes(),'asset/metadata.json':(source_dir/'metadata.json').read_bytes(),'job.json':json.dumps(job).encode()}
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w') as tar:
        for name,raw in files.items():
            info=tarfile.TarInfo(name);info.size=len(raw);info.mode=0o644;tar.addfile(info,io.BytesIO(raw))
    payload=buffer.getvalue();name='openrsi-geometry-v5-'+uuid.uuid4().hex[:12]
    wrapper='tar -xf - -C /work; cd /work; ulimit -f 131072; ulimit -t 30; python3 generator.py job.json output; v5_rc=$?; echo "$v5_rc" > /work/.exitcode; sleep 120'
    command=[*DOCKER,'run','--name',name,'--network','none','--read-only','--user','1000:1000','--cap-drop','ALL','--security-opt','no-new-privileges','--cpus','2','--memory','3g','--memory-swap','3g','--pids-limit','64','--tmpfs','/work:rw,nosuid,size=192m,uid=1000,gid=1000','--tmpfs','/tmp:rw,nosuid,size=64m,uid=1000,gid=1000','--workdir','/work','--entrypoint','/bin/sh','-i',image_id,'-c',wrapper]
    record=dict(image_id=image_id,container=name,command=command,generator_sha256=hashlib.sha256(code.encode()).hexdigest(),payload_sha256=hashlib.sha256(payload).hexdigest(),source_sha256=sha(source_dir/'canonical.npz'),job=job,timeout_seconds=timeout)
    save(out/'execution.json',record);(out/'generator.py').write_text(code);start=time.monotonic();proc=None;rc=None
    try:
        with (out/'stdout.log').open('wb') as stdout,(out/'stderr.log').open('wb') as stderr:
            proc=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr);proc.stdin.write(payload);proc.stdin.close()
            while time.monotonic()-start<timeout:
                r=subprocess.run([*DOCKER,'exec',name,'cat','/work/.exitcode'],capture_output=True,text=True,timeout=5)
                if r.returncode==0:rc=int(r.stdout.strip());break
                if proc.poll() is not None:break
                time.sleep(.25)
            record.update(exit_code=rc,status='generated' if rc==0 else 'candidate_process_failed' if rc is not None else 'generation_timeout_or_infrastructure')
            if rc==0:
                reader="import base64,json,os,stat; out={};\nfor name,cap in [('mesh.npz',33554432),('rig.json',131072)]:\n p='/work/output/'+name;s=os.lstat(p);assert stat.S_ISREG(s.st_mode) and s.st_size<=cap;out[name]=base64.b64encode(open(p,'rb').read()).decode()\nprint(json.dumps(out))"
                r=subprocess.run([*DOCKER,'exec',name,'python3','-c',reader],capture_output=True,timeout=15)
                if r.returncode:record.update(status='candidate_output_missing_or_invalid',error=r.stderr.decode(errors='replace')[-2000:])
                else:
                    output=out/'output';output.mkdir()
                    for filename,data in json.loads(r.stdout).items():
                        if filename not in ['mesh.npz','rig.json']:raise ValueError('Unexpected output file')
                        (output/filename).write_bytes(base64.b64decode(data))
                    record['output_sha256']={p.name:sha(p) for p in output.iterdir()}
    finally:
        cleanup=subprocess.run([*DOCKER,'rm','--force',name],capture_output=True,text=True);record['container_removed']=cleanup.returncode==0
        if proc is not None:
            try:proc.wait(timeout=10)
            except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=5)
        record['wall_seconds']=round(time.monotonic()-start,3);save(out/'execution.json',record)
    return record


def evaluate_method(code,source_dir,scene,out,image_id):
    out=Path(out);execution=execute(code,source_dir,scene,out,image_id)
    result=dict(case=scene['id'],scored=False,generator_sha256=execution['generator_sha256'],execution_status=execution['status'])
    if execution['status']=='generated':
        source=load_source(source_dir)
        try:candidate=read_output(out/'output',source)
        except (ValueError,KeyError,TypeError) as error:result.update(status='candidate_invalid',error=str(error))
        else:
            evaluation=evaluate(source,candidate,scene);result.update(status='evaluated',scored=True,evaluation=evaluation)
    else:result['status']=execution['status']
    save(out/'result.json',result);return result
