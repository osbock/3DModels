# Holiday gems

Small faceted holiday shapes, about the size of `../Heart/heart-resized.stl` (20 × 17 × 5 mm), flat on the bottom and printable without supports on a 0.4 mm nozzle.

## Snowflakes

```bash
../millipod/python/.venv/bin/python snowflakes.py              # all five designs
../millipod/python/.venv/bin/python snowflakes.py star fern    # just some
../millipod/python/.venv/bin/python snowflakes.py --size 25    # tip-to-tip diameter, mm (default 22)
```

Outputs go to `out/`: one STL and one preview PNG per design, plus `snowflakes_all.stl` with all of them laid out on one plate.

| design | look |
|---|---|
| `classic` | two pairs of 60° branches per arm |
| `fern` | short branches close to the centre, swept forward |
| `plate` | hexagon ring joining the arms, forked tips |
| `star` | six bold pointed arms around a faceted hexagon hub |
| `dendrite` | branches that fork again (the busiest one) |

Each stroke of a snowflake is a convex bar: 0.9 mm vertical walls, then two facets meeting in a sharp ridge. The ridge is 4.2 mm high at the centre and drops to 2.0 mm at the tips. Arms are 2.0 mm wide and branches 1.6 mm wide at the base (4–5 nozzle widths). All of these are in `P` at the top of the script.

The script prints a "worst notch" for each design: the largest gap area that a 0.8 mm closing would fill. Every junction leaves a wedge of about 0.1 mm²; above 0.2 mm² it flags a tight spot where two strokes run too close for the nozzle.

## Christmas trees

```bash
../millipod/python/.venv/bin/python trees.py               # all four designs
../millipod/python/.venv/bin/python trees.py bough         # just one
../millipod/python/.venv/bin/python trees.py --size 22     # height in mm (default 24)
```

Writes `out/tree_<name>.stl`, preview PNGs and `trees_all.stl` (all four in a row).

| design | look |
|---|---|
| `classic` | three tiers, trunk, five-point star |
| `simple` | one tall faceted triangle with a star (sturdiest) |
| `bough` | tiers with drooping corners and a notch in the middle, like pine boughs |
| `ornaments` | the classic tree hung with seven faceted beads |

Same construction as the snowflakes: each tier is two convex halves with a sharp ridge up the middle (4.2 mm at its fattest, 1.8 mm at its tip), the trunk is a low block and the star is five ridged arms. About 17 × 24 × 4.2 mm. Size scales the outline only; heights stay put.

The "worst notch" check flags only above 0.5 mm² for trees. The V where each tier's base meets the tier below scores 0.2–0.5 by design, and only its very tip fills in. Each tree's tip runs just past the star's centre so there's no narrow V under the star's lower arms.

All four slice cleanly for the U1 (about 6½ minutes and 1.7 g together).

## Ornament balls

```bash
../millipod/python/.venv/bin/python ornaments.py              # all four designs
../millipod/python/.venv/bin/python ornaments.py teardrop     # just one
../millipod/python/.venv/bin/python ornaments.py --size 22    # total height in mm (default 24)
```

Writes `out/ornament_<name>.stl`, preview PNGs and `ornaments_all.stl`.

| design | look |
|---|---|
| `brilliant` | round brilliant cut: 16-sided girdle, 8 star facets, octagonal table on top |
| `geodesic` | low-poly sphere cap rising to a point |
| `striped` | the geodesic ball with two raised bands (1 mm proud) |
| `teardrop` | onion/drop ornament, pointed at the bottom |

Each ball is stacked polygons hulled into one convex dome, 5 mm tall like the heart (the striped one is 5.8 mm at the bands). A bevelled cap and an octagonal hanging loop sit on top. The loop is 1.8 mm thick with a 2.3 mm hole and 1.25 mm walls, so it can take a thread or jump ring. About 19 × 24 mm (teardrop 15 × 24). `--size` scales the ball only, so the cap and loop keep their printable size.

These are chunkier than the snowflakes and trees, but with the default infill all four together slice to about 8½ minutes and 3 g on the U1.

## Santa cap (two colours by layer)

```bash
../millipod/python/.venv/bin/python santa.py              # out/santa_cap.stl + preview
../millipod/python/.venv/bin/python santa.py --size 22    # width in mm (default 24)
```

A faceted red cap whose tip flops over to the right, a fur trim across the brim and a pompom on the tip. About 24 × 18.6 × 5 mm.

It is designed for **one colour change by height**: the red cap stays at or below 2.6 mm. The trim and pompom rise on vertical walls to 3.2 mm before their own bevels and facets, up to 4.0 mm (trim) and 5.0 mm (pompom).

**Change to white at layer 14 (Z = 2.85 mm)** with the U1 profile (0.25 mm first layer, 0.2 mm layers). Sliced, layer 14 is the first that contains only trim and pompom. Everything seen from above is then the right colour: the cap's top surface is red, and the trim and pompom tops are white. Only the sides of the trim and pompom are red below that height. With different layer heights, `santa.py` prints the right layer for the values at the top of the script.

With `print3d` (in ~/github/printer-tools), using the U1's red on tool 3 and white on tool 2:

```bash
print3d print u1 out/santa_cap.stl --tool 3 --change-at 2.85:2 --start
```

That comes to about 4¾ minutes and 1.5 g with the prime tower.

Or in the OrcaSlicer GUI: slice, then in the preview's layer slider go to layer 14, right-click the + and choose a filament change to the white filament (on the U1, the toolhead with white loaded). Single colour, it slices to about 3 minutes and 0.9 g.

## Menorah

```bash
../millipod/python/.venv/bin/python menorah.py             # all designs
../millipod/python/.venv/bin/python menorah.py classic     # one design
../millipod/python/.venv/bin/python menorah.py --size 24   # width in mm (default 25)
```

A nine-candle hanukkiah with the shamash raised in the middle, about 25 mm wide and 3 mm tall:

| Design | Look | Size (mm) |
|---|---|---|
| `classic` | four nested curved branches meeting a central stem, on a flared base | 25 × 19.5 |
| `modern` | straight bar on a triangular bracket and a stepped stand | 25 × 17.2 |

Writes `out/menorah_<name>.stl` and `.png`, and `out/menorahs_all.stl` with both side by side.

It prints in one colour, but like the Santa cap it is also made for **one colour change by height**: the menorah stays at or below 2.6 mm and the nine flames are short, flat-topped plates that end at 3.05 mm, two layers higher. **Change at layer 14 (Z = 2.85 mm)** for different-coloured flames: layers 14 and 15 are flames only. For example, the menorah in purple on tool 4 and white flames on tool 2:

```bash
print3d print u1 out/menorah_classic.stl --tool 4 --change-at 2.85:2 --start
```

That slices to about 4 minutes and 1 g with the prime tower. On the Prusa (0.2 mm first layer), the change is at Z 2.8 instead, as an M600 filament swap: `print3d print markey out/menorah_classic.stl --change-at 2.8 --start`. `FLAME_LAYERS` at the top of `menorah.py` sets how many layers the flames stand above the body.
