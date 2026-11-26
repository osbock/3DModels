"""Split micro-dragon_fixed.stl into head / middle segment / tail and work out
the offsets that let them be recombined into a dragon of any length.

The source STL holds 5 print-in-place bodies (head, 4 segments, tail -- two of
the middle segments are fused into one body). The segments are near-identical
but hand-placed, so the spacing and joint clearances vary. This script:

  1. rotates the model so the spine runs along +X (head at the low-X end),
  2. takes one clean segment as the canonical middle,
  3. for each joint (head->seg, seg->seg, seg->tail) searches for the offset
     that maximises the minimum gap between the two parts, i.e. centres each
     D-ring around the link / pin it hooks onto,
  4. writes head.stl, middle.stl, tail.stl in one shared frame plus
     joints.json with the offsets used by compose_dragon.py.

Run with the millipod venv (trimesh, manifold3d, scipy):
    ../millipod/python/.venv/bin/python split_dragon.py
"""
import json
from pathlib import Path

import manifold3d as mf
import numpy as np
import trimesh
from scipy.spatial import cKDTree
from trimesh.registration import icp

HERE = Path(__file__).parent
SRC = HERE / "micro-dragon_fixed.stl"
OUT = HERE / "parts"


def to_manifold(t):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32),
                               tri_verts=np.asarray(t.faces, np.uint32)))


def overlap(a, b):
    return (to_manifold(a) ^ to_manifold(b)).volume()


class Joint:
    """Min gap between a fixed part A and part B translated by t."""

    def __init__(self, A, B, guess, n=150_000):
        self.A, self.B = A, B
        # only sample where the two parts are close: that's the joint
        lo = np.maximum(A.bounds[0], B.bounds[0] + guess) - 2.5
        hi = np.minimum(A.bounds[1], B.bounds[1] + guess) + 2.5
        pa, _ = trimesh.sample.sample_surface(A, n, seed=1)
        pb, _ = trimesh.sample.sample_surface(B, n, seed=2)
        self.pa = pa[np.all((pa > lo) & (pa < hi), 1)]
        self.pb = pb[np.all((pb + guess > lo) & (pb + guess < hi), 1)]
        self.ta = cKDTree(self.pa)
        self.Am = to_manifold(A)

    def gap(self, t):
        d, _ = self.ta.query(self.pb + t)
        return d.min()

    def solve(self, guess, span=1.2, step=0.005):
        """1-D scan along X (parts all sit on the bed and are symmetric about
        the spine, so Y and Z offsets stay 0). Picks the X with the largest
        minimum gap, i.e. the link centred in its D-ring."""
        xs = np.arange(guess[0] - span, guess[0] + span, step)
        gaps = np.array([self.gap(np.array([x, 0, 0])) for x in xs])
        i = gaps.argmax()
        t = np.array([xs[i], 0.0, 0.0])
        B = self.B.copy(); B.apply_translation(t)
        ov = (self.Am ^ to_manifold(B)).volume()
        # free travel: range of X where the gap stays above 0.05 mm
        ok = xs[gaps > 0.05]
        self.travel = (ok.min() - t[0], ok.max() - t[0]) if len(ok) else (0, 0)
        return t, gaps[i], ov


def main():
    m = trimesh.load(SRC)
    m.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 4, [0, 0, 1]))
    H, G, B, O, T = sorted(m.split(only_watertight=False), key=lambda p: p.bounds[0][0])

    # common frame: head's min corner x at 0, spine on y=0, sitting on z=0
    shift = -np.array([H.bounds[0][0], O.centroid[1], 0.0])
    for p in (H, G, B, O, T):
        p.apply_translation(shift)

    mid = O  # canonical segment (volume matches each half of the fused pair)
    mid_ref = mid.copy()

    # where does `mid` sit when it replaces the first segment (G)?
    init = np.eye(4); init[:3, 3] = G.bounds[0] - mid.bounds[0]
    Mg, _, _ = icp(mid.vertices, G, initial=init, max_iterations=80)
    g0 = Mg[:3, 3]
    # and one pitch back, inside the fused pair B (seg->seg spacing guess)
    init = np.eye(4); init[:3, 3] = [-8.3, 0, 0]
    Mb, _, _ = icp(mid.vertices, B, initial=init, max_iterations=80)
    p0 = -Mb[:3, 3]  # next segment = previous + pitch

    res = {}
    # head -> first segment: head fixed, segment moves
    t, g, ov = (J:=Joint(H, mid, g0)).solve(g0)
    res["first_segment"] = t; print(flush=True, *[f"head->seg   offset {np.round(t,3)} min gap {g:.3f} overlap {ov:.4f} travel {np.round(J.travel,2)}"])
    # seg -> seg pitch: segment fixed at 0, next one moves
    t, g, ov = (J:=Joint(mid, mid, p0)).solve(p0)
    res["pitch"] = t; print(flush=True, *[f"seg->seg    pitch  {np.round(t,3)} min gap {g:.3f} overlap {ov:.4f} travel {np.round(J.travel,2)}"])
    # seg -> tail: segment fixed at 0, tail moves (tail stays in its own coords)
    t0 = np.zeros(3)  # in original layout tail mates with O directly
    t, g, ov = (J:=Joint(mid, T, t0)).solve(t0)
    res["tail_after_segment"] = t; print(flush=True, *[f"seg->tail   offset {np.round(t,3)} min gap {g:.3f} overlap {ov:.4f} travel {np.round(J.travel,2)}"])

    OUT.mkdir(exist_ok=True)
    # Shared frame: head as-is, middle at slot 1, tail after slot 1.
    first = res["first_segment"]
    H.export(OUT / "head.stl")
    m1 = mid_ref.copy(); m1.apply_translation(first); m1.export(OUT / "middle.stl")
    tl = T.copy(); tl.apply_translation(first + res["tail_after_segment"]); tl.export(OUT / "tail.stl")
    json.dump({
        "note": "head.stl, middle.stl, tail.stl are in one frame forming a 1-segment dragon. "
                "For N segments: middle copy k (k=0..N-1) is translated by k*pitch; "
                "tail is translated by (N-1)*pitch.",
        "pitch": np.round(res["pitch"], 4).tolist(),
        # joint pivots (x, y) in the shared frame, used by compose_dragon.py --spiral:
        # centre of the head pin, of the first segment's ring, of the tail's ring
        # (measured from z=1.5..3 mm sections of the exported parts)
        "head_pin": [15.28, 0.0],
        "segment_ring": [15.57, 0.17],
        "tail_ring": [23.39, 0.0],
        "spiral": {
            "max_bend_deg": 10.0,
            "arm_gap": 26.0,
            "note": "max bend per joint and spacing between spiral turns. seg-seg joint keeps "
                    "0.37mm gap to +-8deg, ~0.25 at 10, touches by 16; tail similar. Head joint "
                    "has ~0 side play so the head stays straight. arm_gap 26 leaves >=0.4mm "
                    "between turns (24 overlapped spike tips).",
        },
    }, open(OUT / "joints.json", "w"), indent=2)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
