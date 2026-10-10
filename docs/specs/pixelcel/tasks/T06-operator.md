# T06 — Operator, report, reconvert rules, Copy collection

Requirements: the spec sections named in plan Task 6
Wave: 2           Depends on: T05
Size: M

## Goal
Implement plan Task 6 exactly: `docs/pixelart/06-pixel-cel-plan.md`, section "### Task 6". That section holds
the files, interfaces, test code, implementation code and commands. Follow its steps in order: test or check first,
see it fail (quote the failing line), implement, see it pass, commit once.

The failing run of Step 1 counts as one of the 3 launches: batch it with the same 3 setups.

## Read first (and only)
- docs/specs/pixelcel/tasks/RULES.md (whole)
- docs/pixelart/06-pixel-cel-plan.md: the header, "Global Constraints", "Review Focus", "File Structure" and
  "### Task 6" (whole)
- docs/pixelart/05-pixel-cel-materials-spec.md: only the sections the task names
- docs/specs/pixelcel/mechanics/*.md (notes from earlier cards, if any)

## Do
1. Follow the plan task's steps in order.
2. If the plan's code does not work as written, fix it inside the fence and record what differed in
   docs/specs/pixelcel/mechanics/operator.md (max 40 lines).
3. Commit once with the plan's commit message, ending with the line
   `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Do not
- Do not edit files outside: BlenderMalt/PixelArtConvert.py, BlenderMalt/__init__.py (register line only), BlenderMalt/MaltMaterial.py (one operator line in the panel draw), tools/pixelart/scenes.py (append only), docs/specs/pixelcel/mechanics/operator.md. If you need another file, report it
  and stop.

## Done when
- [ ] ONE launch with setups `pixel_cel_reconvert,pixel_cel_copy_collection,pixel_cel_convert_asw` into build/pixelart/P/t06/ -> EXIT 0, RECONVERT_OK and COPY_OK in their stdout/log
- [ ] build/pixelart/P/t06/pixel_cel_convert_asw/frame_0001.png vs the T05 render build/pixelart/P/t05/pixel_cel_convert_asw/frame_0001.png -> differing px 0
- [ ] fast checks pass: `H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart -q`

## Report (last message, max 15 lines)
First line DONE or BLOCKED: <reason>. Files changed · what was done · what was not and why · each check with its result.
