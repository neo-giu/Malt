# T01 — 1 px line check tool

Requirements: the spec sections named in plan Task 1
Wave: 1           Depends on: none
Size: S

## Goal
Implement plan Task 1 exactly: `docs/pixelart/06-pixel-cel-plan.md`, section "### Task 1". That section holds
the files, interfaces, test code, implementation code and commands. Follow its steps in order: test or check first,
see it fail (quote the failing line), implement, see it pass, commit once.

tools/pixelart/scenes.py already holds the probe setups (_set_line_width, _frame_objects, _solo, lines_w1, lines_off), committed by the orchestrator: do not rewrite them. Render both setups first (plan Step 5).

## Read first (and only)
- docs/specs/pixelcel/tasks/RULES.md (whole)
- docs/pixelart/06-pixel-cel-plan.md: the header, "Global Constraints", "Review Focus", "File Structure" and
  "### Task 1" (whole)
- docs/pixelart/05-pixel-cel-materials-spec.md: only the sections the task names
- docs/specs/pixelcel/mechanics/*.md (notes from earlier cards, if any)

## Do
1. Follow the plan task's steps in order.
2. If the plan's code does not work as written, fix it inside the fence and record what differed in
   docs/specs/pixelcel/mechanics/line-check.md (max 40 lines).
3. Commit once with the plan's commit message, ending with the line
   `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Do not
- Do not edit files outside: tools/pixelart/line_check.py, tests/pixelart/test_line_check.py, tools/pixelart/scenes.py, docs/pixelart/07-pixel-cel-results.md, docs/specs/pixelcel/mechanics/line-check.md. If you need another file, report it
  and stop.

## Done when
- [ ] `pytest tests/pixelart/test_line_check.py -q` -> 5 passed
- [ ] line_check on build/pixelart/L/lines_w1 vs lines_off -> exit 1, the printed line recorded in docs/pixelart/07-pixel-cel-results.md
- [ ] fast checks pass: `H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart -q`

## Report (last message, max 15 lines)
First line DONE or BLOCKED: <reason>. Files changed · what was done · what was not and why · each check with its result.
