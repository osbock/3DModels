"""Build a micro dragon with any number of middle segments.

    ../millipod/python/.venv/bin/python compose_dragon.py 8              # straight -> dragon_8.stl
    ../millipod/python/.venv/bin/python compose_dragon.py 30 --spiral    # coiled   -> dragon_30_spiral.stl
    ../millipod/python/.venv/bin/python compose_dragon.py 12 -o long.stl

Uses parts/head.stl, parts/middle.stl, parts/tail.stl and parts/joints.json
(all produced by split_dragon.py). The result is a single print-in-place STL.

--spiral coils the dragon into an Archimedean spiral, tail at the centre, so
long dragons fit on the bed. Every joint is turned about its own pivot (the
vertical axis of the D-ring, or the head pin), the same way the printed joint
articulates, so the links stay exactly as they mate in the straight layout.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import trimesh

PARTS = Path(__file__).parent / "parts"


def load():
    j = json.load(open(PARTS / "joints.json"))
    parts = {k: trimesh.load(PARTS / f"{k}.stl") for k in ("head", "middle", "tail")}
    return j, parts


def straight_pieces(n, j, parts):
    """Parts in the shared straight frame (spine along +X), head first."""
    pitch = np.array(j["pitch"])
    pieces = [parts["head"].copy()]
    for k in range(n):
        s = parts["middle"].copy(); s.apply_translation(k * pitch); pieces.append(s)
    t = parts["tail"].copy(); t.apply_translation((n - 1) * pitch); pieces.append(t)
    # joint pivots (x, y) between consecutive pieces, in the same frame
    piv = [np.array(j["head_pin"])]
    piv += [np.array(j["segment_ring"]) + (k + 1) * pitch[:2] for k in range(n - 1)]
    piv += [np.array(j["tail_ring"]) + (n - 1) * pitch[:2]]
    return pieces, piv


def compose(n):
    j, parts = load()
    return trimesh.util.concatenate(straight_pieces(n, j, parts)[0])


def spiral_points(count, step, r0, arm_gap):
    """`count` points on r = r0 + arm_gap*phi/2pi, consecutive chord = step,
    starting at the inside."""
    b = arm_gap / (2 * np.pi)
    pts, phi = [], 0.0
    xy = lambda p: (r0 + b * p) * np.array([np.cos(p), np.sin(p)])
    pts.append(xy(phi))
    for _ in range(count - 1):
        lo, hi = phi, phi + 2 * np.pi
        for _ in range(60):  # bisect for chord length == step
            mid = (lo + hi) / 2
            if np.linalg.norm(xy(mid) - pts[-1]) < step: lo = mid
            else: hi = mid
        phi = (lo + hi) / 2
        pts.append(xy(phi))
    return np.array(pts)


def rz(theta, c):
    return trimesh.transformations.rotation_matrix(theta, [0, 0, 1], [c[0], c[1], 0])


def compose_spiral(n, arm_gap=None, max_bend=None):
    j, parts = load()
    pieces, piv = straight_pieces(n, j, parts)
    pitch = float(np.linalg.norm(j["pitch"][:2]))
    arm_gap = arm_gap or j["spiral"]["arm_gap"]
    max_bend = np.radians(max_bend or j["spiral"]["max_bend_deg"])
    # smallest radius whose chord-to-chord turn stays within the joint's bend limit
    r0 = pitch / (2 * np.sin(max_bend / 2))

    # one spiral point per joint, plus one extra beyond each end for the
    # head / tail headings; generated from the centre (tail) outwards
    q = spiral_points(len(piv) + 2, pitch, r0, arm_gap)[::-1]  # head first
    heading = [np.arctan2(*(q[i + 1] - q[i])[::-1]) for i in range(len(q) - 1)]
    # the head pin joint has almost no side play (0.18 mm), so keep the head
    # in line with the first segment
    heading[0] = heading[1]
    bends = [np.angle(np.exp(1j * (heading[i + 1] - heading[i]))) for i in range(len(heading) - 1)]

    # chain: W_head puts the head pin on q[1] with the head facing heading[0];
    # each later piece = previous transform * rotation about the joint pivot
    W = rz(heading[0], [0, 0]); W[:2, 3] += q[1] - (W[:2, :2] @ piv[0])
    out = []
    for i, p in enumerate(pieces):
        if i > 0:
            W = W @ rz(bends[i - 1], piv[i - 1])
        m = p.copy(); m.apply_transform(W); out.append(m)
    lo = np.min([m.bounds[0] for m in out], axis=0)
    for m in out:
        m.apply_translation([-lo[0], -lo[1], 0])
    d = trimesh.util.concatenate(out)
    return d, out, np.degrees(np.abs(bends)).max()


def check_collisions(pieces):
    """Overlap volume for every pair of pieces whose bounding boxes touch."""
    import manifold3d as mf
    ms = [mf.Manifold(mf.Mesh(vert_properties=np.asarray(p.vertices, np.float32),
                              tri_verts=np.asarray(p.faces, np.uint32))) for p in pieces]
    bad = []
    for a in range(len(pieces)):
        for b in range(a + 1, len(pieces)):
            ba, bb = pieces[a].bounds, pieces[b].bounds
            if np.any(ba[1] < bb[0]) or np.any(bb[1] < ba[0]):
                continue
            v = (ms[a] ^ ms[b]).volume()
            if v > 1e-6:
                bad.append((a, b, v))
    return bad


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("segments", type=int, help="number of middle segments (>=1)")
    ap.add_argument("-o", "--out")
    ap.add_argument("--spiral", action="store_true", help="coil into a flat spiral")
    ap.add_argument("--arm-gap", type=float, help="spiral: centre-to-centre distance between turns, mm")
    ap.add_argument("--max-bend", type=float, help="spiral: max bend per joint, degrees")
    ap.add_argument("--no-check", action="store_true", help="skip the collision check")
    a = ap.parse_args()
    if a.segments < 1:
        ap.error("need at least 1 middle segment")
    if a.spiral:
        d, pieces, bend = compose_spiral(a.segments, a.arm_gap, a.max_bend)
        out = a.out or f"dragon_{a.segments}_spiral.stl"
        extra = f", max joint bend {bend:.1f} deg"
    else:
        j, parts = load()
        pieces = straight_pieces(a.segments, j, parts)[0]
        d = trimesh.util.concatenate(pieces)
        out = a.out or f"dragon_{a.segments}.stl"
        extra = ""
    if not a.no_check:
        bad = check_collisions(pieces)
        names = ["head"] + [f"seg{k}" for k in range(a.segments)] + ["tail"]
        for x, y, v in bad:
            print(f"  WARNING: {names[x]} overlaps {names[y]} by {v:.3f} mm^3")
        if bad and a.spiral:
            print("  -> try a larger --arm-gap or a smaller --max-bend")
    d.export(out)
    print(f"{out}: {a.segments} segments, footprint {d.extents[0]:.1f} x {d.extents[1]:.1f} mm{extra}")
