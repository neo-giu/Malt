# Handoff (pixelcel)

Rewritten by the orchestrator after every wave. A fresh orchestrator session reads this first.

## State
- Last wave: 1 · cards T01 T02 T03 T04 · all verified · $0.76
- Last run folder: `build/cards/20261010-174757/`
- Orchestrator check: pixel_cel_debug has tones {0, 2}, 4030 ray-shadowed px, compare_cel 0 mismatches.

## Done
- Line probe (orchestrator): Malt Line Width = 1 breaks the 1 px rule (line_check: 1302 px, l_corners 4,
  isolated 12, short 16). Hence Pixel Lines (T07).
- T01 line_check.py (+5 tests) · T02 detect.py (+9) · T03 cel_ref.py, presets.py (+11) · T04 PixelCel.glsl node,
  debug material, compare_cel.py.

## Carried issues
- none

## Open questions for the owner
- none

## Next
- Wave 2: `bash tools/cards/run_cards.sh T05 T06`
