"""Publish only derived calibration data and reviewed generator source."""
import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'study-v6'))
from proxy_execution import save, sha
from proxy_task import CASES


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('episode', type=Path)
    parser.add_argument('--scoring-check', type=Path, required=True)
    parser.add_argument('--screen', type=Path, required=True)
    parser.add_argument('--model-engine', type=Path, required=True)
    args = parser.parse_args()
    episode = args.episode
    invocation = json.loads((episode / 'invocation.json').read_text())
    assert invocation['status'] == 'completed'
    integrity = json.loads((episode / 'integrity.json').read_text())
    for relative, digest in integrity.items():
        assert sha(episode / relative) == digest, relative
    transfer = json.loads((episode / 'transfer-results.json').read_text())
    check = json.loads((args.scoring_check / 'record.json').read_text())
    assert check['rows'] and all(r['identical'] for r in check['rows'])
    public = ROOT / 'study-v6'
    generator_dir = public / 'generators'
    generator_dir.mkdir(exist_ok=True)
    for file in sorted((episode / 'frozen-candidates').glob('*.py')):
        if (generator_dir / file.name).exists():
            assert sha(generator_dir / file.name) == sha(file)
        shutil.copyfile(file, generator_dir / file.name)
    record = dict(
        kind='Short bounded convex-proxy method calibration; not an official task reward',
        experiment_source_commit='0009fd0169eaf5cffca74176204f3d3f60c7eda9',
        model={k: invocation[k] for k in ['model', 'reasoning_effort', 'tools', 'seconds',
                                         'max_dev_submissions', 'automatic_retries', 'status',
                                         'returncode', 'wall_seconds', 'dev_submissions',
                                         'completed_item_counts', 'codex_cli', 'usage']},
        native_session=dict(original_preserved_local=True, publicly_uploaded=False,
                            sha256=invocation['native_session']['sha256']),
        image=json.loads((episode / 'image.json').read_text()),
        cases=CASES,
        metric='Unweighted mean of contact recall * free-space specificity, subject to hull/vertex budgets',
        development=json.loads((episode / 'dev-ledger.json').read_text()),
        transfer=transfer,
        retention=json.loads((episode / 'retention.json').read_text()),
        scoring_portability=check,
        actual_model_engine=json.loads((args.model_engine / 'result.json').read_text()),
        episode_inventory_sha256=sha(episode / 'integrity.json'),
        original_local_file_count=len(integrity),
        frozen_source_and_input_hashes=json.loads((episode / 'frozen-source-and-inputs.json').read_text()),
        output_hashes={str(p.relative_to(episode)): sha(p) for p in episode.rglob('output.json')},
    )
    if all(r['summary']['scorable'] for r in transfer.values()) and 'first' in transfer:
        record['transfer_mean_delta'] = transfer['final']['summary']['mean_score'] - transfer['first']['summary']['mean_score']
    save(public / 'recorded.json', record)
    feasibility = dict(
        kind='Separate developer feasibility measurements; not the actual model baseline',
        screen_note='Confirmation run of the same pre-model screen after adding a nonfinite-result guard; original pre-model screen remains local in runs/v6-screen-001',
        screen=json.loads((args.screen / 'record.json').read_text()),
        mac_witness=json.loads((ROOT / 'runs/v6-witness-001/record.json').read_text()),
        linux_witness=json.loads((ROOT / 'runs/v6-linux-ci-42474793869/convex-v6-witness-ci/record.json').read_text()),
        mac_engine=json.loads((ROOT / 'runs/v6-engine-001/result.json').read_text()),
        linux_engine=json.loads((ROOT / 'runs/v6-linux-ci-42474793869/convex-v6-engine-ci/result.json').read_text()),
        library_controls=json.loads((ROOT / 'runs/v6-proxy-controls-001/library-results.json').read_text()),
    )
    save(public / 'feasibility.json', feasibility)
    print('Derived records and frozen programs copied. No native conversation, meshes or hull coordinates published.')


if __name__ == '__main__':
    main()
