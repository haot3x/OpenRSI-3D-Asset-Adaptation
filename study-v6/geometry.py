"""Fixed public CPU measurements for a pre-model LOD/proxy feasibility screen."""
import hashlib
import math

import numpy as np
import trimesh
from scipy.spatial import ConvexHull, QhullError

SPHERE_RADIUS = .002
AMBIGUITY = .001


def clean(vertices, faces):
    mesh = trimesh.Trimesh(vertices, faces, process=True)
    # Repair triangle-soup indexing without moving coordinates. The 10-micron
    # weld identifies seams; all fidelity/probes still reference original input.
    mesh.merge_vertices(digits_vertex=5)
    mesh.update_faces(mesh.unique_faces())
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.remove_unreferenced_vertices()
    return mesh


def distances(mesh, points):
    points = np.asarray(points)
    if not len(points):
        return np.empty(0)
    result = np.concatenate([
        trimesh.proximity.closest_point(mesh, points[i:i + 256])[1]
        for i in range(0, len(points), 256)
    ])
    if not np.isfinite(result).all():
        raise ValueError('Nonfinite proximity result; do not silently discard reference queries')
    return result


def samples(mesh, seed, count=1024):
    rng = np.random.default_rng(seed)
    indices = rng.choice(len(mesh.faces), size=count, p=mesh.area_faces / mesh.area)
    uv = rng.random((count, 2))
    uv[uv.sum(axis=1) > 1] = 1 - uv[uv.sum(axis=1) > 1]
    tri = mesh.triangles[indices]
    points = tri[:, 0] + uv[:, 0, None] * (tri[:, 1] - tri[:, 0]) + uv[:, 1, None] * (tri[:, 2] - tri[:, 0])
    return np.vstack([np.unique(mesh.vertices, axis=0), points])


def surface_report(reference, candidate, seed):
    forward = distances(candidate, samples(reference, seed))
    reverse = distances(reference, samples(candidate, seed + 1))
    all_d = np.r_[forward, reverse]
    maximum = float(all_d.max())
    return dict(
        source_triangles=len(reference.faces), triangles=len(candidate.faces),
        source_samples=len(forward), candidate_samples=len(reverse),
        sampled_max_metres=maximum,
        sampled_rms_metres=float(np.sqrt(np.mean(all_d ** 2))),
        sampled_p99_metres=float(np.quantile(all_d, .99)),
        approximate_max_pixels={
            str(d): maximum / (2 * d * math.tan(math.pi / 6) / 1080)
            for d in [2, 6, 12]
        },
    )


def probe_set(reference, grid_size=9):
    """Outside-visible sphere queries; no arbitrary thin-mesh occupancy labels."""
    lo, hi = reference.bounds
    contact, free = [], []
    for axis in range(3):
        others = [k for k in range(3) if k != axis]
        grids = np.meshgrid(*[
            np.linspace(lo[k] + (hi[k] - lo[k]) * .025,
                        hi[k] - (hi[k] - lo[k]) * .025, grid_size)
            for k in others
        ])
        for sign in [-1., 1.]:
            origins = np.zeros((grid_size ** 2, 3))
            for k, values in zip(others, grids):
                origins[:, k] = values.ravel()
            origins[:, axis] = lo[axis] - .01 if sign > 0 else hi[axis] + .01
            directions = np.zeros_like(origins)
            directions[:, axis] = sign
            hit, ray_ids, _ = reference.ray.intersects_location(origins, directions, multiple_hits=False)
            end_distance = np.full(len(origins), hi[axis] - lo[axis] + .02)
            for point, index in zip(hit, ray_ids):
                end_distance[index] = float(np.dot(point - origins[index], directions[index]))
                contact.append(point - directions[index] * SPHERE_RADIUS * .5)
                free.append(point - directions[index] * (SPHERE_RADIUS + 2 * AMBIGUITY))
            for fraction in [.25, .5, .75]:
                free.extend(origins + directions * (end_distance * fraction)[:, None])
    contact = np.unique(np.round(contact, 10), axis=0).reshape(-1, 3)
    free = np.unique(np.round(free, 10), axis=0).reshape(-1, 3)
    # Corners/nearby walls can invalidate otherwise visible sphere centers.
    free = free[distances(reference, free) > SPHERE_RADIUS + AMBIGUITY]
    contact = contact[distances(reference, contact) < SPHERE_RADIUS - .25 * AMBIGUITY]
    return dict(contact=contact, free=free)


def hull_mesh(points):
    hull = ConvexHull(points)
    vertices = np.asarray(points)[hull.vertices]
    hull = ConvexHull(vertices)
    return trimesh.Trimesh(vertices, hull.simplices, process=False), hull.equations


def make_hulls(mesh, components=False):
    pieces = mesh.split(only_watertight=False, repair=False) if components else [mesh]
    result = []
    for part in pieces:
        try:
            result.append(hull_mesh(part.vertices)[0])
        except QhullError:
            # A zero-volume component has no deployable convex solid; preserve
            # that fact rather than silently substituting a fat box.
            return None
    return result


def proxy_hits(hulls, points):
    hit = np.zeros(len(points), dtype=bool)
    for mesh in hulls:
        equations = ConvexHull(mesh.vertices).equations
        inside = np.all(points @ equations[:, :3].T + equations[:, 3] <= 1e-10, axis=1)
        hit |= inside
        lo, hi = mesh.bounds
        gap = np.maximum(np.maximum(lo - points, points - hi), 0)
        near = (~hit) & (np.linalg.norm(gap, axis=1) <= SPHERE_RADIUS)
        indices = np.flatnonzero(near)
        hit[indices] |= distances(mesh, points[indices]) <= SPHERE_RADIUS + 1e-10
    return hit


def proxy_report(hulls, probes):
    if hulls is None:
        return dict(status='non_volumetric_component', deployable=False)
    blocked_free = int(np.sum(proxy_hits(hulls, probes['free'])))
    missed_contact = int(np.sum(~proxy_hits(hulls, probes['contact'])))
    return dict(
        status='measured', hulls=len(hulls), vertices=sum(len(m.vertices) for m in hulls),
        contact_count=len(probes['contact']), free_count=len(probes['free']),
        false_free=missed_contact, false_blocked=blocked_free,
        false_free_fraction=missed_contact / max(1, len(probes['contact'])),
        false_blocked_fraction=blocked_free / max(1, len(probes['free'])),
        exact_sampled_agreement=blocked_free == missed_contact == 0,
        convex=True,
    )


def seed_for(asset, part):
    return int(hashlib.sha256((asset + '/' + part).encode()).hexdigest()[:8], 16)
