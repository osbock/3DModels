"""Joints between neighbouring parts.

Every part's front joint is at Q = (0, 0, zc) in its local frame and its back
joint at Qb = (-pitch, 0, zc) (see millipede.py). A joint type supplies:

* socket(b): what to cut from the front of every part (around Q), for the
  part in front of it to hook into
* link(b):   what to add at the back of every part (around Qb), which hooks
  into the socket of the part behind it
* nose_radius(p): radius of the sphere at the front of every part that must
  hold the socket (the shells are built around it)
* bends(p): (down, up) degrees the part behind may tilt, which the shells
  are carved to allow; yaw (sideways) comes from p.yaw for every joint
* slack(p): how far the part behind can shift (mm), which the shells allow too
* validate(p): problems with the parameters, as a list of messages

To add a joint: subclass Joint, register it in JOINTS. The check in
millipede.py makes sure the parts come out separate solids.
"""
from __future__ import annotations

import math

from manifold3d import Manifold

SQ2 = math.sqrt(2)


def _mp():
    import millipede
    return millipede


class Joint:
    name = ""
    help = ""

    def nose_radius(self, p) -> float:
        raise NotImplementedError

    def default_height(self, p) -> float:
        return p.leg_height + 2.5

    def bends(self, p) -> tuple[float, float]:
        return (p.drape, p.arch)

    def slack(self, p) -> float:
        return 0.0

    def max_head_groove(self, p) -> float:
        return p.zc - 1.0

    def validate(self, p) -> list[str]:
        return []

    def socket(self, b) -> Manifold:
        raise NotImplementedError

    def link(self, b) -> Manifold:
        raise NotImplementedError


def _fit_vertically(p, name) -> list[str]:
    if p.zc - p.nose_radius < 1.0 or p.zc + p.nose_radius > p.height - 1.5:
        return [f"{name} does not fit vertically: check joint_height / height"]
    return []


def _bend_limits(p) -> list[str]:
    if not 0 <= p.drape <= 30 or not 0 <= p.arch <= 30:
        return ["drape and arch must be between 0 and 30 degrees"]
    return []


class Hinge(Joint):
    """A sideways pin across the cup at the back of each part, through a hole
    in the next part's nose. Bends freely down/up about the pin; the hole fans
    out towards its ends for +/-yaw."""
    name = "hinge"
    help = "bends sideways, down and up"

    def hole_radius(self, p) -> float:
        # the pin's pointed underside sweeps a circle of radius pin_radius*sqrt2
        return p.pin_radius * SQ2 + p.clearance + self.slack(p)

    def nose_radius(self, p) -> float:
        return self.hole_radius(p) + p.nose_wall

    def validate(self, p) -> list[str]:
        errs = []
        back_wall = p.pitch - p.nose_radius - p.gap - self.slack(p) - self.hole_radius(p)
        if back_wall < 0.6:
            errs.append(
                f"wall between a pin hole and the cup behind it is {back_wall:.2f} mm (<0.6): "
                "increase pitch or reduce pin_radius / nose_wall / gap" +
                (" / ring_slack" if self.slack(p) else ""))
        if p.pin_radius < 0.5:
            errs.append("pin_radius below 0.5 mm will be too weak")
        return errs + _fit_vertically(p, self.name) + _bend_limits(p)

    def _hole_half(self, b, roll: float = 0.0) -> Manifold:
        """Hole along +y from the joint outwards, fanned by yaw (and roll)."""
        mp = _mp()
        p = b.p
        rh = self.hole_radius(p)
        half = mp.y_rod(rh, p.width, b.n, roof=rh * SQ2)
        if not roll:
            return mp.swept_yaw(half, (0, 0, 0), p.yaw)
        step = 2.0
        ky, kr = max(1, math.ceil(2 * p.yaw / step)), max(1, math.ceil(2 * roll / step))
        return Manifold.batch_hull([
            half.rotate([-roll + 2 * roll * j / kr, 0, 0]).rotate([0, 0, -p.yaw + 2 * p.yaw * i / ky])
            for i in range(ky + 1) for j in range(kr + 1)])

    def roll(self, p) -> float:
        return 0.0

    def _anchor(self, b, grow: float = 0.0) -> Manifold:
        """Block joining one end (+y) of the pin to the side wall in front of
        it, in the frame of the part that owns the pin, centred on its back
        joint. Pointed top and bottom so it prints and so does the notch the
        next part needs around it."""
        p = b.p
        y0 = p.nose_radius + p.gap + 0.3 - grow
        y1 = self._half_len(p) + grow
        x0, x1 = -0.6 - grow, 1.6 + grow
        h = p.pin_radius + 0.25 + grow
        tip = (x1 - x0) / 2
        box = Manifold.cube([x1 - x0, y1 - y0, 2 * h]).translate([x0, y0, -h])
        line = Manifold.cube([0.001, y1 - y0, 0.001]).translate([(x0 + x1) / 2, y0, 0])
        return Manifold.batch_hull([box, line.translate([0, 0, h + tip]),
                                    line.translate([0, 0, -h - tip])])

    def _notch_half(self, b) -> Manifold:
        """Space the part behind must leave for the anchor block while it
        moves: the block (grown by the gap) swept through the joint's range,
        seen from that part (so the motion is inverted)."""
        p = b.p
        a = self._anchor(b, grow=p.gap + self.slack(p))
        down, up = self.bends(p)
        rl = self.roll(p)
        step = 3.0
        ky = max(1, math.ceil(2 * p.yaw / step))
        kp = max(1, math.ceil((down + up) / step))
        kr = max(1, math.ceil(2 * rl / step)) if rl else 0
        copies = []
        for i in range(ky + 1):
            for j in range(kp + 1):
                for k in range(kr + 1):
                    r = -rl + 2 * rl * k / kr if kr else 0.0
                    copies.append(a.rotate([r, -up + (down + up) * j / kp, 0])
                                   .rotate([0, 0, -p.yaw + 2 * p.yaw * i / ky]))
        return Manifold.batch_hull(copies)

    def socket(self, b) -> Manifold:
        p = b.p
        half = self._hole_half(b, roll=self.roll(p)) + self._notch_half(b)
        # keep the outside of the part solid: the hole and notches stop short
        # of the surface, so the bar ends can't be seen
        keep = b.envelope_inset(max(p.side_wall - p.gap, 0.4))
        return (half + half.mirror([0, 1, 0])).translate(list(b.Q)) ^ keep

    def _half_len(self, p) -> float:
        a, c = p.width / 2, p.height - p.leg_height  # domed top: half-ellipse
        z_top = min(max(p.zc + p.pin_radius + 0.25 - p.leg_height, 0.0), c)
        return a * math.sqrt(1 - (z_top / c) ** 2) - p.side_wall

    def link(self, b) -> Manifold:
        """Pin across the cup, with a block at each end joining it to the side
        wall in front (right behind the cup the walls are too thin to hold it)."""
        mp = _mp()
        p = b.p
        half_len = self._half_len(p)
        pin = mp.y_rod(p.pin_radius, 2 * half_len, b.n, point_down=p.pin_radius * SQ2).translate([0, -half_len, 0])
        a = self._anchor(b)
        pin = pin + a + a.mirror([0, 1, 0])
        # stay inside the part's own front shell, which at the sides (with a
        # small side_angle) is further back than the pin ends
        return pin.translate(list(b.Qb)) ^ b.envelope ^ b.front


class Rings(Hinge):
    """Two interlocking D rings, like chain links. The sideways bar across the
    cup and the part's side walls form a horizontal ring; the next part's nose
    is cut down to a thin upright ring (ring_width wide) around that bar. The
    narrow ring lets the part behind twist about its length as well as bend
    down/up and sideways, and ring_slack lets it rattle a little."""
    name = "rings"
    help = "like hinge, plus twist and a little rattle"

    def slack(self, p) -> float:
        return p.ring_slack

    def roll(self, p) -> float:
        return p.twist

    def validate(self, p) -> list[str]:
        errs = super().validate(p)
        if not 0 <= p.twist <= 30:
            errs.append("twist must be between 0 and 30 degrees")
        if p.ring_width < 1.2:
            errs.append("ring_width below 1.2 mm will be too weak")
        return errs

    def socket(self, b) -> Manifold:
        p = b.p
        hole = super().socket(b).translate([-c for c in b.Q])
        # cut the sides of the nose away, leaving an upright ring
        big = 4 * (p.width + p.height)
        sides = Manifold.cube([big, big, big], True).translate([0, big / 2 + p.ring_width / 2, 0])
        sides = sides + sides.mirror([0, 1, 0])
        nose = Manifold.sphere(p.nose_radius + 0.01, b.n) ^ sides
        return (hole + nose).translate(list(b.Q))


class Ball(Joint):
    """Ball at mid-height in a cavity in the next part's nose, reached through
    a fan-shaped slot thinner than the ball. Turns sideways only."""
    name = "ball"
    help = "sideways only (the first version)"

    def nose_radius(self, p) -> float:
        return p.ball_radius + p.clearance + p.nose_wall

    def default_height(self, p) -> float:
        return (p.leg_height + p.height) / 2

    def bends(self, p) -> tuple[float, float]:
        return (0.0, 0.0)

    def max_head_groove(self, p) -> float:
        return p.zc - p.nose_radius

    def validate(self, p) -> list[str]:
        errs = []
        back_wall = p.pitch - p.nose_radius - p.gap - p.ball_radius - p.clearance
        if back_wall < 0.6:
            errs.append(
                f"wall between a cavity and the cup behind it is {back_wall:.2f} mm (<0.6): "
                "increase pitch or reduce ball_radius / nose_wall / gap")
        if p.neck_radius + p.clearance >= p.ball_radius - 0.15:
            errs.append("ball would not be captive: need neck_radius + clearance < ball_radius - 0.15")
        r = (p.ball_radius + p.clearance) * SQ2
        if p.zc + r > p.height - 1.0 or p.zc - r < 1.0:
            errs.append("ball cavity does not fit vertically: check joint_height / height")
        return errs

    def socket(self, b) -> Manifold:
        mp = _mp()
        p = b.p
        cav = mp.pointed_ball(p.ball_radius + p.clearance, b.n).translate(list(b.Q))
        slot_len = p.nose_radius + p.gap + 3
        slot = mp.x_cylinder(0, slot_len, p.neck_radius + p.clearance, b.n).translate(list(b.Q))
        return cav + mp.swept_yaw(slot, b.Q, p.yaw)

    def link(self, b) -> Manifold:
        mp = _mp()
        p = b.p
        neck_end = -p.pitch + p.nose_radius + p.gap + 0.5
        return (mp.pointed_ball(p.ball_radius, b.n).translate(list(b.Qb))
                + mp.x_cylinder(-p.pitch, neck_end, p.neck_radius, b.n).translate([0, 0, p.zc]))


JOINTS: dict[str, Joint] = {j.name: j for j in (Hinge(), Rings(), Ball())}


def get(name: str) -> Joint:
    return JOINTS[name]
