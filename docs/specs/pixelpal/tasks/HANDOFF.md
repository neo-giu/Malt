# Handoff (pixelpal)

Rewritten by the orchestrator after every wave. A fresh orchestrator session reads this first.

## State
- T01 KEEP done (2109b8c). Owner review 2: outline moved OUTSIDE the model (a4d8c9c, orchestrator): fingers keep their skin, outside 0, L corners 0; 26 overlap/outline 2x2 spots left for rule A (T01b).
- Previous batch: pixelcel (done, refer to docs/specs/pixelcel/tasks/HANDOFF.md). Outline ring fix d5f29d4.

## Waves
| Wave | Cards | Goal |
|---|---|---|
| 1 | T01 KEEP, T01b corner rules A-C, T02 zones.py | fingers never vanish; junction spots, tips, overlap corners; zones + palette |
| 2 | T03 palette GLSL, T04 converter + palette_check | April / Dude in palette colours only |
| 3 | T05 KOF L2 + tuning + owner package | owner review |

## Carried issues
- Marker line check only (`PIXEL_LINES_DEBUG=1`, `line_check.py --marker`), outside must be 0.
- Max 3 launches per card; py_compile before a launch. Heredocs in Git Bash lose backslashes: edit code with the
  Edit tool or a Python file, not inline escapes.

## Next
- After the owner approves plan 10: `bash tools/cards/run_cards.sh T01b T02` (background).
