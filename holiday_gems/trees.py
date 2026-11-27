"""Faceted Christmas-tree "gems", same family as snowflakes.py.

Every part of a tree (tier, trunk, star arm, ornament) is a convex piece: a
flat outline with short vertical walls, topped by facets that rise to a sharp
ridge.  Tiers ridge up the middle of the tree; the star is five pointed arms.
Pieces are unioned with manifold3d; flat bottom at z = 0, no overhangs.

Usage (from this folder):
    ../millipod/python/.venv/bin/python trees.py             # all designs
    ../millipod/python/.venv/bin/python trees.py classic     # one design
    ../millipod/python/.venv/bin/python trees.py --size 22   # height, mm

Writes out/tree_<name>.stl, out/trees_all.stl and out/tree_<name>.png.
Designs are drawn for a 24 mm tall tree (star included) and scaled in X/Y;
heights stay the same so the facets keep their look at any size.
"""
import argparse
import math
import os

import numpy as np
import manifold3d as mf
import trimesh
from shapely.geometry import Polygon
from shapely.ops import unary_union

from snowflakes import render

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
BASE_SIZE = 24.0       # mm, height the designs are drawn at

P = dict(
    wall=0.9,          # vertical side walls, mm
    tier_hi=4.2,       # ridge height at the fattest part of a tier, mm
    tier_lo=1.8,       # ridge height at a tier's tip, mm
    trunk_h=2.2,       # trunk ridge height, mm
    star_hi=3.6,       # star centre height, mm
    star_lo=1.5,       # star tip height, mm
    bead_r=1.1,        # ornament radius, mm
    bead_rise=0.7,     # how far an ornament stands above the tree surface, mm
    min_gap=0.8,       # gaps narrower than this get flagged, mm
)


# ---- pieces: (outline [(x, y)...], ridge [(x, y, z)...]) ---------------------
def tier(y0, y1, w, droop=0.0, notch=0.0):
    """A tier from y0 (base) to y1 (tip), w wide.  droop pulls the two base
    corners down; notch lifts the base centre, so the tier reads as a bough.
    Returned as two convex halves that share the centre ridge."""
    ridge = [(0, y1, P["tier_lo"]), (0, y0 + 0.28 * (y1 - y0) + notch, P["tier_hi"])]
    halves = []
    for s in (-1, 1):
        outline = [(0, y1), (s * w / 2, y0 - droop), (0, y0 + notch)]
        halves.append((outline, ridge))
    return halves


def trunk(y0, y1, w):
    inset = min(w / 2, (y1 - y0) / 2) * 0.8
    outline = [(-w / 2, y0), (w / 2, y0), (w / 2, y1), (-w / 2, y1)]
    ridge = [(0, y0 + inset, P["trunk_h"]), (0, y1, P["trunk_h"])]
    return [(outline, ridge)]


def star(cx, cy, r_out, r_in_frac=0.5, spin=90.0):
    """Five-point star.  Put the tree's tip ~0.6 mm above cy so the lower arms
    meet the tree without a narrow V between them."""
    c = np.array([cx, cy])
    r_in = r_out * r_in_frac
    pieces = []
    for k in range(5):
        a = math.radians(spin + 72 * k)
        tip = c + r_out * np.array([math.cos(a), math.sin(a)])
        l = c + r_in * np.array([math.cos(a + math.radians(36)), math.sin(a + math.radians(36))])
        r = c + r_in * np.array([math.cos(a - math.radians(36)), math.sin(a - math.radians(36))])
        outline = [tuple(c), tuple(l), tuple(tip), tuple(r)]
        ridge = [(cx, cy, P["star_hi"]), (*tip, P["star_lo"])]
        pieces.append((outline, ridge))
    return pieces


# ---- designs (drawn 24 mm tall, centred on x = 0, base at y = 0) ------------
def classic():
    """Three tiers, a trunk and a star."""
    return (trunk(0, 3.2, 3.6)
            + tier(2.4, 10.5, 17.0, droop=0.6)
            + tier(7.6, 15.0, 13.0, droop=0.6)
            + tier(12.4, 20.2, 9.0, droop=0.6)
            + star(0, 19.6, 4.0)), []


def simple():
    """One tall faceted triangle on a trunk: the sturdiest."""
    return trunk(0, 3.4, 4.0) + tier(2.6, 20.6, 16.0) + star(0, 20.0, 4.0), []


def bough():
    """Tiers with drooping corners and a notch in the middle, like pine boughs."""
    return (trunk(0, 4.6, 3.6)          # reaches up into the bottom notch
            + tier(3.0, 10.8, 18.0, droop=1.8, notch=1.2)
            + tier(8.0, 15.2, 14.0, droop=1.6, notch=1.0)
            + tier(12.6, 20.2, 9.6, droop=1.3, notch=0.8)
            + star(0, 19.6, 4.0)), []


def ornaments():
    """The classic tree hung with faceted beads."""
    pieces, _ = classic()
    beads = [(-5.0, 4.6), (4.2, 5.4), (0.0, 7.0), (-3.4, 10.4), (3.2, 11.2),
             (-1.0, 14.6), (1.8, 16.6)]
    return pieces, beads


DESIGNS = dict(classic=classic, simple=simple, bough=bough, ornaments=ornaments)


# ---- build / check ---------------------------------------------------------
def scale_pieces(pieces, k):
    return [([(x * k, y * k) for x, y in o], [(x * k, y * k, z) for x, y, z in r])
            for o, r in pieces]


def hull(outline, ridge):
    pts = [(x, y, z) for x, y in outline for z in (0.0, P["wall"])] + list(ridge)
    return mf.Manifold.hull_points(np.array(pts, float))


def to_trimesh(solid):
    m = solid.simplify(0.002).to_mesh()
    return trimesh.Trimesh(np.asarray(m.vert_properties)[:, :3],
                           np.asarray(m.tri_verts), process=False)


def bead(x, y, surface_z):
    """Faceted hexagonal bead sitting on the tree surface at (x, y)."""
    r = P["bead_r"]
    top = surface_z + P["bead_rise"]
    pts = []
    for k in range(6):
        a = math.radians(30 + 60 * k)
        for rr, z in ((r, 0.0), (r, max(P["wall"], top - 0.9)), (r * 0.55, top - 0.2)):
            pts.append((x + rr * math.cos(a), y + rr * math.sin(a), z))
    pts.append((x, y, top))
    return mf.Manifold.hull_points(np.array(pts))


def surface_z(mesh, x, y):
    hits, _, _ = mesh.ray.intersects_location([[x, y, 20.0]], [[0, 0, -1.0]])
    return max(h[2] for h in hits) if len(hits) else P["wall"]


def build(pieces, beads):
    solid = mf.Manifold.batch_boolean([hull(o, r) for o, r in pieces], mf.OpType.Add)
    if beads:
        base = to_trimesh(solid)
        extra = [bead(x, y, surface_z(base, x, y)) for x, y in beads]
        solid = mf.Manifold.batch_boolean([solid] + extra, mf.OpType.Add)
    return to_trimesh(solid)


def narrow_notch(pieces):
    """Largest patch (mm2) a nozzle-sized closing fills in the footprint
    (see snowflakes.py).  The V where each tier's base meets the tier below is
    part of the silhouette and scores 0.2-0.5 (only its very tip fills in), so
    trees are flagged only above 0.5."""
    fp = unary_union([Polygon(o).buffer(0) for o, _ in pieces])
    g = P["min_gap"] / 2
    filled = fp.buffer(g).buffer(-g).difference(fp)
    return max((p.area for p in getattr(filled, "geoms", [filled])), default=0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", help=" ".join(DESIGNS))
    ap.add_argument("--size", type=float, default=BASE_SIZE, help="tree height, mm")
    ap.add_argument("--no-png", action="store_true")
    args = ap.parse_args()
    names = args.names or list(DESIGNS)
    k = args.size / BASE_SIZE
    os.makedirs(OUT, exist_ok=True)

    meshes = []
    for name in names:
        pieces, beads = DESIGNS[name]()
        pieces = scale_pieces(pieces, k)
        beads = [(x * k, y * k) for x, y in beads]
        mesh = build(pieces, beads)
        notch = narrow_notch(pieces)
        ex = mesh.extents
        print(f"{name:9s} {ex[0]:5.1f} x {ex[1]:5.1f} x {ex[2]:4.1f} mm  "
              f"watertight={mesh.is_watertight}  vol={mesh.volume:5.0f} mm3  "
              f"worst notch={notch:.2f} mm2" + ("  <-- tight spot" if notch > 0.5 else ""))
        mesh.export(os.path.join(OUT, f"tree_{name}.stl"))
        if not args.no_png:
            render(mesh, os.path.join(OUT, f"tree_{name}.png"),
                   f"{name}  {ex[0]:.1f} x {ex[1]:.1f} x {ex[2]:.1f} mm",
                   rgb=(0.35, 0.8, 0.45))
        meshes.append(mesh)

    if len(meshes) > 1:  # all on one plate, in a row
        x = 0.0
        placed = []
        for m in meshes:
            m = m.copy()
            m.apply_translation((x - m.bounds[0][0], -m.bounds[0][1], 0))
            x += m.extents[0] + 4
            placed.append(m)
        trimesh.util.concatenate(placed).export(os.path.join(OUT, "trees_all.stl"))


if __name__ == "__main__":
    main()
