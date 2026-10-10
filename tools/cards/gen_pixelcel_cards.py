"""Generates docs/specs/pixelcel/tasks/T01..T08 from the plan task list (one plan task = one card)."""
import os

ROOT = os.path.join(os.path.dirname(__file__), '..', '..', 'docs', 'specs', 'pixelcel', 'tasks')
CHECKS = '`H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart -q`'

CARDS = [
    ('T01', 'line-check', '1 px line check tool', 1, 1, 'none', 'S',
     'tools/pixelart/line_check.py, tests/pixelart/test_line_check.py, tools/pixelart/scenes.py, '
     'docs/pixelart/07-pixel-cel-results.md',
     ['`pytest tests/pixelart/test_line_check.py -q` -> 5 passed',
      'line_check on build/pixelart/L/lines_w1 vs lines_off -> exit 1, the printed line recorded in '
      'docs/pixelart/07-pixel-cel-results.md'],
     'tools/pixelart/scenes.py already holds the probe setups (_set_line_width, _frame_objects, _solo, lines_w1, '
     'lines_off), committed by the orchestrator: do not rewrite them. Render both setups first (plan Step 5).'),
    ('T02', 'detect', 'Style detection (pure Python)', 2, 1, 'T01', 'S',
     'Malt/PixelArt/__init__.py, Malt/PixelArt/detect.py, tests/pixelart/test_pixel_cel_detect.py',
     ['`pytest tests/pixelart/test_pixel_cel_detect.py -q` -> 9 passed'], ''),
    ('T03', 'cel-ref', 'Shading reference and presets (pure Python)', 3, 1, 'T02', 'S',
     'Malt/PixelArt/cel_ref.py, Malt/PixelArt/presets.py, tests/pixelart/test_pixel_cel_ref.py',
     ['`pytest tests/pixelart/test_pixel_cel_ref.py -q` -> 11 passed'], ''),
    ('T04', 'pixel-cel-glsl', 'The pixel_cel GLSL node', 4, 1, 'T03', 'M',
     'Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/PixelCel.glsl, '
     'Malt/Pipelines/NPR_Pipeline/Shaders/NPR_MeshShader.glsl (one include line), '
     'tools/pixelart/pixel_cel_debug.mesh.glsl, tools/pixelart/compare_cel.py, tools/pixelart/scenes.py (append only), '
     'docs/pixelart/07-pixel-cel-results.md',
     ['render pixel_cel_debug -> EXIT 0, no GLSL error in stdout.txt',
      '`compare_cel.py build/pixelart/P/pixel_cel_debug/frame_0001.png` -> checked px > 5000, mismatches 0',
      'the debug PNG, read by you, shows Suzanne (not all black, not the yellow default material)'],
     'If the GLSL fails to compile, read stdout.txt for the exact error line and fix the shader. Malt\'s include '
     'root is Malt/Shaders, so "Common/Color.glsl" resolves.'),
    ('T05', 'build-trees', 'Build Malt trees from a ConvertPlan', 5, 2, 'T04', 'M',
     'BlenderMalt/PixelArtConvert.py, tools/pixelart/scenes.py (append only; delete the temporary _probe_tree_api '
     'setup before committing)',
     ['the batch launch -> EXIT 0, PIXEL_CEL_REPORT lines (in build/pixelart/P/t05/stdout.txt) with the expected '
      'styles',
      'sheet build/pixelart/P/sheet_convert.png, read by you: April shows base colours, 2 tones (ASW) and 4 tones '
      '(KOF), no yellow default material'],
     'Batch: run the probe and the 4 converts in ONE launch: setups '
     '`_probe_tree_api,pixel_cel_convert_asw,pixel_cel_convert_kof,pixel_cel_convert_arthur,pixel_cel_convert_dude` '
     'into build/pixelart/P/t05/. The failing run of Step 1 is that same batch before PixelArtConvert.py exists. '
     'Step 2 (probe) is required: write the printed Malt node API facts (IO node names, socket names, function keys, '
     'custom output storage) into docs/specs/pixelcel/mechanics/build-trees.md, because T06 and T07 depend on them.'),
    ('T06', 'operator', 'Operator, report, reconvert rules, Copy collection', 6, 2, 'T05', 'M',
     'BlenderMalt/PixelArtConvert.py, BlenderMalt/__init__.py (register line only), BlenderMalt/MaltMaterial.py '
     '(one operator line in the panel draw), tools/pixelart/scenes.py (append only)',
     ['ONE launch with setups `pixel_cel_reconvert,pixel_cel_copy_collection,pixel_cel_convert_asw` into '
      'build/pixelart/P/t06/ -> EXIT 0, RECONVERT_OK and COPY_OK in their stdout/log',
      'build/pixelart/P/t06/pixel_cel_convert_asw/frame_0001.png vs the T05 render '
      'build/pixelart/P/t05/pixel_cel_convert_asw/frame_0001.png -> differing px 0'],
     'The failing run of Step 1 counts as one of the 3 launches: batch it with the same 3 setups.'),
    ('T07', 'pixel-lines', 'Pixel Lines render-layer node (exactly 1 px lines)', 7, 3, 'T06', 'L',
     'Malt/Pipelines/NPR_Pipeline/Nodes/RenderLayer/PixelLines.py, Malt/Shaders/Passes/PixelLines.glsl, '
     'BlenderMalt/PixelArtConvert.py, Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/PixelCel.glsl, '
     'Malt/PixelArt/cel_ref.py, tools/pixelart/scenes.py (append only), docs/pixelart/07-pixel-cel-results.md',
     ['renders pixel_lines_on / _off / _border / _border_off -> all EXIT 0',
      '`line_check.py` on on vs off and on border vs border_off -> \'total\': 0 for both, line px > 500',
      'compare_cel on pixel_cel_debug still 0 mismatches'],
     'Batch: ONE launch with setups `pixel_lines_on,pixel_lines_off,pixel_lines_border,pixel_lines_border_off,'
     'pixel_cel_debug` into build/pixelart/P/t07/. Size L: commit what works first (lattice pass + decide + composite, with the line_check numbers) and list the '
     'rest in the Report. Never add a filter on colours to pass line_check: fix the line decision at its cause.'),
    ('T08', 'both-styles', 'End to end on April, KOF XIII tuning, owner review', 8, 4, 'T07', 'M',
     'Malt/PixelArt/presets.py, tools/pixelart/scenes.py (append only), docs/pixelart/07-pixel-cel-results.md, '
     'docs/pixelart/img/pixel_cel_*.png',
     ['the last batch launch -> EXIT 0, sheet docs/pixelart/img/pixel_cel_both.png exists',
      'line_check on both vs both_off -> \'total\': 0',
      'docs/pixelart/07-pixel-cel-results.md covers every spec success criterion with a measured result'],
     'Batch: ONE launch per tuning round with setups `pixel_cel_both_styles,pixel_cel_both_styles_off,lines_w1` '
     '(lines_w1 gives the Suzanne frame time for criterion 6) into build/pixelart/P/t08_<round>/; at most 3 rounds. '
     'Do not copy files into H:/GameDev/Pixelizer (the orchestrator does that): skip the plan\'s copy step and say so. '
     'Do not push.'),
]

TEMPLATE = """# {id} — {title}

Requirements: the spec sections named in plan Task {task}
Wave: {wave}           Depends on: {deps}
Size: {size}

## Goal
Implement plan Task {task} exactly: `docs/pixelart/06-pixel-cel-plan.md`, section "### Task {task}". That section holds
the files, interfaces, test code, implementation code and commands. Follow its steps in order: test or check first,
see it fail (quote the failing line), implement, see it pass, commit once.
{extra}

## Read first (and only)
- docs/specs/pixelcel/tasks/RULES.md (whole)
- docs/pixelart/06-pixel-cel-plan.md: the header, "Global Constraints", "Review Focus", "File Structure" and
  "### Task {task}" (whole)
- docs/pixelart/05-pixel-cel-materials-spec.md: only the sections the task names
- docs/specs/pixelcel/mechanics/*.md (notes from earlier cards, if any)

## Do
1. Follow the plan task's steps in order.
2. If the plan's code does not work as written, fix it inside the fence and record what differed in
   docs/specs/pixelcel/mechanics/{slug}.md (max 40 lines).
3. Commit once with the plan's commit message, ending with the line
   `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Do not
- Do not edit files outside: {fence}, docs/specs/pixelcel/mechanics/{slug}.md. If you need another file, report it
  and stop.

## Done when
{done}
- [ ] fast checks pass: {checks}

## Report (last message, max 15 lines)
First line DONE or BLOCKED: <reason>. Files changed · what was done · what was not and why · each check with its result.
"""

for id_, slug, title, task, wave, deps, size, fence, done, extra in CARDS:
    text = TEMPLATE.format(id=id_, slug=slug, title=title, task=task, wave=wave, deps=deps, size=size, fence=fence,
                           done='\n'.join(f'- [ ] {d}' for d in done), checks=CHECKS,
                           extra=('\n' + extra) if extra else '')
    with open(os.path.join(ROOT, f'{id_}-{slug}.md'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    print('wrote', id_)
