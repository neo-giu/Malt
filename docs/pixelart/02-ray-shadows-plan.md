# Ray-traced hard shadows — Implementation Plan

> Executed as card waves (`bash tools/cards/run_cards.sh R1 R2 R3 R4`), one task = one card = one commit, on branch
> `pixelart`. Steps use checkbox (`- [ ]`) syntax. Each card's fence = its **Files** list.

**Goal:** Malt's NPR pipeline gets a `Ray Traced Shadows` option: one exact, hard yes/no shadow test per pixel and
light, traced on the GPU against the scene triangles.

**Architecture:** CPU side (Malt server, numpy): keep each sub-mesh's triangles, build one world-space BVH per frame,
upload to 3 SSBOs at fixed bindings. GPU side: `ray_occluded()` in GLSL, called from `npr_lit_surface` instead of the
shadow-map lookups when the scene flag is on.

**Tech stack:** Python 3.13 (Blender 5.2 / Malt server), numpy, PyOpenGL (Malt.GL), GLSL 4.50. Tests run outside
Blender with `H:/GameDev/Pixelizer/.venv/Scripts/python` (numpy + pytest), so the BVH code must not import OpenGL.

**Spec:** `docs/pixelart/01-ray-shadows-spec.md` (approved 2026-10-07).

## Global constraints

- Hard shadows only: a boolean per ray. No PCF, no soft shadows, no blending.
- Shadow maps stay the default; ray tracing only when `Ray Traced Shadows` is on.
- Only opaque materials cast ray shadows (v1). Transparent shadow maps keep working for shadow-map mode.
- A triangle blocks light L only if its material's `Light Groups.Shadow` contains L's `Light Group` (same rule as
  `SceneLighting.get_light_group_batches`), and, when self-shadows are off, its object ID differs from the receiver's.
- SSBO bindings are fixed: 0 = nodes, 1 = triangles, 2 = triangle info. Malt has no other SSBO users.
- Never save or modify owner `.blend` files. Renders: `tools/pixelart/render_gui.py` (GUI launch, quits without saving).

## Review focus

1. **Per-sample vs per-frame:** `SceneLighting.execute` runs once per AA sample; the BVH must be built once per frame
   (cache keyed by frame + object matrices + mesh identities) — R3 test: 2 executes with different sample offsets build once.
2. **Watertightness:** a ray through a shared edge or vertex of a closed mesh must hit (R2 test).
3. **Self-shadow acne:** a lit sphere must have 0 ray-shadowed pixels on its lit side (R3 render check).
4. **Empty scene / no casters:** 0 triangles must not crash the build or the shader (R2 + R3 tests).
5. **Mirrored objects:** negative-scale matrices flip winding; the triangle test must be two-sided (R2 test).

---

### Task R1: SSBO class + CPU triangles on meshes

**Files:** Modify `Malt/GL/Shader.py`, `Malt/Pipeline.py`; Create `tests/pixelart/test_r1_mesh_cpu.py`

**Interfaces (produces):**
- `Malt.GL.Shader.SSBO`: `__init__()`, `load_array(np_array)` (`glBufferData(GL_SHADER_STORAGE_BUFFER, ...)`,
  `GL_DYNAMIC_DRAW`), `bind(binding: int)` (`glBindBufferBase(GL_SHADER_STORAGE_BUFFER, binding, buf)`), `__del__`.
- In `Pipeline.load_mesh`, every returned `MeshCustomLoad` gets `cpu_positions` (`(V, 3) float32` numpy copy) and
  `cpu_indices` (`(T, 3) uint32` numpy copy of that sub-mesh's index buffer). Copies, not views (the IPC buffers are
  reused).
- Helper `Malt.Render.RayGeometry.mesh_triangles(mesh) -> (T, 3, 3) float32` in a NEW pure-numpy module
  `Malt/Render/RayGeometry.py` (no OpenGL import) — add it to the fence list: Create `Malt/Render/RayGeometry.py`.

- [ ] Step 1: Test (pure numpy, no GL): build a fake mesh object with `cpu_positions`/`cpu_indices` for a unit quad
  (2 triangles) and assert `mesh_triangles` returns the 6 expected vertices in order; assert an empty mesh returns
  shape `(0, 3, 3)`.
- [ ] Step 2: Implement `RayGeometry.mesh_triangles`, the `Pipeline.load_mesh` copies (use
  `np.frombuffer(ctypes buffer)` via the IBuffer's `buffer()` and `ctype()`; positions reshape `(-1, 3)`, indices
  `(-1, 3)`), and the `SSBO` class next to `UBO`.
- [ ] Step 3: Run `H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart -q`; GUI smoke render
  (see RULES) of `H:/GameDev/Pixelizer/content/malt/testmalt.blend` frame 1 still succeeds and is pixel-identical to
  `tests/pixelart/ref/testmalt_f1.png` (copy the current dev render there first, in this card).
- [ ] Step 4: Commit `R1: SSBO class, CPU triangles on meshes`.

### Task R2: BVH build + reference traversal (pure numpy)

**Files:** Create `Malt/Render/RayBVH.py`, `tests/pixelart/test_r2_bvh.py`

**Interfaces (produces):**
- `build_bvh(tris: (T,3,3) float32, info: (T,2) uint32) -> BVH` with fields
  `nodes: (N, 8) float32` (bmin.xyz, a, bmax.xyz, b — `a`,`b` stored as float-bit-cast uint32: leaf when `b > 0`:
  `a` = first triangle, `b` = count; inner: `a` = right child index, `b` = 0, left child = this + 1),
  `tris: (T, 4, 4) float32` (v0, v1, v2 as vec4 + padding, triangle order = leaf order), `info: (T, 4) uint32`
  (object id, shadow-group bitmask, 0, 0), `depth: int`.
  Binned SAH (12 bins) on centroids, leaf size <= 4, max depth 48; numpy vectorised per level.
- `occluded_ref(bvh, origin, dir, t_max, self_id, self_shadows, light_group_bit) -> bool` — the same traversal and
  the same watertight test (Woop/Benthin/Wald 2013) as the GLSL will use, in numpy/Python, for tests.
- `brute_occluded(tris, info, ...)` — brute force over all triangles, same test.

- [ ] Step 1: Tests:
  - 2000 random rays vs a random soup of 500 triangles: `occluded_ref == brute_occluded` for all.
  - Watertight: an icosphere (subdiv 2, closed); rays from outside aimed exactly at every vertex and edge midpoint
    through the centre: all report a hit.
  - Two-sided: a triangle with flipped winding still blocks.
  - Group mask: a triangle without the light's group bit does not block; self-id skip when `self_shadows=False`.
  - Empty input: `build_bvh` of 0 triangles returns 1 empty leaf; `occluded_ref` returns False.
  - `depth <= 48` and every triangle appears in exactly one leaf.
- [ ] Step 2: Implement. Step 3: run tests. Step 4: commit `R2: BVH build and reference traversal`.

### Task R3: GPU ray shadows + Ray Traced Shadows input + render checks

**Files:** Create `Malt/Render/RayShadows.py`, `Malt/Shaders/Lighting/RayShadows.glsl`,
`tools/pixelart/scenes.py`, `tests/pixelart/test_r3_cache.py`; Modify
`Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/NPR_Lighting.glsl`,
`Malt/Pipelines/NPR_Pipeline/Nodes/Render/SceneLighting.py`

**Interfaces:**
- `RayShadows` (one instance per SceneLighting node): `update(scene, opaque_batches) -> bool rebuilt` — collects
  `(obj.matrix, obj.mesh, obj.parameters['ID'], material.parameters['Light Groups.Shadow'])` from the opaque batches,
  world-transforms `mesh_triangles`, builds the BVH only when the cache key changes (frame, matrices bytes, mesh ids),
  uploads 3 SSBOs, binds them at 0/1/2; `shader_callback(shader)` sets uniform `RAY_SHADOWS` (bool) and
  `RAY_BIAS_PX` (float) when present.
- GLSL `RayShadows.glsl`: std430 blocks at bindings 0/1/2 matching R2 layouts; `uniform bool RAY_SHADOWS;`
  `uniform float RAY_BIAS_PX;` `bool ray_occluded(vec3 origin, vec3 dir, float t_max, uint self_id, bool self_shadows,
  uint light_group_bit)` — stack of 48 ints, any-hit, watertight test identical to R2.
  `float pixel_world_size(vec3 position)`: perspective `2 * depth / (PROJECTION[1][1] * RESOLUTION.y)`, orthographic
  (`PROJECTION[3][3] == 1`) `2 / (PROJECTION[1][1] * RESOLUTION.y)`, depth = view-space distance.
- `npr_lit_surface`: if `RAY_SHADOWS` and `shadows`: origin = `position + true_normal() * RAY_BIAS_PX *
  pixel_world_size(position)` (true_normal = geometric normal facing the light side); sun: `dir = -light.direction`,
  `t_max = 1e30`; point/spot: towards `light.position`, `t_max = distance * (1 - 1e-4)`; `S.shadow = ray_occluded(...)`,
  `S.shadow_multiply` as now; skip the shadow-map lookups.
- `SceneLighting` inputs: `Ray Traced Shadows` (bool, default off; enum sockets do not register in the Render graph), `Ray Bias (px)`
  (float, default 1.0). Ray mode: call `RayShadows.update` once per frame, register it in `scene.shader_resources`
  as `'RAY_SHADOWS'`, still render shadow maps for transparent batches only.
- `tools/pixelart/scenes.py`: setup functions the GUI render script calls by name (in-memory edits only, never saved):
  `box_plane` (orthographic top-down camera, 1 m quad caster at z=1 over a ground plane, sun at a known angle),
  `lit_sphere`, `cube_contact`, each also switching the Render graph's SceneLighting to `Ray Traced` and
  `Samples.Grid Size` to 1.

- [ ] Step 1: `test_r3_cache.py` (numpy only, fake scene objects): two `update` calls with the same frame and matrices
  build once; a moved object rebuilds; zero opaque objects -> 1 empty leaf, no exception.
- [ ] Step 2: Implement; GUI renders (RULES) of the 3 scenes + `testmalt.blend` in both modes into
  `build/pixelart/R3/`.
- [ ] Step 3: Checks, quoted in the Report: box_plane shadow pixels vs the analytic rectangle (count of mismatches
  away from the edge = 0, edge within 1 px); lit_sphere shadowed lit-side pixels = 0; cube_contact: no lit pixel row
  between cube and shadow; same frame rendered twice identical; build ms and frame ms.
- [ ] Step 4: Commit `R3: ray-traced hard shadows (Ray Traced Shadows input)`.

### Task R4 (orchestrator): owner comparison

- [ ] Side-by-side zoomed sheet: shadow maps vs ray traced on `testmalt.blend` and on a character file the owner picks;
  timings for a ~120k-triangle scene; results note `docs/pixelart/03-ray-shadows-results.md`.
