# Handoff: ray-traced hard shadows (2026-10-07, end of night)

Fork `H:\GameDev\Malt`, branch `pixelart`, pushed to `neo-giu/Malt`. Last commit `2967caf`.
Owner verdict: **not done**. "The ray-traced shadow still looks jagged/biased at subdiv 4. This shouldn't happen at all."
Goal unchanged: pixel-perfect HARD shadows. No soft shadows, no post-pass filters. Fallback: stencil shadow volumes.

## 1. State

| Piece | Where | Status |
|---|---|---|
| CPU copies of positions, indices, corner normals | `Malt/Pipeline.py: load_mesh` | done |
| BVH (binned SAH, numpy, per frame, `order` field) | `Malt/Render/RayBVH.py` | done, tested |
| Per-frame cache, 4 SSBOs (0 nodes, 1 tris, 2 info, 3 vertex normals) | `Malt/Render/RayShadows.py` | done |
| Phong tessellation of shadow geometry (crack-free) | `Malt/Render/RayGeometry.py: phong_tessellate` | done, off by default |
| GLSL any-hit + own-triangle search + Hanika lift | `Malt/Shaders/Lighting/RayShadows.glsl` | done |
| Hook | `NPR_Lighting.glsl: npr_lit_surface` (`if(RAY_SHADOWS)`) | done |
| Inputs on SceneLighting | `Ray Traced Shadows` (bool), `Ray Smooth Levels` (int, 0), `Ray Bias (px)` (1.0) | done |
| Tests | `tests/pixelart` (24 pass): `H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart -q` | green |
| R4 (owner comparison sheet, timings, results note) | - | not started |

Notes:
- An enum input does not register as a Render-graph socket in Malt. Use bool/int/float inputs.
- Objects/lights created by script need `BlenderMalt.MaltPipeline.setup_all_ids()` (done in `scenes.py`).
- The `KeyError: ... "Ray Traced Shadows" not found` at file load is transient (stale node before re-setup). Ignore it.

## 2. How to render and compare

```bash
cd /h/GameDev/Malt
RENDER_TIMEOUT=150 bash tools/pixelart/render.sh /h/GameDev/Pixelizer/content/malt/testmalt.blend build/pixelart/X/NAME 1 SETUP
```
- GUI launch with the dev add-on (`BLENDER_USER_SCRIPTS=H:/GameDev/MaltDev/scripts`), quits without saving, kills the
  Blender tree on timeout. Exit 1 on a Python traceback or `MaltGraphExecutionException`.
- `SETUP` = a function in `tools/pixelart/scenes.py` (in-memory edits only): `box_plane`, `lit_sphere(_maps)`,
  `cube_contact`, `ray_traced`, `shadow_maps`, `ray_traced_subd1/4`, `shadow_maps_subd1/4`, `*_noshadow` (bias 1e5 =
  ramp only), `ray_traced_subd1_flatshadow` (smooth levels 0), `*_nosubd`.
- Only the copies in `H:/GameDev/Pixelizer/content/malt/` (never the owner's D:/ originals). The owner saved
  `testmalt.blend` there with a LOWER subdivision (uncommitted in Pixelizer). The `_subd4` setups force level 4 in memory.
- Always judge zoomed (3x, NEAREST) and side by side. Sheets so far: `build/pixelart/R3/testmalt_sheet.png`,
  `build/pixelart/T2/{sheet,noshadow_sheet,cast_sheet}.png` (build/ is not in git).
- Frame time: 2.5 s maps, 4.5 s ray (first, with shader compile), 44 s at subd 4 + `Ray Smooth Levels` 2 (4M tris).

## 3. What we know about the remaining jaggedness

Measured on Suzanne:
- Analytic box over plane: 2 colours, 0 wrong pixels off the edge; the edge row is 0.4 px off. Cause: the bias moves
  the origin 1 px along the normal, which shifts a shadow edge by `bias * tan(light angle)`. At grazing light this grows
  without bound. **This is the "biased" part and it is real.**
- The Hanika origin lift changed only 101 px at subd 1. Smooth (Phong) shadow geometry changed ~140 px more.
- "Shadows off" (ramp only) is also blocky at subd 1, so part of the low-subd look is the mesh itself.
- Not yet explained: the jagged/spiky edges at **subd 4**, where facets are ~1-2 px. The fixes above should have
  made those smooth. So an assumption is wrong somewhere. Find which one before writing more fixes.

Suspects, most likely first:
1. **Ramp vs shadow disagree near the terminator.** The ramp uses the smooth normal (N.L), the ray uses geometry. Where
   N.L is near 0 every ray is grazing and a 1-px bias decides the answer per pixel -> notches. Check: dump N.L and the
   raw shadow bit per pixel; plot where the shadow bit flips vs N.L.
2. **Bias direction.** Offsetting along the geometric normal moves edges by `bias * tan(angle)`. Try offsetting along
   the light direction only (origin + L * eps, plus a tiny normal epsilon), or an epsilon that scales with
   `1 / max(N.L, small)` but capped. Measure the box edge error at 30, 60, 80 degrees.
3. **The own-triangle search fails** on some pixels (8 px search, `abs(t - search)` choice) -> origin left on the flat
   triangle. Check: debug colour for "not found" and for "found triangle of another surface".
4. **Grid Size really 1?** `scenes.py` sets `world.malt_parameters['Samples.Grid Size'] = 1`; not verified on the
   GPU side. If AA samples still run, edges average or jitter. Check the colour count of a shadow edge.
5. **Precision** of world-space float32 BVH vs `POSITION` from the depth/raster (position mismatch of 1e-4 at the scale
   of the scene). Check the distance from `position` to the found triangle.

## 4. What to try next (ordered)

### Step 1 - Diagnose before fixing (about 1 h)
- Add a debug uniform `RAY_DEBUG` (0 off; 1 shadow bit; 2 N.L sign vs shadow; 3 origin search result) and write it
  to the colour output, or add a render output. Render subd 4 Suzanne, 360 px, Grid Size 1.
- Build a **ground truth**: the same frame in Cycles with a sun of angle 0 (hard), no AA (1 sample, filter 0.01 px),
  at 360 px, or at 4x then majority-downsample. Compare the shadow mask pixel by pixel and count mismatches by cause.
- Decide from the numbers which suspect in section 3 is real.

### Step 2 - Fixes per suspect (pick from Step 1, one at a time, measured)
- Terminator: treat the shadow as one more ramp input instead of a separate switch: the pixel is "lit" only if
  `N.L_smooth > 0` AND the ray is clear, and self-hits closer than the local triangle size count only when the hit
  triangle faces the light (`dot(n_hit, L) > 0`). This keeps real cast shadows (brow on face) and drops
  grazing self-hits on the same curved patch.
- Bias: light-direction offset (above). Expect the box edge error to drop to < 0.1 px at every angle.
- Shadow geometry from the **render-level subdivision** regardless of the viewport level (owner wants shadows not to
  change when the viewport subdivision is lowered). Needs the evaluated mesh at render levels sent to the server.
- Speed: two-level BVH (per-mesh BVH built once, top level over instances) before any heavier geometry.

### Step 3 - Stencil shadow volumes experiment (the agreed fallback, about 1 day)
Exact per-pixel hard shadows by rasterization; a good cross-check of the ray result even if we keep rays.
1. CPU, per light per frame: for each closed mesh, classify triangles as light-facing; silhouette edges = edges between
   a light-facing and a back-facing triangle (needs edge adjacency; build once per mesh, cache).
2. Extrude silhouette quads away from the light (sun: to infinity, w = 0; point/spot: to infinity from the light) and
   add front/back caps for z-fail (Carmack's reverse). Use an infinite far projection for the volume pass.
3. Per light: clear stencil, draw volumes with depth test against the scene depth (the Malt pre-pass depth), no colour,
   back faces incr-wrap on depth fail, front faces decr-wrap on depth fail. Stencil != 0 = shadow. Resolve into one
   layer of an R8 texture array `STENCIL_SHADOWS[light]`.
4. In `npr_lit_surface`, `S.shadow = texelFetch(STENCIL_SHADOWS, ivec3(screen_pixel(), light_index)).r > 0` when
   a new `Stencil Shadows` bool input is on (enum inputs do not work in the Render graph).
5. Light groups and self-shadow: only meshes whose material shadows the light's group; self-shadow off needs an ID
   compare (render volumes per object ID or skip it in v1).
Risks: needs 2-manifold meshes (Suzanne's eyes are separate closed parts: fine; open meshes leak -> cap or skip),
same coarse-silhouette terminator problem on low-poly meshes (classify facing with smooth vertex normals to soften),
fill rate for big volumes. Compare against the ray result and Cycles with the same masks and counts.

### Step 4 - R4 owner comparison
Zoomed sheet: shadow maps vs ray (vs stencil) on testmalt and a character; timings for ~120k triangles; results note
`docs/pixelart/03-ray-shadows-results.md`.

## 5. Rules (from the owner)
- Never save or modify the owner's `.blend` files; render only from `content/malt/` copies, in memory edits only.
- No post-pass filters, no whack-a-mole; fix at the source, measure every change, show zoomed side by side.
- Do not compare Malt scenes with the Goo GIF.
- Commit and push the fork when a step is verified. Do not edit the release add-on in `%APPDATA%`.
