# Pixel Cel results

## Line probe (Malt Line Width = 1)

Setups `lines_w1` and `lines_off`, 356x256, `tools/pixelart/line_check.py` (exit 1):

```
line px 1302 {'blocks': 0, 'l_corners': 4, 'isolated': 12, 'short': 16, 'total': 32}
```

Malt Line Width = 1 breaks the 1 px rule: isolated dots, short pieces and L corners.

## pixel_cel vs cel_ref

`tools/pixelart/compare_cel.py` on `pixel_cel_debug` (356x256, Suzanne, ray traced shadows):

```
checked px 35280 mismatches 0
```

## Pixel Lines
April, ASW preset, 256 px high, ray traced shadows. Line mask = Pixel Lines on minus off (off: Line Width 0).

| Setup pair | line px | blocks | l_corners | isolated | short | total |
|---|---|---|---|---|---|---|
| pixel_lines_on / _off (decision, thin, prune only) | 1530 | 44 | 0 | 0 | 0 | 44 |
| pixel_lines_border / _border_off (same) | 1960 | 79 | 0 | 0 | 0 | 79 |
| pixel_lines_on / _off (+ Zhang-Suen x3, thin, prune) | 1457 | 0 | 0 | 0 | 0 | 0 |
| pixel_lines_border / _border_off (same) | 1878 | 0 | 0 | 0 | 0 | 0 |

`compare_cel` on pixel_cel_debug: 35280 checked px, 0 mismatches. Border render: 2 / 4 line px on the top / bottom row,
31 / 31 on the left / right column (object edges that meet the border, no line along the whole border).
Not done: 3 animation frames.

## End to end on April, ASW and KOF XIII (task 8)
Setup `pixel_cel_both_styles` (April ASW at x=0, the Copy collection KOF XIII beside it), 396x256, ray traced shadows,
Pixel Lines on. Sheet: `docs/pixelart/img/pixel_cel_both.png` (3x zoom, left ASW, right KOF XIII).
Render files: `build/pixelart/P/t08_fix/` and `build/pixelart/P/t08_marker/` (not in git). Status: ready for owner review.

Found on the way: the KOF copy was not visible in the first render. The copied armature's action keys location, so
`frame_set` moved the copy back onto April. Fixed (orchestrator): `copy_collection` offsets with `delta_location`,
`COPY_SPACING` 1.6 m (at 1 m the arms overlap). Measured after `frame_set`: `COPY_OFFSET [1.6]`.

### Outline colour (T07 finding: sRGB 89 on screen)
`outline_value` is a linear colour. ASW 0.1 -> 0.01, KOF 0.35 -> 0.1 (= base x0.35 in display terms).
Measured: ASW outline sRGB (25, 25, 25) on 1261 of 1410 line px. KOF outline on the blue skirt (13, 36, 49), base x0.35
with the hue kept.

### Success criteria
| # | Criterion | Result |
|---|---|---|
| 1 | April converts, side by side with a reference | ASW half on the sheet: base + Sss 2 tones, ilm inner lines, decals cut out, 1 px outline sRGB 25. Owner judges against `refs/april_ggxrd_1.png`. Not compared by me. |
| 2 | Arthur and Dude convert, no errors | Converted in T05 without errors (reports). 3 animation frames: not done. |
| 3 | Convert twice = identical | T06: 0 differing px (`pixel_cel_convert_asw` vs T05). Not repeated here. |
| 4 | Originals unchanged | T06 `original_hash` unchanged. Not repeated here. |
| 5 | Hand ramp gives N bands, survives reconvert | T06 `pixel_cel_reconvert`: hand edit and hand node kept. Not repeated here. |
| 5a | ASW and KOF XIII side by side | Sheet above. 4 tones and purple-shifted shadows visible on skirt and hat in KOF. Owner judges. |
| 5b | 0 line px that break the 1 px rule | PASS (orchestrator fix, below). Exact marker check (`PIXEL_LINES_DEBUG=1`, `line_check.py --marker`): both styles 2937 line px, total 0; April alone 1457, total 0; border 1878, total 0. Still frames only. |
| 6 | Unit tests; frame time <= +10 % | 54 passed. Frame time: not measured as a pair (render.sh logs whole-render wall time only; T08 saw 3.281 s for 2 characters with Pixel Lines vs 4.448 s for Suzanne `lines_w1`). Open. |

### KOF XIII values
Only `outline_value` changed (0.35 -> 0.1, reason above). Ramp stops, hue shift 15, saturation 1.25, value 0.55, spec
1.2, highlight 0.85 / 0.2 are the spec's starting values: no tuning round was possible (3 launches used).

### Line fixes (orchestrator)
- Block at (50, 132): a junction of 3 lines around a 1 px background hole between hair and collar. Zhang-Suen keeps it
  (every pixel of the block has more than one 0->1 transition). New stage `PIXEL_LINES_BLOCK` after Zhang-Suen: 4 passes,
  one per block corner; a pixel of a 2x2 block is removed when its Yokoi 8-connectivity number is 1 (no piece splits, no
  hole opens). Tested in numpy first: 1 px removed, 11 components before and after, T07 masks unchanged.
- The on-minus-off mask is not exact: a KOF outline (base x0.1) on a black surface has the surface colour, so 3 line
  px were invisible to it (3 false violations at the black shoes). Hence the marker check above.

### Open items
- The camera of `pixel_cel_both_styles` crops the KOF copy's right hand (396 px wide frame).
- 3 animation frames for criteria 2 and 5b.
- Frame-time pair for criterion 6.
- KOF XIII tuning against KOF XIII sprites: after the owner review.
