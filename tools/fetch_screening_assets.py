"""Fetch immutable public screening inputs; verify every byte against manifest."""
import concurrent.futures
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.tools/real-assets-screen'


def fetch(row):
    relative=Path(row['path'])
    if relative.is_absolute() or '..' in relative.parts:raise ValueError('Invalid manifest path')
    target=OUT/relative
    if target.exists():raw=target.read_bytes()
    else:
        with urllib.request.urlopen(row['url'],timeout=90) as response:raw=response.read(row['bytes']+1)
    if len(raw)!=row['bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:
        raise ValueError('Source hash mismatch: '+row['path'])
    if not target.exists():
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as stream:stream.write(raw)
    return row['bytes']


if __name__=='__main__':
    manifest=json.loads((ROOT/'study-v3/sources.json').read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        sizes=list(executor.map(fetch,manifest['files']))
    print('Verified',len(sizes),'files;',sum(sizes),'bytes')
