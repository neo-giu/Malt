# Palette GLSL mechanics (T03)

Differences from plan Task 3 as written:
- `_pixel_cel_zone`: `dFdx/dFdy(vec2)` do not compile, because PixelCel.glsl is also built in the vertex stage
  (`C1115 unable to find compatible overloaded function "dFdx(vec2)"`, then a link error). Fix: `#ifdef PIXEL_SHADER`
  around the footprint; `rho = 1.0` in other stages.
- The slot / zone / colour block is one helper `_pixel_cel_palette(...)` called from the lit end and from the unlit
  branch (unlit = slot 1, or the last slot if the ramp has one), not inline at the end of `pixel_cel`.
- Composite inner lines: `(ld.w > 0.0 && ld.w < 0.75)`. The `> 0.0` guard keeps pixels no material wrote (w = 0) on the
  old path.
- `line_data.z` unlit write is unchanged (`outline_shadow_only ? 1.0 : 0.0`): unlit is never the darkest tone.
- The first launch hung at "ready" after the compile error (blender.exe had to be killed). It counted as launch 1.

Launch 2 (pal_glsl2, pixel_cel_debug, face_sdf_l120, pixel_cel_both_styles): EXIT 0, no shader error in stdout.txt,
compare_cel 0 mismatches of 35280 px, face_sdf_check l120 0.29 % (105 px).

Open: both_styles vs `build/pixelart/P/ring/pixel_cel_both_styles/frame_0001.png` = 4449 differing px, not 0.
The `ring` render (mtime before T01) predates KEEP (2109b8c), the outside-outline change (a4d8c9c) and corner rules A-C
(a3281c2), which all add line pixels (diff pixels are line colour 25,25,25 where `ring` has background or surface).
The render `out2` (before a4d8c9c) differs by 10 px, all single pixels, at junctions and tips. The reference needs a
re-render from the commit before T03, outside this card's fence.
