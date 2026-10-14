# T02 — zones.py: zones, ramps and the palette (pure Python)

Requirements: the spec sections named in plan Task 2
Wave: 1           Depends on: T01b
Size: M

## Goal
Implement plan Task 2 exactly: `docs/pixelart/10-pixel-cel-palette-plan.md`, section "### Task 2". That section holds
the files, interfaces, test code, implementation code and commands. Follow its steps in order: test or check first,
see it fail (quote the failing line), implement, see it pass, commit once.

No Blender launch in this card.

## Read first (and only)
- docs/specs/pixelpal/tasks/RULES.md (whole)
- docs/pixelart/10-pixel-cel-palette-plan.md: the header, "Global Constraints", "Review Focus", "File Structure" and
  "### Task 2" (whole)
- docs/pixelart/09-pixel-cel-palette-spec.md (whole, it is short)
- docs/specs/pixelpal/mechanics/*.md (notes from earlier cards, if any)

## Do
1. Follow the plan task's steps in order.
2. If the plan's code does not work as written, fix it inside the fence and record what differed in
   docs/specs/pixelpal/mechanics/zones.md (max 40 lines).
3. Commit once with the plan's commit message, ending with the line
   `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Do not
- Do not edit files outside: Malt/PixelArt/zones.py, tests/pixelart/test_zones.py, Malt/PixelArt/presets.py, BlenderMalt/PixelArtConvert.py (the preset loop skip line only), tests/pixelart/test_pixel_cel_ref.py, docs/specs/pixelpal/mechanics/zones.md. If you need another file, report it
  and stop.

## Done when
- [ ] `pytest tests/pixelart -q` -> all pass (zones 14 new)
- [ ] plan Step 6 command on APRL_baseX.png -> the printed clusters / merged line quoted
- [ ] fast checks pass: `H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart -q`

## Report (last message, max 15 lines)
First line DONE or BLOCKED: <reason>. Files changed · what was done · what was not and why · each check with its result.
