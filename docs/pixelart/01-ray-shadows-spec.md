# Spec: ray-traced hard shadows for Malt (pixelart branch)

Status: draft for owner review, 2026-10-07. Analysis: `00-analysis.md`. Fallback if this does not work well: stencil
(shadow volume) shadows.

## 1. Goal

Pixel-perfect hard shadows in Malt's NPR pipeline: for every shaded pixel, one exact yes/no answer to "is the light
blocked between this surface point and the light?", from the scene triangles themselves. No shadow-map texels, no
cascades, no bias tuning per scene, no soft edges.

Success means, judged side by side and zoomed:
- Shadow edges follow the caster's real shape at the sprite resolution (no blocks, no stair-steps larger than the
  pixel grid itself).
- Edges do not crawl when the camera or the light moves a little; a static scene renders identically every time.
- No acne on lit curved surfaces, no gap between a caster and its shadow at contact.

## 2. Non-goals (v1)

- Soft shadows, penumbra, PCF, any blending. (Owner: hard, pixel-perfect only.)
- Transparent / coloured shadows (Malt's transparent shadow maps keep working for shadow-map lights).
- Viewport real-time speed for big scenes (final renders first; speed in a later step).
- Replacing shadow maps: they stay available; ray shadows are an option per scene.

## 3. Constraints

- Malt pipeline shaders compile as GLSL 4.50 (`Malt/GL/Shader.py`), so SSBOs are available.
- Malt's GL wrapper has `UBO` (`Shader.py:130`) but no SSBO class: we add one.
- Mesh data reaches the Malt server as arrays (`Bridge/Mesh.py: load_mesh`: positions, indices, ...); a deformed mesh is
  re-sent when it changes. Object matrices arrive per frame in `Scene.objects`.
- Python side has numpy (Malt dependency). No new dependency in v1.
- Never save or modify owner `.blend` files; test renders use scripted GUI launches (option B) into scratch folders.

## 4. Design

### 4.1 Data
- **CPU mesh cache** (`Bridge/Mesh.py`): keep the object-space `positions` and `indices` of every loaded mesh (numpy),
  next to the GL mesh, keyed by mesh name.
- **World triangles per frame**: for every visible object in `Scene.objects`, transform its cached triangles by
  `Object.matrix`; record per triangle the object's ID (the same ID Malt writes in its ID pass) and its material's
  shadow light-group mask.
- **BVH (v1: one level, rebuilt per frame in world space)**: binned-SAH build in numpy; nodes flattened depth-first
  (AABB min/max, left-child-or-first-triangle, count). Triangles stored as 3 vertices (float32, std430).
  v2 (later): two-level (per-mesh BVH built once, top level over object matrices) when build time matters.

### 4.2 GPU
- New `SSBO` class in `Malt/GL/Shader.py` (create, `glBufferData`, `glBindBufferBase(GL_SHADER_STORAGE_BUFFER, ...)`,
  block binding by name like `UBO`).
- New `Malt/Render/RayShadows.py`: owns the cache, the per-frame build and the 3 SSBOs (`RAY_BVH_NODES`,
  `RAY_TRIANGLES`, `RAY_TRIANGLE_INFO`), and exposes `shader_callback(shader)` like `LightsBuffer`.
- New `Malt/Shaders/Lighting/RayShadows.glsl`:
  `bool ray_occluded(vec3 origin, vec3 dir, float t_max, uint self_id, bool self_shadows, int light_group, out uint hit_id)`
  - fixed-size stack traversal (depth <= 64), any-hit early exit;
  - watertight ray/triangle test (Woop, Benthin, Wald 2013), so rays never slip through shared edges;
  - a hit counts only if the triangle's shadow light-group mask contains the light's group, and
    (`self_shadows` or the triangle's object ID != `self_id`).

### 4.3 Hook
- `NPR_Lighting.glsl: npr_lit_surface`: when ray shadows are on (scene setting), replace the shadow-map lookups with
  one ray per light:
  - sun: `dir = -light.direction`, `t_max = inf`; point/spot: towards `light.position`, `t_max = distance - eps`;
  - origin = `position + geometric_normal * offset`, `offset` in world units scaled by the pixel footprint at that depth
    (so the bias is the same in pixels everywhere and needs no per-scene tuning);
  - back-facing to the light (`NoL <= 0`) is left to the ramp, as now.
- `SceneLighting` node: new bool input `Ray Traced Shadows` (default off = shadow maps, current behaviour; an enum socket does not
  register in Malt's Render graph); when on, build the BVH and skip shadow-map rendering for opaque shadows.
- Sprite mode note: for pixel-perfect output render 1 sample per pixel (World `Samples.Grid Size` = 1) so the shadow
  test is taken once at the pixel centre; with more samples the yes/no answers are averaged by Malt's AA.

## 5. Validation (acceptance tests)

Python (pytest, numpy only, outside Blender), in the fork:
1. BVH build + a Python reference traversal agree with brute-force ray/triangle on random rays (0 mismatches).
2. Watertight: rays aimed exactly at shared edges and vertices of a closed mesh never pass through.

Scripted GUI renders (option B), each with a debug output of the raw shadow mask:
3. Box over a plane, sun from above: the shadow region matches the analytic projected box at pixel centres
   (0 mismatched pixels away from the edge; the edge itself within 1 px).
4. Lit sphere: 0 shadow pixels on the lit side (no acne).
5. Contact: a cube resting on a plane has no lit gap between it and its shadow.
6. Stability: the same frame rendered twice is identical; moving the camera by 1/4 px changes only edge pixels.
7. Owner comparison: `testmalt.blend` and a character, shadow maps vs ray traced, zoomed side by side.
8. Time: report BVH build ms and render ms at 360x360 for ~120k triangles (Kim-sized).

## 6. Build order (one card each, each ends with its tests)

R1. SSBO class + CPU mesh cache (+ tests: data round-trip through an SSBO read-back).
R2. BVH build + Python reference traversal + watertight test (tests 1-2).
R3. `RayShadows.py` + `RayShadows.glsl` + hook + `Ray Traced Shadows` input (renders 3-6).
R4. Owner comparison + timings (7-8), results note in `docs/pixelart/`.
Later: two-level BVH, deforming-mesh refit, viewport speed.

## 7. Risks

- SSBO binding through Malt's shader reflection may need changes in `Shader.py` uniform-block handling.
- Per-frame numpy build may be slow for big scenes (v2 two-level BVH).
- Malt's ID pass and per-triangle ID must match exactly for the self-shadow switch.
- If ray shadows show artifacts we cannot remove at the source, switch to stencil shadow volumes (owner).
