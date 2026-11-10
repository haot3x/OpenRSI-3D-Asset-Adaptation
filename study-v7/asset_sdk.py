"""Subject IO only; no evaluator, fixture construction or reference geometry."""
import json
from pathlib import Path
import numpy as np

def load_job(path):
 job=json.loads(Path(path).read_text());meta=json.loads(Path(job['metadata']).read_text())
 with np.load(job['source'],allow_pickle=False) as a:
  parts={p:(np.array(a['v_'+p]),np.array(a['f_'+p])) for p in meta['part_ids']}
 return job,meta,parts

def write_output(folder,parts,proxies,rig):
 folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
 np.savez_compressed(folder/'visual.npz',**{**{'v_'+p:np.asarray(v) for p,(v,f) in parts.items()},**{'f_'+p:np.asarray(f,dtype=np.int32) for p,(v,f) in parts.items()}})
 (folder/'proxies.json').write_text(json.dumps({p:[np.asarray(v).tolist() for v in hs] for p,hs in proxies.items()},allow_nan=False))
 (folder/'rig.json').write_text(json.dumps(rig,allow_nan=False))
