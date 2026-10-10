# T08 — End to end on April, KOF XIII tuning, owner review

Requirements: the spec sections named in plan Task 8
Wave: 4           Depends on: T07
Size: M

## Goal
Implement plan Task 8 exactly: `docs/pixelart/06-pixel-cel-plan.md`, section "### Task 8". That section holds
the files, interfaces, test code, implementation code and commands. Follow its steps in order: test or check first,
see it fail (quote the failing line), implement, see it pass, commit once.

Do not copy files into H:/GameDev/Pixelizer (the orchestrator does that): skip the plan's copy step and say so. Do not push.

## Read first (and only)
- docs/specs/pixelcel/tasks/RULES.md (whole)
- docs/pixelart/06-pixel-cel-plan.md: the header, "Global Constraints", "Review Focus", "File Structure" and
  "### Task 8" (whole)
- docs/pixelart/05-pixel-cel-materials-spec.md: only the sections the task names
- docs/specs/pixelcel/mechanics/*.md (notes from earlier cards, if any)

## Do
1. Follow the plan task's steps in order.
2. If the plan's code does not work as written, fix it inside the fence and record what differed in
   docs/specs/pixelcel/mechanics/both-styles.md (max 40 lines).
3. Commit once with the plan's commit message, ending with the line
   `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Do not
- Do not edit files outside: Malt/PixelArt/presets.py, tools/pixelart/scenes.py (append only), docs/pixelart/07-pixel-cel-results.md, docs/pixelart/img/pixel_cel_*.png, docs/specs/pixelcel/mechanics/both-styles.md. If you need another file, report it
  and stop.

## Done when
- [ ] render pixel_cel_both_styles -> EXIT 0, sheet docs/pixelart/img/pixel_cel_both.png exists
- [ ] line_check on both vs both_off -> 'total': 0
- [ ] docs/pixelart/07-pixel-cel-results.md covers every spec success criterion with a measured result
- [ ] fast checks pass: `H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart -q`

## Report (last message, max 15 lines)
First line DONE or BLOCKED: <reason>. Files changed · what was done · what was not and why · each check with its result.
