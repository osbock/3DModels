"""Quick shaded PNG previews (top view + 3/4 view) with matplotlib."""
from __future__ import annotations

import numpy as np


def render(mesh, path, max_faces: int = 250_000):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    tris = mesh.triangles
    normals = mesh.face_normals
    if len(tris) > max_faces:
        idx = np.random.default_rng(0).choice(len(tris), max_faces, replace=False)
        tris, normals = tris[idx], normals[idx]
    light = np.array([0.4, -0.5, 0.75])
    light /= np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.clip(normals @ light, 0, 1)
    base = np.array([0.85, 0.45, 0.15])
    colors = np.clip(shade[:, None] * base, 0, 1)

    lo, hi = mesh.bounds
    size = hi - lo
    fig = plt.figure(figsize=(14, 7))
    for i, (elev, azim, title) in enumerate([(90, -90, "top"), (30, -60, "3/4")]):
        ax = fig.add_subplot(1, 2, i + 1, projection="3d")
        ax.add_collection3d(Poly3DCollection(tris, facecolors=colors, edgecolor="none"))
        ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_zlim(lo[2], hi[2])
        ax.set_box_aspect(tuple(size), zoom=0.95)
        ax.view_init(elev=elev, azim=azim)
        ax.set_title(f"{title}  ({hi[0]-lo[0]:.0f} x {hi[1]-lo[1]:.0f} x {hi[2]-lo[2]:.0f} mm)")
        ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
