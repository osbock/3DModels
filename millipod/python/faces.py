"""Faces for the head.

A face function gets the Builder (for params and resolution) and the x
position of the head tip in head-local coordinates, and returns
(add, subtract): Manifolds to union with / cut from the head, or None.
Anything added must stay in front of the first body segment; the head's back
carve is applied afterwards, so it is safe near the back too.

To add a face: write a function and register it in FACES. A face can also be
loaded from a mesh file, see `mesh_face`.
"""
from __future__ import annotations

import math

from manifold3d import Manifold


def _on_head(b, az_deg: float, el_deg: float, inset: float):
    """Point on the head ellipsoid surface (same ellipsoid as Builder.head)."""
    p = b.p
    hw = p.width / 2 + p.foot_flare + 0.5
    cx, cz = -p.pitch, p.height * 0.35
    rx, ry, rz = p.head_length, hw, p.height * 0.68
    az, el = math.radians(az_deg), math.radians(el_deg)
    d = (math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el))
    # scale so the point lies on the ellipsoid, then pull in along the normal-ish direction
    s = 1 / math.sqrt((d[0] / rx) ** 2 + (d[1] / ry) ** 2 + (d[2] / rz) ** 2)
    x, y, z = cx + d[0] * s, d[1] * s, cz + d[2] * s
    n = (x - cx) / rx ** 2, y / ry ** 2, (z - cz) / rz ** 2
    nl = math.sqrt(sum(c * c for c in n))
    n = tuple(c / nl for c in n)
    return (x - n[0] * inset, y - n[1] * inset, z - n[2] * inset), n


def none(b, tip):
    return None, None


def eyes(b, tip, r=1.8, az=38, el=22):
    """Two domed eyes with a dimple pupil."""
    add, sub = [], []
    for s in (1, -1):
        c, n = _on_head(b, az * s, el, r * 0.35)
        add.append(Manifold.sphere(r, b.n).translate(list(c)))
        pc = [c[i] + n[i] * r for i in range(3)]
        sub.append(Manifold.sphere(r * 0.38, b.n).translate(pc))
    return add[0] + add[1], sub[0] + sub[1]


def dimple_eyes(b, tip, r=1.6, az=38, el=22):
    """Engraved eyes only (nothing sticks out)."""
    sub = []
    for s in (1, -1):
        c, n = _on_head(b, az * s, el, -r * 0.45)
        sub.append(Manifold.sphere(r, b.n).translate(list(c)))
    return None, sub[0] + sub[1]


def googly(b, tip):
    """Big eyes, smaller pupils."""
    return eyes(b, tip, r=2.4, az=32, el=26)


def load_mesh(path: str, tip: float) -> Manifold:
    """Load an STL/3MF/OBJ drawn in *face coordinates* and move it into head
    coordinates.

    Face coordinates: origin on the bed (z=0), on the centre line (y=0),
    directly under the head's tip; +x points forward out of the face, +y to
    the millipede's left, +z up. Run face_guide.py to get the bare head in
    these coordinates to model against.
    """
    import numpy as np
    import trimesh
    from manifold3d import Mesh
    m = trimesh.load(path, force="mesh")
    m.merge_vertices()
    mf = Manifold(Mesh(vert_properties=np.asarray(m.vertices, dtype=np.float32),
                       tri_verts=np.asarray(m.faces, dtype=np.uint32)))
    if mf.is_empty():
        raise SystemExit(f"{path}: not a closed (watertight) solid: {mf.status()}")
    return mf.translate([tip, 0, 0])


def mesh_face(add_path: str | None = None, cut_path: str | None = None):
    """Factory for a face made from mesh files in face coordinates (see
    load_mesh): `add_path` is unioned onto the head, `cut_path` is cut out of
    it. Register with e.g. FACES["robot"] = mesh_face("face_meshes/robot.stl").
    For one-off use the --face-mesh / --face-cut command-line options instead."""
    def f(b, tip):
        add = load_mesh(add_path, tip) if add_path else None
        cut = load_mesh(cut_path, tip) if cut_path else None
        return add, cut
    return f


FACES = {
    "eyes": eyes,
    "dimple_eyes": dimple_eyes,
    "googly": googly,
    "none": none,
}


def build(name, b, tip):
    return FACES[name](b, tip)
