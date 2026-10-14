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

## Outline ring and KOF lit edges (owner review 1, 2026-10-10)
Owner: model pixels sat outside the outline (where thinning removed a line pixel, the surface behind stayed), and the
KOF XIII copy drew outlines on lit areas.
- Silhouette outline = the outermost ring of covered pixels. A removed ring pixel becomes background, and only when no
  surface pixel would then touch the background with a side. A pixel the lattice sees uncovered is background (hair-tip
  slivers the main pass covers but the lattice centre misses).
- KOF XIII: `outline_shadow_only` (Pixel Cel and Pixel Cel Face SDF): an outline pixel that is not in the darkest
  tone keeps its own colour.
- New check: `line_check.py --marker` also counts `outside` (covered, not a line, a side on the background); exit 1 if > 0.
- Before: outside 70 (both styles), 45 (April). After (`build/pixelart/P/ring_marker2/`): both styles 3012 line px,
  April 1541, border 1907, all with total 0 and outside 0. compare_cel 0 mismatches. Face SDF l120 0.29 % (unchanged).
- Also fixed: `Col` was not named for Malt, so COLOR[0] was 0 and the ASW offset -0.5 put every pixel in shadow.

## KEEP (plan Task 1, 2026-10-14) - NOT committed, one check open
- Parts named hand/finger/glove/strap get the KEEP bit (`pixel_cel_keep_id`, ID.w bit 0). Pixel Lines shows an uncovered
  pixel when a KEEP part touches any of its 9 lattice samples; marker colour yellow, exempt from isolated/short.
- April (`build/pixelart/P/keep_marker/`): KEEP px in the hands box 240 (off: 0). Opaque px in the box 3270 on, 3232 off.
- line_check --marker: pixel_keep, pixel_keep_off, both_styles total 0, outside 0. pixel_lines_border (was 1907 px, total 0)
  now 1919 px, total 2: two l_corners, both KEEP pixels at the frame border (4,0) and (4,239). Open.
- compare_cel on pixel_cel_debug: 0 mismatches (35280 px).

## Outline outside the model (owner review 2, 2026-10-14)
Owner: with the outline on the model's edge pixels (d5f29d4), 2 px fingers became a 1 px line (no skin) and needed
L corners showed everywhere. Now the silhouette outline is drawn OUTSIDE the model: a background pixel beside a covered
pixel (4-neighbour) is outline, coloured from that neighbour. The fill is never turned into line.
- A removed outline pixel becomes background, only when no covered pixel (line or not) is beside it.
- Pinholes (an uncovered pixel with 4 covered neighbours) are filled. KEEP fills only slivers that would vanish (no
  pixel centre of the 3x3 shows that object); on April the fingers show without it (KEEP adds 0 px there now).
- The Col.A switch applies only where a material wrote line_data (w > 0). gb now stores the fill offset -2..2 as /4.
- Marker checks (`build/pixelart/P/out_marker3`, `out_marker4`): outside 0 and l_corners 0 in all scenes; 2x2
  blocks left where overlap lines meet the outline: both styles 16, April 8, border 2 (corner rule A, card T01b).
  compare_cel 0 mismatches.
