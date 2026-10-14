# T01 — KEEP: thin parts never vanish

Requirements: the spec sections named in plan Task 1
Wave: 1           Depends on: none
Size: M

## Goal
Implement plan Task 1 exactly: `docs/pixelart/10-pixel-cel-palette-plan.md`, section "### Task 1". That section holds
the files, interfaces, test code, implementation code and commands. Follow its steps in order: test or check first,
see it fail (quote the failing line), implement, see it pass, commit once.

Owner fact (2026-10-14): since the outline-ring fix (commit d5f29d4) the fingers of April nearly disappear: removed ring pixels become background, and pixel-centre sampling misses sub-pixel fingers. KEEP is the Pixelizer method (H:/GameDev/Pixelizer/src/pixelizer/keep.py, read it): a KEEP part shows wherever it touches a subsample. Malt facts: the pre pass writes PPO.id = ID (uvec4; ID.x = object id, 16 bit hash; ID.y/z/w = custom ids) into the lattice texture t_lattice_id (GL_RGBA16UI) of PixelLines.py; the converter adds a pre pass output node with _pre_pass_node(tree). the April hands material is 5_hands_1_0_0.001.

## Read first (and only)
- docs/specs/pixelpal/tasks/RULES.md (whole)
- docs/pixelart/10-pixel-cel-palette-plan.md: the header, "Global Constraints", "Review Focus", "File Structure" and
  "### Task 1" (whole)
- docs/pixelart/09-pixel-cel-palette-spec.md (whole, it is short)
- docs/specs/pixelpal/mechanics/*.md (notes from earlier cards, if any)

## Do
1. Follow the plan task's steps in order.
2. If the plan's code does not work as written, fix it inside the fence and record what differed in
   docs/specs/pixelpal/mechanics/keep.md (max 40 lines).
3. Commit once with the plan's commit message, ending with the line
   `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Do not
- Do not edit files outside: Malt/PixelArt/detect.py, tests/pixelart/test_pixel_cel_detect.py, Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/PixelCel.glsl (new function only), Malt/Shaders/Passes/PixelLines.glsl, BlenderMalt/PixelArtConvert.py, tools/pixelart/line_check.py, tests/pixelart/test_line_check.py, tools/pixelart/scenes.py (append only), docs/pixelart/07-pixel-cel-results.md, docs/specs/pixelpal/mechanics/keep.md. If you need another file, report it
  and stop.

## Done when
- [ ] `pytest tests/pixelart -q` -> all pass (detect +1, line_check +1)
- [ ] marker launch: line_check --marker on pixel_keep, pixel_keep_off, pixel_cel_both_styles, pixel_lines_border -> 'total': 0 and outside 0 for all four
- [ ] yellow KEEP px in the HANDS_BOX of pixel_keep > 0; opaque px in the box: pixel_keep >= pixel_keep_off (both quoted)
- [ ] compare_cel on pixel_cel_debug -> mismatches 0; hands zoom on vs off read by you
- [ ] fast checks pass: `H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart -q`

## Report (last message, max 15 lines)
First line DONE or BLOCKED: <reason>. Files changed · what was done · what was not and why · each check with its result.
