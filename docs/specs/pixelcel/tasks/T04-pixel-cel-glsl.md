# T04 — The pixel_cel GLSL node

Requirements: the spec sections named in plan Task 4
Wave: 1           Depends on: T03
Size: M

## Goal
Implement plan Task 4 exactly: `docs/pixelart/06-pixel-cel-plan.md`, section "### Task 4". That section holds
the files, interfaces, test code, implementation code and commands. Follow its steps in order: test or check first,
see it fail (quote the failing line), implement, see it pass, commit once.

If the GLSL fails to compile, read stdout.txt for the exact error line and fix the shader. Malt's include root is Malt/Shaders, so "Common/Color.glsl" resolves.

## Read first (and only)
- docs/specs/pixelcel/tasks/RULES.md (whole)
- docs/pixelart/06-pixel-cel-plan.md: the header, "Global Constraints", "Review Focus", "File Structure" and
  "### Task 4" (whole)
- docs/pixelart/05-pixel-cel-materials-spec.md: only the sections the task names
- docs/specs/pixelcel/mechanics/*.md (notes from earlier cards, if any)

## Do
1. Follow the plan task's steps in order.
2. If the plan's code does not work as written, fix it inside the fence and record what differed in
   docs/specs/pixelcel/mechanics/pixel-cel-glsl.md (max 40 lines).
3. Commit once with the plan's commit message, ending with the line
   `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Do not
- Do not edit files outside: Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/PixelCel.glsl, Malt/Pipelines/NPR_Pipeline/Shaders/NPR_MeshShader.glsl (one include line), tools/pixelart/pixel_cel_debug.mesh.glsl, tools/pixelart/compare_cel.py, tools/pixelart/scenes.py (append only), docs/pixelart/07-pixel-cel-results.md, docs/specs/pixelcel/mechanics/pixel-cel-glsl.md. If you need another file, report it
  and stop.

## Done when
- [ ] render pixel_cel_debug -> EXIT 0, no GLSL error in stdout.txt
- [ ] `compare_cel.py build/pixelart/P/pixel_cel_debug/frame_0001.png` -> checked px > 5000, mismatches 0
- [ ] the debug PNG, read by you, shows Suzanne (not all black, not the yellow default material)
- [ ] fast checks pass: `H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart -q`

## Report (last message, max 15 lines)
First line DONE or BLOCKED: <reason>. Files changed · what was done · what was not and why · each check with its result.
