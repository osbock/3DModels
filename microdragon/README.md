# Micro dragon: any length

`micro-dragon_fixed.stl` is a print-in-place dragon: head, 4 body segments and a tail, linked by interlocking D-rings (the head uses a vertical pin instead). It is split here into three parts that chain into a dragon of any length.

```
parts/head.stl     head with its pin
parts/middle.stl   one body segment (repeat as needed)
parts/tail.stl
parts/joints.json  pitch between segments
```

The three STLs share one coordinate frame, with the spine along +X. Loaded together as-is, they form a complete dragon with one segment. For N segments, copy `middle.stl` N times and shift copy k (k = 0…N−1) by `k × 7.758 mm` in X. Shift the tail by `(N−1) × 7.758 mm`. Y and Z stay at 0.

Or let the script do it:

```bash
../millipod/python/.venv/bin/python compose_dragon.py 8
```

That writes `dragon_8.stl` as one multi-body STL (head + 8 segments + tail, about 95 mm long). The length is roughly 33 mm + 7.76 mm per segment.

## Spiral layout for long dragons

```bash
../millipod/python/.venv/bin/python compose_dragon.py 60 --spiral
```

This writes `dragon_60_spiral.stl`, coiled with the tail at the centre: 150 × 161 mm for 60 segments. Each joint turns about its own pivot (the vertical axis of the D-ring), the same way the printed joint moves, so every link keeps its straight-layout fit.

| segments | spiral footprint |
|---|---|
| 12 | 96 × 71 mm |
| 30 | 123 × 131 mm |
| 60 | 150 × 161 mm |

- `--max-bend` (default 10°) sets how far each joint turns. Joints keep their full 0.37 mm gap up to about ±8°, have about 0.25 mm at 10°, and touch by ±16°. That limit makes the innermost turn about 44 mm in radius, so the spiral only starts a second turn past about 40 segments. The head joint has almost no side play, so the head is always kept in line with the first segment.
- `--arm-gap` (default 26 mm) is the centre-to-centre spacing between turns. At 24 mm, spike tips of neighbouring turns overlap; 25 mm or more leaves at least 0.4 mm of clearance.
- Every build checks all parts for overlaps and prints a warning if any are found (`--no-check` skips this).

## How the joints were placed

The source segments are hand-placed, so their spacing and clearances vary (from 0.09 mm to 0.86 mm). `split_dragon.py` takes the 4th segment as the canonical middle. For each joint it slides the next part along X and picks the position with the largest minimum gap, which centers each arch in its ring.

| joint | min gap | free travel |
|---|---|---|
| head pin → segment | 0.17 mm | ±0.12 mm |
| segment → segment | 0.37 mm | −0.34 / +0.62 mm |
| segment → tail | 0.90 mm | −0.86 / +1.36 mm |

Re-running `split_dragon.py` takes about 30 min, mostly the segment → segment scan.
