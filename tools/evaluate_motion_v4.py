"""Evaluate one JSON behavior adapter on immutable public development scenes."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'study-v4'))
from motion import Actor,evaluate,validate


def main():
    p=argparse.ArgumentParser();p.add_argument('candidate',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--frames',action='store_true');args=p.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    try:
        if args.candidate.stat().st_size>256*1024:raise ValueError('Candidate exceeds 256 KiB')
        candidate=json.loads(args.candidate.read_text());validate(candidate)
    except (ValueError,KeyError,TypeError) as error:result=dict(status='candidate_invalid',scored=False,error=str(error))
    else:
        actor=Actor()
        try:
            evaluation=evaluate(candidate,actor,include_frames=args.frames)
            if args.frames:
                for scene in evaluation['scenes']:(out/(scene['scene']+'.frames.json')).write_text(json.dumps(scene.pop('frames'))+'\n')
            result=dict(status='evaluated',scored=True,evaluation=evaluation)
        except ValueError as error:result=dict(status='candidate_sampling_cap_or_invalid',scored=False,error=str(error))
    (out/'evaluation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
