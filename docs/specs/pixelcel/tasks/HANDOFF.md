# Handoff (pixelcel)

Rewritten by the orchestrator after every wave. A fresh orchestrator session reads this first.

## State
- All 8 cards done. Last commit 3ced546. Waiting for the owner review of `docs/pixelart/img/pixel_cel_both.png`.
- Costs: wave 1 $0.76, T06 $0.35, T07 $1.77, T08 $1.35 (blocked, finished by the orchestrator).

## Done
- T01-T04: line_check, detect, cel_ref + presets, PixelCel.glsl. T05 (orchestrator): trees from plans.
- T06: operator, reconvert keeps hand edits, Copy collection. T07: Pixel Lines (lattice diamond rule, Zhang-Suen).
- T08 + orchestrator: both styles on one sheet; outline values linear (ASW 0.01, KOF 0.1); PIXEL_LINES_BLOCK
  junction stage; exact marker line check (`PIXEL_LINES_DEBUG=1`, `line_check.py --marker`): 0 violations
  (both 2937 px, April 1457, border 1878); copy_collection uses delta_location, 1.6 m spacing.

## Carried issues
- Use the marker check, not on-minus-off: a line on a surface of the same colour is invisible to the colour diff.
- render.sh: max 3 launches per card, batch setups. py_compile edited Python before every launch.
- Open: camera crops the KOF copy's right hand; 3 animation frames; frame-time pair (criterion 6).

## Open questions for the owner
- ASW half vs the GGXrd reference, KOF half vs KOF XIII sprites: what to change? (KOF values are still the spec's
  starting values.)

## Next
- After the review: one tuning card (presets.py) + the open items, then sub-project 3 (shadow smoothing) or 2 (export).
