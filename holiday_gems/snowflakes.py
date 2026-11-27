"""Faceted snowflake "gems", about the size of Heart/heart-resized.stl (20 x 17 x 5 mm).

Every stroke of a snowflake (arm, branch, ring edge) is a convex faceted bar:
vertical walls at the bottom, two sloped facets meeting in a sharp ridge on top,
and pointed ends.  The ridge is highest at the centre and drops toward the tips,
so the whole piece reads like a cut crystal.  Bars are unioned with manifold3d,
flat bottom at z = 0, no overhangs, so it prints without supports.

Usage (from this folder):
    ../millipod/python/.venv/bin/python snowflakes.py            # all designs
    ../millipod/python/.venv/bin/python snowflakes.py classic    # one design
    ../millipod/python/.venv/bin/python snowflakes.py --size 25  # tip-to-tip mm

Writes out/snowflake_<name>.stl, out/snowflakes_all.stl (all of them on one
plate) and out/snowflake_<name>.png previews.
"""
import argparse
import math
import os

import numpy as np
import manifold3d as mf
import trimesh
from shapely.geometry import Polygon
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

# ---- print parameters (0.4 mm nozzle) -------------------------------------
P = dict(
    size=22.0,     # tip-to-tip diameter, mm
    width=2.0,     # base width of a main arm, mm (5 perimeters' worth)
    branch_w=1.6,  # base width of a branch, mm (>= 4 x nozzle)
    wall=0.9,      # height of the vertical side walls, mm
    h_center=4.2,  # ridge height at the centre, mm
    h_tip=2.0,     # ridge height at the arm tips, mm
    min_gap=0.8,   # warn when two strokes come closer than this, mm
)


# ---- geometry --------------------------------------------------------------
def ridge_z(p, R):
    r = min(np.hypot(*p) / R, 1.0)
    return P["h_center"] - (P["h_center"] - P["h_tip"]) * r


def bar_points(a, b, w, R):
    """Hull points of one faceted bar from a to b (2D, mm)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a
    L = np.hypot(*d)
    d /= L
    n = np.array([-d[1], d[0]])
    tip = w * 0.45                      # pointed ends
    pts = []
    for p, sgn in ((a, -1), (b, 1)):
        for s in (-1, 1):
            q = p + n * s * w / 2
            pts += [(*q, 0.0), (*q, P["wall"])]
        q = p + d * sgn * tip
        pts += [(*q, 0.0), (*q, P["wall"])]
        pts.append((*p, ridge_z(p, R)))
    return np.array(pts)


def bar_footprint(a, b, w):
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = (b - a) / np.hypot(*(b - a))
    n = np.array([-d[1], d[0]])
    t = w * 0.45
    return Polygon([a + n * w / 2, b + n * w / 2, b + d * t,
                    b - n * w / 2, a - n * w / 2, a - d * t])


def rot(p, ang):
    c, s = math.cos(ang), math.sin(ang)
    return (c * p[0] - s * p[1], s * p[0] + c * p[1])


def six_fold(strokes):
    """strokes for one arm along +X (and mirrored halves) -> all six arms."""
    out = []
    for k in range(6):
        ang = k * math.pi / 3
        for a, b, w in strokes:
            out.append((rot(a, ang), rot(b, ang), w))
    return out


def mirror(strokes):
    return strokes + [((a[0], -a[1]), (b[0], -b[1]), w) for a, b, w in strokes]


def polar(r, deg):
    return (r * math.cos(math.radians(deg)), r * math.sin(math.radians(deg)))


def branch(R, r0, length, deg=60, w=None):
    """a branch leaving the +X arm at radius r0, angled deg off the arm."""
    w = w or P["branch_w"]
    s = (r0 * R, 0.0)
    e = (s[0] + length * R * math.cos(math.radians(deg)),
         length * R * math.sin(math.radians(deg)))
    return (s, e, w)


# ---- designs (R = tip radius; lengths are fractions of R) -------------------
def classic(R):
    """Main arm with two pairs of 60 degree branches."""
    W = P["width"]
    arm = [((0, 0), (R, 0), W)]
    br = [branch(R, 0.42, 0.34), branch(R, 0.70, 0.22)]
    return six_fold(arm + mirror(br))


def fern(R):
    """Short branches close to the centre, swept a little more forward."""
    W = P["width"]
    arm = [((0, 0), (R, 0), W)]
    br = [branch(R, 0.32, 0.28, 55), branch(R, 0.66, 0.22, 55)]
    return six_fold(arm + mirror(br))


def plate(R):
    """Hexagonal ring joining the arms, a forked tip on each arm."""
    W = P["width"]
    rr = 0.48 * R
    ring = [(polar(rr, 0), polar(rr, 60), P["branch_w"])]
    arm = [((0, 0), (0.78 * R, 0), W)]
    fork = [((0.62 * R, 0), polar(R, 14), P["branch_w"])]
    return six_fold(ring + arm + mirror(fork))


def star(R):
    """Big faceted hexagon hub with plain pointed arms: the simplest gem."""
    W = P["width"] * 1.4
    return six_fold([((0, 0), (R, 0), W)]), (0.45 * R, 2.4)


def dendrite(R):
    """Branches that fork again: the fanciest, check the gaps."""
    W = P["width"]
    b1 = branch(R, 0.38, 0.40)
    mid = (b1[0][0] + (b1[1][0] - b1[0][0]) * 0.75,
           b1[0][1] + (b1[1][1] - b1[0][1]) * 0.75)
    sub = (mid, (mid[0] + 0.17 * R, mid[1]), P["branch_w"])  # parallel to arm
    tip_br = branch(R, 0.80, 0.16)
    arm = [((0, 0), (R, 0), W)]
    return six_fold(arm + mirror([b1, sub, tip_br]))


DESIGNS = dict(classic=classic, fern=fern, plate=plate, star=star,
               dendrite=dendrite)


# ---- build / check ---------------------------------------------------------
def build(strokes, R, hub=None):
    """hub = (radius, wall height) of the hexagonal dome at the centre."""
    hub_r, hub_wall = hub or (P["width"] * 0.9, P["wall"])
    bars = [mf.Manifold.hull_points(bar_points(a, b, w, R)) for a, b, w in strokes]
    # little faceted dome over the centre so all six ridges meet in a point
    hub = [(*polar(hub_r, 30 + 60 * k), z) for k in range(6)
           for z in (0.0, hub_wall)] + [(0, 0, P["h_center"])]
    bars.append(mf.Manifold.hull_points(np.array(hub)))
    solid = mf.Manifold.batch_boolean(bars, mf.OpType.Add).simplify(0.002)
    m = solid.to_mesh()
    return trimesh.Trimesh(np.asarray(m.vert_properties)[:, :3],
                           np.asarray(m.tri_verts), process=False)


def narrow_notch(strokes):
    """Largest patch (mm2) that a nozzle-sized closing fills in the footprint.

    Every junction leaves a small wedge (~0.1 mm2 at the default sizes); a
    bigger number means two strokes run closer than min_gap and the slicer
    will likely bridge or blob the gap between them.
    """
    fp = unary_union([bar_footprint(a, b, w) for a, b, w in strokes])
    g = P["min_gap"] / 2
    filled = fp.buffer(g).buffer(-g).difference(fp)
    return max((p.area for p in getattr(filled, "geoms", [filled])), default=0.0)


def render(mesh, path, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    fig = plt.figure(figsize=(8, 4), dpi=110)
    light = np.array([-0.4, -0.5, 0.8])
    light /= np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.clip(mesh.face_normals @ light, 0, 1)
    colors = np.c_[0.55 * shade, 0.75 * shade, 0.95 * shade, np.ones_like(shade)]
    for i, (elev, azim) in enumerate(((90, -90), (35, -60))):
        ax = fig.add_subplot(1, 2, i + 1, projection="3d")
        ax.add_collection3d(Poly3DCollection(mesh.triangles, facecolors=colors,
                                             edgecolor="none"))
        r = mesh.extents.max() / 2
        ax.set_xlim(-r, r); ax.set_ylim(-r, r); ax.set_zlim(-r / 2, r / 2)
        ax.set_box_aspect((1, 1, 0.5))
        ax.view_init(elev, azim)
        ax.set_axis_off()
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", help=" ".join(DESIGNS))
    ap.add_argument("--size", type=float, default=P["size"])
    ap.add_argument("--no-png", action="store_true")
    args = ap.parse_args()
    names = args.names or list(DESIGNS)
    R = args.size / 2 - P["width"] * 0.45   # pointed tip pokes out by this much
    os.makedirs(OUT, exist_ok=True)

    meshes = []
    for name in names:
        d = DESIGNS[name](R)
        strokes, hub = d if isinstance(d, tuple) else (d, None)
        mesh = build(strokes, R, hub)
        notch = narrow_notch(strokes)
        ex = mesh.extents
        print(f"{name:9s} {ex[0]:5.1f} x {ex[1]:5.1f} x {ex[2]:4.1f} mm  "
              f"watertight={mesh.is_watertight}  vol={mesh.volume:5.0f} mm3  "
              f"worst notch={notch:.2f} mm2" + ("  <-- tight spot" if notch > 0.2 else ""))
        mesh.export(os.path.join(OUT, f"snowflake_{name}.stl"))
        if not args.no_png:
            render(mesh, os.path.join(OUT, f"snowflake_{name}.png"),
                   f"{name}  {ex[0]:.1f} x {ex[1]:.1f} x {ex[2]:.1f} mm")
        meshes.append(mesh)

    if len(meshes) > 1:  # all on one plate, 3 per row
        step = args.size + 4
        placed = [m.copy().apply_translation(((i % 3) * step, -(i // 3) * step, 0))
                  for i, m in enumerate(meshes)]
        trimesh.util.concatenate(placed).export(os.path.join(OUT, "snowflakes_all.stl"))


if __name__ == "__main__":
    main()
