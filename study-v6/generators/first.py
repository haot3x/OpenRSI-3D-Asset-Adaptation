"""Geometry-driven compound convex collision proxies.

Weld triangle soups, preserve disconnected parts, and decompose concave parts.
All tolerances are in metres except CoACD's normalized concavity threshold.
"""
import os
os.environ.setdefault('OMP_NUM_THREADS', '2')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
import sys
import time
import multiprocessing as mp
import numpy as np
import trimesh
from scipy.spatial import ConvexHull
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from proxy_sdk import load_job, write_output


def clean_components(vertices, faces):
    mesh = trimesh.Trimesh(vertices, faces, process=True)
    mesh.update_faces(mesh.unique_faces() & mesh.nondegenerate_faces())
    mesh.remove_unreferenced_vertices()
    edges = mesh.edges
    graph = coo_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])),
                       shape=(len(mesh.vertices), len(mesh.vertices)))
    count, labels = connected_components(graph, directed=False)
    parts = []
    for label in range(count):
        ix = np.flatnonzero(labels[mesh.faces[:, 0]] == label)
        if len(ix):
            part = mesh.submesh([ix], append=True)
            if part.area > 1e-12:
                parts.append(part)
    return sorted(parts, key=lambda p: -p.area)


def limited_hull(points, limit):
    p = np.unique(np.asarray(points, dtype=float), axis=0)
    if len(p) < 4 or np.linalg.matrix_rank(p-p.mean(0), tol=1e-10) < 3:
        # Give open, planar source surfaces a small physical thickness.
        if len(p) < 3:
            return None
        _, _, basis = np.linalg.svd(p-p.mean(0), full_matrices=False)
        n = basis[-1] * 0.00015
        p = np.concatenate((p+n, p-n))
    try:
        h = ConvexHull(p)
    except Exception:
        return None
    p = p[h.vertices]
    if len(p) <= limit:
        return p
    # A support-point approximation retains corners and long contact planes.
    n = min(48, max(8, limit//2))
    k = np.arange(n)
    z = 1 - 2*(k+.5)/n
    a = k * (np.pi*(3-np.sqrt(5)))
    dirs = np.column_stack((np.sqrt(1-z*z)*np.cos(a),
                            np.sqrt(1-z*z)*np.sin(a), z))
    dirs = np.concatenate((dirs, np.eye(3), -np.eye(3)))
    selected = list(np.unique(np.argmax(p @ dirs.T, axis=0)))
    selected = selected[:limit]
    while len(selected) < limit:
        try:
            h = ConvexHull(p[selected])
        except Exception:
            selected.append(next(i for i in range(len(p)) if i not in selected))
            continue
        distance = np.max(p @ h.equations[:, :3].T + h.equations[:, 3], axis=1)
        distance[selected] = -np.inf
        j = int(np.argmax(distance))
        if distance[j] < 0.00012:
            break
        selected.append(j)
    return p[selected]


def coacd_worker(vertices, faces, count, queue):
    try:
        import coacd
        coacd.set_log_level('error')
        result = coacd.run_coacd(
            coacd.Mesh(vertices, faces), threshold=0.012,
            max_convex_hull=count, preprocess_mode='auto',
            preprocess_resolution=60, resolution=1500,
            mcts_nodes=12, mcts_iterations=50, mcts_max_depth=3,
            merge=True, decimate=False, seed=17)
        queue.put([np.asarray(v) for v, f in result])
    except Exception:
        queue.put([])


def generate(job, vertices, faces):
    start = time.monotonic()
    deadline = start + max(1, float(job.get('generation_seconds', 45))-4)
    budget = int(job['max_hulls'])
    limit = int(job.get('max_vertices_per_hull', 128))
    parts = clean_components(vertices, faces)
    hulls = []
    concave = []
    for part in parts:
        try:
            h = ConvexHull(part.vertices)
            ratio = abs(part.volume) / max(h.volume, 1e-20)
        except Exception:
            ratio = 0
        if ratio > .998:
            hulls.append(np.asarray(part.vertices))
        else:
            concave.append(part)
    # Preserve one slot per source component before spending the extra budget.
    for i, part in enumerate(concave):
        remaining = len(concave)-i
        count = max(1, (budget-len(hulls))//remaining)
        available = deadline-time.monotonic()
        result = []
        if count > 1 and available > 1:
            ctx = mp.get_context('fork')
            queue = ctx.Queue()
            process = ctx.Process(target=coacd_worker,
                                 args=(np.asarray(part.vertices), np.asarray(part.faces), count, queue))
            process.start()
            try:
                result = queue.get(timeout=max(.1, available/remaining))
            except Exception:
                pass
            if process.is_alive():
                process.terminate()
            process.join(timeout=.2)
            queue.close()
        hulls.extend(result if result else [np.asarray(part.vertices)])
    # If input has more disconnected objects than the budget, merge the closest
    # pair by the extra convex volume introduced rather than dropping contacts.
    while len(hulls) > budget:
        centers = np.array([p.mean(0) for p in hulls])
        ds = np.sum((centers[:, None]-centers[None, :])**2, axis=2)
        np.fill_diagonal(ds, np.inf)
        i,j = np.unravel_index(np.argmin(ds), ds.shape)
        hulls[i] = np.concatenate((hulls[i], hulls[j]))
        hulls.pop(j)
    output = []
    for p in hulls:
        h = limited_hull(p, limit)
        if h is not None:
            output.append(h)
    return output


if __name__ == '__main__':
    job, vertices, faces = load_job(sys.argv[1])
    write_output(sys.argv[2], generate(job, vertices, faces))
