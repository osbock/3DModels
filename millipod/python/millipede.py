#!/usr/bin/env python3
"""Parametric print-in-place millipede.

Every part (head, N body segments, tail) is a separate solid. Adjacent parts
are linked by a captive ball joint at mid-height and nest like stacked
lampshades:

* Each part's front is a "bullet" around its front joint Q: a sphere of radius
  `nose_radius` plus the cone tangent to it (half-angle `chevron_angle`).
  Everything belonging to that part lies inside its own bullet.
* The back of each part is carved by the *next* part's bullet, grown by `gap`
  and swept through +/-`yaw` about the joint. Since the next part never leaves
  its own bullet, the two parts cannot collide anywhere inside that yaw range.
* The ball (owned by the front part) sits in a cavity in the next part's nose,
  reached through a fan-shaped slot. The slot is thinner than the ball, so the
  ball is captive. Ball and cavity have pointed 45 degree tops and bottoms so
  nothing overhangs.

Local frame of every part: +x points toward the head, +y left, +z up, the
part's front joint is at (0, 0, joint_height) and its back joint is at
(-pitch, 0, joint_height). Because body segments are identical in their own
frame, a segment is built once and then placed; a layout only has to supply
joint positions whose spacing is `pitch` and whose bend at each joint is
within `yaw`.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import math
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from manifold3d import CrossSection, JoinType, Manifold, OpType, set_circular_segments

import faces
import layouts
import textures


@dataclass
class Params:
    # --- overall --------------------------------------------------------
    segments: int = 26           # body segments between head and tail
    layout: str = "line"         # line | spiral
    name: str = ""               # output file stem (auto if empty)

    # --- body shape (mm) ------------------------------------------------
    pitch: float = 5.2           # joint-to-joint distance
    width: float = 14.0          # body width (without foot flare)
    height: float = 12.0         # total height
    leg_height: float = 3.0      # height of the legs below the domed body
    chevron_angle: float = 50.0  # cone half-angle of the nested shells (deg, >=45 prints cleanly)

    # --- feet -----------------------------------------------------------
    foot_gap: float = 2.0        # gap between left and right foot (0 = one wide foot)
    foot_flare: float = 1.0      # how far each foot pad sticks out past the body sides
    foot_pad: float = 0.6        # vertical part of the flared pad before the 45 deg chamfer
    mouse_ears: bool = False     # thin discs under head and tail for adhesion
    ear_radius: float = 6.0
    ear_thickness: float = 0.4

    # --- joint ----------------------------------------------------------
    ball_radius: float = 1.2
    neck_radius: float = 0.6
    nose_wall: float = 0.9       # wall between ball cavity and nose surface
    clearance: float = 0.35      # ball/cavity and neck/slot clearance
    gap: float = 0.45            # clearance between nested shells
    bottom_gap: float = 0.7      # shell clearance in the first layers (elephant's foot)
    bottom_gap_height: float = 0.4
    yaw: float = 12.0            # side-to-side bend allowed per joint (deg)
    joint_height: float = 0.0    # 0 = middle of the domed body

    # --- head / tail / decoration ----------------------------------------
    head_length: float = 11.0    # from the first joint behind the head to its tip
    tail_length: float = 8.0     # from the tail's front joint to its tip
    face: str = "eyes"           # see faces.py
    face_mesh: str = ""          # STL/3MF/OBJ in face coordinates to add to the head
    face_cut: str = ""           # STL/3MF/OBJ in face coordinates to cut from the head
    texture: str = "none"        # see textures.py

    # --- spiral layout ----------------------------------------------------
    spiral_inner_radius: float = 0.0  # 0 = smallest radius the yaw allows
    spiral_turn_gap: float = 2.0      # clearance between spiral turns
    spiral_bend_fraction: float = 0.75  # use at most this fraction of yaw when printing

    # --- output -----------------------------------------------------------
    resolution: int = 48         # segments per full circle
    out_dir: str = "out"
    stl: bool = False
    preview: bool = True
    check: bool = True

    # derived -------------------------------------------------------------
    @property
    def nose_radius(self) -> float:
        return self.ball_radius + self.clearance + self.nose_wall

    @property
    def zc(self) -> float:
        return self.joint_height or (self.leg_height + self.height) / 2

    def validate(self) -> list[str]:
        """Return a list of problems; empty means OK."""
        errs = []
        back_wall = self.pitch - self.nose_radius - self.gap - self.ball_radius - self.clearance
        if back_wall < 0.6:
            errs.append(
                f"wall between a cavity and the cup behind it is {back_wall:.2f} mm (<0.6): "
                "increase pitch or reduce ball_radius / nose_wall / gap")
        if self.neck_radius + self.clearance >= self.ball_radius - 0.15:
            errs.append("ball would not be captive: need neck_radius + clearance < ball_radius - 0.15")
        top = self.zc + (self.ball_radius + self.clearance) * math.sqrt(2)
        if top > self.height - 1.0 or self.zc - (self.ball_radius + self.clearance) * math.sqrt(2) < 1.0:
            errs.append("ball cavity does not fit vertically: check joint_height / height")
        if self.chevron_angle < 45:
            errs.append("chevron_angle < 45 deg will leave overhangs under the shells")
        if self.foot_gap / 2 >= self.width / 2 - 1:
            errs.append("foot_gap too large for width")
        return errs


# ---------------------------------------------------------------------------
# primitives
# ---------------------------------------------------------------------------

def x_cylinder(x0: float, x1: float, r: float, n: int) -> Manifold:
    """Cylinder along +x from x0 to x1 on the x axis."""
    return Manifold.cylinder(x1 - x0, r, r, n).rotate([0, 90, 0]).translate([x0, 0, 0])


def pointed_ball(r: float, n: int) -> Manifold:
    """Sphere with 45 degree cones on top and bottom (overhang-free)."""
    tip = r * math.sqrt(2)
    dot = Manifold.cube([0.001] * 3, True)
    return Manifold.batch_hull([Manifold.sphere(r, n), dot.translate([0, 0, tip]),
                                dot.translate([0, 0, -tip])])


def bullet(r: float, half_angle_deg: float, back: float, n: int) -> Manifold:
    """Sphere of radius r at the origin plus the cone tangent to it that opens
    toward -x with the given half-angle, truncated at x = -back."""
    phi = math.radians(half_angle_deg)
    apex = r / math.sin(phi)
    rad = (apex + back) * math.tan(phi)
    disk = Manifold.cylinder(0.01, rad, rad, n * 2, True).rotate([0, 90, 0]).translate([-back, 0, 0])
    return Manifold.batch_hull([Manifold.sphere(r, n), disk])


def yaw_about(m: Manifold, pivot, deg: float) -> Manifold:
    px, py, pz = pivot
    return m.translate([-px, -py, -pz]).rotate([0, 0, deg]).translate([px, py, pz])


def swept_yaw(m: Manifold, pivot, max_deg: float, step: float = 1.5) -> Manifold:
    """Region covered by convex `m` rotated about a vertical axis through
    `pivot` over +/-max_deg. Uses the hull of the rotated copies: exact for
    the convex sweeps used here (or very slightly larger, which only adds
    clearance), and free of the slivers a union of copies leaves behind."""
    k = max(1, math.ceil(2 * max_deg / step))
    parts = [yaw_about(m, pivot, -max_deg + 2 * max_deg * i / k) for i in range(k + 1)]
    return Manifold.batch_hull(parts)


def drop_slivers(m: Manifold, min_volume: float = 1e-3) -> Manifold:
    """Remove zero-volume shells that booleans between nearly parallel
    faceted surfaces (e.g. groove walls on the cones) can leave behind.
    Real disconnected pieces are kept, so the check still reports them."""
    pieces = m.decompose()
    if len(pieces) == 1:
        return m
    keep = [q for q in pieces if abs(q.volume()) >= min_volume]
    return Manifold.compose(keep) if keep else m


def ellipsoid(center, radii, n: int) -> Manifold:
    return Manifold.sphere(1.0, n).scale(list(radii)).translate(list(center))


def slab_z(z0: float, z1: float, big: float = 400) -> Manifold:
    return Manifold.cube([big, big, z1 - z0]).translate([-big / 2, -big / 2, z0])


# ---------------------------------------------------------------------------
# part geometry
# ---------------------------------------------------------------------------

class Builder:
    def __init__(self, p: Params):
        self.p = p
        n = p.resolution
        self.n = n
        set_circular_segments(n)
        zc = p.zc
        self.Q = (0.0, 0.0, zc)
        self.Qb = (-p.pitch, 0.0, zc)
        back = 4 * max(p.width, p.height) + p.head_length

        # region every part's material must stay inside (front bullet)
        self.front = bullet(p.nose_radius, p.chevron_angle, back, n).translate(list(self.Q))

        # carve for the back of a part: next part's bullet + gap, swept by yaw
        b = bullet(p.nose_radius + p.gap, p.chevron_angle, back, n).translate(list(self.Qb))
        carve = swept_yaw(b, self.Qb, p.yaw)
        if p.bottom_gap > p.gap:
            bb = bullet(p.nose_radius + p.bottom_gap, p.chevron_angle, back, n).translate(list(self.Qb))
            carve = carve + (swept_yaw(bb, self.Qb, p.yaw) ^ slab_z(-1, p.bottom_gap_height))
        self.back_carve = carve

        # socket in the front of a part for the previous part's ball
        cav = pointed_ball(p.ball_radius + p.clearance, n).translate(list(self.Q))
        slot_len = p.nose_radius + p.gap + 3
        slot = x_cylinder(0, slot_len, p.neck_radius + p.clearance, n).translate(list(self.Q))
        self.socket = cav + swept_yaw(slot, self.Q, p.yaw)

        # ball + neck on the back of a part
        neck_end = -p.pitch + p.nose_radius + p.gap + 0.5
        self.ball = (pointed_ball(p.ball_radius, n).translate(list(self.Qb))
                     + x_cylinder(-p.pitch, neck_end, p.neck_radius, n).translate([0, 0, zc]))

        self.envelope = self._envelope(back)

    # cross-section of the body (y, z), extruded along x
    def _section(self, inset: float = 0.0) -> CrossSection:
        p = self.p
        hw = p.width / 2
        pts = []
        for i in range(self.n + 1):
            t = math.pi * i / self.n
            pts.append((hw * math.cos(t), p.leg_height + (p.height - p.leg_height) * math.sin(t)))
        dome = CrossSection([pts])
        li, lo, fl, pad = p.foot_gap / 2, hw, p.foot_flare, p.foot_pad
        top = p.leg_height + 1.0
        leg = [(li, 0), (lo + fl, 0), (lo + fl, pad), (lo, pad + fl), (lo, top), (li, top)]
        legs = CrossSection([leg]) + CrossSection([[(-y, z) for (y, z) in reversed(leg)]])
        sec = dome + legs
        if inset:
            sec = sec.offset(-inset, join_type=JoinType.Round)
        return sec

    def _extrude_x(self, sec: CrossSection, x0: float, x1: float) -> Manifold:
        # extrude along z, then map (u, v, w) -> (x=w, y=u, z=v)
        m = sec.extrude(x1 - x0)
        return m.transform([[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0]])

    def _envelope(self, back: float) -> Manifold:
        return self._extrude_x(self._section(), -back, self.p.head_length + 10)

    def envelope_inset(self, inset: float) -> Manifold:
        back = 4 * max(self.p.width, self.p.height) + self.p.head_length
        return self._extrude_x(self._section(inset), -back, self.p.head_length + 10)

    def ears(self, x: float) -> Manifold:
        p = self.p
        return Manifold.cylinder(p.ear_thickness, p.ear_radius, p.ear_radius, self.n * 2).translate([x, 0, 0])

    # parts ------------------------------------------------------------------
    def body(self, index: int) -> Manifold:
        m = (self.envelope ^ self.front) - self.back_carve - self.socket
        m = textures.apply(self.p.texture, m, self, "body", index)
        return drop_slivers(m + self.ball)

    def head(self) -> Manifold:
        p = self.p
        hw = p.width / 2 + p.foot_flare + 0.5
        ell = ellipsoid((-p.pitch, 0, p.height * 0.35), (p.head_length, hw, p.height * 0.68), self.n)
        m = self.envelope ^ ell
        tip = p.head_length - p.pitch
        if p.mouse_ears:
            m = m + self.ears(tip - 2)
        add, sub = faces.build(p.face, self, tip)
        if add is not None:
            m = m + add
        if sub is not None:
            m = m - sub
        if p.face_mesh:
            m = m + faces.load_mesh(p.face_mesh, tip)
        if p.face_cut:
            m = m - faces.load_mesh(p.face_cut, tip)
        m = m - self.back_carve
        m = textures.apply(p.texture, m, self, "head", 0)
        return drop_slivers(m + self.ball)

    def tail(self) -> Manifold:
        p = self.p
        hw = p.width / 2 + p.foot_flare + 0.5
        ell = ellipsoid((0, 0, p.height * 0.35), (p.tail_length, hw, p.height * 0.68), self.n)
        m = self.envelope ^ ell
        if p.mouse_ears:
            m = m + self.ears(-p.tail_length + 2)
        m = (m ^ self.front) - self.socket
        return drop_slivers(textures.apply(p.texture, m, self, "tail", p.segments + 1))


# ---------------------------------------------------------------------------
# assembly / checks / output
# ---------------------------------------------------------------------------

def to_trimesh(m: Manifold):
    import trimesh
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False)


def build(p: Params) -> tuple[list[Manifold], dict]:
    errs = p.validate()
    if errs:
        raise SystemExit("Parameter problems:\n  - " + "\n  - ".join(errs))
    t0 = time.time()
    b = Builder(p)
    body = b.body(1)
    textured_per_segment = textures.varies(p.texture)
    local = [b.head()]
    for i in range(1, p.segments + 1):
        local.append(b.body(i) if textured_per_segment else body)
    local.append(b.tail())

    frames, info = layouts.frames(p)
    parts = [m.transform(f) for m, f in zip(local, frames)]

    # drop to the bed and center
    lo = np.min([q.bounding_box()[:3] for q in parts], axis=0)
    hi = np.max([q.bounding_box()[3:] for q in parts], axis=0)
    shift = [-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]]
    parts = [q.translate(shift) for q in parts]
    info["size_mm"] = [round(float(v), 1) for v in (hi - lo)]
    info["build_s"] = round(time.time() - t0, 1)
    return parts, info


def check(parts: list[Manifold], p: Params) -> list[str]:
    """Every part one solid; every pair of nearby parts separated."""
    problems = []
    need = min(p.clearance, p.gap) * 0.8
    boxes = [np.array(q.bounding_box()) for q in parts]
    for i, q in enumerate(parts):
        if len(q.decompose()) != 1:
            problems.append(f"part {i} is not a single solid ({len(q.decompose())} pieces)")
    for i in range(len(parts)):
        for j in range(i + 1, len(parts)):
            a, c = boxes[i], boxes[j]
            if np.any(a[:3] > c[3:] + 1) or np.any(c[:3] > a[3:] + 1):
                continue
            g = parts[i].min_gap(parts[j], 1.0)
            if g < need:
                problems.append(f"parts {i} and {j}: gap {g:.3f} mm < {need:.2f}")
    return problems


def default_name(p: Params) -> str:
    s = f"millipede-{p.segments}seg-{p.layout}"
    if p.face != "eyes":
        s += f"-{p.face}"
    if p.face_mesh or p.face_cut:
        s += "-" + Path(p.face_mesh or p.face_cut).stem
    if p.texture != "none":
        s += f"-{p.texture}"
    return s


def parse_params(argv=None, description=None) -> Params:
    """Command line (+ optional --config JSON) -> Params."""
    ap = argparse.ArgumentParser(description=description or __doc__.split("\n\n")[0],
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("--config", help="JSON file with parameter values (command line wins)")
    defaults = Params()
    for f in dataclasses.fields(Params):
        v = getattr(defaults, f.name)
        flag = "--" + f.name.replace("_", "-")
        if isinstance(v, bool):
            ap.add_argument(flag, action=argparse.BooleanOptionalAction, default=None, help=f"(default {v})")
        else:
            ap.add_argument(flag, type=type(v), default=None, help=f"(default {v})")
    args = ap.parse_args(argv)

    values = {}
    if args.config:
        values.update(json.loads(Path(args.config).read_text()))
    for f in dataclasses.fields(Params):
        v = getattr(args, f.name)
        if v is not None:
            values[f.name] = v
    p = Params(**values)
    if p.face not in faces.FACES:
        raise SystemExit(f"unknown face {p.face!r}; choose from {', '.join(faces.FACES)}")
    if p.texture not in textures.TEXTURES:
        raise SystemExit(f"unknown texture {p.texture!r}; choose from {', '.join(textures.TEXTURES)}")
    for path in (p.face_mesh, p.face_cut):
        if path and not Path(path).is_file():
            raise SystemExit(f"face mesh not found: {path}")
    return p


def main(argv=None):
    p = parse_params(argv)
    parts, info = build(p)
    print(f"built {len(parts)} parts in {info['build_s']} s; size {info['size_mm']} mm")
    for k in ("max_bend_deg", "spiral_inner_radius"):
        if k in info:
            print(f"  {k}: {info[k]}")

    if p.check:
        probs = check(parts, p)
        print("check: OK" if not probs else "check FAILED:\n  " + "\n  ".join(probs))

    out = Path(p.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = p.name or default_name(p)
    import trimesh
    mesh = trimesh.util.concatenate([to_trimesh(q) for q in parts])
    mesh.export(out / f"{stem}.3mf")
    if p.stl:
        mesh.export(out / f"{stem}.stl")
    (out / f"{stem}.json").write_text(json.dumps(dataclasses.asdict(p), indent=2) + "\n")
    print(f"wrote {out / (stem + '.3mf')}")
    if p.preview:
        import preview
        preview.render(mesh, out / f"{stem}.png")
        print(f"wrote {out / (stem + '.png')}")


if __name__ == "__main__":
    main()
