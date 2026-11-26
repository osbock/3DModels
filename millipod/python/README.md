# Millipede: parametric print-in-place (Python + manifold3d)

Generates a print-in-place articulated millipede as a 3MF. Every part (head,
N body segments, tail) is a separate solid linked to its neighbours by a
captive joint (a hinge pin, two interlocking rings, or a ball), so it comes
off the bed already assembled. With the hinge or rings it bends sideways and
droops down (you can drape it over a finger).

![](images/spiral-60.png)

## Setup

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

## Usage

```bash
.venv/bin/python millipede.py                               # 26 segments, straight
.venv/bin/python millipede.py --segments 40
.venv/bin/python millipede.py --config presets/spiral.json  # 60 segments in a spiral
.venv/bin/python millipede.py --face googly --texture grooves --mouse-ears
.venv/bin/python millipede.py --help                        # every parameter
```

Output goes to `out/`: `<name>.3mf`, a `<name>.png` preview and a
`<name>.json` with the exact parameters used (pass it back with `--config` to
regenerate). Command-line flags override the config file. Each run checks that
every part is a single solid and that no two parts are closer than the
clearance; `--no-check` skips that.

## How it works

* **Nested chevron shells.** Each part's front is a "bullet" (a sphere around
  its front joint plus a cone tangent to it). The cone is 45° top and bottom,
  where it overhangs, but only `side_angle` (25°) at the sides, which nothing
  overhangs, so the sides of each shell sweep back over the next part like
  scales and hide the joint. Below the joint it returns to 45° so the feet
  stay thick. The back of each part is cut
  by the next part's bullet, grown by `gap` and swept through ±`yaw`
  sideways, `drape` degrees down and `arch` degrees up. A part can therefore
  move anywhere in that range without touching its neighbour, and the sloped
  faces are ≥45° so they print without supports.
* **Hinge joint** (`--joint hinge`, the default), 2.5 mm above the legs: each
  part has a sideways pin across the hollow at its back, with a solid block
  at each end buried in the part's swept-back sides. Both stop `side_wall`
  short of the surface, so nothing of the joint shows. The pin runs through a hole in the next
  part's nose, so that part swings freely up and down about it. The hole
  fans out towards its ends so the part can also turn ±`yaw` sideways, and
  the next part has notches at the sides of its nose so it moves clear of
  the blocks. The pin has a pointed underside; the hole, the blocks and the
  notches have pointed tops and bottoms, so nothing overhangs.
* **Interlocking rings** (`--joint rings`), like the links of a chain and the
  original model: the bar and its end blocks make a horizontal D ring at the
  back of each part, and the next part's nose is cut down to a thin upright
  ring (`ring_width`) around the bar. Compared with the hinge, the part
  behind can also twist about its length (±`twist`), so it feels floppier.
  `ring_slack` adds play in every direction (0 by default: 0.1 printed too
  loose).
* **Ball joint** (`--joint ball`, the first version): a ball at mid-height in
  a cavity in the next part's nose, reached through a fan-shaped slot thinner
  than the ball. It only turns sideways (`drape` and `arch` are ignored), so
  the millipede stays stiff when you try to bend it over a finger, but it
  has bigger feet (44 mm² per segment).
* **Feet.** Two flared pads per segment (`foot_gap`, `foot_flare`,
  `foot_pad`). Drooping brings the bottoms of neighbouring segments
  together, so the more `drape`, the shorter the feet: at the defaults each
  segment touches the bed with ~24 mm², a little less than the original
  26-vertebra model (~27 mm²; `--chevron-angle 50` gives 28). In the first
  `bottom_gap_height` mm the clearance between shells widens to `bottom_gap`
  so elephant's foot can't fuse neighbours. The head has a 45° groove
  underneath (`head_groove`) so it touches the bed with about the same area
  as a segment (36 mm² with the hinge or rings) and comes off as easily. `--mouse-ears` adds thin discs
  under the head and tail.
* **Layouts** (`layouts.py`) only supply joint points spaced `pitch` apart.
  The spiral is Archimedean, tail in the middle, and its inner radius is
  chosen so that no joint is bent more than `spiral_bend_fraction` × `yaw`.

## Trade-off: bending vs. feet

The more a joint can bend, the more material is carved from the feet. How
far it can bend sideways (`yaw`) also sets how tight a spiral can be.

| yaw | foot area / segment, hinge (ball) | tightest spiral radius |
|----:|----------------------------------:|-----------------------:|
| 12° (default) | 24 mm² (41) | 33 mm |
| 16° | 20 mm² (36) | 25 mm |
| 18° (spiral preset) | 18 mm² (34) | 22 mm |
| 20° | 16 mm² (31) | 20 mm |
| 25° | 12 mm² (25) | 16 mm |

Rings are the same as the hinge. Hinge, at yaw 12°:

| drape | foot area / segment | head |
|------:|--------------------:|-----:|
| 0° | 41 mm² | 43 mm² |
| 8° | 30 mm² | 38 mm² |
| 12° (default) | 24 mm² | 36 mm² |
| 16° | 19 mm² | 34 mm² |
| 20° | 15 mm² | 32 mm² |

12° per joint is plenty to drape it over a finger. With 26 joints it adds up
to far more than a full circle. `arch` (bending up) only carves the tops of
the shells, so it doesn't change the feet.

## Extending

* **Faces in code**: `faces.py`. A face returns `(add, subtract)` solids in
  head coordinates; register it in `FACES`. To make a mesh face permanent, add
  e.g. `FACES["robot"] = mesh_face("face_meshes/robot.stl", "face_meshes/robot_cut.stl")`.
  For faces designed in a CAD tool, see "Designing your own face" below.
* **Joints**: `joints.py`. A joint type is a class that says what to cut
  from the front of each part, what to add at its back, how big the nose
  must be and how far it bends; the shells are carved from that. Subclass
  `Joint` and register it in `JOINTS`. This is the place to start for other
  jointed creatures.
* **Textures**: `textures.py`. A texture takes a part and returns it modified
  (`grooves`, `spots` and `bumpy` are the examples). Keep cuts shallow and away from
  the front/back faces, joint and feet. Textures in `PER_SEGMENT` are rebuilt
  for every segment (e.g. random patterns); others are built once and reused.

## Faces (`--face`)

| option | what it is |
|---|---|
| `eyes` (default) | two domed eyes (1.8 mm radius) on the front of the head, each with a dimple pupil |
| `googly` | bigger domed eyes (2.4 mm), set a little closer together and higher |
| `dimple_eyes` | engraved eyes only, nothing sticks out; the safest to print |
| `none` | plain rounded head |

### Designing your own face

![](face_meshes/face_guide.png)

Model a face in any CAD tool and pass it in as mesh files (STL, 3MF or OBJ):

* `--face-mesh file.stl` is **added** to the head (eyes, horns, a nose...)
* `--face-cut file.stl` is **cut** from it (pupils, a mouth, engraved patterns)

Draw them in **face coordinates**: origin on the bed (z = 0), on the centre
line (y = 0), directly under the tip of the head. +x points forward out of the
face, +y to the millipede's left, +z up, in millimetres. Both meshes must be
closed (watertight) solids.

`face_meshes/` has everything needed to start:

| file | what it is |
|---|---|
| `head_reference.stl` | the bare head in face coordinates; import it into your CAD tool and model against it |
| `sample_face.stl` | example add mesh: two domed eyes |
| `sample_face_cut.stl` | example cut mesh: pupils and a smile |
| `face_guide.png` | the picture above |

Try the sample (use `--face none` so the built-in eyes don't get in the way):

```bash
.venv/bin/python millipede.py --face none --face-mesh face_meshes/sample_face.stl --face-cut face_meshes/sample_face_cut.stl
```

Things to keep in mind:

* Anything behind about x = -8 near the centre line, and further forward at
  the sides, is cut away by the joint to the first segment.
* Keep features printable without supports: nothing on the underside that
  overhangs more than 45°, and nothing narrower than about 0.8 mm.
* The head's shape depends on `width`, `height`, `head_length`, `pitch` and
  `foot_flare`. If you change those, regenerate the reference files with the
  same values: `.venv/bin/python face_guide.py --config my_params.json`
  (or the same flags you build with; `--out-dir` writes them elsewhere).

## Textures (`--texture`)

Textures apply to the body segments only, not the head or tail.

| option | what it is |
|---|---|
| `none` (default) | smooth shells |
| `grooves` | one groove (0.6 mm deep, 0.8 mm wide) across the top of each segment, following the chevron |
| `spots` | three rows of shallow oval dimples (2.2 mm across, 0.45 mm deep): one down the spine and one along each side, the same on every segment |
| `bumpy` | densely packed small bumps of random size (0.7–1.5 mm across), different on every segment; adds ~0.7 mm to the height. Bumps have 45° cones underneath so the ones on the sides print without supports |

Faces and textures combine freely, e.g. `--face googly --texture spots`.

To tune `spots` or `bumpy` (spot size and position; bump size range, how far
bumps stick out, how tightly they pack), change the keyword defaults of
`spots()` / `bumpy()` in `textures.py`.

## All parameters

Lengths in mm, angles in degrees. On the command line, underscores become
dashes (`foot_flare` → `--foot-flare`); on/off options take `--name` /
`--no-name` (e.g. `--mouse-ears`, `--no-preview`). In a `--config` JSON file
use the underscore names.

**Overall**

| parameter | default | notes |
|---|---:|---|
| `segments` | 26 | body segments between head and tail |
| `layout` | `line` | `line` or `spiral` |
| `name` | auto | output file stem, e.g. `millipede-26seg-line` |

**Body shape**

| parameter | default | notes |
|---|---:|---|
| `pitch` | 5.2 | joint-to-joint distance; the original was 4.64 |
| `width` | 14 | body width, not counting the foot flare |
| `height` | 12 | total height |
| `leg_height` | 3 | height of the legs below the domed body |
| `chevron_angle` | 45 | cone half-angle of the nested shells top and bottom; keep ≥45 to avoid overhangs. 50 gives bigger feet (28 mm²) |
| `side_angle` | 25 | cone half-angle at the sides above the feet; smaller sweeps the sides further back over the next part. 0 = same as `chevron_angle` (the joint then shows through the side seams) |

**Feet**

| parameter | default | notes |
|---|---:|---|
| `foot_gap` | 2 | gap between left and right foot (0 = one wide foot) |
| `foot_flare` | 1 | how far each foot pad sticks out past the body side |
| `foot_pad` | 0.6 | vertical edge of the pad before its 45° chamfer |
| `mouse_ears` | off | thin discs under head and tail for adhesion |
| `ear_radius` | 6 | |
| `ear_thickness` | 0.4 | |

**Joint and clearances**

| parameter | default | notes |
|---|---:|---|
| `ball_radius` | 1.2 | ball joint only |
| `neck_radius` | 0.6 | ball joint only; must stay below `ball_radius` − `clearance` − 0.15 so the ball is captive |
| `nose_wall` | 0.9 | wall between the pin hole (or ball cavity) and the front surface |
| `clearance` | 0.35 | pin/hole (or ball/cavity and neck/slot) clearance |
| `gap` | 0.45 | clearance between nested shells |
| `bottom_gap` | 0.7 | shell clearance in the first layers (against elephant's foot) |
| `bottom_gap_height` | 0.4 | how high the wider `bottom_gap` reaches |
| `yaw` | 12 | sideways bend allowed per joint; see the trade-off tables above |
| `joint` | `hinge` | `hinge` (bends sideways, down and up), `rings` (also twists, with a little play) or `ball` (sideways only) |
| `pin_radius` | 0.75 | hinge pin / ring bar radius (plus a pointed underside); the hole is `pin_radius`×1.41 + `clearance` (+ `ring_slack`) |
| `drape` | 12 | hinge/rings: downward bend allowed per joint, e.g. over a finger |
| `arch` | 6 | hinge/rings: upward bend allowed per joint |
| `twist` | 15 | rings: twist allowed per joint about the body's length |
| `ring_width` | 2.4 | rings: width of the upright ring at the front of each part |
| `ring_slack` | 0 | rings: extra play in every direction. Each 0.1 mm also widens the gap between shells by 0.1; 0.1 printed noticeably loose |
| `side_wall` | 1.2 | hinge/rings: solid wall kept between the pin ends (and the holes and notches around them) and the body's surface |
| `joint_height` | 0 | height of the joint; 0 = auto (hinge/rings: `leg_height` + 2.5, lower means less carved from the feet; ball: middle of the domed body) |

**Head, tail and decoration**

| parameter | default | notes |
|---|---:|---|
| `head_length` | 11 | from the first joint behind the head to its tip |
| `head_groove` | 4.5 | height of the 45° groove under the head (twice as wide at the bed). Bigger = smaller head feet, easier to remove. With the ball joint: 3 → 74 mm², 4.5 → 44 mm², 0 = flat-bottomed head (116 mm²). With the hinge the head is already shorter underneath: 4.5 → 32 mm² |
| `tail_length` | 8 | from the tail's front joint to its tip |
| `face` | `eyes` | see Faces |
| `face_mesh` | none | mesh file in face coordinates to add to the head |
| `face_cut` | none | mesh file in face coordinates to cut from the head |
| `texture` | `none` | see Textures |

**Spiral layout**

| parameter | default | notes |
|---|---:|---|
| `spiral_inner_radius` | 0 | 0 = the tightest radius `yaw` allows |
| `spiral_turn_gap` | 2 | clearance between neighbouring turns |
| `spiral_bend_fraction` | 0.75 | use at most this fraction of `yaw` when laying out the spiral |

**Output**

| parameter | default | notes |
|---|---:|---|
| `resolution` | 48 | segments per full circle |
| `out_dir` | `out` | |
| `stl` | off | also write an STL |
| `preview` | on | write a PNG preview |
| `check` | on | check every part is one solid and no parts touch |

The generator refuses parameter combinations that can't work (e.g. a wall
behind the pin hole or ball cavity thinner than 0.6 mm, or a ball that isn't captive) and
says which values to change.

The default `clearance` (0.35) and `gap` (0.45) come from test prints of
the ball joint and the rings. On a different printer or filament, or to try
the hinge for the first time, print a short one first (`--segments 6`) and
adjust them.
