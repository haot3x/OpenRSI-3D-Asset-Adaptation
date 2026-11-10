"""Verify hashes and rescore frozen v7 geometry without executing candidate code.

The record supplies repository-relative source/probe/artifact paths, cases and
their expected evaluations. Use the exact frozen source and cached probes for
cross-platform replay; do not regenerate the witness during this comparison.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'study-v7'))
from evaluator import evaluate


def local(relative):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError('Record path escapes repository')
    return path


def compare(actual, expected, path='evaluation'):
    # Wall clock is diagnostic only; identities, flags, counts and discrete
    # outcomes are exact. Geometric floats allow tiny native-library drift.
    if isinstance(expected, dict):
        assert isinstance(actual, dict) and actual.keys() == expected.keys(), path
        for key, value in expected.items():
            if key != 'wall_seconds':
                compare(actual[key], value, path + '.' + key)
    elif isinstance(expected, list):
        assert isinstance(actual, list) and len(actual) == len(expected), path
        for index, (a, e) in enumerate(zip(actual, expected)):
            compare(a, e, path + '[' + str(index) + ']')
    elif isinstance(expected, float):
        assert math.isfinite(actual) and math.isclose(actual, expected, rel_tol=1e-7, abs_tol=1e-9), (path, actual, expected)
    else:
        assert actual == expected, (path, actual, expected)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('record', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    record = json.loads(args.record.read_text())
    args.out.mkdir(parents=True, exist_ok=False)
    for relative, digest in record['hashes'].items():
        assert hashlib.sha256(local(relative).read_bytes()).hexdigest() == digest, relative
    results = []
    for row in record['evaluations']:
        result = evaluate(local(row['source']), local(row['artifact']), row['case'], local(row['probes']))
        compare(result, row['expected'])
        results.append(dict(id=row['id'], evaluation=result))
        print('V7_REPLAY_PASS', row['id'], result['score'], flush=True)
    (args.out / 'replayed.json').write_text(json.dumps(dict(passed=True, evaluations=results), indent=2) + '\n')
    print('ALL_V7_FROZEN_OUTPUTS_REPRODUCED', len(results), flush=True)


if __name__ == '__main__':
    main()
