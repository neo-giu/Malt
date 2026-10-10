# both-styles (T08) — differences from the plan code, status: done (orchestrator fixed the 2 open items, refer to 07-pixel-cel-results.md)

Launches: 1 `t08_1` (KOF copy not visible), 2 `t08_2` (3 diagnostic setups, since removed), 3 `t08_3` (final).

Cause of "the KOF copy is not in the render" (also true for the T06 copy render, which was never looked at):
`copy_collection` does `armature.location.x += offset`, but the April armature has an action that keys location.
`render_gui.py` / the render call `frame_set`, the action writes location.x = 0 back, and the KOF copy lands exactly on
April (the 2 characters overlap; the camera was framed on the wrong, pre frame_set, bounds). Proof (blender -b): KOF
armature world x = 1.0 before `frame_set`, 0.0 after; diag_kof_only drew a KOF coloured character at April's place.
Fix needed in BlenderMalt/PixelArtConvert.py (outside this card's fence): offset through a parent Empty, not through
the animated armature location. Workaround in scenes.py: `_copy_collection_beside` (copy, frame_set, Empty at x=1,
parent the copy's root objects to it); the offset survives frame_set (checked in blender -b).

Differences from the plan code:
- Setup uses `_setup_malt_ids()` after the copy and `_use_pixel_lines` (not `setup_pixel_lines` directly) so the `_off`
  setup zeroes Line Width like the T07 setups (line mask = on minus off).
- Outline colour: `outline_value` is a linear colour. ASW 0.1 -> 0.01 (sRGB 25). KOF 0.35 -> 0.1 (linear 0.1 =
  base x0.35 in display terms: 0.35^2.2 = 0.1). Measured: ASW outline sRGB (25, 25, 25) on 1261 of 1410 line px (was
  (89, 89, 89)); KOF outline (13, 36, 49) on the blue skirt = base x0.35 hue kept.
- Plan step "copy to H:/GameDev/Pixelizer": skipped (the orchestrator does it). No push.

Open: line_check on/off = 1 block, at (y 50, x 132) (April's hair/collar, 2x2 line px). T07 April alone was 0 at
240 px wide; the frame here is 396 px wide, so the lattice sampling differs. Fix is in PixelLines.glsl (outside the
fence). Not tuned: ramp stops, hue shift, spec/highlight values (no launches left; the 4 tones and purple shadows
are visible on the sheet at the first values).
