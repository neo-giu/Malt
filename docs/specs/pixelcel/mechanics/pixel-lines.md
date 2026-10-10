# pixel-lines (T07) — differences from the plan code, status: done

Launch 1 (all five setups, EXIT 0): the plan's decision gave line_check totals 44 (on/off) and 79 (border), all `blocks`
(2 px wide runs where a third surface or a thin part sits between two lattice samples). Launch 2 (with the fix): 0 / 0.

Differences from the plan code:
- `PixelLines.glsl` has a `VERTEX_SHADER` block (`DEFAULT_SCREEN_VERTEX_SHADER`): the plan only had the pixel shader.
- Depth: the pre pass stores screen depth, so the decision compares `abs(depth_to_z(d))` (Common.glsl), not `.w`.
- Inner lines only on covered pixels (`line_data` is 0 on the background).
- Cause of the 2x2 blocks is in the decision (two transitions around one edge sample, both pixels draw). Fix: a
  Zhang-Suen thinning stage (`PIXEL_LINES_ZS`, `zs_sub` 0/1, 3 iterations) between prune and a second thin + prune.
  It was tested first in numpy on the launch 1 masks (0 violations at 2 iterations), then ported; the render matched.
  No colour filter is involved: it only removes line pixels.
- The node has only `Scene`, `Color`, `Line Color`, `Pixel Line Data`, `Depth Threshold`. `Normal Depth`, `ID` and
  `Min Line` from the card are not inputs: the node makes its own lattice pass and the prune size is fixed at 3 px.
  Without `Scene` or `Pixel Line Data` the node passes `Color` through.
- Custom main pass output: `Pixel Line Data` is added to the world's custom pass IO (`world.malt_graph_types[<Mesh
  graph>].custom_passes['Default'].io['MAIN_PASS_PIXEL_SHADER'].outputs`, type vec4), not to a tree's IO node. Then
  every main-pass IO node and every `MainPass` function node gets `setup()`. Unlinked, the output is a uniform.
- `setup_pixel_lines(scene, enabled=True)` finds nodes by `function_type` (`LineRender`, `MainPass`, `PrePass`,
  `PixelLines`). Off moves the Color links back to LineRender. LineRender stays in the tree.
- The unlinked `Line Width` of a converted tree is a uniform, so LineRender still draws lines when Pixel Lines is off.
  The `_off` setups zero it (`_use_pixel_lines` in scenes.py) so on minus off is the line mask.
- Step 5: the `ilm.a` darkening block is gone from `PixelCel.glsl`; compare_cel still has 0 mismatches.
- Not run: the plan's "fails first" render (the stub raises TypeError); the card allows one batch launch only.
- Not done: 3 animation frames.
