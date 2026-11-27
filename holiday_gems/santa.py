"""Faceted Santa-cap gem, made for a single layer colour change.

Printed flat, so colour goes by height: the red cap is kept at or below
RED_TOP, and the fur trim and pompom stand on vertical walls up to at least
WHITE_WALL before their own facets start.  Change filament (or toolhead) to
white at the first layer above RED_TOP and every top surface above that is
white; only the sides of the trim and pompom below that height stay red.

Usage (from this folder):
    ../millipod/python/.venv/bin/python santa.py
    ../millipod/python/.venv/bin/python santa.py --size 24   # width, mm

Writes out/santa_cap.stl and out/santa_cap.png (two-colour preview), and prints
the colour-change height for the U1 profile's layers.
"""
import argparse
import math
import os

import numpy as np
import manifold3d as mf
from shapely.geometry import Polygon
from shapely.ops import unary_union

from snowflakes import render
from trees import to_trimesh
from ornaments import ngon, stacked

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
BASE_WIDTH = 24.0      # mm, drawn width

WALL = 0.9             # cap side walls, mm
RED_TOP = 2.6          # highest point of the red cap, mm
WHITE_WALL = 3.2       # white parts are vertical up to here, mm
TRIM_TOP = 4.0         # fur trim top, mm
POM_TOP = 5.0          # pompom apex, mm
FIRST_LAYER, LAYER = 0.25, 0.2   # U1 profile; used to report the change layer


def ridge_piece(outline, ridge):
    """Convex piece: outline with WALL-high sides, facets up to the ridge."""
    pts = [(x, y, z) for x, y in outline for z in (0.0, WALL)] + list(ridge)
    return mf.Manifold.hull_points(np.array(pts, float))


def cap_parts():
    """Red cap: a wide lower body and a tip that flops over to the right."""
    lower = [(-8.6, 1.0), (8.6, 1.0), (6.2, 11.2), (-4.2, 13.2)]
    flop = [(-4.2, 13.2), (0.8, 15.2), (6.0, 13.6), (10.6, 8.4), (6.2, 11.2)]
    return [
        (lower, [(0.0, 2.2, RED_TOP), (0.8, 11.6, RED_TOP)]),
        (flop, [(0.8, 12.6, RED_TOP), (8.6, 9.6, RED_TOP - 0.5)]),
    ]


def trim_outline():
    """Fur band across the brim: a long octagon."""
    w, y0, y1, c = 21.0, -3.2, 2.4, 1.4
    return [(-w / 2 + c, y0), (w / 2 - c, y0), (w / 2, y0 + c), (w / 2, y1 - c),
            (w / 2 - c, y1), (-w / 2 + c, y1), (-w / 2, y1 - c), (-w / 2, y0 + c)]


def inset(poly, d):
    return list(Polygon(poly).buffer(-d, join_style=2).exterior.coords)[:-1]


POM_C, POM_R = (10.0, 7.8), 3.3   # overlaps the cap edge: no thin sliver


def build():
    red = [ridge_piece(o, r) for o, r in cap_parts()]
    trim = trim_outline()
    white = [
        stacked([(trim, 0.0), (trim, WHITE_WALL), (inset(trim, 0.7), TRIM_TOP)]),
        stacked([(ngon(10, POM_R, 0, POM_C), 0.0), (ngon(10, POM_R, 0, POM_C), WHITE_WALL),
                 (ngon(5, POM_R * 0.55, 18, POM_C), POM_TOP - 0.5),
                 ([POM_C], POM_TOP)]),
    ]
    solid = mf.Manifold.batch_boolean(red + white, mf.OpType.Add)
    footprint = [Polygon(o).convex_hull for o, _ in cap_parts()] + [
        Polygon(trim), Polygon(ngon(10, POM_R, 0, POM_C))]
    return solid, footprint


def change_layer():
    """First layer (1-based) and its top Z that lies wholly above RED_TOP."""
    n, top = 1, FIRST_LAYER
    while top - LAYER < RED_TOP + 1e-6 or top <= RED_TOP:
        n, top = n + 1, top + LAYER
    return n, round(top, 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=float, default=BASE_WIDTH, help="width, mm")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    solid, fp = build()
    mesh = to_trimesh(solid)
    k = args.size / mesh.extents[0]
    mesh.apply_scale([k, k, 1.0])
    mesh.apply_translation([-mesh.bounds[0][0], -mesh.bounds[0][1], 0])

    fpu = unary_union(fp)
    filled = fpu.buffer(0.4).buffer(-0.4).difference(fpu)
    notch = max((p.area for p in getattr(filled, "geoms", [filled])), default=0.0) * k * k
    ex = mesh.extents
    n, z = change_layer()
    print(f"santa_cap {ex[0]:5.1f} x {ex[1]:5.1f} x {ex[2]:4.1f} mm  "
          f"watertight={mesh.is_watertight}  vol={mesh.volume:5.0f} mm3  "
          f"worst notch={notch:.2f} mm2")
    print(f"red up to {RED_TOP} mm; change to white at layer {n} (Z = {z} mm) "
          f"for a {FIRST_LAYER} mm first layer and {LAYER} mm layers")
    mesh.export(os.path.join(OUT, "santa_cap.stl"))

    # preview: what each face will look like after the colour change
    zc = mesh.triangles_center[:, 2]
    up = mesh.face_normals[:, 2] > 0.05
    white_face = (zc > RED_TOP + 0.05) | (up & (zc > RED_TOP))
    face_rgb = np.where(white_face[:, None], [0.95, 0.95, 0.95], [0.85, 0.12, 0.12])
    render(mesh, os.path.join(OUT, "santa_cap.png"),
           f"santa cap  {ex[0]:.1f} x {ex[1]:.1f} x {ex[2]:.1f} mm  (white from Z {z})",
           face_rgb=face_rgb)


if __name__ == "__main__":
    main()
