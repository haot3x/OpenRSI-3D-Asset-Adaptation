"""Candidate-only public IO; evaluator and test queries are not delivered."""
import json
from pathlib import Path
import numpy as np


def load_job(path):
    job = json.loads(Path(path).read_text())
    with np.load(job['mesh'], allow_pickle=False) as raw:
        return job, np.array(raw['vertices']), np.array(raw['faces'])


def write_output(path, convex_vertices):
    Path(path).write_text(json.dumps({'hulls': [np.asarray(v).tolist() for v in convex_vertices]}, allow_nan=False))
