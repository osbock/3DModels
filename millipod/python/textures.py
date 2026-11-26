"""Surface textures for the shells.

A texture function gets the part (in local coordinates, before the ball/neck
is added), the Builder, the part kind ("head", "body", "tail") and its index,
and returns the modified part. Keep cuts shallow and away from the joint,
feet and the front/back faces (anything that changes those can make parts
collide).

Textures listed in PER_SEGMENT are recomputed for every segment (e.g. random
patterns); others are built once and reused, which is much faster.
"""
from __future__ import annotations

import math
import random

from manifold3d import Manifold, OpType


def _band(b, depth_from_front: float, width: float) -> Manifold:
    """Conical band parallel to the part's front face."""
    import millipede as mp
    p = b.p
    back = 4 * max(p.width, p.height) + p.head_length
    r_out = p.nose_radius - depth_from_front
    r_in = r_out - width
    outer = mp.bullet(max(r_out, 0.05), p.chevron_angle, back, b.n)
    inner = mp.bullet(max(r_in, 0.01), p.chevron_angle, back, b.n)
    return (outer - inner).translate(list(b.Q))


def _skin(b, depth: float) -> Manifold:
    """Region within `depth` of the domed top surface (not the legs)."""
    import millipede as mp
    p = b.p
    outside = b.envelope - b.envelope_inset(depth)
    return outside ^ mp.slab_z(p.leg_height + 0.8, p.height + 1)


def none(m, b, kind, index):
    return m


def grooves(m, b, kind, index, depth=0.6, width=0.8):
    """One groove across the top of each shell, following the chevron."""
    if kind != "body":
        return m
    p = b.p
    thickness = (p.pitch - p.gap) * math.sin(math.radians(p.chevron_angle))
    band = _band(b, thickness / 2 - width / 2, width)
    return m - (band ^ _skin(b, depth))


def _dome_point(p, t: float):
    """Point and outward normal on the domed top, at angle t (radians) around
    the dome: 90 deg is the spine, smaller angles go down the +y side."""
    a, c = p.width / 2, p.height - p.leg_height
    y, z = a * math.cos(t), p.leg_height + c * math.sin(t)
    ny, nz = math.cos(t) / a, math.sin(t) / c
    ln = math.hypot(ny, nz)
    return (y, z), (ny / ln, nz / ln)


def _mid_x(m, y: float, z: float) -> float:
    """Middle of the shell along x at (y, z): measured from the part itself,
    so it accounts for the chevron and for the extra back carve at the sides."""
    probe = Manifold.cube([200, 0.05, 0.05], True).translate([0, y, z])
    lo, _, _, hi, _, _ = (m ^ probe).bounding_box()
    return (lo + hi) / 2


def spots(m, b, kind, index, side_angle=48.0, r=1.1, depth=0.45):
    """Three rows of shallow oval dimples: one down the spine and one along
    each side, the same on every segment.

    side_angle: how far down the side the side rows sit, in degrees from the
    spine. r: radius of each spot across the surface. depth: how deep it is.
    """
    if kind != "body":
        return m
    p = b.p
    cuts = []
    for deg in (90.0, 90.0 - side_angle, 90.0 + side_angle):
        (y, z), (ny, nz) = _dome_point(p, math.radians(deg))
        x = _mid_x(m, y - ny * 0.3, z - nz * 0.3)
        tilt = math.degrees(math.atan2(-ny, nz))  # turn local +z onto the normal
        dimple = (Manifold.sphere(1.0, b.n).scale([r, r, depth])
                  .rotate([tilt, 0, 0]).translate([x, y, z]))
        cuts.append(dimple)
    return m - Manifold.batch_boolean(cuts, OpType.Add)


def _shell_rows(m, b, rows: int = 120, t_min_deg: float = 25.0):
    """For angles around the dome, the surface point, normal and the x extent
    of the shell there. Same for every body segment, so cached on the Builder."""
    cached = getattr(b, "_shell_rows", None)
    if cached is not None:
        return cached
    out = []
    for i in range(rows):
        t = math.radians(t_min_deg + (180 - 2 * t_min_deg) * i / (rows - 1))
        (y, z), (ny, nz) = _dome_point(b.p, t)
        probe = Manifold.cube([200, 0.05, 0.05], True).translate([0, y - ny * 0.2, z - nz * 0.2])
        lo, _, _, hi, _, _ = (m ^ probe).bounding_box()
        if hi > lo:
            out.append((y, z, ny, nz, lo, hi))
    b._shell_rows = out
    return out


def bumpy(m, b, kind, index, r_min=0.35, r_max=0.75, height=0.6,
          packing=0.9, tries=6000):
    """Densely packed small bumps of random size, different on every segment.

    r_min / r_max: bump radius range. height: how much of each bump's radius
    sticks out of the surface. packing: bumps may overlap until their centres
    are closer than packing x (sum of radii); lower = denser and lumpier.
    Bumps have 45 degree cones underneath (printable on the sides) and are
    trimmed to the segment's own space, so they can't touch a neighbour.
    """
    if kind != "body":
        return m
    import millipede as mp
    rows = _shell_rows(m, b)
    rng = random.Random(index)
    placed = []  # (x, y, z, r, ny, nz)
    for _ in range(tries):
        y, z, ny, nz, lo, hi = rows[rng.randrange(len(rows))]
        r = rng.uniform(r_min, r_max)
        if hi - lo < r:
            continue
        x = rng.uniform(lo + r / 2, hi - r / 2)
        if any((x - px) ** 2 + (y - py) ** 2 + (z - pz) ** 2 < (packing * (r + pr)) ** 2
               for px, py, pz, pr, _, _ in placed):
            continue
        placed.append((x, y, z, r, ny, nz))
    if not placed:
        return m
    sink = []
    for x, y, z, r, ny, nz in placed:
        off = r * height - r  # move the centre in so only `height` of it shows
        sink.append(mp.pointed_ball(r, 16).translate([x, y + ny * off, z + nz * off]))
    allowed = getattr(b, "_own_space", None)
    if allowed is None:
        allowed = b._own_space = b.front - b.back_carve - b.socket
    return m + (Manifold.batch_boolean(sink, OpType.Add) ^ allowed)


TEXTURES = {
    "none": none,
    "grooves": grooves,
    "spots": spots,
    "bumpy": bumpy,
}
PER_SEGMENT: set[str] = {"bumpy"}


def varies(name: str) -> bool:
    return name in PER_SEGMENT


def apply(name, m, b, kind, index):
    return TEXTURES[name](m, b, kind, index)
