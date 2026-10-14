"""Generates docs/specs/pixelpal/tasks/T01..T05 from the plan task list (one plan task = one card)."""
import os

ROOT = os.path.join(os.path.dirname(__file__), '..', '..', 'docs', 'specs', 'pixelpal', 'tasks')
CHECKS = '`H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart -q`'

CARDS = [
    ('T01', 'keep', 'KEEP: thin parts never vanish', 1, 1, 'none', 'M',
     'Malt/PixelArt/detect.py, tests/pixelart/test_pixel_cel_detect.py, '
     'Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/PixelCel.glsl (new function only), '
     'Malt/Shaders/Passes/PixelLines.glsl, BlenderMalt/PixelArtConvert.py, tools/pixelart/line_check.py, '
     'tests/pixelart/test_line_check.py, tools/pixelart/scenes.py (append only), docs/pixelart/07-pixel-cel-results.md',
     ['`pytest tests/pixelart -q` -> all pass (detect +1, line_check +1)',
      'marker launch: line_check --marker on pixel_keep, pixel_keep_off, pixel_cel_both_styles, pixel_lines_border -> '
      "'total': 0 and outside 0 for all four",
      'yellow KEEP px in the HANDS_BOX of pixel_keep > 0; opaque px in the box: pixel_keep >= pixel_keep_off (both quoted)',
      'compare_cel on pixel_cel_debug -> mismatches 0; hands zoom on vs off read by you'],
     'Owner fact (2026-10-14): since the outline-ring fix (commit d5f29d4) the fingers of April nearly disappear: removed '
     'ring pixels become background, and pixel-centre sampling misses sub-pixel fingers. KEEP is the Pixelizer method '
     '(H:/GameDev/Pixelizer/src/pixelizer/keep.py, read it): a KEEP part shows wherever it touches a subsample. '
     'Malt facts: the pre pass writes PPO.id = ID (uvec4; ID.x = object id, 16 bit hash; ID.y/z/w = custom ids) into '
     'the lattice texture t_lattice_id (GL_RGBA16UI) of PixelLines.py; the converter adds a pre pass output node with '
     '_pre_pass_node(tree). the April hands material is 5_hands_1_0_0.001.'),
    ('T01b', 'corners', 'Corner rules A, B, C (junction spots, tips, overlap corners)', '1b', 1, 'T01', 'M',
     'Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/PixelCel.glsl, '
     'Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/FaceSDF.glsl (line_data.y bits only), '
     'Malt/Shaders/Passes/PixelLines.glsl, Malt/Pipelines/NPR_Pipeline/Nodes/RenderLayer/PixelLines.py, '
     'Malt/PixelArt/presets.py, tests/pixelart/test_pixel_cel_ref.py, tools/pixelart/line_check.py, '
     'tests/pixelart/test_line_check.py, tools/pixelart/pixel_cel_debug.mesh.glsl, tools/pixelart/face_sdf_cel.mesh.glsl, '
     'tools/pixelart/scenes.py (append only), docs/pixelart/07-pixel-cel-results.md',
     ['`pytest tests/pixelart -q` -> all pass (line_check +3)',
      "marker launch: line_check --marker --rules junctions,tips,overlap_corners on the 4 frames -> 'total': 0, outside 0",
      "line_check --marker (no rules) on pixel_rules_off -> 'total': 0",
      'kept counts per rule (A, B, C) and per 100 line px quoted next to the sprite ranges; compare_cel 0 mismatches',
      'face + hands zoom, rules on vs off, read by you'],
     'Sprite numbers: docs/pixelart/11-sprite-lines-report.txt (read the summary lines only). '
     'Orchestrator facts (commit a4d8c9c, after the plan was written): the silhouette outline is now OUTSIDE the model '
     '(ring kinds SILHOUETTE / KEEP are uncovered background pixels; every other kind is a covered pixel); gb stores '
     'the fill offset -2..2 as (offset + 2) / 4 (decode: p + ivec2(round(gb * 4.0)) - 2), so the plan text '
     '"q + offset(gb)" means that decode; _surface(q) counts every covered kind, line or not. line_check already '
     'exempts needed L corners (beside a surface pixel). Marker results before this card (build/pixelart/P/out_marker3, '
     'out_marker4): outside 0, l_corners 0; 2x2 blocks where overlap lines meet the outline: both styles 16, April 8, '
     'border 2. Rule A must classify these: keep junctions (3+ runs on the ring), and every other block must be broken '
     'without exposing the model; quote the before/after block counts.'),
    ('T02', 'zones', 'zones.py: zones, ramps and the palette (pure Python)', 2, 1, 'T01b', 'M',
     'Malt/PixelArt/zones.py, tests/pixelart/test_zones.py, Malt/PixelArt/presets.py, '
     'BlenderMalt/PixelArtConvert.py (the preset loop skip line only), tests/pixelart/test_pixel_cel_ref.py',
     ['`pytest tests/pixelart -q` -> all pass (zones 14 new)',
      'plan Step 6 command on APRL_baseX.png -> the printed clusters / merged line quoted'],
     'No Blender launch in this card.'),
    ('T03', 'palette-glsl', 'Pixel Cel palette shading', 3, 2, 'T02', 'M',
     'Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/PixelCel.glsl, '
     'Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/FaceSDF.glsl (line_data.z encoding only), '
     'Malt/Shaders/Passes/PixelLines.glsl (composite only), Malt/PixelArt/cel_ref.py, tests/pixelart/test_pixel_cel_ref.py, '
     'tools/pixelart/pixel_cel_debug.mesh.glsl, tools/pixelart/face_sdf_cel.mesh.glsl',
     ['`pytest tests/pixelart -q` -> all pass',
      'launch pixel_cel_debug,face_sdf_l120,pixel_cel_both_styles -> EXIT 0; compare_cel 0 mismatches; '
      'face_sdf_check 0.29 %; both_styles vs build/pixelart/P/ring/pixel_cel_both_styles/frame_0001.png -> 0 differing px'],
     ''),
    ('T04', 'palette-convert', 'Converter builds and wires the palette; palette check', 4, 2, 'T03', 'M',
     'BlenderMalt/PixelArtConvert.py, tools/pixelart/scenes.py (append only), tools/pixelart/palette_check.py, '
     'tools/pixelart/render_gui.py (the RENDER_OUT line only)',
     ['palette_check on pixel_pal_asw, pixel_pal_kof, pixel_pal_dude, pixel_pal_edit -> exit 0, foreign colours 0, '
      'colours <= 40 (each quoted)',
      'pixel_pal_edit frame holds (255, 0, 0) px (count quoted)',
      'pixel_pal_asw_bias: palette_check exit 0, zone-boundary pairs lower than pixel_pal_asw (both quoted)',
      'marker launch: line_check --marker on pixel_pal_asw and pixel_pal_kof -> total 0, outside 0',
      'zoom sheet of asw / kof / dude read by you'],
     ''),
    ('T05', 'kof-l2', 'KOF XIII L2 rule, tuning round, owner review package', 5, 3, 'T04', 'M',
     'Malt/Shaders/Passes/PixelLines.glsl (overlap decision only), Malt/PixelArt/presets.py, '
     'tools/pixelart/scenes.py (append only), tools/pixelart/l2_check.py, docs/pixelart/07-pixel-cel-results.md, '
     'docs/pixelart/img/pixel_pal_*.png',
     ['l2_check -> 0 overlap line px over a lit far part',
      'line_check --marker on pixel_pal_asw and pixel_pal_kof -> total 0, outside 0; palette_check exit 0 on both',
      'sheet docs/pixelart/img/pixel_pal_both.png exists; results note covers every spec 09 success criterion'],
     'At most 3 launches in total, tuning included. Do not copy files into H:/GameDev/Pixelizer. Do not push.'),
]

TEMPLATE = """# {id} — {title}

Requirements: the spec sections named in plan Task {task}
Wave: {wave}           Depends on: {deps}
Size: {size}

## Goal
Implement plan Task {task} exactly: `docs/pixelart/10-pixel-cel-palette-plan.md`, section "### Task {task}". That section holds
the files, interfaces, test code, implementation code and commands. Follow its steps in order: test or check first,
see it fail (quote the failing line), implement, see it pass, commit once.
{extra}

## Read first (and only)
- docs/specs/pixelpal/tasks/RULES.md (whole)
- docs/pixelart/10-pixel-cel-palette-plan.md: the header, "Global Constraints", "Review Focus", "File Structure" and
  "### Task {task}" (whole)
- docs/pixelart/09-pixel-cel-palette-spec.md (whole, it is short)
- docs/specs/pixelpal/mechanics/*.md (notes from earlier cards, if any)

## Do
1. Follow the plan task's steps in order.
2. If the plan's code does not work as written, fix it inside the fence and record what differed in
   docs/specs/pixelpal/mechanics/{slug}.md (max 40 lines).
3. Commit once with the plan's commit message, ending with the line
   `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Do not
- Do not edit files outside: {fence}, docs/specs/pixelpal/mechanics/{slug}.md. If you need another file, report it
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
