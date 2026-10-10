# T07 — Pixel Lines render-layer node (exactly 1 px lines)

Requirements: the spec sections named in plan Task 7
Wave: 3           Depends on: T06
Size: L

## Goal
Implement plan Task 7 exactly: `docs/pixelart/06-pixel-cel-plan.md`, section "### Task 7". That section holds
the files, interfaces, test code, implementation code and commands. Follow its steps in order: test or check first,
see it fail (quote the failing line), implement, see it pass, commit once.

Size L: commit what works first (lattice pass + decide + composite, with the line_check numbers) and list the rest in the Report. Never add a filter on colours to pass line_check: fix the line decision at its cause.

## Read first (and only)
- docs/specs/pixelcel/tasks/RULES.md (whole)
- docs/pixelart/06-pixel-cel-plan.md: the header, "Global Constraints", "Review Focus", "File Structure" and
  "### Task 7" (whole)
- docs/pixelart/05-pixel-cel-materials-spec.md: only the sections the task names
- docs/specs/pixelcel/mechanics/*.md (notes from earlier cards, if any)

## Do
1. Follow the plan task's steps in order.
2. If the plan's code does not work as written, fix it inside the fence and record what differed in
   docs/specs/pixelcel/mechanics/pixel-lines.md (max 40 lines).
3. Commit once with the plan's commit message, ending with the line
   `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Do not
- Do not edit files outside: Malt/Pipelines/NPR_Pipeline/Nodes/RenderLayer/PixelLines.py, Malt/Shaders/Passes/PixelLines.glsl, BlenderMalt/PixelArtConvert.py, Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/PixelCel.glsl, Malt/PixelArt/cel_ref.py, tools/pixelart/scenes.py (append only), docs/pixelart/07-pixel-cel-results.md, docs/specs/pixelcel/mechanics/pixel-lines.md. If you need another file, report it
  and stop.

## Done when
- [ ] renders pixel_lines_on / _off / _border / _border_off -> all EXIT 0
- [ ] `line_check.py` on on vs off and on border vs border_off -> 'total': 0 for both, line px > 500
- [ ] compare_cel on pixel_cel_debug still 0 mismatches
- [ ] fast checks pass: `H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart -q`

## Report (last message, max 15 lines)
First line DONE or BLOCKED: <reason>. Files changed · what was done · what was not and why · each check with its result.
