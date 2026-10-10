# Handoff (pixelcel)

Rewritten by the orchestrator after every wave. A fresh orchestrator session reads this first.

## State
- Waves 1-3 done. T07 Pixel Lines (1ffe235, $1.77): line_check total 0 (1457 px; border 1878 px), checked by the orchestrator. Wave 4 (T08) running.
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
- Wave 4: `bash tools/cards/run_cards.sh T08` (card has the outline-colour fact), then owner review.
