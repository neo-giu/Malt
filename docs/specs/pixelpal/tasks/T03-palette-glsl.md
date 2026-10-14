# T03 — Pixel Cel palette shading

Requirements: the spec sections named in plan Task 3
Wave: 2           Depends on: T02
Size: M

## Goal
Implement plan Task 3 exactly: `docs/pixelart/10-pixel-cel-palette-plan.md`, section "### Task 3". That section holds
the files, interfaces, test code, implementation code and commands. Follow its steps in order: test or check first,
see it fail (quote the failing line), implement, see it pass, commit once.


## Read first (and only)
- docs/specs/pixelpal/tasks/RULES.md (whole)
- docs/pixelart/10-pixel-cel-palette-plan.md: the header, "Global Constraints", "Review Focus", "File Structure" and
  "### Task 3" (whole)
- docs/pixelart/09-pixel-cel-palette-spec.md (whole, it is short)
- docs/specs/pixelpal/mechanics/*.md (notes from earlier cards, if any)

## Do
1. Follow the plan task's steps in order.
2. If the plan's code does not work as written, fix it inside the fence and record what differed in
   docs/specs/pixelpal/mechanics/palette-glsl.md (max 40 lines).
3. Commit once with the plan's commit message, ending with the line
   `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Do not
- Do not edit files outside: Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/PixelCel.glsl, Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/FaceSDF.glsl (line_data.z encoding only), Malt/Shaders/Passes/PixelLines.glsl (composite only), Malt/PixelArt/cel_ref.py, tests/pixelart/test_pixel_cel_ref.py, tools/pixelart/pixel_cel_debug.mesh.glsl, tools/pixelart/face_sdf_cel.mesh.glsl, docs/specs/pixelpal/mechanics/palette-glsl.md. If you need another file, report it
  and stop.

## Done when
- [ ] `pytest tests/pixelart -q` -> all pass
- [ ] launch pixel_cel_debug,face_sdf_l120,pixel_cel_both_styles -> EXIT 0; compare_cel 0 mismatches; face_sdf_check 0.29 %; both_styles vs build/pixelart/P/ring/pixel_cel_both_styles/frame_0001.png -> 0 differing px
- [ ] fast checks pass: `H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart -q`

## Report (last message, max 15 lines)
First line DONE or BLOCKED: <reason>. Files changed · what was done · what was not and why · each check with its result.
