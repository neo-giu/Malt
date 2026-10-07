# Ray-traced hard shadows: results (2026-10-07)

Fork commit `ccc5425` (branch `pixelart`). Follows `04-handoff.md` Step 1 (diagnose), Step 2 (bias fix) and Step 4 (R4).

## 1. Cause of the "biased" shadows

The ray origin was moved 1 px along the geometric normal. That moves every shadow edge by `bias * tan(light angle)`,
so cast shadows shrank. At grazing light the shift was 1-3 px (the brow shadows).

Fix: the origin gets only a 0.01 px normal offset (float safety). The bias is now a minimum hit distance **along the
ray**, and only for hits on the receiver's own object (`ray_occluded(..., self_t_min)`). A shadow edge does not move.
Hits on other objects are never ignored, so contact shadows have no gap.

## 2. Measurements

Ground truth: Cycles, sun angle 0 (hard), direct light only, box filter 0.01 px (samples at the pixel centre).
Malt: `tools/pixelart/ray_debug.mesh.glsl` (R = N.L > 0, G = shadowed, B = origin search). Tool:
`tools/pixelart/compare_truth.py`. testmalt Suzanne, 360 px, about 37 400 covered pixels.

| Case | Malt lit / Cycles dark | Malt dark / Cycles lit |
|---|---|---|
| subd 4, before (normal bias) | 687 | 326 |
| subd 4, after | **37** | 399 (186 shadow edge, 213 N.L tie at the silhouette) |
| subd 4, after, Hanika lift off | 12 | 436 |
| subd 1 (the file's level), after | 49 | 516 |
| subd 1, after, Hanika lift off | 1 | 1126 |

- subd 4: every remaining mismatch is a 1 px boundary pixel (186 of 186 touch a Malt lit/shadow edge). This is the
  sub-pixel noise floor (Cycles coverage itself differs from Malt on 51 silhouette pixels).
- subd 1: the remaining band is on top of the brows. There Cycles is speckled (its own terminator offset of 0.1);
  Malt draws one clean band. This is a terminator policy difference, not an error.
- The Hanika lift still helps: keep it.
- Analytic box over plane (`box_plane`, `box_plane_60`, `box_plane_80`): **0 wrong pixels** at 30, 60 and 80 degrees,
  2 colours only. Before, the edge row was 1 px off at 30 degrees.
- `cube_contact`: the shadow starts at the cube row, no lit gap.
- Tests: 25 pass (`tests/pixelart`), new test for `self_t_min` in `test_r2_bvh.py`.

## 3. What the remaining "jagged" look is

At subd 4 the Malt mask and the Cycles mask are the same staircase (`img/eye_left2.png`, `img/R4_mask_subd4.png`).
A hard shadow decided once per pixel always draws the mesh's real shadow outline as pixel steps. There is no further
error to remove in the shadow test. Smoother outlines need smoother shadow geometry (more subdivision or
`Ray Smooth Levels`), not a different test.

## 4. Sheets (3x, NEAREST)

- `img/R4_subd1.png`, `img/R4_subd4.png`: ray before / ray after / shadow maps.
- `img/R4_mask_subd1.png`, `img/R4_mask_subd4.png`: Malt ray lit mask / Cycles lit mask.
- `img/eye_left2.png`: left eye, before / after / Cycles (5x).

## 5. Timings (GUI render of one frame, includes start up)

| Scene | Shadow maps | Ray |
|---|---|---|
| testmalt subd 1, 360 px | 2.4 s | 2.4 s |
| testmalt subd 4, 360 px | 2.4 s | 4.5 s |
| mannequin_malttest, 1920x1080 | 10.2 s | 35.0 s |

The mannequin camera shows only the floor and the sky (no character in frame), so the mannequin numbers are for cost
only. The split between the per-frame BVH build and the GPU rays is not measured yet.

## 6. Open items (owner decision)

1. Shadow geometry from the render-level subdivision in the viewport (needs the evaluated render mesh on the server and
   a receiver-to-shadow-surface match; the own-triangle search does part of this).
2. Speed: two-level BVH (per-mesh BVH built once, top level over instances).
3. Stencil shadow volumes: not needed as a fallback now (the ray result matches Cycles). Still possible as a
   cross-check.
4. Terminator policy at low subdivision (section 2): keep the clean band, or copy Cycles' partial offset.
