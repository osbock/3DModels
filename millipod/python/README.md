# Millipede: parametric print-in-place (Python + manifold3d)

Generates a print-in-place articulated millipede as a 3MF. Every part (head,
N body segments, tail) is a separate solid linked to its neighbours by a
captive ball joint, so it comes off the bed already assembled.

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
  its front joint plus a 50° cone tangent to it). The back of each part is cut
  by the next part's bullet, grown by `gap` and swept through ±`yaw`. A part
  can therefore swing ±`yaw` sideways without ever touching its neighbour, and
  all the sloped faces are ≥45° so they print without supports.
* **Ball joint** at mid-height: the ball belongs to the front part and sits
  in a cavity in the next part's nose, reached through a fan-shaped slot that
  is thinner than the ball (so it can't pull out). Ball and cavity have 45°
  pointed tops and bottoms instead of flat overhangs.
* **Feet.** Two flared pads per segment (`foot_gap`, `foot_flare`,
  `foot_pad`). At the defaults each segment touches the bed with ~44 mm²,
  compared with ~27 mm² for the original 26-vertebra model. In the first
  `bottom_gap_height` mm the clearance between shells widens to `bottom_gap`
  so elephant's foot can't fuse neighbours. `--mouse-ears` adds thin discs
  under the head and tail.
* **Layouts** (`layouts.py`) only supply joint points spaced `pitch` apart.
  The spiral is Archimedean, tail in the middle, and its inner radius is
  chosen so that no joint is bent more than `spiral_bend_fraction` × `yaw`.

## Trade-off: yaw vs. feet vs. spiral tightness

How much a joint can bend also sets how tight a spiral can be, and more bend
means more material carved from the outer ends of the feet:

| yaw | foot area / segment | tightest spiral radius |
|----:|--------------------:|-----------------------:|
| 12° (default) | 44 mm² | 33 mm |
| 16° | 39 mm² | 25 mm |
| 18° (spiral preset) | ~37 mm² | 22 mm |
| 20° | 34 mm² | 20 mm |
| 25° | 27 mm² (thin outer toes) | 16 mm |

## Extending

* **Faces**: `faces.py`. A face returns `(add, subtract)` solids in head
  coordinates. `mesh_face("my_face.stl")` lets you design a face in any CAD
  tool (origin at the head tip, +x forward, z=0 on the bed) and register it in
  `FACES`.
* **Textures**: `textures.py`. A texture takes a part and returns it modified
  (`grooves` and `spots` are the examples). Keep cuts shallow and away from
  the front/back faces, joint and feet. Textures in `PER_SEGMENT` are rebuilt
  for every segment (e.g. random patterns); others are built once and reused.

## Key parameters (mm / degrees)

| parameter | default | notes |
|---|---:|---|
| `segments` | 26 | body segments between head and tail |
| `pitch` | 5.2 | joint spacing; the original was 4.64 |
| `width`, `height` | 14, 12 | body cross-section |
| `yaw` | 12 | sideways bend per joint |
| `clearance` | 0.3 | ball/cavity and neck/slot |
| `gap` | 0.4 | between nested shells |
| `ball_radius`, `neck_radius` | 1.2, 0.6 | |
| `foot_flare` | 1.0 | foot pads stick out this far past the body |
| `chevron_angle` | 50 | cone half-angle; keep ≥45 |

Not yet print-tested: start with a short one (`--segments 6`) to dial in
`clearance` / `gap` for your printer.
