# Dowel length stop for a Gartol miter shear.
# Caps the outer end of the right-hand fence (set at 90 deg) and puts a stop
# face STOP_DIST from the blade.
#
# Run:  /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd dowel-stop-cap.py
#
# Coordinates (as mounted): X runs along the fence away from the blade (blade
# face at X=0). Y=0 is the fence face the dowel rests against (+Y is the dowel
# side, toward the blade tip). Z=0 is the plate top where the fence and dowel sit.

import math
import os
import FreeCAD as App
import Part
import Mesh

# ---- parameters (mm) -------------------------------------------------------
STOP_DIST = 63.5     # blade face -> stop face (2.5")
FENCE_LEN = 50.8     # blade face -> end of fence (measured 2")
FENCE_W = 10.0       # fence width (Y)
FENCE_H = 12.2       # fence height (Z)
DOWEL_D = 6.0
CLR = 0.15           # clearance per side on the fence
SLEEVE = 16.0        # how much of the fence end the cap covers
TOP_T = 3.0          # top plate thickness
BACK_T = 6.0         # back wall (holds the M3 nut)
FRONT_T = 2.5        # front wall hanging over the dowel
FRONT_GAP = 2.0      # space between dowel top and front wall underside
END_T = 3.0          # end wall that butts the fence end
STOP_T = 5.0         # stop block thickness
WALL_Z = 3.5         # walls and the stop body end this high above the deck
STOP_Z = 1.0         # only the stop finger in the dowel's path goes lower, to here
STOP_REACH = 1.5     # how far the stop finger reaches past the dowel's far side
SCREW_Z = 8.0        # clamp screw height (raised so the nut clears the short wall)
RIB_H = 0.5          # crush ribs on the back wall's inner face (interference = RIB_H - CLR)
RIB_W = 1.2
M3_HOLE = 3.3
M3_NUT_AF = 5.7      # across flats incl. clearance
M3_NUT_T = 2.7       # nut thickness incl. clearance

NAME = "dowel-stop-cap"
out_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else os.getcwd()
V = App.Vector


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


x0 = FENCE_LEN - SLEEVE
x_stop1 = STOP_DIST + STOP_T
y_back_in = -FENCE_W - CLR
y_back = y_back_in - BACK_T
y_front_in = CLR
y_stop = DOWEL_D + STOP_REACH
z_top_in = FENCE_H + 0.2
z_top = z_top_in + TOP_T

parts = [
    # top plate, from sleeve start to the stop, covering fence + front wall
    box(x0, x_stop1, y_back, y_front_in + FRONT_T, z_top_in, z_top),
    # back wall, full length; short, so it stays well clear of the deck
    box(x0, x_stop1, y_back, y_back_in, WALL_Z, z_top_in),
    # front wall above the dowel
    box(x0, STOP_DIST, y_front_in, y_front_in + FRONT_T, DOWEL_D + FRONT_GAP, z_top_in),
    # end wall registers against the fence end (fence side only, dowel path clear)
    box(FENCE_LEN + CLR, FENCE_LEN + CLR + END_T, y_back_in, -0.2, WALL_Z, z_top_in),
    # stop block body, same height as the walls...
    box(STOP_DIST, x_stop1, y_back, y_stop, WALL_Z, z_top),
    # ...plus a finger dropping into the dowel's path only
    box(STOP_DIST, x_stop1, -0.5, y_stop, STOP_Z, WALL_Z),
]
body = parts[0]
# vertical crush ribs on the back wall's inner face, either side of the screw
for rx in (x0 + 2.5, FENCE_LEN - 2.5):
    parts.append(box(rx - RIB_W / 2, rx + RIB_W / 2, y_back_in, y_back_in + RIB_H, WALL_Z, z_top_in))
for p in parts[1:]:
    body = body.fuse(p)

# M3 set screw through the back wall pushes the fence against the front wall.
# The nut drops into a slot from the top and is walled in on both faces, so
# the screw's reaction load bears on the outer skin of the back wall.
sx, sz = x0 + SLEEVE / 2, SCREW_Z
hole = Part.makeCylinder(M3_HOLE / 2, BACK_T + 2, V(sx, y_back - 1, sz), V(0, 1, 0))
ny0 = y_back + (BACK_T - M3_NUT_T) / 2
r = M3_NUT_AF / math.sqrt(3)
pts = [V(sx + r * math.cos(math.radians(a)), ny0, sz + r * math.sin(math.radians(a)))
       for a in range(30, 391, 60)]  # points up/down, flats facing the slot walls
nut = Part.Face(Part.makePolygon(pts)).extrude(V(0, M3_NUT_T, 0))
nut = nut.fuse(box(sx - M3_NUT_AF / 2, sx + M3_NUT_AF / 2, ny0, ny0 + M3_NUT_T, sz, z_top + 1))
body = body.cut(hole).cut(nut).removeSplitter()

doc = App.newDocument("dowel_stop_cap")
f = doc.addObject("Part::Feature", "DowelStopCap")
f.Shape = body
doc.recompute()
doc.saveAs(os.path.join(out_dir, NAME + ".FCStd"))

# print orientation: flip so the top plate is on the bed
m = App.Matrix()
m.rotateX(math.pi)
printed = body.transformGeometry(m)
bb = printed.BoundBox
printed.translate(V(-bb.XMin, -bb.YMin, -bb.ZMin))
mesh = Mesh.Mesh(printed.tessellate(0.02))
mesh.write(os.path.join(out_dir, NAME + ".3mf"))
print("volume mm3:", round(body.Volume, 1), "valid:", body.isValid(), "solids:", len(body.Solids))
