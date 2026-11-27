"""Faceted Christmas ornament-ball "gems", same family as snowflakes.py/trees.py.

A ball is a faceted dome: stacked polygons that shrink as they rise (a girdle
with vertical walls at the bottom, then crown rings, then a table or a point),
hulled into one convex solid.  A cap and a hanging loop sit on top.  Flat
bottom at z = 0, no overhangs, so it prints without supports.

Usage (from this folder):
    ../millipod/python/.venv/bin/python ornaments.py             # all designs
    ../millipod/python/.venv/bin/python ornaments.py brilliant   # one design
    ../millipod/python/.venv/bin/python ornaments.py --size 22   # total height, mm

Writes out/ornament_<name>.stl, out/ornaments_all.stl and previews.
Designs are drawn 24 mm tall (loop included) and scaled in X/Y only.
"""
import argparse
import math
import os

import numpy as np
import manifold3d as mf
import trimesh
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union

from snowflakes import render
from trees import to_trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
BASE_SIZE = 24.0

P = dict(
    wall=0.9,        # girdle (vertical wall) height, mm
    dome_h=5.0,      # ball height, like the heart, mm
    ball_r=8.5,      # ball radius at 24 mm total height, mm
    cap_w=4.4, cap_h=2.6, cap_z=2.6,   # cap: width, length (Y), height, mm
    loop_r=2.4, hole_r=1.15, loop_z=1.8,  # hanging loop, mm (hole 2.3 mm)
    band_rise=1.0,   # how far stripes stand proud of the ball, mm
    min_gap=0.8,
)


def ngon(n, r, rot=0.0, c=(0.0, 0.0)):
    return [(c[0] + r * math.cos(math.radians(rot + 360 * k / n)),
             c[1] + r * math.sin(math.radians(rot + 360 * k / n))) for k in range(n)]


def stacked(levels):
    """levels: [(polygon [(x, y)...], z), ...] -> convex hull solid."""
    pts = [(x, y, z) for poly, z in levels for x, y in poly]
    return mf.Manifold.hull_points(np.array(pts, float))


# ---- ball shapes (centred at the origin, radius r) ---------------------------
def brilliant(r, h):
    """Round brilliant cut: 16-sided girdle, 8 star facets, octagonal table."""
    return [(ngon(16, r), 0.0), (ngon(16, r), P["wall"]),
            (ngon(8, r * 0.82, 22.5), P["wall"] + (h - P["wall"]) * 0.55),
            (ngon(8, r * 0.48), h)]


def geodesic(r, h):
    """Low-poly sphere cap with a point on top."""
    return [(ngon(14, r), 0.0), (ngon(14, r), P["wall"]),
            (ngon(14, r * 0.88, 360 / 28), P["wall"] + (h - P["wall"]) * 0.42),
            (ngon(7, r * 0.55), P["wall"] + (h - P["wall"]) * 0.82),
            ([(0.0, 0.0)], h)]


def teardrop_poly(n, r, tip=1.55):
    """Circle with a point at the bottom (-Y), convex."""
    pts = [p for p in ngon(n, r, 90) if p[1] > -r * 0.55] + [(0.0, -r * tip)]
    return pts


def teardrop(r, h):
    """Onion / drop ornament: pointed at the bottom, faceted crown."""
    return [(teardrop_poly(16, r), 0.0), (teardrop_poly(16, r), P["wall"]),
            ([(x, y + r * 0.08) for x, y in teardrop_poly(10, r * 0.8)],
             P["wall"] + (h - P["wall"]) * 0.5),
            ([(x, y + r * 0.15) for x, y in teardrop_poly(6, r * 0.45)], h)]


# ---- designs ----------------------------------------------------------------
def ball(shape, r, h, bands=()):
    """Ball solid plus optional raised horizontal stripes at the given y's."""
    levels = shape(r, h)
    solid = stacked(levels)
    if bands:
        proud = stacked([(poly, z if i < 2 else z + P["band_rise"])
                         for i, (poly, z) in enumerate(levels)])
        for y, w in bands:
            slab = mf.Manifold.cube([4 * r, w, 4 * h]).translate([-2 * r, y - w / 2, -h])
            solid = solid + (proud ^ slab)
    return solid, Polygon(levels[0][0]).convex_hull


def hanger(top_y):
    """Cap (bevelled block) and an octagonal loop above a ball whose top is top_y."""
    w, L, z = P["cap_w"], P["cap_h"], P["cap_z"]
    y0 = top_y - 1.0                       # sinks 1 mm into the ball
    cap_base = [(-w / 2, y0), (w / 2, y0), (w / 2, y0 + L), (-w / 2, y0 + L)]
    i = 0.5
    cap_top = [(-w / 2 + i, y0 + i * 0.5), (w / 2 - i, y0 + i * 0.5),
               (w / 2 - i, y0 + L - i), (-w / 2 + i, y0 + L - i)]
    cap = stacked([(cap_base, 0.0), (cap_base, z - 0.6), (cap_top, z)])
    cy = y0 + L + P["loop_r"] - 0.9        # overlaps the cap by 0.9 mm
    outer = stacked([(ngon(8, P["loop_r"], 22.5, (0, cy)), 0.0),
                     (ngon(8, P["loop_r"], 22.5, (0, cy)), P["loop_z"])])
    hole = stacked([(ngon(8, P["hole_r"], 22.5, (0, cy)), -1.0),
                    (ngon(8, P["hole_r"], 22.5, (0, cy)), P["loop_z"] + 1.0)])
    loop = outer - hole
    fp = [Polygon(cap_base),
          Polygon(ngon(8, P["loop_r"], 22.5, (0, cy))).difference(
              Polygon(ngon(8, P["hole_r"], 22.5, (0, cy))))]
    return cap + loop, fp, cy + P["loop_r"]


def design(shape, bands=()):
    def make(k):
        r, h = P["ball_r"] * k, P["dome_h"]
        solid, fp = ball(shape, r, h, [(y * k, w) for y, w in bands])
        top = max(y for y, in [(p[1],) for p in shape(r, h)[0][0]])
        hang, hfp, _ = hanger(top)
        return solid + hang, [fp] + hfp
    return make


DESIGNS = dict(
    brilliant=design(brilliant),
    geodesic=design(geodesic),
    striped=design(geodesic, bands=[(-3.4, 2.0), (2.2, 2.0)]),
    teardrop=design(teardrop),
)


def narrow_notch(polys):
    fp = unary_union(polys)
    g = P["min_gap"] / 2
    filled = fp.buffer(g).buffer(-g).difference(fp)
    return max((p.area for p in getattr(filled, "geoms", [filled])), default=0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", help=" ".join(DESIGNS))
    ap.add_argument("--size", type=float, default=BASE_SIZE, help="total height, mm")
    ap.add_argument("--no-png", action="store_true")
    args = ap.parse_args()
    names = args.names or list(DESIGNS)
    os.makedirs(OUT, exist_ok=True)

    # the loop and cap keep their size; the ball takes up the rest of the height
    meshes = []
    for name in names:
        solid, polys = DESIGNS[name](1.0)
        k = 1.0
        for _ in range(4):   # fit total height to --size by scaling the ball
            ext = to_trimesh(solid).extents[1]
            k *= 1 + (args.size - ext) / (2 * P["ball_r"] * k + 1e-9)
            solid, polys = DESIGNS[name](k)
        mesh = to_trimesh(solid)
        mesh.apply_translation([0, -mesh.bounds[0][1], 0])
        notch = narrow_notch(polys)
        ex = mesh.extents
        print(f"{name:9s} {ex[0]:5.1f} x {ex[1]:5.1f} x {ex[2]:4.1f} mm  "
              f"watertight={mesh.is_watertight}  vol={mesh.volume:5.0f} mm3  "
              f"worst notch={notch:.2f} mm2" + ("  <-- tight spot" if notch > 0.2 else ""))
        mesh.export(os.path.join(OUT, f"ornament_{name}.stl"))
        if not args.no_png:
            render(mesh, os.path.join(OUT, f"ornament_{name}.png"),
                   f"{name}  {ex[0]:.1f} x {ex[1]:.1f} x {ex[2]:.1f} mm",
                   rgb=(0.9, 0.3, 0.3))
        meshes.append(mesh)

    if len(meshes) > 1:
        x, placed = 0.0, []
        for m in meshes:
            m = m.copy()
            m.apply_translation((x - m.bounds[0][0], 0, 0))
            x += m.extents[0] + 4
            placed.append(m)
        trimesh.util.concatenate(placed).export(os.path.join(OUT, "ornaments_all.stl"))


if __name__ == "__main__":
    main()
