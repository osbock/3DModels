#!/usr/bin/env python3
"""Reference files for designing a custom face.

Writes to face_meshes/ (or --out-dir):
  head_reference.stl   the bare head (no face) in face coordinates, to model against
  sample_face.stl      example face to ADD (eyes)      -> --face-mesh
  sample_face_cut.stl  example face to CUT (pupils, smile) -> --face-cut
  face_guide.png       the head and sample face in four labelled views

Face coordinates: origin on the bed (z=0), on the centre line (y=0), directly
under the head's tip. +x points forward out of the face, +y to the
millipede's left, +z up. The head depends on width / height / head_length /
pitch / foot_flare, so pass the same parameters (or --config) you build with.

Try the sample:
  .venv/bin/python millipede.py --face none \
      --face-mesh face_meshes/sample_face.stl --face-cut face_meshes/sample_face_cut.stl
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
from manifold3d import Manifold, OpType

import faces
import millipede as mp


def sample_face(b: mp.Builder, tip: float) -> tuple[Manifold, Manifold]:
    """Eyes to add; pupils and a smile to cut. Built on the head surface, then
    moved into face coordinates."""
    n = b.n
    add, cut = [], []
    for s in (1, -1):
        c, nrm = faces._on_head(b, 34 * s, 24, 0.8)
        add.append(Manifold.sphere(2.0, n).translate(list(c)))
        pupil = [c[i] + nrm[i] * 2.0 for i in range(3)]
        cut.append(Manifold.sphere(0.8, n).translate(pupil))
    # smile: a groove of hulled spheres along an upward-curving arc
    pts = []
    for az in np.linspace(-24, 24, 9):
        el = -2 + 0.012 * az * az
        pts.append(faces._on_head(b, az, el, 0.0)[0])
    balls = [Manifold.sphere(0.6, n).translate(list(p)) for p in pts]
    cut += [Manifold.batch_hull([a, c]) for a, c in zip(balls, balls[1:])]
    shift = [-tip, 0, 0]
    return (Manifold.batch_boolean(add, OpType.Add).translate(shift),
            Manifold.batch_boolean(cut, OpType.Add).translate(shift))


def bare_head(p: mp.Params) -> tuple[Manifold, float]:
    q = mp.Params(**{**p.__dict__, "face": "none", "face_mesh": "", "face_cut": "",
                     "mouse_ears": False, "texture": "none"})
    b = mp.Builder(q)
    tip = q.head_length - q.pitch
    return b.head().translate([-tip, 0, 0]), tip


def _tris(m: Manifold):
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3]
    return v[np.asarray(mesh.tri_verts)]


def render(head: Manifold, add: Manifold, cut: Manifold, p: mp.Params, path: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    light = np.array([0.5, -0.4, 0.75])
    light /= np.linalg.norm(light)

    def shaded(m, color):
        t = _tris(m)
        nrm = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
        nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12
        shade = 0.4 + 0.6 * np.clip(np.abs(nrm @ light), 0, 1)
        return t, np.clip(shade[:, None] * np.array(color), 0, 1)

    # one collection so matplotlib depth-sorts head, face and cut together
    parts = [shaded(head, (0.85, 0.72, 0.55)), shaded(add, (0.2, 0.45, 0.9)),
             shaded(cut, (0.9, 0.15, 0.15))]
    tris = np.concatenate([t for t, _ in parts])
    cols = np.concatenate([c for _, c in parts])

    lo = np.array(head.bounding_box()[:3]); hi = np.array(head.bounding_box()[3:])
    lo = np.minimum(lo, -1); hi = np.maximum(hi, 3)
    fig = plt.figure(figsize=(15, 11))
    views = [("side (from the millipede's right, -y)", 0, -90, 1),
             ("top", 90, -90, 2),
             ("front (looking at the face, from +x)", 0, 0, 3),
             ("3/4", 22, -40, 4)]
    for title, elev, azim, k in views:
        ax = fig.add_subplot(2, 2, k, projection="3d")
        ax.set_proj_type("ortho")
        ax.add_collection3d(Poly3DCollection(tris, facecolors=cols, edgecolor="none"))
        L = 4
        for d, c, lab in (((L, 0, 0), "r", "+x"), ((0, L, 0), "g", "+y"), ((0, 0, L), "b", "+z")):
            ax.quiver(0, 0, 0, *d, color=c, lw=2.5, arrow_length_ratio=0.25)
            ax.text(d[0] * 1.15, d[1] * 1.15, d[2] * 1.15, lab, color=c, fontsize=12, weight="bold")
        ax.scatter([0], [0], [0], color="k", s=30)
        ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_zlim(lo[2], hi[2])
        ax.set_box_aspect(tuple(hi - lo))
        ax.view_init(elev=elev, azim=azim)
        ax.set_xlabel("x (mm)"); ax.set_ylabel("y (mm)"); ax.set_zlabel("z (mm)")
        if elev == 90:
            ax.set_zticks([]); ax.set_zlabel("")
        if azim == -90 and elev == 0:
            ax.set_yticks([]); ax.set_ylabel("")
        if azim == 0:
            ax.set_xticks([]); ax.set_xlabel("")
        ax.set_title(title)
    back = -(p.head_length - p.nose_radius - p.gap)
    fig.suptitle(
        "Face coordinates: origin (black dot) = on the bed, centre line, under the head tip.  "
        "+x forward, +y left, +z up.\n"
        f"Tan = bare head (head_reference.stl, {hi[0]-lo[0]:.0f} x {hi[1]-lo[1]:.0f} x {hi[2]-lo[2]:.0f} mm box).  "
        "Blue = sample_face.stl (added).  Red = sample_face_cut.stl (cut).\n"
        f"Anything behind about x = {back:.1f} near the centre line (further forward at the sides) is "
        "cut away by the joint to the first segment. Keep the underside printable (no overhang below 45°).",
        fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(path, dpi=100)
    plt.close(fig)


def export_stl(m: Manifold, path: Path):
    mp.to_trimesh(m).export(path)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    out = Path("face_meshes")
    if "--out-dir" in argv:
        i = argv.index("--out-dir")
        out = Path(argv[i + 1])
        del argv[i:i + 2]
    p = mp.parse_params(argv, description="Write reference files for designing a custom face.")
    out.mkdir(parents=True, exist_ok=True)
    head, tip = bare_head(p)
    b = mp.Builder(p)
    add, cut = sample_face(b, tip)
    export_stl(head, out / "head_reference.stl")
    export_stl(add, out / "sample_face.stl")
    export_stl(cut, out / "sample_face_cut.stl")
    render(head, add, cut, p, out / "face_guide.png")
    for f in ("head_reference.stl", "sample_face.stl", "sample_face_cut.stl", "face_guide.png"):
        print(f"wrote {out / f}")


if __name__ == "__main__":
    main()
