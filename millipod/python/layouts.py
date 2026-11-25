"""Where the parts go on the bed.

A layout produces joint points Q_0 .. Q_{S+2} in the XY plane (Q_k is the
front joint of part k; part 0 is the head, part S+1 the tail, Q_{S+2} only
orients the tail). Consecutive points must be exactly `pitch` apart and the
bend between consecutive parts must stay within the joint's yaw range.
Each part's local +x axis points from its back joint to its front joint.
"""
from __future__ import annotations

import math

import numpy as np


def _frames_from_joints(Q: np.ndarray) -> list[list[list[float]]]:
    frames = []
    for k in range(len(Q) - 1):
        u = Q[k] - Q[k + 1]
        u = u / np.linalg.norm(u)
        frames.append([[u[0], -u[1], 0.0, Q[k][0]],
                       [u[1], u[0], 0.0, Q[k][1]],
                       [0.0, 0.0, 1.0, 0.0]])
    return frames


def _bends(Q: np.ndarray) -> np.ndarray:
    d = Q[:-1] - Q[1:]
    ang = np.arctan2(d[:, 1], d[:, 0])
    return np.degrees(np.abs((np.diff(ang) + np.pi) % (2 * np.pi) - np.pi))


def line(p) -> np.ndarray:
    n = p.segments + 3
    return np.array([[-k * p.pitch, 0.0] for k in range(n)])


def _walk_chords(poly: np.ndarray, step: float, count: int) -> np.ndarray:
    """Points along a polyline, each exactly `step` (straight-line) from the last."""
    pts = [poly[0]]
    i = 0
    cur = poly[0]
    while len(pts) < count:
        while i < len(poly) - 1 and np.linalg.norm(poly[i + 1] - cur) < step:
            i += 1
        if i >= len(poly) - 1:
            raise ValueError("polyline too short")
        # intersect circle(cur, step) with segment poly[i] -> poly[i+1]
        a, b = poly[i], poly[i + 1]
        d = b - a
        f = a - cur
        A, B, C = d @ d, 2 * f @ d, f @ f - step * step
        t = (-B + math.sqrt(max(B * B - 4 * A * C, 0))) / (2 * A)
        cur = a + t * d
        pts.append(cur)
    return np.array(pts)


def spiral(p) -> tuple[np.ndarray, float]:
    """Archimedean spiral, tail in the middle, head outside."""
    n = p.segments + 3
    turn = p.width + 2 * p.foot_flare + p.spiral_turn_gap
    b = turn / (2 * math.pi)
    max_bend = p.yaw * p.spiral_bend_fraction
    r0 = p.spiral_inner_radius or p.pitch / (2 * math.sin(math.radians(max_bend) / 2))
    for _ in range(50):
        length = n * p.pitch * 1.2 + 50
        # theta range long enough: arc length ~ r0*t + b t^2 / 2
        tmax = (-r0 + math.sqrt(r0 * r0 + 2 * b * length)) / b
        t = np.linspace(0, tmax, int(tmax * 2000) + 10)
        r = r0 + b * t
        poly = np.stack([r * np.cos(t), r * np.sin(t)], axis=1)
        J = _walk_chords(poly, p.pitch, n)
        Q = J[::-1].copy()  # head (outermost) first
        if p.spiral_inner_radius or _bends(Q).max() <= max_bend + 1e-6:
            return Q, r0
        r0 *= 1.03
    raise RuntimeError("could not fit spiral")


def frames(p):
    info = {}
    if p.layout == "line":
        Q = line(p)
    elif p.layout == "spiral":
        Q, r0 = spiral(p)
        info["spiral_inner_radius"] = round(r0, 1)
    else:
        raise SystemExit(f"unknown layout {p.layout!r} (line | spiral)")
    bends = _bends(Q)
    info["max_bend_deg"] = round(float(bends.max()), 1) if len(bends) else 0.0
    if bends.max() > p.yaw:
        raise SystemExit(f"layout bends a joint {bends.max():.1f} deg, more than yaw={p.yaw}")
    return _frames_from_joints(Q), info
