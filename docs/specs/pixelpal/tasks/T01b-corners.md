# T01b — Corner rules A, B, C (junction spots, tips, overlap corners)

Requirements: the spec sections named in plan Task 1b
Wave: 1           Depends on: T01
Size: M

## Goal
Implement plan Task 1b exactly: `docs/pixelart/10-pixel-cel-palette-plan.md`, section "### Task 1b". That section holds
the files, interfaces, test code, implementation code and commands. Follow its steps in order: test or check first,
see it fail (quote the failing line), implement, see it pass, commit once.

Sprite numbers: docs/pixelart/11-sprite-lines-report.txt (read the summary lines only).

## Read first (and only)
- docs/specs/pixelpal/tasks/RULES.md (whole)
- docs/pixelart/10-pixel-cel-palette-plan.md: the header, "Global Constraints", "Review Focus", "File Structure" and
  "### Task 1b" (whole)
- docs/pixelart/09-pixel-cel-palette-spec.md (whole, it is short)
- docs/specs/pixelpal/mechanics/*.md (notes from earlier cards, if any)

## Do
1. Follow the plan task's steps in order.
2. If the plan's code does not work as written, fix it inside the fence and record what differed in
   docs/specs/pixelpal/mechanics/corners.md (max 40 lines).
3. Commit once with the plan's commit message, ending with the line
   `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Do not
- Do not edit files outside: Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/PixelCel.glsl, Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/FaceSDF.glsl (line_data.y bits only), Malt/Shaders/Passes/PixelLines.glsl, Malt/Pipelines/NPR_Pipeline/Nodes/RenderLayer/PixelLines.py, Malt/PixelArt/presets.py, tests/pixelart/test_pixel_cel_ref.py, tools/pixelart/line_check.py, tests/pixelart/test_line_check.py, tools/pixelart/pixel_cel_debug.mesh.glsl, tools/pixelart/face_sdf_cel.mesh.glsl, tools/pixelart/scenes.py (append only), docs/pixelart/07-pixel-cel-results.md, docs/specs/pixelpal/mechanics/corners.md. If you need another file, report it
  and stop.

## Done when
- [ ] `pytest tests/pixelart -q` -> all pass (line_check +3)
- [ ] marker launch: line_check --marker --rules junctions,tips,overlap_corners on the 4 frames -> 'total': 0, outside 0
- [ ] line_check --marker (no rules) on pixel_rules_off -> 'total': 0
- [ ] kept counts per rule (A, B, C) and per 100 line px quoted next to the sprite ranges; compare_cel 0 mismatches
- [ ] face + hands zoom, rules on vs off, read by you
- [ ] fast checks pass: `H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart -q`

## Report (last message, max 15 lines)
First line DONE or BLOCKED: <reason>. Files changed · what was done · what was not and why · each check with its result.
