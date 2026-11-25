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


def spots(m, b, kind, index, count=3, r=0.9):
    """A few random dimples on top of each shell (different per segment)."""
    if kind != "body":
        return m
    p = b.p
    rng = random.Random(index)
    phi = math.radians(p.chevron_angle)
    apex_f = p.nose_radius / math.sin(phi)
    apex_b = -p.pitch + (p.nose_radius + p.gap) / math.sin(phi)
    cuts = []
    for _ in range(count):
        t = rng.uniform(0.2, 0.8) * math.pi
        y = p.width / 2 * math.cos(t)
        z = p.leg_height + (p.height - p.leg_height) * math.sin(t)
        rho = math.hypot(y, z - p.zc)
        x = (apex_f + apex_b) / 2 - rho / math.tan(phi)
        x += rng.uniform(-0.4, 0.4)
        cuts.append(Manifold.sphere(r, b.n).translate([x, y, z]))
    return m - Manifold.batch_boolean(cuts, OpType.Add)


TEXTURES = {
    "none": none,
    "grooves": grooves,
    "spots": spots,
}
PER_SEGMENT = {"spots"}


def varies(name: str) -> bool:
    return name in PER_SEGMENT


def apply(name, m, b, kind, index):
    return TEXTURES[name](m, b, kind, index)
