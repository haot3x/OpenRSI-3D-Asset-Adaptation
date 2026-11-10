"""Public subject client; request only development feedback via a file exchange."""
import argparse,json,os,time,uuid
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('generator',type=Path);args=p.parse_args();root=Path(__file__).resolve().parent
    source=args.generator.resolve()
    if not source.is_relative_to(root) or source.is_symlink() or source.stat().st_size>128*1024:raise ValueError('Require a regular <=128 KiB generator in the workspace')
    id=uuid.uuid4().hex;request=dict(id=id,code=source.read_text());exchange=root/'.exchange';temp=exchange/'requests'/(id+'.tmp');final=exchange/'requests'/(id+'.json')
    temp.write_text(json.dumps(request));os.replace(temp,final);response=exchange/'responses'/(id+'.json');start=time.monotonic()
    while time.monotonic()-start<420:
        if response.is_file():
            raw=response.read_text();result=json.loads(raw);out=root/'dev-results'/id;out.mkdir(parents=True,exist_ok=False);(out/'result.json').write_text(raw);print(json.dumps(result,indent=2));return
        time.sleep(.25)
    raise TimeoutError('No development feedback within 420 seconds')


if __name__=='__main__':main()
