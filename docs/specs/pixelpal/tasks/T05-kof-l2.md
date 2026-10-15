# T05 — KOF XIII L2 rule, tuning round, owner review package

Requirements: the spec sections named in plan Task 5
Wave: 3           Depends on: T04
Size: M

## Goal
Implement plan Task 5 exactly: `docs/pixelart/10-pixel-cel-palette-plan.md`, section "### Task 5". That section holds
the files, interfaces, test code, implementation code and commands. Follow its steps in order: test or check first,
see it fail (quote the failing line), implement, see it pass, commit once.

At most 3 launches in total, tuning included. Do not copy files into H:/GameDev/Pixelizer. Do not push.

## Read first (and only)
- docs/specs/pixelpal/tasks/RULES.md (whole)
- docs/pixelart/10-pixel-cel-palette-plan.md: the header, "Global Constraints", "Review Focus", "File Structure" and
  "### Task 5" (whole)
- docs/pixelart/09-pixel-cel-palette-spec.md (whole, it is short)
- docs/specs/pixelpal/mechanics/*.md (notes from earlier cards, if any)

## Do
1. Follow the plan task's steps in order.
2. If the plan's code does not work as written, fix it inside the fence and record what differed in
   docs/specs/pixelpal/mechanics/kof-l2.md (max 40 lines).
3. Commit once with the plan's commit message, ending with the line
   `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Do not
- Do not edit files outside: Malt/Shaders/Passes/PixelLines.glsl (overlap decision only), Malt/PixelArt/presets.py, tools/pixelart/scenes.py (append only), tools/pixelart/l2_check.py, docs/pixelart/07-pixel-cel-results.md, docs/pixelart/img/pixel_pal_*.png, docs/specs/pixelpal/mechanics/kof-l2.md. If you need another file, report it
  and stop.

## Done when
- [ ] l2_check -> 0 overlap line px over a lit far part
- [ ] line_check --marker FRAME --rules junctions,tips,overlap_corners on pixel_pal_asw and pixel_pal_kof -> total 0, outside 0; palette_check exit 0 on both
- [ ] sheet docs/pixelart/img/pixel_pal_both.png exists; results note covers every spec 09 success criterion
- [ ] fast checks pass: `H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart -q`

## Report (last message, max 15 lines)
First line DONE or BLOCKED: <reason>. Files changed · what was done · what was not and why · each check with its result.
