# Handoff (pixelcel)

Rewritten by the orchestrator after every wave. A fresh orchestrator session reads this first.

## State
- Wave 2 in progress: T05 finished by the orchestrator (commit 25e0196), T06 running.
- T05 reference renders: `build/pixelart/P/t05/<setup>/frame_0001.png`, sheet `build/pixelart/P/t05/sheet.png`
  (April ASW 2 tones + Sss, April KOF 4 tones, Arthur textured).

## Done
- Line probe (orchestrator): Malt Line Width = 1 breaks the 1 px rule (line_check: 1302 px, l_corners 4,
  isolated 12, short 16). Hence Pixel Lines (T07).
- T01 line_check.py (+5 tests) · T02 detect.py (+9) · T03 cel_ref.py, presets.py (+11) · T04 PixelCel.glsl node,
  debug material, compare_cel.py · T05 PixelArtConvert.py (build_tree, convert_material, convert_objects).

## Carried issues
- render.sh: --no-window-focus, 640x400, comma list of setups in one launch. RULES: max 3 launches per card.
- render_gui waits for compiled materials before rendering (Malt restarts its server after a conversion).
- Malt bools must be set through `malt_parameters.bools[key].boolean` (refer to mechanics/build-trees.md).

## Open questions for the owner
- none

## Next
- Wave 2 rest: `bash tools/cards/run_cards.sh T06`, then wave 3 (T07), wave 4 (T08).
