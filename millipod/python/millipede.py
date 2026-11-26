#!/usr/bin/env python3
"""Parametric print-in-place millipede.

Every part (head, N body segments, tail) is a separate solid. Adjacent parts
are linked by a captive joint and nest like stacked lampshades:

* Each part's front is a "bullet" around its front joint Q: a sphere of radius
  `nose_radius` plus the cone tangent to it (half-angle `chevron_angle`).
  Everything belonging to that part lies inside its own bullet.
* The back of each part is carved by the *next* part's bullet, grown by `gap`
  and swept through +/-`yaw` sideways and through `drape` (down) / `arch` (up)
  about the joint. Since the next part never leaves its own bullet, the two
  parts cannot collide anywhere inside that range.
* The joint (joints.py) links each part to the one behind it: a sideways
  hinge pin (default), two interlocking rings, or a captive ball. Each joint
  type says how far it bends; the shells are carved to match.

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
import joints
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
    chevron_angle: float = 45.0  # cone half-angle of the nested shells (deg, >=45 prints cleanly)
    side_angle: float = 25.0     # shell half-angle at the sides above the feet (no overhang there): smaller sweeps back further. 0 = chevron_angle

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
    joint: str = "hinge"         # see joints.py: hinge, rings or ball
    pin_radius: float = 0.75     # hinge/rings: the sideways bar (it also has a pointed underside)
    drape: float = 12.0          # hinge/rings: downward bend allowed per joint (deg), e.g. over a finger
    arch: float = 6.0            # hinge/rings: upward bend allowed per joint (deg)
    twist: float = 15.0          # rings: twist allowed per joint about the body's length (deg)
    ring_width: float = 2.4      # rings: width of the upright ring at the front of each part
    ring_slack: float = 0.0      # rings: extra play in every direction (mm)
    side_wall: float = 1.2       # hinge/rings: solid wall kept outside the bar ends, hiding the joint
    joint_height: float = 0.0    # 0 = auto (hinge/rings: leg_height + 2.5; ball: middle of the dome)

    # --- head / tail / decoration ----------------------------------------
    head_length: float = 11.0    # from the first joint behind the head to its tip
    head_groove: float = 4.5     # 45 deg groove under the head: this tall, 2x as wide at the bed
                                 # (smaller feet = easier to remove; 0 = flat-bottomed head)
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
    def joint_type(self) -> joints.Joint:
        return joints.get(self.joint)

    @property
    def nose_radius(self) -> float:
        return self.joint_type.nose_radius(self)

    @property
    def zc(self) -> float:
        return self.joint_height or self.joint_type.default_height(self)

    @property
    def bend_down_up(self) -> tuple[float, float]:
        return self.joint_type.bends(self)

    def validate(self) -> list[str]:
        """Return a list of problems; empty means OK."""
        errs = []
        if self.joint not in joints.JOINTS:
            return [f"unknown joint {self.joint!r}; choose from {', '.join(joints.JOINTS)}"]
        errs += self.joint_type.validate(self)
        if self.chevron_angle < 45:
            errs.append("chevron_angle < 45 deg will leave overhangs under the shells")
        if self.foot_gap / 2 >= self.width / 2 - 1:
            errs.append("foot_gap too large for width")
        groove_max = self.joint_type.max_head_groove(self)
        if self.head_groove > groove_max:
            errs.append(f"head_groove reaches the joint: keep it <= {groove_max:.1f}")
        if self.head_groove >= self.width / 2 + self.foot_flare - 0.8:
            errs.append("head_groove is wider than the head's feet")
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


def shell_angle(psi: float, top: float, side: float) -> float:
    """Half-angle (deg) of the shell cone in the direction psi (radians, 0 =
    the +/-y side, +pi/2 = up). The top uses `top` (an overhang, so >=45);
    the upper sides blend to `side` along an ellipse; below the joint the
    angle returns to `top` by 45 deg down, so the feet stay thick."""
    if not side or side == top:
        return top
    c, s = abs(math.cos(psi)), math.sin(psi)
    if s >= 0:
        ty, tz = math.tan(math.radians(side)), math.tan(math.radians(top))
        return math.degrees(math.atan(ty * tz / math.hypot(tz * c, ty * s)))
    t = min(1.0, math.degrees(math.asin(-s)) / 45.0)
    return side + (top - side) * t * t * (3 - 2 * t)


def bullet(r: float, half_angle_deg: float, back: float, n: int,
           side_angle_deg: float = 0.0) -> Manifold:
    """Sphere of radius r at the origin plus the cone tangent to it that opens
    toward -x with the given half-angle, truncated at x = -back. With
    side_angle_deg the cone sweeps back further at the sides (shell_angle)."""
    if not side_angle_deg or side_angle_deg == half_angle_deg:
        phi = math.radians(half_angle_deg)
        rad = (r / math.sin(phi) + back) * math.tan(phi)
        disk = Manifold.cylinder(0.01, rad, rad, n * 2, True).rotate([0, 90, 0]).translate([-back, 0, 0])
        return Manifold.batch_hull([Manifold.sphere(r, n), disk])
    pts = []
    for k in range(4 * n):
        psi = 2 * math.pi * k / (4 * n)
        phi = math.radians(shell_angle(psi, half_angle_deg, side_angle_deg))
        rad = (r / math.sin(phi) + back) * math.tan(phi)
        pts.append((rad * math.cos(psi), rad * math.sin(psi)))
    disk = CrossSection([pts]).extrude(0.01).transform([[0, 0, 1, -back], [1, 0, 0, 0], [0, 1, 0, 0]])
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


def rotate_about(m: Manifold, pivot, yaw: float, pitch: float) -> Manifold:
    """Pitch about the y axis, then yaw about the z axis, both through pivot.
    Negative pitch lowers whatever is behind the pivot (-x)."""
    px, py, pz = pivot
    return m.translate([-px, -py, -pz]).rotate([0, pitch, 0]).rotate([0, 0, yaw]).translate([px, py, pz])


def swept(m: Manifold, pivot, yaw: float, down: float, up: float, step: float = 2.0) -> Manifold:
    """Like swept_yaw, but also tilting the part behind the pivot from `down`
    degrees down to `up` degrees up."""
    if not down and not up:
        return swept_yaw(m, pivot, yaw)
    ky = max(1, math.ceil(2 * yaw / step))
    kp = max(1, math.ceil((down + up) / step))
    return Manifold.batch_hull([
        rotate_about(m, pivot, -yaw + 2 * yaw * i / ky, -down + (down + up) * j / kp)
        for i in range(ky + 1) for j in range(kp + 1)])


def y_rod(r: float, length: float, n: int, point_down: float = 0.0, roof: float = 0.0) -> Manifold:
    """Round rod along +y from y=0 to y=length, axis through the origin.
    point_down / roof: 45 degree point below / above the rod at this distance
    from the axis (0 = none); the roof is cut flat at 1.2 x r."""
    rod = Manifold.cylinder(length, r, r, n).rotate([-90, 0, 0])
    line = Manifold.cube([0.001, length, 0.001])
    if point_down:
        rod = Manifold.batch_hull([rod, line.translate([0, 0, -point_down])])
    if roof:
        rod = Manifold.batch_hull([rod, line.translate([0, 0, roof])]) ^ slab_z(-100, 1.2 * r)
    return rod


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
        self.front = bullet(p.nose_radius, p.chevron_angle, back, n, p.side_angle).translate(list(self.Q))

        # carve for the back of a part: next part's bullet + gap, swept through
        # the joint's range of motion. Tilting a long cone sweeps a huge
        # volume, so only the part near the joint is swept; far behind, the
        # unswept cone covers the rest.
        down, up = p.bend_down_up
        near = 3 * p.pitch + max(p.width, p.height)

        def sweep_cup(grow):
            short = bullet(p.nose_radius + grow, p.chevron_angle, near, n, p.side_angle).translate(list(self.Qb))
            whole = bullet(p.nose_radius + grow, p.chevron_angle, back, n, p.side_angle).translate(list(self.Qb))
            return swept(short, self.Qb, p.yaw, down, up) + swept_yaw(whole, self.Qb, p.yaw)

        slack = p.joint_type.slack(p)
        carve = sweep_cup(p.gap + slack)
        if p.bottom_gap > p.gap:
            carve = carve + (sweep_cup(p.bottom_gap + slack) ^ slab_z(-1, p.bottom_gap_height))
        self.back_carve = carve

        self.envelope = self._envelope(back)
        self.socket = p.joint_type.socket(self)  # cut from the front of every part
        self.link = p.joint_type.link(self)      # added at the back of every part

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

    def groove(self, h: float) -> Manifold:
        """A-frame groove along x on the centre line: h tall, 45 deg sides."""
        if h <= 0:
            return Manifold()
        w = h + 5
        cs = CrossSection([[(-w, -5), (w, -5), (0, h)]])
        return self._extrude_x(cs, -100, 100)

    # parts ------------------------------------------------------------------
    def body(self, index: int) -> Manifold:
        m = (self.envelope ^ self.front) - self.back_carve - self.socket
        m = textures.apply(self.p.texture, m, self, "body", index)
        return drop_slivers(m + self.link)

    def head(self) -> Manifold:
        p = self.p
        hw = p.width / 2 + p.foot_flare + 0.5
        ell = ellipsoid((-p.pitch, 0, p.height * 0.35), (p.head_length, hw, p.height * 0.68), self.n)
        m = (self.envelope ^ ell) - self.groove(p.head_groove)
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
        return drop_slivers(m + self.link)

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
    # one object named after the file (trimesh would call it "geometry_0")
    scene = trimesh.Scene()
    scene.add_geometry(mesh, node_name=stem, geom_name=stem)
    scene.export(out / f"{stem}.3mf")
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
