# KOF XIII L2 mechanics (T05)

Differences from plan Task 5 as written:
- The plan's L2 code is right, its comment is not. `line_data.z` from PixelCel.glsl:133/260 is 1.0 = lit slot, 0.5 =
  darkest slot, 0 = no rule (ASW). The code skips the overlap line when the near part is shadow-only (z > 0.25) and the
  far part is lit (z > 0.75). The plan comment says the opposite. Inverting the test (my first try) left 17 of 23
  overlap px over a lit far part and is wrong.
- `l2_check.py` takes MARKER and COLOUR frames. An overlap px (orange marker) is a violation when its non-line,
  covered 4-neighbours are all lit-slot colours and none is a darkest slot. It cannot tell the near side from the far
  side (no depth in the frame), so a lit near side next to a lit far side counts, a dark near side hides a lit far side.
- Baseline before L2 (pal_marker + pal2 renders of pixel_pal_kof): 168 overlap px, 26 over a lit far part.
- With the inverted test (t05_marker + t05_col): 23 overlap px, 17 over a lit far part.

Open (3 launches used, T05 not verified):
- A setup cannot switch `PIXEL_LINES_DEBUG` on: `pixel_pal_asw_marker` (env set inside the setup) rendered a colour
  frame (line px 0, outside 1184). Malt builds the pipeline once per launch; the env must be set before the launch.
  Marker frames need `PIXEL_LINES_DEBUG=1 render.sh ...` as a separate launch. The 4th setup of that launch hung and
  Blender was killed after 600 s.
- Not measured with the final shader: l2_check, line_check --marker for asw and kof, the tuning round (Task 5 step 3),
  the sheet pixel_pal_both.png, the results note. palette_check on the final colour frames: asw 0, kof 0 (foreign 0).
- Next launch needed: `PIXEL_LINES_DEBUG=1 ... pixel_pal_asw,pixel_pal_kof_l2` then a colour launch of
  `pixel_pal_asw,pixel_pal_kof_l2,pixel_pal_dude`; `pixel_pal_asw_marker` and `pixel_pal_kof_l2_marker` in scenes.py
  are dead and can be removed.
