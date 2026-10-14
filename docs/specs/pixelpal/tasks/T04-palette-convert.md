# T04 — Converter builds and wires the palette; palette check

Requirements: the spec sections named in plan Task 4
Wave: 2           Depends on: T03
Size: M

## Goal
Implement plan Task 4 exactly: `docs/pixelart/10-pixel-cel-palette-plan.md`, section "### Task 4". That section holds
the files, interfaces, test code, implementation code and commands. Follow its steps in order: test or check first,
see it fail (quote the failing line), implement, see it pass, commit once.


## Read first (and only)
- docs/specs/pixelpal/tasks/RULES.md (whole)
- docs/pixelart/10-pixel-cel-palette-plan.md: the header, "Global Constraints", "Review Focus", "File Structure" and
  "### Task 4" (whole)
- docs/pixelart/09-pixel-cel-palette-spec.md (whole, it is short)
- docs/specs/pixelpal/mechanics/*.md (notes from earlier cards, if any)

## Do
1. Follow the plan task's steps in order.
2. If the plan's code does not work as written, fix it inside the fence and record what differed in
   docs/specs/pixelpal/mechanics/palette-convert.md (max 40 lines).
3. Commit once with the plan's commit message, ending with the line
   `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Do not
- Do not edit files outside: BlenderMalt/PixelArtConvert.py, tools/pixelart/scenes.py (append only), tools/pixelart/palette_check.py, tools/pixelart/render_gui.py (the RENDER_OUT line only), docs/specs/pixelpal/mechanics/palette-convert.md. If you need another file, report it
  and stop.

## Done when
- [ ] palette_check on pixel_pal_asw, pixel_pal_kof, pixel_pal_dude, pixel_pal_edit -> exit 0, foreign colours 0, colours <= 40 (each quoted)
- [ ] pixel_pal_edit frame holds (255, 0, 0) px (count quoted)
- [ ] marker launch: line_check --marker on pixel_pal_asw and pixel_pal_kof -> total 0, outside 0
- [ ] zoom sheet of asw / kof / dude read by you
- [ ] fast checks pass: `H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart -q`

## Report (last message, max 15 lines)
First line DONE or BLOCKED: <reason>. Files changed · what was done · what was not and why · each check with its result.
