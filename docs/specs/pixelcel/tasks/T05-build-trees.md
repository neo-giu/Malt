# T05 — Build Malt trees from a ConvertPlan

Requirements: the spec sections named in plan Task 5
Wave: 2           Depends on: T04
Size: M

## Goal
Implement plan Task 5 exactly: `docs/pixelart/06-pixel-cel-plan.md`, section "### Task 5". That section holds
the files, interfaces, test code, implementation code and commands. Follow its steps in order: test or check first,
see it fail (quote the failing line), implement, see it pass, commit once.

Step 2 (probe) is required: write the printed Malt node API facts (IO node names, socket names, function keys, custom output storage) into docs/specs/pixelcel/mechanics/build-trees.md, because T06 and T07 depend on them.

## Read first (and only)
- docs/specs/pixelcel/tasks/RULES.md (whole)
- docs/pixelart/06-pixel-cel-plan.md: the header, "Global Constraints", "Review Focus", "File Structure" and
  "### Task 5" (whole)
- docs/pixelart/05-pixel-cel-materials-spec.md: only the sections the task names
- docs/specs/pixelcel/mechanics/*.md (notes from earlier cards, if any)

## Do
1. Follow the plan task's steps in order.
2. If the plan's code does not work as written, fix it inside the fence and record what differed in
   docs/specs/pixelcel/mechanics/build-trees.md (max 40 lines).
3. Commit once with the plan's commit message, ending with the line
   `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Do not
- Do not edit files outside: BlenderMalt/PixelArtConvert.py, tools/pixelart/scenes.py (append only; delete the temporary _probe_tree_api setup before committing), docs/specs/pixelcel/mechanics/build-trees.md. If you need another file, report it
  and stop.

## Done when
- [ ] renders pixel_cel_convert_asw / _kof / _arthur / _dude -> all EXIT 0, PIXEL_CEL_REPORT lines with the expected styles
- [ ] sheet build/pixelart/P/sheet_convert.png, read by you: April shows base colours, 2 tones (ASW) and 4 tones (KOF), no yellow default material
- [ ] fast checks pass: `H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart -q`

## Report (last message, max 15 lines)
First line DONE or BLOCKED: <reason>. Files changed · what was done · what was not and why · each check with its result.
