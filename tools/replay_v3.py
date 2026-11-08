"""Recompute recorded mechanism diagnostics without a model call."""
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'study-v3'))
from core import load_asset,score,validate_prediction
from run import controls

parser=argparse.ArgumentParser()
parser.add_argument('record',type=Path)
args=parser.parse_args()
record=json.loads(args.record.read_text())
for row in record['cases']:
    asset=load_asset(row['asset']);controls(asset)
    validate_prediction(row['prediction'],asset['input']['parts'])
    actual=score(asset['reference'],row['prediction'],asset['diagonal'])
    if actual!=row['diagnostic']:raise AssertionError('Recorded diagnostic mismatch: '+row['asset'])
    print(row['asset'],str(actual['correct'])+'/'+str(actual['joint_count']))
print('All recorded diagnostics and scorer controls reproduced. No model calls made.')
