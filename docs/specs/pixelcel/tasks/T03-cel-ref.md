# T03 — Shading reference and presets (pure Python)

Requirements: the spec sections named in plan Task 3
Wave: 1           Depends on: T02
Size: S

## Goal
Implement plan Task 3 exactly: `docs/pixelart/06-pixel-cel-plan.md`, section "### Task 3". That section holds
the files, interfaces, test code, implementation code and commands. Follow its steps in order: test or check first,
see it fail (quote the failing line), implement, see it pass, commit once.


## Read first (and only)
- docs/specs/pixelcel/tasks/RULES.md (whole)
- docs/pixelart/06-pixel-cel-plan.md: the header, "Global Constraints", "Review Focus", "File Structure" and
  "### Task 3" (whole)
- docs/pixelart/05-pixel-cel-materials-spec.md: only the sections the task names
- docs/specs/pixelcel/mechanics/*.md (notes from earlier cards, if any)

## Do
1. Follow the plan task's steps in order.
2. If the plan's code does not work as written, fix it inside the fence and record what differed in
   docs/specs/pixelcel/mechanics/cel-ref.md (max 40 lines).
3. Commit once with the plan's commit message, ending with the line
   `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Do not
- Do not edit files outside: Malt/PixelArt/cel_ref.py, Malt/PixelArt/presets.py, tests/pixelart/test_pixel_cel_ref.py, docs/specs/pixelcel/mechanics/cel-ref.md. If you need another file, report it
  and stop.

## Done when
- [ ] `pytest tests/pixelart/test_pixel_cel_ref.py -q` -> 11 passed
- [ ] fast checks pass: `H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart -q`

## Report (last message, max 15 lines)
First line DONE or BLOCKED: <reason>. Files changed · what was done · what was not and why · each check with its result.
