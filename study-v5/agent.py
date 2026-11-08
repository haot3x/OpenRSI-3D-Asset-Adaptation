"""One public-only tool-using research episode, then frozen transfer evaluation."""
import argparse,copy,hashlib,json,os,re,shutil,signal,stat,subprocess,threading,time
from pathlib import Path
from asset_task import json_read
from execution import DOCKER,IMAGE,evaluate_method,save,sha
from isolation import config_args,PYTHON
ROOT=Path(__file__).resolve().parents[1]
HERE=Path(__file__).resolve().parent


def aggregate(rows):
    scorable=all(r['scored'] for r in rows)
    return dict(scorable=scorable,passed=sum(bool(r.get('evaluation',{}).get('passed')) for r in rows),total=len(rows),fraction=sum(bool(r.get('evaluation',{}).get('passed')) for r in rows)/len(rows) if scorable else None)


class Broker:
    def __init__(self,workspace,out,cases,image_id):
        self.work=workspace;self.out=out;self.cases=cases;self.image_id=image_id;self.stop=threading.Event();self.records=[];self.seen=set();self.error=None
    def start(self):self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
    def run(self):
        try:
            while not self.stop.is_set():
                for path in sorted((self.work/'.exchange/requests').glob('*.json')):
                    if self.stop.is_set():break
                    if path.name in self.seen:continue
                    self.seen.add(path.name)
                    if not re.fullmatch('[a-f0-9]{32}\\.json',path.name) or path.is_symlink():continue
                    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
                    try:
                        info=os.fstat(fd)
                        if not stat.S_ISREG(info.st_mode) or info.st_size>256*1024:continue
                        raw=os.read(fd,256*1024+1)
                    finally:os.close(fd)
                    try:
                        request=json.loads(raw);code=request['code'];assert request['id']==path.stem and isinstance(code,str) and len(code.encode())<=128*1024
                    except (ValueError,KeyError,AssertionError,TypeError):continue
                    if len(self.records)>=6:response=dict(status='development_submission_budget_exhausted',remaining=0)
                    else:
                        number=len(self.records)+1;folder=self.out/('dev-'+str(number).zfill(2));folder.mkdir();(folder/'generator.py').write_text(code)
                        print('DEV_SUBMISSION',number,hashlib.sha256(code.encode()).hexdigest(),flush=True);rows=[]
                        for case in self.cases:
                            r=evaluate_method(code,ROOT/'.tools/v5-inputs'/case['source'],case,folder/case['id'],self.image_id);rows.append(r)
                        response=dict(status='evaluated',submission=number,remaining=6-number,generator_sha256=hashlib.sha256(code.encode()).hexdigest(),summary=aggregate(rows),cases=rows)
                        save(folder/'feedback.json',response);self.records.append(dict(number=number,folder=str(folder.relative_to(self.out)),**response));save(self.out/'dev-ledger.json',self.records)
                        print('DEV_RESULT',number,response['summary'],flush=True)
                    feedback=copy.deepcopy(response)
                    for row in feedback.get('cases',[]):row.get('evaluation',{}).get('preservation',{}).pop('affines',None)
                    destination=self.work/'.exchange/responses'/path.name
                    with destination.open('x') as stream:stream.write(json.dumps(feedback,indent=2)+'\n')
                self.stop.wait(.2)
        except BaseException as error:self.error=repr(error);save(self.out/'broker-error.json',dict(error=self.error))


def copy_native(events,folder):
    ids={e['thread_id'] for e in events if e.get('type')=='thread.started'}
    if len(ids)!=1:return dict(status='missing_or_ambiguous_thread')
    id=next(iter(ids));session_root=Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))/'sessions';paths=list(session_root.glob('**/*'+id+'*.jsonl'))
    if len(paths)!=1:return dict(status='missing_native_session')
    if json.loads(paths[0].read_text().splitlines()[0]).get('payload',{}).get('id')!=id:return dict(status='native_identity_mismatch')
    target=folder/'native-session.jsonl';shutil.copyfile(paths[0],target);return dict(status='copied_exact_fresh_session',thread_id=id,sha256=sha(target))


def workspace(out,devcases):
    work=out/'workspace';work.mkdir();(work/'.exchange/requests').mkdir(parents=True);(work/'.exchange/responses').mkdir();(work/'.tmp').mkdir()
    for name in ['asset_task.py','dev_eval.py','TASK.md']:shutil.copyfile(HERE/name,work/name)
    shutil.copytree(ROOT/'.tools/v5-inputs/medical_cart001',work/'asset')
    save(work/'dev-scenes.json',dict(cases=[dict(id=c['id'],bounds=c['bounds']) for c in devcases]))
    reference=ROOT/'.tools/real-assets-screen/ArtVIP/medical_cart001/close.png';shutil.copyfile(reference,work/'reference.png')
    (work/'python').write_text('#!/bin/sh\nexec '+"'"+str(PYTHON).replace("'","'\\''")+"' \"$@\"\n");(work/'python').chmod(0o755)
    sentinel=out/'outside-sentinel.txt';sentinel.write_text('Public non-secret boundary sentinel')
    probe="""import pathlib,socket
try:pathlib.Path(%r).read_text()
except PermissionError:pass
else:raise AssertionError('Outside-workspace read unexpectedly allowed')
try:pathlib.Path('.exchange/responses/forbidden-check.txt').write_text('probe')
except PermissionError:pass
else:raise AssertionError('Protected feedback directory writable')
s=socket.socket()
try:s.connect(('127.0.0.1',9))
except PermissionError:pass
except OSError as e:raise AssertionError('Network not denied by policy: '+str(e))
else:raise AssertionError('Network unexpectedly allowed')
print('BOUNDARY_OK: outside reads, feedback writes and network denied')
"""%str(sentinel)
    (work/'check_boundary.py').write_text(probe)
    return work


def main():
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--controls',type=Path,required=True);args=p.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    assert json_read(args.controls/'verified.json')['passed'];cases=json_read(args.controls/'cases-private.json')['cases'];dev=[c for c in cases if c['split']=='dev'];test=[c for c in cases if c['split']=='heldout']
    image=json.loads(subprocess.check_output([*DOCKER,'image','inspect',IMAGE],text=True))[0];image_id=image['Id'];save(out/'image.json',{k:image[k] for k in ['Id','Architecture','Os','Created']})
    work=workspace(out,dev);protected=['asset','asset_task.py','dev_eval.py','TASK.md','dev-scenes.json','reference.png','python','check_boundary.py','.exchange']
    policy=config_args(work,protected);save(out/'permission-config.json',policy)
    # Exact production policy preflight, without an inference call.
    command=['codex','sandbox','-P','openrsi_v5','-C',str(work),*policy,'--',str(PYTHON),str(work/'check_boundary.py')]
    r=subprocess.run(command,cwd=work,capture_output=True,text=True,timeout=30);save(out/'boundary-preflight.json',dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0 and 'BOUNDARY_OK' in r.stdout,r.stderr
    source=[p for p in HERE.iterdir() if p.is_file()]+[ROOT/'study-v3/sources.json']
    frozen={str(p.relative_to(ROOT)):sha(p) for p in sorted(source)};save(out/'frozen-source.json',frozen);save(out/'frozen-cases-private.json',cases)
    for name in ['medical_cart001','cabinet_1']:
        for path in (ROOT/'.tools/v5-inputs'/name).iterdir():frozen[str(path.relative_to(ROOT))]=sha(path)
    save(out/'frozen-source-and-inputs.json',frozen)
    for relative,digest in frozen.items():
        target=out/'frozen-source-copy'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/relative,target)
    baseline_files={str(p.relative_to(work)):sha(p) for p in work.rglob('*') if p.is_file()};save(out/'initial-workspace-hashes.json',baseline_files)
    prompt='Read TASK.md and implement the reusable 3D geometry/rig generator at generator.py. First run ./python check_boundary.py and stop immediately if it fails. Use the authoritative dev_eval.py feedback while improving your code, with at most 6 dev submissions. You have 900 seconds total; prioritize a complete portable generator and finish normally within the budget. All source data in this workspace is public. Do not inspect other paths, request escalation, access network, spawn agents, or invent transfer results. Leave generator.py as the final artifact. The attached image is reference appearance only; canonical NPZ geometry and metadata are authoritative.'
    (out/'prompt.txt').write_text(prompt)
    cmd=['codex','exec','--skip-git-repo-check','--ignore-user-config','--ignore-rules',*policy,'-c','model_reasoning_effort="max"','-c','web_search="disabled"','-c','project_doc_max_bytes=0','-c','mcp_servers={}']
    for feature in ['apps','plugins','memories','multi_agent','multi_agent_v2','hooks','goals','browser_use','computer_use','image_generation']:cmd+=['-c','features.'+feature+'=false']
    cmd+=['--model','gpt-6-astra','--json','--color','never','-C',str(work),'--image',str(work/'reference.png'),'--output-last-message',str(out/'last-message.txt'),'-']
    run=dict(command=cmd,codex_cli=subprocess.check_output(['codex','--version'],text=True).strip(),model='gpt-6-astra',reasoning_effort='max',tools=True,seconds=900,max_dev_submissions=6,automatic_retries=0,prompt_sha256=sha(out/'prompt.txt'));save(out/'invocation.json',run)
    broker=Broker(work,out,dev,image_id);broker.start();start=time.monotonic();print('START_TOOL_USING_AGENT',flush=True)
    with (out/'events.jsonl').open('wb') as stdout,(out/'stderr.log').open('wb') as stderr:
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr,start_new_session=True)
        try:proc.communicate(prompt.encode(),timeout=900);run['status']='completed' if proc.returncode==0 else 'cli_or_provider_error'
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGTERM)
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=5)
            run['status']='incomplete_deadline'
    broker.stop.set();broker.thread.join(timeout=180)
    run.update(returncode=proc.returncode,wall_seconds=round(time.monotonic()-start,3),dev_submissions=len(broker.records),broker_error=broker.error)
    events=[json.loads(line) for line in (out/'events.jsonl').read_text().splitlines()];run['native_session']=copy_native(events,out);run['item_types']=sorted({e['item'].get('type','') for e in events if 'item' in e});run['usage']=[e.get('usage') for e in events if e.get('type')=='turn.completed'];save(out/'invocation.json',run)
    print('AGENT_END',run['status'],run['wall_seconds'],'seconds; dev submissions',len(broker.records),flush=True)
    if run['status']!='completed' or broker.error or broker.thread.is_alive() or run['native_session']['status']!='copied_exact_fresh_session':return
    for relative,digest in baseline_files.items():
        if relative.startswith('.exchange/'):continue
        assert sha(work/relative)==digest,'Read-only workspace input changed: '+relative
    final=work/'generator.py'
    if final.is_symlink() or not final.is_file() or final.stat().st_size>128*1024:save(out/'artifact-error.json',dict(status='missing_or_invalid_final_generator',scored=False));return
    snapshots=out/'frozen-candidates';snapshots.mkdir();shutil.copyfile(final,snapshots/'final.py');final_code=(snapshots/'final.py').read_text()
    first=next((r for r in broker.records if r['summary']['scorable']),None)
    if first:shutil.copyfile(out/first['folder']/'generator.py',snapshots/'first.py')
    candidates=[('first',(snapshots/'first.py').read_text())] if first else []
    candidates.append(('final',final_code));results={};cache={}
    for name,code in candidates:
        digest=hashlib.sha256(code.encode()).hexdigest();rows=[]
        for case in test:
            key=(digest,case['id'])
            if key not in cache:
                path=out/('transfer-'+name)/case['id'];path.parent.mkdir(exist_ok=True);print('TRANSFER',name,case['id'],flush=True)
                cache[key]=evaluate_method(code,ROOT/'.tools/v5-inputs'/case['source'],case,path,image_id)
            rows.append(cache[key])
        results[name]=dict(generator_sha256=digest,summary=aggregate(rows),cases=rows)
        save(out/'transfer-results.json',results);print('TRANSFER_RESULT',name,results[name]['summary'],flush=True)
    final_hash=hashlib.sha256(final_code.encode()).hexdigest();existing=next((r for r in broker.records if r['generator_sha256']==final_hash),None)
    if existing:retention=dict(reused_exact_code_development_submission=existing['number'],summary=existing['summary'],cases=existing['cases'])
    else:
        rows=[]
        for case in dev:
            folder=out/'final-dev'/case['id'];folder.parent.mkdir(exist_ok=True);rows.append(evaluate_method(final_code,ROOT/'.tools/v5-inputs'/case['source'],case,folder,image_id))
        retention=dict(summary=aggregate(rows),cases=rows)
    save(out/'retention.json',retention)
    for p,digest in frozen.items():assert sha(ROOT/p)==digest,'Frozen study changed: '+p
    print('DONE_V5',flush=True)


if __name__=='__main__':main()
