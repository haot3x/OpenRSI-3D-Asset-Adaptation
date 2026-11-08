"""Deterministic, capacity-preserving adaptation of an articulated storage prop.

All dimensions and attachment locations come from the delivered mesh and rig.
Motion envelopes are expressed as linear constraints on the chassis scales;
rigid assemblies retain their original geometry throughout those motions.
"""
import copy
import json
import math
import sys

import fcl
import numpy as np
from scipy.optimize import minimize, linprog

from asset_task import load_source, write_output, Actor, frames, joint_transform


def collides(a, b):
    return bool(fcl.collide(a, b, fcl.CollisionRequest(), fcl.CollisionResult()))


def seating_offsets(source, actor):
    """Repair shallow closed-rest intersections in unscaled source coordinates.

    A shared invertible diagonal map preserves intersections between the body
    and drawers.  Consequently this correction remains valid at every scale.
    """
    meta = source['meta']
    root = meta['root_id']
    result = {}
    for p in meta['part_ids']:
        if meta['roles'][p] != 'drawer':
            continue
        obj = actor.objects[p]
        body = actor.objects[root]
        def hit(y):
            obj.setTransform(fcl.Transform(np.array([0., y, 0.])))
            return collides(obj, body)
        shift = 0.
        limit = min(.025 / .700000001, .06 * np.ptp(source['vertices'][p][:, 1]))
        samples = np.linspace(0., limit, 81)
        overlaps = [hit(float(y)) for y in samples]
        if any(overlaps):
            last = max(i for i, overlap in enumerate(overlaps) if overlap)
            if last == len(samples) - 1:
                shift = limit
            else:
                lo, hi = float(samples[last]), float(samples[last + 1])
                for _ in range(15):
                    middle = (lo + hi) / 2
                    if hit(middle):
                        lo = middle
                    else:
                        hi = middle
                shift = min(limit, hi + .000025)
        result[p] = shift
        obj.setTransform(fcl.Transform())
    return result


def attachment_points(source):
    joints = {j['child']: j for j in source['rig']['joints']}
    roles = source['meta']['roles']
    points = {}
    for p, j in joints.items():
        attach = joints[j['parent']] if roles[p] == 'wheel' else j
        points[p] = np.asarray(attach['pivot'], dtype=float)
    return points


def adapted(source, scales, seats, stroke=1.):
    anchor = np.asarray(source['meta']['anchor'], dtype=float)
    roles = source['meta']['roles']
    attach = attachment_points(source)
    vertices = {}
    for p, v in source['vertices'].items():
        if roles[p] in ('body', 'drawer'):
            vertices[p] = anchor + (v - anchor) * scales
            if roles[p] == 'drawer':
                vertices[p][:, 1] += seats.get(p, 0.) * scales[1]
        else:
            vertices[p] = v + (attach[p] - anchor) * (scales - 1.)
    rig = copy.deepcopy(source['rig'])
    for j in rig['joints']:
        p = j['child']
        old = np.asarray(j['pivot'], dtype=float)
        if roles[p] == 'wheel':
            pivot = old + (attach[p] - anchor) * (scales - 1.)
        else:
            pivot = anchor + (old - anchor) * scales
        if roles[p] == 'drawer':
            pivot[1] += seats.get(p, 0.) * scales[1]
            j['lower'] = 0.
            j['upper'] *= float(scales[1]) * stroke
        j['pivot'] = pivot.tolist()
    return dict(meta=source['meta'], vertices=vertices,
                faces=source['faces'], rig=rig)


def motion_constraints(source, scene, seats, stroke=1.):
    """Accumulate exact sampled motion supports and their affine derivatives.

    Joint rotations do not depend on scale. Joint translations and pivots do,
    linearly. Propagating their three derivatives through the actual tree
    handles arbitrary part IDs, part counts, and nested caster/wheel chains.
    Duplicate inequalities are reduced to the strongest bound.
    """
    base = adapted(source, np.ones(3), seats, stroke)
    actor = Actor(base)
    meta = source['meta']
    roles = meta['roles']
    anchor = np.asarray(meta['anchor'], dtype=float)
    attach = attachment_points(source)
    joints = actor.joints
    order = []
    known = {actor.root}
    while len(order) < len(joints):
        ready = [p for p, j in joints.items() if p not in known and j['parent'] in known]
        if not ready:
            raise ValueError('Joint graph is not a tree')
        order.extend(ready)
        known.update(ready)
    pivot_derivative = {}
    for p in order:
        pivot_derivative[p] = np.diag(
            (attach[p] if roles[p] == 'wheel' else np.asarray(joints[p]['pivot'])) - anchor)
    mesh_derivative = {p: np.diag(a - anchor) for p, a in attach.items()}
    constraints = {}
    cache = {}
    local_cache = {}
    eye = np.eye(3)
    zero = np.zeros((3, 3))
    ones = np.ones(3)
    corners = {}
    for p in actor.ids:
        if roles[p] in ('body', 'drawer'):
            lo, hi = actor.points[p].min(0), actor.points[p].max(0)
            corners[p] = np.array([[x, y, z] for x in [lo[0], hi[0]]
                                  for y in [lo[1], hi[1]] for z in [lo[2], hi[2]]])
    def add(row, bound, wall=True):
        # Separate physical support constraints from the adjustable wall margin.
        row = np.asarray(row, dtype=float)
        key = (tuple(np.round(row, 11)), wall)
        if key not in constraints or bound < constraints[key][1]:
            constraints[key] = (row.copy(), float(bound), wall)
    support = [p for p in actor.ids if roles[p] == 'wheel'] or [actor.root]
    for frame in frames(base):
        world = {actor.root: (eye, np.zeros(3), zero)}
        for p in order:
            j = joints[p]
            q = frame['q'].get(p, 0.)
            key = (p, q)
            if key not in local_cache:
                t = joint_transform(j, q)
                if j['type'] == 'prismatic':
                    d = np.zeros((3, 3))
                    if roles[p] == 'drawer':
                        d[:, 1] = np.asarray(j['axis']) * q
                else:
                    d = (eye - t[:3, :3]) @ pivot_derivative[p]
                local_cache[key] = (t[:3, :3], t[:3, 3], d)
            rj, tj, dj = local_cache[key]
            rp, tp, dp = world[j['parent']]
            world[p] = (rp @ rj, tp + rp @ tj, dp + rp @ dj)
        wall_lo, wall_hi = np.asarray(scene['bounds'][frame['phase']])
        for p in actor.ids:
            r, t, d = world[p]
            state = (frame['phase'], r.tobytes(), t.tobytes(), d.tobytes())
            if cache.get((p, 'state')) == state:
                continue
            cache[p, 'state'] = state
            if roles[p] in ('body', 'drawer'):
                const = r @ anchor + t - d @ ones
                # Eight corners are exact for the declared unrotated chassis
                # and prismatic drawers, conservative for rotated descendants.
                coefficients = r[None, :, :] * (corners[p] - anchor)[:, None, :] + d
                for k in range(3):
                    for row in coefficients[:, k, :]:
                        add(row, wall_hi[k] - .008 - const[k])
                        if k != 2:
                            add(-row, -wall_lo[k] - .008 + const[k])
                if p in support:
                    # Root is stationary and scaling is positive.
                    row = np.array([0., 0., actor.points[p][:, 2].min() - anchor[2]])
                    add(-row, anchor[2] + .0025, False)
                    add(row, .003 - anchor[2], False)
            else:
                bounds_key = (r.tobytes(), t.tobytes())
                if cache.get((p, 'bounds_key')) != bounds_key:
                    points = actor.bound_points[p] @ r.T + t
                    cache[p, 'bounds'] = (points.min(0), points.max(0))
                    cache[p, 'bounds_key'] = bounds_key
                lo, hi = cache[p, 'bounds']
                coefficient = r @ mesh_derivative[p] + d
                constant_lo = lo - coefficient @ ones
                constant_hi = hi - coefficient @ ones
                for k in range(3):
                    add(coefficient[k], wall_hi[k] - .008 - constant_hi[k])
                    if k != 2:
                        add(-coefficient[k], -wall_lo[k] - .008 + constant_lo[k])
                if p in support:
                    add(-coefficient[2], constant_lo[2] + .00249, False)
                    add(coefficient[2], .00299 - constant_lo[2], False)
    for p, seat in seats.items():
        if seat:
            add([0., seat, 0.], .024999, False)
    rows = list(constraints.values())
    return np.array([v[0] for v in rows]), np.array([v[1] for v in rows]), np.array([v[2] for v in rows])


def choose_scales(a, b, wall, target=None, extra=None):
    bounds = [(.700000001, 1.149999999), (.700000001, 1.749999999),
              (.700000001, 1.149999999)]
    if extra:
        bounds = [(max(lo, extra[i][0]), min(hi, extra[i][1]))
                  for i, (lo, hi) in enumerate(bounds)]
    target = np.ones(3) if target is None else np.asarray(target)
    best = None
    # Prefer a small reserve; retain tight feasible solutions when necessary.
    for margin in [.00025, .000025, .0000002, 0.]:
        rhs = b - wall * margin
        lp = linprog(np.zeros(3), A_ub=a, b_ub=rhs, bounds=bounds, method='highs')
        if not lp.success:
            continue
        cons = [dict(type='ineq', fun=lambda s: rhs - a @ s,
                     jac=lambda s: -a),
                dict(type='ineq', fun=lambda s: np.log(s).sum() - math.log(.950002),
                     jac=lambda s: 1. / s)]
        def objective(s):
            return np.sum((np.log(s) - np.log(target)) ** 2)
        def jac(s):
            return 2. * (np.log(s) - np.log(target)) / s
        r = minimize(objective, lp.x, jac=jac, bounds=bounds,
                     constraints=cons, method='SLSQP',
                     options=dict(maxiter=150, ftol=1e-12))
        valid = np.min(rhs - a @ r.x) >= -2e-8 and np.prod(r.x) >= .9500005
        if valid:
            return r.x
        if best is None or np.prod(r.x) > np.prod(best):
            best = r.x
    if best is not None:
        return best
    return None


def feasible(scales, a, b):
    return (scales is not None and np.prod(scales) >= .9500005
            and np.min(b - a @ scales) >= -2e-8)


def self_collision(candidate):
    """Check the prescribed motion samples, using exact triangle collisions.

    Workspace and support inequalities are already accounted for by the
    optimizer. Here we only need the nonadjacent part pairs in the SDK.
    """
    actor = Actor(candidate)
    cached = {}
    for frame in frames(candidate):
        transforms = actor.transforms(frame['q'])
        rot = transforms[:, :3, :3]
        tr = transforms[:, :3, 3]
        centers = np.einsum('nij,nj->ni', rot, actor.centers) + tr
        half = np.einsum('nij,nj->ni', abs(rot), actor.halves)
        lo, hi = centers - half, centers + half
        changed = set()
        for i, j in actor.pairs:
            if np.any(lo[i] > hi[j]) or np.any(lo[j] > hi[i]):
                continue
            key = (transforms[i].tobytes(), transforms[j].tobytes())
            if cached.get((i, j)) == key:
                continue
            for k in (i, j):
                if k not in changed:
                    actor.objects[actor.ids[k]].setTransform(fcl.Transform(rot[k], tr[k]))
                    changed.add(k)
            if collides(actor.objects[actor.ids[i]], actor.objects[actor.ids[j]]):
                return dict(parts=(actor.ids[i], actor.ids[j]), phase=frame['phase'], q=frame['q'])
            cached[i, j] = key
    return None


def main():
    job = json.load(open(sys.argv[1]))
    source = load_source(job['asset_dir'])
    source_actor = Actor(source)
    seats = seating_offsets(source, source_actor)
    a, b, wall = motion_constraints(source, job['scene'], seats)
    scales = choose_scales(a, b, wall)
    stroke = 1.
    if not feasible(scales, a, b):
        # The permitted stroke band is useful for a genuinely tight front
        # workspace. Keep full nominal travel whenever it is feasible.
        stroke = .95001
        a, b, wall = motion_constraints(source, job['scene'], seats, stroke)
        scales = choose_scales(a, b, wall)
    if scales is None:
        scales = np.ones(3)
    result = adapted(source, scales, seats, stroke)
    if feasible(scales, a, b) and self_collision(result) is not None:
        # The scale-feasible set is convex in log-capacity. Explore distinct
        # feasible proportions, retaining exact motion and collision checks.
        # These targets express geometric preferences, never scene identities.
        targets = [(1.15, .70, 1.15), (.70, 1.75, 1.15),
                   (1.15, 1.75, .70), (.70, 1.75, .70)]
        tested = [scales]
        for target in targets:
            trial = choose_scales(a, b, wall, target)
            if not feasible(trial, a, b) or any(np.max(abs(trial - v)) < 1e-6 for v in tested):
                continue
            tested.append(trial)
            candidate = adapted(source, trial, seats, stroke)
            if self_collision(candidate) is None:
                result = candidate
                break
    write_output(sys.argv[2], result['vertices'], result['faces'], result['rig'])


if __name__ == '__main__':
    main()
