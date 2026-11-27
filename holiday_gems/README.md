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
