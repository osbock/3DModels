"""Faceted Hanukkah menorah (hanukkiah) gems, same family as trees.py.

Nine candles, the shamash raised in the middle, standing on branches and a
base.  Every part is a convex faceted piece (outline with short vertical walls,
facets up to a ridge), unioned with manifold3d; flat bottom, no overhangs.

The menorah itself stays at or below BODY_TOP and the nine flames are flat
plates FLAME_LAYERS layers thicker than it, so it prints in one colour or, with
a layer colour change at the first layer above BODY_TOP, with coloured flames.

Designs:
    classic  curved branches, nested half-ellipses meeting a central stem
    modern   straight bar on a stepped stand

Usage (from this folder):
    ../millipod/python/.venv/bin/python menorah.py             # all designs
    ../millipod/python/.venv/bin/python menorah.py classic     # one design
    ../millipod/python/.venv/bin/python menorah.py --size 24   # width, mm

Writes out/menorah_<name>.stl/.png and out/menorahs_all.stl.  Designs are
drawn 25 mm wide and scaled in X/Y only.
"""
import argparse
import math
import os

import numpy as np
import manifold3d as mf
import trimesh
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union

from snowflakes import render
from trees import to_trimesh
from ornaments import ngon, stacked

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
BASE_WIDTH = 25.0

WALL = 0.9             # vertical side walls, mm
BODY_TOP = 2.6         # highest point of the menorah body, mm
FLAME_LAYERS = 2       # flames stand this many layers above the body
FIRST_LAYER, LAYER = 0.25, 0.2   # U1 profile; used to report the change layer
MIN_GAP = 0.8

PITCH = 2.75           # candle spacing, mm
ARM_W = 1.1            # branch width, mm
CANDLE_W, CANDLE_H = 1.3, 4.0
FLAME_R = 0.95


# ---- pieces -----------------------------------------------------------------
def ridged(outline, ridge):
    """Convex piece: outline with WALL-high sides, facets up to the ridge."""
    pts = [(x, y, z) for x, y in outline for z in (0.0, WALL)] + list(ridge)
    return mf.Manifold.hull_points(np.array(pts, float)), Polygon(outline).convex_hull


def capsule(p, q, w, h):
    """Faceted rod from p to q, w wide, ridge height h (rounded octagon ends)."""
    outline = ngon(8, w / 2, 22.5, p) + ngon(8, w / 2, 22.5, q)
    solid, _ = ridged(outline, [(*p, h), (*q, h)])
    return solid, LineString([p, q]).buffer(w / 2, 8)


def box(x0, y0, x1, y1, h, inset=None):
    """Rectangle with a ridge along its long axis."""
    outline = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if x1 - x0 >= y1 - y0:
        d = inset if inset is not None else (y1 - y0) / 2
        ridge = [(x0 + d, cy, h), (x1 - d, cy, h)]
    else:
        d = inset if inset is not None else (x1 - x0) / 2
        ridge = [(cx, y0 + d, h), (cx, y1 - d, h)]
    return ridged(outline, ridge)


def trapezoid(y0, y1, w0, w1, h):
    outline = [(-w0 / 2, y0), (w0 / 2, y0), (w1 / 2, y1), (-w1 / 2, y1)]
    m = (y1 - y0) / 2
    return ridged(outline, [(-w1 / 2 + m * 0.6, y0 + m, h), (w1 / 2 - m * 0.6, y0 + m, h)])


def candle(x, y0, h=CANDLE_H):
    return box(x - CANDLE_W / 2, y0, x + CANDLE_W / 2, y0 + h, 2.2, inset=0.4)


def flame(x, y_top):
    """Short teardrop flame pointing up, sitting 0.65 mm into the candle top:
    a flat-topped plate FLAME_LAYERS layers above the body."""
    c = (x, y_top + FLAME_R - 0.65)
    tip = (x, c[1] + FLAME_R * 1.6)
    foot = [p for p in ngon(12, FLAME_R, 90, c) if p[1] <= c[1] + 0.3] + [tip]
    solid = stacked([(foot, 0.0), (foot, flame_top())])
    return solid, Polygon(foot).convex_hull


def arc(rx, ry, cy, w, h, n=12):
    """Half-ellipse branch below y = cy, from x = -rx to rx, as joined rods."""
    pts = [(rx * math.cos(math.pi + math.pi * k / n), cy + ry * math.sin(math.pi + math.pi * k / n))
           for k in range(n + 1)]
    return [capsule(pts[k], pts[k + 1], w, h) for k in range(n)]


# ---- designs (drawn 25 mm wide, centred on x = 0, base at y = 0) ------------
def candles_and_flames(top_y, shamash_lift):
    parts, flames = [], []
    for k in range(-4, 5):
        x = k * PITCH
        y0 = top_y + (shamash_lift if k == 0 else 0.0)
        parts.append(candle(x, y0))
        flames.append(flame(x, y0 + CANDLE_H))
    return parts, flames


def classic():
    """Curved branches: four nested half-ellipses meeting a central stem."""
    cup_y = 11.0
    parts = [trapezoid(0.0, 1.8, 12.0, 6.0, BODY_TOP),
             box(-2.6, 1.6, 2.6, 2.6, 2.3),
             box(-0.9, 2.0, 0.9, cup_y + 1.8, BODY_TOP, inset=0.6)]
    for k in range(1, 5):
        rx = k * PITCH
        parts += arc(rx, 0.75 * rx, cup_y + 0.3, ARM_W, 1.8)
    c, f = candles_and_flames(cup_y, 1.8)
    return parts + c, f


def modern():
    """Straight bar on a triangular bracket and stepped stand; the shamash rides
    higher on the stem."""
    bar_y = 7.6
    parts = [trapezoid(0.0, 1.6, 14.0, 9.0, BODY_TOP),
             trapezoid(1.4, 3.0, 8.0, 3.4, 2.4),
             box(-1.0, 2.8, 1.0, bar_y + 3.4, BODY_TOP, inset=0.6),
             box(-4 * PITCH - 0.9, bar_y - 0.6, 4 * PITCH + 0.9, bar_y + 0.9, 2.0, inset=0.75)]
    # solid inverted-triangle bracket between the stem and the bar
    parts.append(ridged([(-6.0, bar_y), (6.0, bar_y), (0.0, 2.8)],
                        [(-4.6, bar_y - 0.3, 1.8), (4.6, bar_y - 0.3, 1.8), (0.0, 3.6, 1.8)]))
    c, f = candles_and_flames(bar_y + 0.6, 2.4)
    return parts + c, f


DESIGNS = dict(classic=classic, modern=modern)


# ---- build / check ----------------------------------------------------------
def scaled(solid, k):
    return solid.scale([k, k, 1.0])


def narrow_notch(polys):
    fp = unary_union(polys)
    g = MIN_GAP / 2
    filled = fp.buffer(g).buffer(-g).difference(fp)
    return max((p.area for p in getattr(filled, "geoms", [filled])), default=0.0)


def change_layer():
    n, top = 1, FIRST_LAYER
    while top - LAYER < BODY_TOP + 1e-6 or top <= BODY_TOP:
        n, top = n + 1, top + LAYER
    return n, round(top, 2)


def flame_top():
    _, z = change_layer()
    return round(z + LAYER * (FLAME_LAYERS - 1), 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", help=" ".join(DESIGNS))
    ap.add_argument("--size", type=float, default=BASE_WIDTH, help="width, mm")
    ap.add_argument("--no-png", action="store_true")
    args = ap.parse_args()
    names = args.names or list(DESIGNS)
    os.makedirs(OUT, exist_ok=True)
    n, zc = change_layer()

    meshes = []
    for name in names:
        body, flames = DESIGNS[name]()
        solid = mf.Manifold.batch_boolean([s for s, _ in body + flames], mf.OpType.Add)
        polys = [p for _, p in body + flames]
        raw = to_trimesh(solid)
        k = args.size / raw.extents[0]
        mesh = to_trimesh(scaled(solid, k))
        mesh.apply_translation([-mesh.bounds[0][0], -mesh.bounds[0][1], 0])
        polys = [Polygon([(x * k, y * k) for x, y in p.exterior.coords]) for p in polys]
        notch = narrow_notch(polys)
        ex = mesh.extents
        print(f"{name:8s} {ex[0]:5.1f} x {ex[1]:5.1f} x {ex[2]:4.1f} mm  "
              f"watertight={mesh.is_watertight}  vol={mesh.volume:5.0f} mm3  "
              f"worst notch={notch:.2f} mm2" + ("  <-- tight spot" if notch > 0.3 else ""))
        mesh.export(os.path.join(OUT, f"menorah_{name}.stl"))
        if not args.no_png:
            z = mesh.triangles_center[:, 2]
            up = mesh.face_normals[:, 2] > 0.05
            lit = z > BODY_TOP + 0.05
            face_rgb = np.where(lit[:, None], [1.0, 0.78, 0.2], [0.25, 0.45, 0.9])
            render(mesh, os.path.join(OUT, f"menorah_{name}.png"),
                   f"{name}  {ex[0]:.1f} x {ex[1]:.1f} x {ex[2]:.1f} mm  (flames from Z {zc})",
                   face_rgb=face_rgb)
        meshes.append(mesh)
    print(f"body up to {BODY_TOP} mm; for coloured flames change at layer {n} (Z = {zc} mm)")

    if len(meshes) > 1:
        x, placed = 0.0, []
        for m in meshes:
            m = m.copy()
            m.apply_translation((x - m.bounds[0][0], 0, 0))
            x += m.extents[0] + 4
            placed.append(m)
        trimesh.util.concatenate(placed).export(os.path.join(OUT, "menorahs_all.stl"))


if __name__ == "__main__":
    main()
