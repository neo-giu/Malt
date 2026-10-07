# Malt for pixel-art sprites: analysis (2026-10-07)

Fork: `neo-giu/Malt` (branch `pixelart`), upstream `bnpr/Malt` @ `b5ba805` (= Release 1.0.0, installed in Blender 5.2).
Inputs read (read-only, never saved): `D:/DocuBKP/Blender/testmalt.blend`, `D:/DocuBKP/Downloads/testmalt.blend`,
`D:/DocuBKP/Imagens/Renders/mannequin4renders/malttest.blend`, plus Malt source.

## 1. What Malt already gives us

| Need (from Pixelizer) | Malt today | Where |
|---|---|---|
| Toon bands from a ramp | `NPR_diffuse_shading`: N.L (or half-range) -> 1D gradient texture; constant interpolation = hard bands; offset, light groups, max/add per light | `NPR_Shading2.glsl:51` |
| Specular / rim stops | `NPR_specular_shading`, `rim_light` | `NPR_Shading2.glsl:281`, `ShadingModels.glsl` |
| Custom light response | Light "Shader" material per light (light graph), light groups (4 per material) | `NPR_Lighting.glsl:50`, `NPR_Lighting.py` |
| Lines | Per-material `Line Width` from ID boundaries, depth jump, normal angle (thresholds, px/screen/world units), `LineRender` expands and composites over Color | `NPR_Filters.glsl:198`, `Nodes/LineRender.py`, `Passes/LineComposite.glsl` |
| Pre-pass buffers | Normal+Depth, ID (object/material), custom colour passes; screen passes and full custom Render / Render Layer graphs | `RenderLayer/PrePass.py`, `MainPass.py`, `ScreenPass.py` |
| Extra masks | AO, curvature filters | `NPR_Filters.glsl` |
| Custom code | GLSL functions become nodes automatically (META comments); plugins dir; whole pipelines in Python | `Malt/Pipelines`, `plugins/` |

The owner's files use exactly these: NPR Diffuse (ramp), NPR Specular + Rim Light + Curvature/AO (car), per-material
`line_width_2`, `LineRender`, `SuperSamplingAA` on the final colour.

## 2. Shadows: why they look bad, from the code

`Malt/Render/Lighting.py`, `Malt/Shaders/Lighting/Lighting.glsl`, `NPR_Lighting.glsl`:

1. **Resolution spent on empty space.** Sun shadows are 2048^2 cascades fitted to the *camera frustum* up to
   `Sun Max Distance` (100 units, 4 cascades, distribution 0.9). A sprite-sized character gets a small fraction of those
   texels: blocky, stair-stepped edges (`get_sun_cascades`, `sun_shadowmap_matrix`).
2. **Not stabilised.** Each cascade is the AABB of the frustum slice, recomputed every frame with no texel snapping and
   no fixed size. Any camera move changes texel size and phase: shadow edges crawl and shimmer.
3. **One hard compare, constant bias.** `S.depth < light_uv.z - bias` with `bias = 1e-3` (sun) / `1e-5` (spot/point) in
   NDC depth, so the bias changes with cascade depth range; no slope-scaled or normal-offset bias (the slope term is
   commented out, `Lighting.glsl:144`). Result: acne on lit curves or detached shadows, per scene.
4. **Jitter + accumulation.** `sample_offset` is baked into the shadow matrices and `SuperSamplingAA` averages the
   samples: soft, blended shadow edges = colours that are not in the ramp (bad for indexed pixel art).
5. **Self-shadow switch is per ID only** (`id == shadow_id`): an object either shadows itself everywhere or nowhere.

## 3. What we learned in Pixelizer (keep / avoid)

Keep:
- Colours only from ramps; a cast shadow puts the surface in a chosen ramp slot (no blending).
- Render at the sprite resolution with one decision per pixel (no supersample averaging of colours).
- Snap the root/camera to the pixel grid (stops swimming).
- Exact shadow tests are possible and stable (ray cast agrees with a 4096^2 tight shadow map within 4%).
- Judge every change side by side, zoomed, against a reference, before calling it better.

Avoid (failed there):
- Post-pass pixel filters (despeckle, lone-pixel fusion, erosion) to hide decision noise.
- Per-pixel line decisions on noisy signals (dashed lines).
- Exact shadows with no control for tiny creases (Suzanne's mouth became a blob).

## 4. Proposed first steps

1. **Dev install of the fork** in Blender 5.2 (`scripts/setup_blender_addon.py`), keeping the release install as a
   fallback.
2. **Baseline:** Suzanne (`compositetest.blend` scene) in Malt at sprite resolution, 1 sample, constant ramps, ID lines
   at 1 px; side by side with the Goo composite.
3. **Shadow work, one change at a time, each judged against that baseline:**
   a. Fit the sun shadow to the bounds of the visible objects (one cascade option for sprites).
   b. Stabilise: fixed size, centre snapped to shadow texels.
   c. Normal-offset + slope-scaled bias in world units instead of a constant NDC bias.
   d. Shadow = a ramp slot (no jitter averaging in sprite mode).
   e. Optional later: higher-quality tests (PCF only as a coverage decision, or ray-traced shadows via a BVH texture).
