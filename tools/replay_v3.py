"""Recompute recorded mechanism diagnostics without a model call."""
import argparse
import json
import math
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'study-v3'))
from core import load_asset,score,validate_prediction
from run import controls

def same_report(actual,expected,key=''):
    if isinstance(expected,dict):
        return isinstance(actual,dict) and actual.keys()==expected.keys() and all(same_report(actual[k],v,k) for k,v in expected.items())
    if isinstance(expected,list):
        return isinstance(actual,list) and len(actual)==len(expected) and all(same_report(a,b,key) for a,b in zip(actual,expected))
    # Diagnostic libm rounding differs across OS/CPU; all score/count/pass fields
    # remain exact. This does not change the evaluator or any decision threshold.
    tolerances={'axis_error_degrees':1e-6,'pivot_perpendicular_error_metres':1e-9,'pivot_tolerance_metres':1e-9}
    if key in tolerances:return math.isclose(actual,expected,rel_tol=1e-12,abs_tol=tolerances[key])
    return actual==expected


def main():
    parser=argparse.ArgumentParser();parser.add_argument('record',type=Path);args=parser.parse_args();record=json.loads(args.record.read_text())
    for row in record['cases']:
        asset=load_asset(row['asset']);controls(asset);validate_prediction(row['prediction'],asset['input']['parts'])
        actual=score(asset['reference'],row['prediction'],asset['diagonal'])
        if not same_report(actual,row['diagnostic']):raise AssertionError('Recorded diagnostic mismatch: '+row['asset']+' '+json.dumps(dict(actual=actual,expected=row['diagnostic'])))
        print(row['asset'],str(actual['correct'])+'/'+str(actual['joint_count']))
    print('All recorded diagnostics and scorer controls reproduced. No model calls made.')


if __name__=='__main__':main()
