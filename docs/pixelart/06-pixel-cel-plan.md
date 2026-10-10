# Pixel Cel Materials and Converter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> In this project the owner's chosen executor is the `card-pipeline` skill (one fresh headless Sonnet session per task).

**Goal:** One click turns imported characters (ASW/GGXrd, generic textured, untextured) into Malt cel-shaded
pixel-art materials, in an ASW or a KOF XIII style, with lines that are always exactly 1 px.

**Architecture:** One GLSL library function `pixel_cel` (a Malt node) does all shading. A pure-Python core
(`Malt/PixelArt/`) detects the source style, picks textures and holds the presets and a Python reference of the shading
rules; a Blender module (`BlenderMalt/PixelArtConvert.py`) builds the Malt node trees and the operator. Lines come from
a new render-layer node `Pixel Lines` (half-pixel lattice pre pass + 1 px line decision), because Malt's own Line Width
breaks the 1 px rule.

**Tech Stack:** Malt fork (`H:/GameDev/Malt`, branch `pixelart`), GLSL 4.x, Python 3.13 + numpy, Blender 5.2,
pytest (`H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart -q`).

**Spec:** `docs/pixelart/05-pixel-cel-materials-spec.md` (read it before any task).

## Global Constraints

- Every line (outline and inner line) is exactly 1 px thick, no thickness variation anywhere for any reason; `Col.A`
  only switches the outline on (`>= 0.5`) or off (`< 0.5`). There is no line width input.
- Never save or modify the owner's `.blend` files from tests or tools runs; render only from
  `H:/GameDev/Pixelizer/content/malt/` copies, with in-memory edits (setup functions in `tools/pixelart/scenes.py`).
- The converter never changes or deletes the original Cycles/EEVEE material nodes; it only sets `material.malt`.
- No post-pass filters on colours. The line pass decides line pixels only.
- Enum inputs do not register as Render-graph sockets; use bool/int/float inputs.
- Malt cannot render in Blender background mode: render tests use `tools/pixelart/render.sh` (GUI launch, quits
  without saving). Background mode (`blender -b`) is fine for reading data only.
- Pure-Python modules under `Malt/PixelArt/` must not import `bpy` or OpenGL (they are unit tested outside Blender).
- Collections that are off for render in the owner's file are turned on in memory by the setup (`_solo`), never saved.
- Commit after each task; push the fork (`git push origin pixelart`) when a task is verified.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. Materials that share one image set (April: 7 materials, 1 `APRL_base`): one shared tree, and a hand edit on one
   material's tree shows on all of them. Test: Task 6 `test_shared_tree_key`.
2. Image paths that are relative (`//..\\..\\`), use backslashes, or point to missing files: detection must still work
   and report the missing file, never raise. Test: Task 2 `test_relative_and_missing_paths`.
3. A material with no node tree at all (`use_nodes` off) or no BSDF: untextured from the viewport colour, no crash.
   Test: Task 2 `test_no_nodes_material`.
4. Reconvert after the owner edited an input or added a node: the edit stays. Test: Task 6
   `test_reconvert_keeps_hand_edits` (render setup).
5. Lines where two characters overlap or touch the frame border: still 1 px, no line along the image border.
   Test: Task 7 `test_border_and_overlap`.

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `tools/pixelart/line_check.py` | numpy check of the 1 px line rule on a line mask | 1 |
| `tests/pixelart/test_line_check.py` | tests for it | 1 |
| `Malt/PixelArt/__init__.py` | package marker | 2 |
| `Malt/PixelArt/detect.py` | material description -> `ConvertPlan` (style, textures, warnings) | 2 |
| `tests/pixelart/test_pixel_cel_detect.py` | detection tests | 2 |
| `Malt/PixelArt/cel_ref.py` | Python reference of the shading rules + KOF shadow colour | 3 |
| `Malt/PixelArt/presets.py` | ASW and KOF XIII input values | 3 |
| `tests/pixelart/test_pixel_cel_ref.py` | reference + preset tests | 3 |
| `Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/PixelCel.glsl` | the `pixel_cel` node | 4 |
| `Malt/Pipelines/NPR_Pipeline/Shaders/NPR_MeshShader.glsl` | include PixelCel.glsl | 4 |
| `tools/pixelart/pixel_cel_debug.mesh.glsl` | debug material: tone, s, shadowed | 4 |
| `tools/pixelart/compare_cel.py` | per-pixel check of the debug render against `cel_ref` | 4 |
| `BlenderMalt/PixelArtConvert.py` | describe materials (bpy -> dict), build trees, operator, report | 5, 6 |
| `BlenderMalt/__init__.py` | register the operator | 6 |
| `Malt/Pipelines/NPR_Pipeline/Nodes/RenderLayer/PixelLines.py` | lattice pre pass + line passes | 7 |
| `Malt/Shaders/Passes/PixelLines.glsl` | line decision, thinning, composite shaders | 7 |
| `tools/pixelart/scenes.py` | render setups for every task | 1-8 |
| `docs/pixelart/07-pixel-cel-results.md` | measurements, sheets, owner review | 4, 7, 8 |

---

### Task 1: 1 px line check tool

**Files:**
- Create: `tools/pixelart/line_check.py`
- Create: `tests/pixelart/test_line_check.py`
- Modify: `tools/pixelart/scenes.py` (the `_set_line_width`, `_frame_objects`, `_solo`, `_collection_objects`,
  `lines_w1`, `lines_off` helpers are already in the working tree from the line probe: commit them in this task)

**Interfaces:**
- Produces: `line_violations(mask: np.ndarray) -> dict` with integer counts `blocks` (2x2 all-line), `l_corners`
  (pixel-perfect breaks), `isolated` (no 8-neighbour), `short` (8-connected pieces under 3 px, counted in pixels),
  and `total` (sum). `line_mask(with_lines: np.ndarray, without_lines: np.ndarray) -> np.ndarray[bool]`.
  CLI: `python tools/pixelart/line_check.py WITH.png WITHOUT.png` prints the dict and exits 1 when total > 0.

- [ ] **Step 1: Write the failing test**

```python
# tests/pixelart/test_line_check.py
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'tools', 'pixelart'))
from line_check import line_violations, line_mask


def _mask(rows):
    return np.array([[c == '#' for c in row] for row in rows])


def test_clean_diagonal_and_straight_lines_pass():
    m = _mask([
        '#.....',
        '.#....',
        '..####',
        '......',
    ])
    assert line_violations(m)['total'] == 0


def test_2x2_block_fails():
    m = _mask(['....', '.##.', '.##.', '....'])
    assert line_violations(m)['blocks'] == 1


def test_l_corner_fails():
    # the middle pixel of an L (one horizontal and one vertical neighbour, no diagonal) is a doubled step
    m = _mask(['#...', '##..', '.##.', '..##'])
    assert line_violations(m)['l_corners'] > 0


def test_isolated_and_short_pieces_fail():
    m = _mask(['#.....', '......', '...##.', '......'])
    v = line_violations(m)
    assert v['isolated'] == 1
    assert v['short'] == 3  # the isolated pixel and the 2 px piece


def test_line_mask_is_the_pixel_difference():
    a = np.zeros((2, 2, 3), dtype=np.uint8)
    b = a.copy()
    b[0, 1] = 255
    assert line_mask(b, a).tolist() == [[False, True], [False, False]]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart/test_line_check.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'line_check'`. Quote the failing line in the commit body.

- [ ] **Step 3: Write minimal implementation**

```python
# tools/pixelart/line_check.py
"""Checks the 1 px line rule on a line mask.  python line_check.py WITH.png WITHOUT.png
The line mask is the set of pixels that differ between a render with lines and the same render without lines."""
import sys

import numpy as np


def line_mask(with_lines, without_lines):
    a = np.asarray(with_lines).astype(int)
    b = np.asarray(without_lines).astype(int)
    if a.ndim == 3:
        return np.abs(a[..., :3] - b[..., :3]).max(axis=2) > 0
    return a != b


def _neighbours(mask):
    p = np.pad(mask, 1)
    return {
        'up': p[:-2, 1:-1], 'dn': p[2:, 1:-1], 'lf': p[1:-1, :-2], 'rt': p[1:-1, 2:],
        'ul': p[:-2, :-2], 'ur': p[:-2, 2:], 'dl': p[2:, :-2], 'dr': p[2:, 2:],
    }


def _components(mask):
    # 8-connected components: list of pixel lists
    todo = set(zip(*np.nonzero(mask)))
    out = []
    while todo:
        comp, stack = [], [todo.pop()]
        while stack:
            y, x = stack.pop()
            comp.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    q = (y + dy, x + dx)
                    if q in todo:
                        todo.remove(q)
                        stack.append(q)
        out.append(comp)
    return out


def line_violations(mask):
    mask = np.asarray(mask, dtype=bool)
    n = _neighbours(mask)
    blocks = int((mask[:-1, :-1] & mask[1:, :-1] & mask[:-1, 1:] & mask[1:, 1:]).sum())
    ortho = n['up'].astype(int) + n['dn'] + n['lf'] + n['rt']
    diag = n['ul'] | n['ur'] | n['dl'] | n['dr']
    l_corners = int((mask & (n['up'] ^ n['dn']) & (n['lf'] ^ n['rt']) & (ortho == 2) & ~diag).sum())
    count8 = ortho + n['ul'] + n['ur'] + n['dl'] + n['dr']
    isolated = int((mask & (count8 == 0)).sum())
    short = sum(len(c) for c in _components(mask) if len(c) < 3)
    return {'blocks': blocks, 'l_corners': l_corners, 'isolated': isolated, 'short': short,
            'total': blocks + l_corners + isolated + short}


if __name__ == '__main__':
    from PIL import Image
    with_lines = np.array(Image.open(sys.argv[1]).convert('RGB'))
    without_lines = np.array(Image.open(sys.argv[2]).convert('RGB'))
    mask = line_mask(with_lines, without_lines)
    result = line_violations(mask)
    print('line px', int(mask.sum()), result)
    sys.exit(1 if result['total'] > 0 else 0)
```

Note: an `isolated` pixel is also counted in `short`; `total` counts it twice on purpose (any value > 0 fails).

- [ ] **Step 4: Run test to verify it passes**

Run: `H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart/test_line_check.py -q`
Expected: 5 passed.

- [ ] **Step 5: Record the Malt line probe**

Run:
```bash
cd /h/GameDev/Malt
for S in lines_w1 lines_off; do RENDER_TIMEOUT=200 bash tools/pixelart/render.sh /h/GameDev/Pixelizer/content/malt/testmalt.blend build/pixelart/L/$S 1 $S; done
/h/GameDev/Pixelizer/.venv/Scripts/python tools/pixelart/line_check.py build/pixelart/L/lines_w1/frame_0001.png build/pixelart/L/lines_off/frame_0001.png
```
Expected: exit 1, about `line px 1302 {'blocks': 0, 'l_corners': 12, 'isolated': 12, ...}`. Create
`docs/pixelart/07-pixel-cel-results.md` with a section `## Line probe (Malt Line Width = 1)` holding the printed line.

- [ ] **Step 6: Commit**

```bash
git add tools/pixelart/line_check.py tests/pixelart/test_line_check.py tools/pixelart/scenes.py docs/pixelart/07-pixel-cel-results.md
git commit -m "pixelart: 1 px line check tool; Malt Line Width probe breaks the rule (L corners, gaps, dots)"
```

---

### Task 2: Style detection (pure Python)

**Files:**
- Create: `Malt/PixelArt/__init__.py` (empty)
- Create: `Malt/PixelArt/detect.py`
- Create: `tests/pixelart/test_pixel_cel_detect.py`

**Interfaces:**
- Consumes: nothing.
- Produces (used by Tasks 5, 6):
  - A material description is a dict:
    `{'name': str, 'images': [{'name': str, 'filepath': str, 'colorspace': str, 'feeds_base': bool,
    'size': (w, h), 'uv_map': str or None}], 'base_color': (r, g, b, a) or None, 'display_color': (r, g, b, a),
    'has_nodes': bool}`. `filepath` is already absolute (Task 5 resolves `//` paths with `bpy.path.abspath`).
  - `ConvertPlan` dataclass: `style: str` (one of `'asw'`, `'asw_decal'`, `'asw_eyeshine'`, `'generic'`,
    `'untextured'`), `textures: dict[str, str]` (keys from `'base'`, `'sss'`, `'ilm'`, `'decal'`, `'normal'`; values
    absolute paths), `base_color: tuple`, `uv_map: str or None`, `use_vertex_color: bool`, `warnings: list[str]`,
    property `key -> str` (equal for materials with the same style, textures and base colour).
  - `detect(description: dict, listdir=os.listdir, exists=os.path.exists) -> ConvertPlan`.

- [ ] **Step 1: Write the failing test**

```python
# tests/pixelart/test_pixel_cel_detect.py
from Malt.PixelArt.detect import detect

APRIL_DIR = 'H:/Blender/gultygear/GGXrd - April'
APRIL_FILES = ['APRL_Sss.png', 'APRL_base.png', 'APRL_baseX.png', 'APRL_decal.png', 'APRL_decalX.png',
               'APRL_ilm.png', 'xps.xps']


def _fs(files_by_dir):
    def listdir(path):
        return files_by_dir.get(path.replace('\\', '/').rstrip('/'), [])

    def exists(path):
        path = path.replace('\\', '/')
        folder, _, name = path.rpartition('/')
        return name in files_by_dir.get(folder, [])
    return listdir, exists


def _image(name, filepath, feeds_base=True, colorspace='sRGB', size=(1024, 1024), uv_map='UV1'):
    return {'name': name, 'filepath': filepath, 'colorspace': colorspace, 'feeds_base': feeds_base,
            'size': size, 'uv_map': uv_map}


def _material(name, images=(), base_color=None, has_nodes=True):
    return {'name': name, 'images': list(images), 'base_color': base_color,
            'display_color': (0.8, 0.8, 0.8, 1.0), 'has_nodes': has_nodes}


def test_april_body_is_asw():
    listdir, exists = _fs({APRIL_DIR: APRIL_FILES})
    m = _material('5_body_1_0_0.001', [_image('APRL_baseX.png', APRIL_DIR + '\\APRL_baseX.png')])
    plan = detect(m, listdir, exists)
    assert plan.style == 'asw'
    assert plan.textures['base'].endswith('APRL_baseX.png')
    assert plan.textures['sss'].endswith('APRL_Sss.png')
    assert plan.textures['ilm'].endswith('APRL_ilm.png')
    assert plan.use_vertex_color and plan.uv_map == 'UV1' and plan.warnings == []


def test_april_decal_and_eyeshine():
    listdir, exists = _fs({APRIL_DIR: APRIL_FILES})
    decal = detect(_material('7_DecalFace_1_0_0.001', [_image('APRL_decalX.png', APRIL_DIR + '/APRL_decalX.png')]),
                   listdir, exists)
    assert decal.style == 'asw_decal' and decal.textures['decal'].endswith('APRL_decalX.png')
    shine = detect(_material('5_eyeshine_1_0_0.001', [_image('APRL_baseX.png', APRIL_DIR + '/APRL_baseX.png')]),
                   listdir, exists)
    assert shine.style == 'asw_eyeshine'


def test_asw_missing_sss_falls_back_with_warning():
    listdir, exists = _fs({APRIL_DIR: ['APRL_base.png', 'APRL_ilm.png']})
    plan = detect(_material('5_head', [_image('APRL_base.png', APRIL_DIR + '/APRL_base.png')]), listdir, exists)
    assert plan.style == 'asw' and 'sss' not in plan.textures
    assert any('Sss' in w for w in plan.warnings)


def test_generic_textured_arthur():
    d = 'H:/Blender/umvc3_arthur_by_jsrremix_db29n16/UMVC3 Arthur'
    listdir, exists = _fs({d: ['arthur_tex01_bmout.png', 'arthur_tex01_nmout.png']})
    m = _material('24_+mesh81', [
        _image('arthur_tex01_bmout.png', d + '/arthur_tex01_bmout.png'),
        _image('arthur_tex01_nmout.png', d + '/arthur_tex01_nmout.png', feeds_base=False, colorspace='Non-Color'),
    ])
    plan = detect(m, listdir, exists)
    assert plan.style == 'generic'
    assert plan.textures['base'].endswith('bmout.png') and plan.textures['normal'].endswith('nmout.png')
    assert not plan.use_vertex_color


def test_generic_fallback_largest_srgb_image():
    listdir, exists = _fs({'C:/t': ['small.png', 'big.png']})
    m = _material('m', [_image('small.png', 'C:/t/small.png', feeds_base=False, size=(64, 64)),
                        _image('big.png', 'C:/t/big.png', feeds_base=False, size=(512, 512))])
    plan = detect(m, listdir, exists)
    assert plan.style == 'generic' and plan.textures['base'].endswith('big.png')
    assert any('largest' in w for w in plan.warnings)


def test_untextured_uses_base_color_then_display_color():
    assert detect(_material('dude', base_color=(0.2, 0.3, 0.4, 1.0))).base_color == (0.2, 0.3, 0.4, 1.0)
    plan = detect(_material('dude'))
    assert plan.style == 'untextured' and plan.base_color == (0.8, 0.8, 0.8, 1.0)


def test_no_nodes_material():
    plan = detect(_material('plain', has_nodes=False))
    assert plan.style == 'untextured' and plan.warnings == []


def test_relative_and_missing_paths():
    listdir, exists = _fs({})
    m = _material('5_body', [_image('APRL_base.png', 'H:/nowhere/APRL_base.png')])
    plan = detect(m, listdir, exists)
    assert plan.style in ('asw', 'generic')
    assert any('missing' in w for w in plan.warnings)


def test_shared_key():
    listdir, exists = _fs({APRIL_DIR: APRIL_FILES})
    a = detect(_material('5_body', [_image('APRL_baseX.png', APRIL_DIR + '/APRL_baseX.png')]), listdir, exists)
    b = detect(_material('5_hat', [_image('APRL_baseX.png', APRIL_DIR + '/APRL_baseX.png')]), listdir, exists)
    assert a.key == b.key
```

- [ ] **Step 2: Run test to verify it fails**

Run: `H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart/test_pixel_cel_detect.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'Malt.PixelArt'`.

- [ ] **Step 3: Write minimal implementation**

```python
# Malt/PixelArt/detect.py
# Source material style detection for the Pixel Cel converter. No bpy, no OpenGL (unit tested outside Blender).
import dataclasses
import os
import re

_ASW_BASE = re.compile(r'^(?P<prefix>.+?)_base(x)?$', re.IGNORECASE)
_DECAL = re.compile(r'_decal', re.IGNORECASE)
_NORMAL = re.compile(r'(nm|normal)', re.IGNORECASE)


@dataclasses.dataclass
class ConvertPlan:
    style: str
    textures: dict
    base_color: tuple
    uv_map: str = None
    use_vertex_color: bool = False
    warnings: list = dataclasses.field(default_factory=list)

    @property
    def key(self):
        textures = ','.join(f'{k}={os.path.normcase(v)}' for k, v in sorted(self.textures.items()))
        return f'{self.style}|{textures}|{tuple(round(c, 4) for c in self.base_color)}'


def _norm(path):
    return path.replace('\\', '/')


def _stem(path):
    return os.path.splitext(os.path.basename(_norm(path)))[0]


def _sibling(folder, prefix, suffix, listdir):
    # A file named <prefix>_<suffix>.* in folder, case-insensitive; returns its path or None
    try:
        names = listdir(folder)
    except OSError:
        return None
    wanted = f'{prefix}_{suffix}'.lower()
    for name in sorted(names):
        if os.path.splitext(name)[0].lower() == wanted:
            return folder + '/' + name
    return None


def detect(description, listdir=os.listdir, exists=os.path.exists):
    name = description['name']
    images = description.get('images', []) if description.get('has_nodes', True) else []
    base_color = tuple(description.get('base_color') or description['display_color'])
    warnings = []
    for image in images:
        if not exists(image['filepath']):
            warnings.append(f"missing file: {_norm(image['filepath'])}")
    base_images = [i for i in images if i['feeds_base']]
    first = (base_images or images or [None])[0]
    uv_map = first['uv_map'] if first else None

    if 'eyeshine' in name.lower() and first:
        return ConvertPlan('asw_eyeshine', {'base': _norm(first['filepath'])}, base_color, uv_map, True, warnings)

    decal = next((i for i in images if _DECAL.search(_stem(i['name']))), None)
    if name.lower().startswith('7_decal') or decal:
        image = decal or first
        textures = {'decal': _norm(image['filepath'])} if image else {}
        return ConvertPlan('asw_decal', textures, base_color, uv_map, True, warnings)

    for image in base_images or images:
        match = _ASW_BASE.match(_stem(image['name']))
        if not match:
            continue
        folder = _norm(os.path.dirname(_norm(image['filepath'])))
        prefix = match.group('prefix')
        sss = _sibling(folder, prefix, 'sss', listdir)
        ilm = _sibling(folder, prefix, 'ilm', listdir)
        if sss or ilm or any(w.startswith('missing') for w in warnings):
            textures = {'base': _norm(image['filepath'])}
            if sss:
                textures['sss'] = sss
            else:
                warnings.append(f'no {prefix}_Sss texture: shadow tint colour used')
            if ilm:
                textures['ilm'] = ilm
            else:
                warnings.append(f'no {prefix}_ilm texture: neutral ilm used')
            return ConvertPlan('asw', textures, base_color, image['uv_map'] or uv_map, True, warnings)

    if images:
        srgb = [i for i in images if i['colorspace'] != 'Non-Color']
        if base_images:
            base = base_images[0]
        elif srgb:
            base = max(srgb, key=lambda i: i['size'][0] * i['size'][1])
            warnings.append(f"base colour image not traced: largest sRGB image {base['name']} used")
        else:
            base = None
        if base:
            textures = {'base': _norm(base['filepath'])}
            normal = next((i for i in images if i['colorspace'] == 'Non-Color' and _NORMAL.search(_stem(i['name']))), None)
            if normal:
                textures['normal'] = _norm(normal['filepath'])
            return ConvertPlan('generic', textures, base_color, base['uv_map'] or uv_map, False, warnings)

    return ConvertPlan('untextured', {}, base_color, uv_map, False, warnings)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart/test_pixel_cel_detect.py -q`
Expected: 9 passed. If `test_relative_and_missing_paths` gives style `asw`, that is accepted by the test (a missing
folder cannot prove the ASW set; the warning is what matters).

- [ ] **Step 5: Commit**

```bash
git add Malt/PixelArt/__init__.py Malt/PixelArt/detect.py tests/pixelart/test_pixel_cel_detect.py
git commit -m "pixelart: source material style detection (ASW, decal, eyeshine, generic, untextured)"
```

---

### Task 3: Shading reference and presets (pure Python)

**Files:**
- Create: `Malt/PixelArt/cel_ref.py`
- Create: `Malt/PixelArt/presets.py`
- Create: `tests/pixelart/test_pixel_cel_ref.py`

**Interfaces:**
- Produces (used by Tasks 4, 5, 8):
  - Tones: `TONE_SHADOW = 0`, `TONE_MID = 1`, `TONE_LIT = 2`, `TONE_HIGHLIGHT = 3`.
  - `cel_tone(n_dot_l, n_dot_h, offset, threshold, shadowed, ramp=None, spec_mask=0.0, spec_size=0.0,
    spec_threshold=0.5, highlight_threshold=2.0) -> (tone: int, t: float)`. `ramp` is a callable `s -> t` or None.
  - `cel_color(base_rgb, shadow_rgb, tone, t, spec_boost=1.3, highlight_rgb=(1, 0.97, 0.9), highlight_mix=0.0,
    line_mask=1.0) -> (r, g, b)`.
  - `shifted_shadow(base_rgb, hue_shift_degrees, saturation, value) -> (r, g, b)`: linear RGB in and out; HSV in sRGB
    space like Malt's `rgb_to_hsv`; hue moves toward 260 degrees by at most `hue_shift_degrees`.
  - `PRESETS: dict[str, dict]` with keys `'ASW'`, `'KOF XIII'`; each value maps `pixel_cel` input names (Task 4) to
    values, plus `'ramp_stops'`: list of `(position, value)` for a constant-interpolation gradient (empty for ASW).

- [ ] **Step 1: Write the failing test**

```python
# tests/pixelart/test_pixel_cel_ref.py
import colorsys

import pytest

from Malt.PixelArt.cel_ref import (TONE_SHADOW, TONE_MID, TONE_LIT, TONE_HIGHLIGHT, cel_tone, cel_color,
                                   shifted_shadow, linear_to_srgb, srgb_to_linear)
from Malt.PixelArt.presets import PRESETS


@pytest.mark.parametrize('n_dot_l, offset, shadowed, tone', [
    (1.0, 0.0, False, TONE_LIT),
    (0.01, 0.0, False, TONE_LIT),       # s = 0.505 > 0.5
    (-0.01, 0.0, False, TONE_SHADOW),   # s = 0.495
    (1.0, 0.0, True, TONE_SHADOW),      # ray shadow wins
    (0.2, -0.5, False, TONE_SHADOW),    # ASW ilm.G = 0: always shadow
    (-0.8, 0.5, False, TONE_LIT),       # ilm.G = 1: nearly always lit
])
def test_two_tone(n_dot_l, offset, shadowed, tone):
    assert cel_tone(n_dot_l, 0.0, offset, 0.5, shadowed)[0] == tone


def test_ramp_bands_from_kof_preset():
    stops = PRESETS['KOF XIII']['ramp_stops']

    def ramp(s):
        value = stops[0][1]
        for position, v in stops:
            if s >= position:
                value = v
        return value
    assert cel_tone(-0.5, 0.0, 0.0, 0.5, False, ramp)[0] == TONE_SHADOW     # s = 0.25
    assert cel_tone(-0.1, 0.0, 0.0, 0.5, False, ramp)[0] == TONE_MID        # s = 0.45
    assert cel_tone(0.4, 0.0, 0.0, 0.5, False, ramp)[0] == TONE_LIT         # s = 0.7
    tone, t = cel_tone(0.9, 0.0, 0.0, 0.5, False, ramp, highlight_threshold=0.85)
    assert tone == TONE_HIGHLIGHT and t == 1.0                              # s = 0.95


def test_specular_only_on_lit():
    assert cel_tone(0.5, 1.0, 0.0, 0.5, False, spec_mask=1.0, spec_size=0.0)[0] == TONE_HIGHLIGHT
    assert cel_tone(-0.5, 1.0, 0.0, 0.5, False, spec_mask=1.0, spec_size=0.0)[0] == TONE_SHADOW


def test_colors():
    base, shadow = (0.8, 0.6, 0.4), (0.2, 0.1, 0.3)
    assert cel_color(base, shadow, TONE_SHADOW, 0.0) == pytest.approx(shadow)
    assert cel_color(base, shadow, TONE_LIT, 1.0) == pytest.approx(base)
    assert cel_color(base, shadow, TONE_MID, 0.45) == pytest.approx(tuple(s + (b - s) * 0.45 for b, s in zip(base, shadow)))
    assert cel_color(base, shadow, TONE_HIGHLIGHT, 1.0, spec_boost=1.25) == pytest.approx(tuple(b * 1.25 for b in base))
    assert cel_color(base, shadow, TONE_LIT, 1.0, line_mask=0.2) == pytest.approx(tuple(b * 0.2 for b in base))
    assert cel_color(base, shadow, TONE_LIT, 1.0, line_mask=0.7) == pytest.approx(base)  # above 0.5: no line


def test_shifted_shadow_moves_hue_toward_purple_and_darkens():
    base = srgb_to_linear((0.9, 0.6, 0.3))  # warm orange
    h0, s0, v0 = colorsys.rgb_to_hsv(*linear_to_srgb(base))
    h1, s1, v1 = colorsys.rgb_to_hsv(*linear_to_srgb(shifted_shadow(base, 15.0, 1.25, 0.55)))
    assert abs(((h1 - h0 + 0.5) % 1.0) - 0.5) == pytest.approx(15.0 / 360.0, abs=1e-3)
    assert v1 == pytest.approx(v0 * 0.55, abs=1e-3) and s1 == pytest.approx(min(1.0, s0 * 1.25), abs=1e-3)


def test_presets_have_the_same_inputs_and_no_line_width():
    asw, kof = PRESETS['ASW'], PRESETS['KOF XIII']
    assert set(asw) == set(kof)
    assert not any('width' in k for k in asw)
    assert asw['use_ramp'] is False and kof['use_ramp'] is True
    assert asw['ramp_stops'] == [] and len(kof['ramp_stops']) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart/test_pixel_cel_ref.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'Malt.PixelArt.cel_ref'`.

- [ ] **Step 3: Write minimal implementation**

```python
# Malt/PixelArt/cel_ref.py
# Python reference of the Pixel Cel shading rules (spec section 3). Same as PixelCel.glsl: keep them in sync.
import colorsys
import math

TONE_SHADOW = 0
TONE_MID = 1
TONE_LIT = 2
TONE_HIGHLIGHT = 3


def cel_tone(n_dot_l, n_dot_h, offset, threshold, shadowed, ramp=None, spec_mask=0.0, spec_size=0.0,
             spec_threshold=0.5, highlight_threshold=2.0):
    s = n_dot_l * 0.5 + 0.5 + offset
    if shadowed:
        return TONE_SHADOW, 0.0
    if ramp is not None:
        t = float(ramp(min(max(s, 0.0), 1.0)))
        tone = TONE_SHADOW if t < 0.25 else (TONE_MID if t < 0.75 else TONE_LIT)
    else:
        lit = s > threshold
        t = 1.0 if lit else 0.0
        tone = TONE_LIT if lit else TONE_SHADOW
    if tone == TONE_LIT:
        if s > highlight_threshold:
            tone = TONE_HIGHLIGHT
        exponent = 4.0 + (128.0 - 4.0) * spec_size
        if spec_mask > 0.0 and spec_mask * math.pow(max(n_dot_h, 0.0), exponent) > spec_threshold:
            tone = TONE_HIGHLIGHT
    return tone, t


def cel_color(base_rgb, shadow_rgb, tone, t, spec_boost=1.3, highlight_rgb=(1.0, 0.97, 0.9), highlight_mix=0.0,
              line_mask=1.0):
    if tone == TONE_HIGHLIGHT:
        color = tuple(b * spec_boost * (1.0 - highlight_mix) + h * highlight_mix for b, h in zip(base_rgb, highlight_rgb))
    else:
        color = tuple(s + (b - s) * t for b, s in zip(base_rgb, shadow_rgb))
    line = 1.0 if line_mask > 0.5 else line_mask
    return tuple(c * line for c in color)


def linear_to_srgb(rgb):
    return tuple(c * 12.92 if c <= 0.0031308 else 1.055 * math.pow(c, 1.0 / 2.4) - 0.055 for c in rgb)


def srgb_to_linear(rgb):
    return tuple(c / 12.92 if c <= 0.04045 else math.pow((c + 0.055) / 1.055, 2.4) for c in rgb)


def shifted_shadow(base_rgb, hue_shift_degrees, saturation, value):
    h, s, v = colorsys.rgb_to_hsv(*linear_to_srgb(base_rgb))
    target = 260.0 / 360.0
    d = target - h
    d -= round(d)  # shortest signed distance, in [-0.5, 0.5]
    step = min(hue_shift_degrees / 360.0, abs(d)) * (1.0 if d >= 0 else -1.0)
    h = (h + step) % 1.0
    s = min(max(s * saturation, 0.0), 1.0)
    v = v * value
    return srgb_to_linear(colorsys.hsv_to_rgb(h, s, v))
```

```python
# Malt/PixelArt/presets.py
# Pixel Cel input values per style preset (spec section 3.1). Keys are pixel_cel input names (PixelCel.glsl).
# There is no line width anywhere: every line is exactly 1 px (spec section 3.2).

PRESETS = {
    'ASW': {
        'use_ramp': False,
        'ramp_stops': [],
        'threshold': 0.5,
        'shadow_from_hue_shift': False,
        'hue_shift': 15.0,
        'shadow_saturation': 1.25,
        'shadow_value': 0.55,
        'spec_threshold': 0.5,
        'spec_boost': 1.3,
        'highlight_threshold': 2.0,
        'highlight_mix': 0.0,
        'outline_from_base': False,
        'outline_value': 0.1,
    },
    'KOF XIII': {
        'use_ramp': True,
        'ramp_stops': [(0.0, 0.0), (0.35, 0.45), (0.5, 1.0)],
        'threshold': 0.5,
        'shadow_from_hue_shift': True,
        'hue_shift': 15.0,
        'shadow_saturation': 1.25,
        'shadow_value': 0.55,
        'spec_threshold': 0.5,
        'spec_boost': 1.2,
        'highlight_threshold': 0.85,
        'highlight_mix': 0.2,
        'outline_from_base': True,
        'outline_value': 0.35,
    },
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart/test_pixel_cel_ref.py -q`
Expected: 11 passed (6 parametrized + 5).

- [ ] **Step 5: Commit**

```bash
git add Malt/PixelArt/cel_ref.py Malt/PixelArt/presets.py tests/pixelart/test_pixel_cel_ref.py
git commit -m "pixelart: Pixel Cel shading reference and ASW / KOF XIII presets"
```

---

### Task 4: The `pixel_cel` GLSL node

**Files:**
- Create: `Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/PixelCel.glsl`
- Modify: `Malt/Pipelines/NPR_Pipeline/Shaders/NPR_MeshShader.glsl` (last lines: add the include)
- Create: `tools/pixelart/pixel_cel_debug.mesh.glsl`
- Create: `tools/pixelart/compare_cel.py`
- Modify: `tools/pixelart/scenes.py` (setup `pixel_cel_debug`)

**Interfaces:**
- Consumes: `cel_ref.cel_tone` (Task 3), `npr_lit_surface` (`NPR_Lighting.glsl`), `rgb_to_hsv`/`hsv_to_rgb`
  (`Common/Color.glsl`, sRGB-space HSV), globals `POSITION`, `NORMAL`, `ID`, `UV[4]`, `COLOR[4]`, `LIGHTS`.
- Produces (used by Tasks 5-8): node function `pixel_cel` with exactly these parameters and names (the converter sets
  them by name):

```
void pixel_cel(
    vec4 base_color, bool use_base_texture, sampler2D base_texture,
    bool use_shadow_texture, sampler2D shadow_texture,
    bool use_ilm_texture, sampler2D ilm_texture,
    bool use_cutout, float cutout,
    int uv_index, bool use_vertex_color, int vertex_color_index, bool nearest,
    vec3 shadow_tint, bool shadow_from_hue_shift, float hue_shift, float shadow_saturation, float shadow_value,
    float threshold, bool use_ramp, sampler1D ramp,
    float spec_threshold, float spec_boost,
    float highlight_threshold, vec3 highlight_color, float highlight_mix,
    bool outline_from_base, float outline_value,
    bool unlit, int light_group, bool shadows, bool self_shadows,
    out vec4 color, out vec4 line_color, out vec4 line_data, out int tone, out bool shadowed)
```
  `line_data` = (inner line value = ilm.A or 1, outline enable 0/1, 0, 1) for the Pixel Lines node (Task 7).
  `line_color` = outline colour of this pixel (near black, or base x `outline_value` when `outline_from_base`).
  Also `float pixel_cel_opacity(sampler2D texture, int uv_index, bool use_cutout, float cutout)` for the pre pass.

- [ ] **Step 1: Write the failing check**

`tools/pixelart/compare_cel.py` (the check) first:

```python
# tools/pixelart/compare_cel.py
"""Per-pixel check of a pixel_cel_debug render against Malt/PixelArt/cel_ref.py.
    python compare_cel.py DEBUG.png
Debug channels: R = tone / 3, G = s = N.L * 0.5 + 0.5 (first sun), B = shadowed. Threshold 0.5, no ramp, offset 0.
Pixels whose s is within 2/255 of the threshold are skipped (8-bit quantization). Exit 1 on any mismatch."""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from Malt.PixelArt.cel_ref import cel_tone

a = np.array(Image.open(sys.argv[1]).convert('RGB')).astype(np.float64) / 255.0
covered = a.sum(axis=2) > 0
tone = np.rint(a[..., 0] * 3).astype(int)
s = a[..., 1]
shadowed = a[..., 2] > 0.5
checked = covered & (np.abs(s - 0.5) > 2.0 / 255.0)
bad = 0
for y, x in zip(*np.nonzero(checked)):
    expected = cel_tone((s[y, x] - 0.5) * 2.0, 0.0, 0.0, 0.5, bool(shadowed[y, x]))[0]
    bad += int(expected != tone[y, x])
print('checked px', int(checked.sum()), 'mismatches', bad)
sys.exit(1 if bad or not checked.any() else 0)
```

The debug material calls the node that does not exist yet:

```glsl
// tools/pixelart/pixel_cel_debug.mesh.glsl
// Debug material for pixel_cel (tools/pixelart/scenes.py: pixel_cel_debug). R = tone / 3, G = s of the first sun,
// B = shadowed. No textures, threshold 0.5, no ramp: compare with tools/pixelart/compare_cel.py.
#include "NPR_MeshShader.glsl"

void PRE_PASS_PIXEL_SHADER(inout PrePassOutput PPO){ }
void DEPTH_OFFSET(inout float depth_offset, inout bool offset_position){ }

#ifdef MAIN_PASS
layout (location = 0) out vec4 OUT_COLOR;
layout (location = 1) out vec4 OUT_LINE_COLOR;
layout (location = 2) out vec4 OUT_LINE_WIDTH;
uniform sampler2D DEBUG_TEXTURE;
uniform sampler1D DEBUG_RAMP;
#endif

void MAIN_PASS_PIXEL_SHADER()
{
    #ifdef MAIN_PASS
    {
        vec4 color, line_color, line_data;
        int tone;
        bool shadowed;
        pixel_cel(vec4(1), false, DEBUG_TEXTURE, false, DEBUG_TEXTURE, false, DEBUG_TEXTURE, false, 0.5,
            0, false, 0, false,
            vec3(0.55, 0.5, 0.7), false, 15.0, 1.25, 0.55,
            0.5, false, DEBUG_RAMP,
            0.5, 1.3,
            2.0, vec3(1.0, 0.97, 0.9), 0.0,
            false, 0.1,
            false, 1, true, true,
            color, line_color, line_data, tone, shadowed);
        float s = 0.0;
        for(int i = 0; i < LIGHTS.lights_count; i++)
        {
            if(LIGHTS.lights[i].type == LIGHT_SUN)
            {
                s = dot(NORMAL, -LIGHTS.lights[i].direction) * 0.5 + 0.5;
                break;
            }
        }
        OUT_COLOR = vec4(float(tone) / 3.0, s, shadowed ? 1.0 : 0.0, 1.0);
        // The Standard view transform encodes to sRGB: pre-decode so the PNG holds the raw values
        OUT_COLOR.rgb = srgb_to_linear(OUT_COLOR.rgb);
        OUT_LINE_COLOR = vec4(0.0);
        OUT_LINE_WIDTH = vec4(0.0);
    }
    #endif
}
```

Setup in `tools/pixelart/scenes.py` (append; reuses `_debug_material` with a different shader file):

```python
def _debug_shader(scene, filename):
    import os
    material = bpy.data.materials.new('PixelCelDebug')
    material.malt.material_type = 'Mesh'
    material.malt.shader_source = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    for obj in scene.objects:
        if obj.type == 'MESH':
            if len(obj.material_slots) == 0:
                obj.data.materials.append(material)
            for slot in obj.material_slots:
                slot.link = 'OBJECT'
                slot.material = material
    _setup_malt_ids()
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0


def pixel_cel_debug(scene):
    # Suzanne alone, 256 px, ray traced shadows, the pixel_cel debug material
    ray_traced(scene)
    suzanne = [bpy.data.objects['Suzanne']]
    _solo(scene, suzanne)
    _frame_objects(scene, suzanne, 256)
    _debug_shader(scene, 'pixel_cel_debug.mesh.glsl')
```

Note: `srgb_to_linear` (Common/Color.glsl) undoes the `Standard` view transform, so the PNG holds the raw values.

- [ ] **Step 2: Run the check to verify it fails**

Run:
```bash
cd /h/GameDev/Malt
RENDER_TIMEOUT=200 bash tools/pixelart/render.sh /h/GameDev/Pixelizer/content/malt/testmalt.blend build/pixelart/P/pixel_cel_debug 1 pixel_cel_debug; echo EXIT $?
```
Expected: the render log or `stdout.txt` shows a GLSL compile error naming `pixel_cel` (no matching function), or
the frame is the default yellow material. Quote that line in the commit body.

- [ ] **Step 3: Write the implementation**

```glsl
// Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/PixelCel.glsl
#ifndef PIXEL_CEL_GLSL
#define PIXEL_CEL_GLSL

#include "NPR_Lighting.glsl"
#include "Common/Color.glsl"

/*  META GLOBAL
    @meta: category=Shading;
*/

// Pixel Cel: cel-shaded pixel-art material (docs/pixelart/05-pixel-cel-materials-spec.md, section 3).
// Same rules as Malt/PixelArt/cel_ref.py: keep them in sync.

#define PIXEL_CEL_TONE_SHADOW 0
#define PIXEL_CEL_TONE_MID 1
#define PIXEL_CEL_TONE_LIT 2
#define PIXEL_CEL_TONE_HIGHLIGHT 3

vec4 _pixel_cel_sample(sampler2D tex, vec2 uv, bool nearest)
{
    if(nearest)
    {
        ivec2 size = textureSize(tex, 0);
        ivec2 texel = ivec2(floor(fract(uv) * vec2(size)));
        return texelFetch(tex, clamp(texel, ivec2(0), size - 1), 0);
    }
    return texture(tex, uv);
}

// KOF XIII shadow colour: hue moved toward blue-purple (260 degrees) by at most hue_shift degrees, then saturation
// and value scaled. HSV is in sRGB space (Malt rgb_to_hsv), like cel_ref.shifted_shadow.
vec3 _pixel_cel_shifted_shadow(vec3 base, float hue_shift, float saturation, float value)
{
    vec3 hsv = rgb_to_hsv(base);
    float d = 260.0 / 360.0 - hsv.x;
    d -= round(d);
    hsv.x = fract(hsv.x + min(hue_shift / 360.0, abs(d)) * (d >= 0.0 ? 1.0 : -1.0));
    hsv.y = clamp(hsv.y * saturation, 0.0, 1.0);
    hsv.z *= value;
    return hsv_to_rgb(hsv);
}

int _pixel_cel_tone(float n_dot_l, float n_dot_h, float offset, float threshold, bool light_shadowed,
    bool use_ramp, sampler1D ramp, float spec_mask, float spec_size, float spec_threshold, float highlight_threshold,
    out float t)
{
    float s = n_dot_l * 0.5 + 0.5 + offset;
    t = 0.0;
    if(light_shadowed)
    {
        return PIXEL_CEL_TONE_SHADOW;
    }
    int tone;
    if(use_ramp)
    {
        t = texture(ramp, clamp(s, 0.0, 1.0)).r;
        tone = t < 0.25 ? PIXEL_CEL_TONE_SHADOW : (t < 0.75 ? PIXEL_CEL_TONE_MID : PIXEL_CEL_TONE_LIT);
    }
    else
    {
        bool lit = s > threshold;
        t = lit ? 1.0 : 0.0;
        tone = lit ? PIXEL_CEL_TONE_LIT : PIXEL_CEL_TONE_SHADOW;
    }
    if(tone == PIXEL_CEL_TONE_LIT)
    {
        if(s > highlight_threshold)
        {
            tone = PIXEL_CEL_TONE_HIGHLIGHT;
        }
        float exponent = mix(4.0, 128.0, spec_size);
        if(spec_mask > 0.0 && spec_mask * pow(max(n_dot_h, 0.0), exponent) > spec_threshold)
        {
            tone = PIXEL_CEL_TONE_HIGHLIGHT;
        }
    }
    return tone;
}

/*  META
    @meta: label=Pixel Cel;
    @base_color: subtype=Color; default=vec4(1.0);
    @use_base_texture: default=false;
    @use_shadow_texture: default=false;
    @use_ilm_texture: default=false;
    @use_cutout: default=false;
    @cutout: default=0.5;
    @uv_index: default=0;
    @use_vertex_color: default=false;
    @vertex_color_index: default=0;
    @nearest: default=false;
    @shadow_tint: subtype=Color; default=vec3(0.55, 0.5, 0.7);
    @shadow_from_hue_shift: default=false;
    @hue_shift: default=15.0;
    @shadow_saturation: default=1.25;
    @shadow_value: default=0.55;
    @threshold: default=0.5;
    @use_ramp: default=false;
    @spec_threshold: default=0.5;
    @spec_boost: default=1.3;
    @highlight_threshold: default=2.0;
    @highlight_color: subtype=Color; default=vec3(1.0, 0.97, 0.9);
    @highlight_mix: default=0.0;
    @outline_from_base: default=false;
    @outline_value: default=0.1;
    @unlit: default=false;
    @light_group: default=1;
    @shadows: default=true;
    @self_shadows: default=true;
*/
void pixel_cel(
    vec4 base_color, bool use_base_texture, sampler2D base_texture,
    bool use_shadow_texture, sampler2D shadow_texture,
    bool use_ilm_texture, sampler2D ilm_texture,
    bool use_cutout, float cutout,
    int uv_index, bool use_vertex_color, int vertex_color_index, bool nearest,
    vec3 shadow_tint, bool shadow_from_hue_shift, float hue_shift, float shadow_saturation, float shadow_value,
    float threshold, bool use_ramp, sampler1D ramp,
    float spec_threshold, float spec_boost,
    float highlight_threshold, vec3 highlight_color, float highlight_mix,
    bool outline_from_base, float outline_value,
    bool unlit, int light_group, bool shadows, bool self_shadows,
    out vec4 color, out vec4 line_color, out vec4 line_data, out int tone, out bool shadowed)
{
    vec2 uv = UV[uv_index];
    vec4 base = base_color;
    if(use_base_texture)
    {
        base *= _pixel_cel_sample(base_texture, uv, nearest);
    }
    vec3 tint = use_shadow_texture ? _pixel_cel_sample(shadow_texture, uv, nearest).rgb : shadow_tint;
    vec4 ilm = use_ilm_texture ? _pixel_cel_sample(ilm_texture, uv, nearest) : vec4(0.0, 0.5, 0.0, 1.0);
    vec4 vertex_color = use_vertex_color ? COLOR[vertex_color_index] : vec4(1.0);
    float offset = use_ilm_texture ? ilm.g * vertex_color.r - 0.5 : 0.0;
    vec3 shadow_color = shadow_from_hue_shift
        ? _pixel_cel_shifted_shadow(base.rgb, hue_shift, shadow_saturation, shadow_value)
        : base.rgb * tint;

    line_color = vec4(outline_from_base ? base.rgb * outline_value : vec3(outline_value), 1.0);
    line_data = vec4(use_ilm_texture ? ilm.a : 1.0, (use_vertex_color && vertex_color.a < 0.5) ? 0.0 : 1.0, 0.0, 1.0);
    shadowed = false;

    if(unlit)
    {
        color = base;
        tone = PIXEL_CEL_TONE_LIT;
        return;
    }

    tone = -1;
    float best_t = 0.0;
    for(int i = 0; i < LIGHTS.lights_count; i++)
    {
        if(LIGHT_GROUP_INDEX(i) != light_group)
        {
            continue;
        }
        Light L = LIGHTS.lights[i];
        LitSurface LS = npr_lit_surface(POSITION, NORMAL, ID.x, L, i, shadows, self_shadows);
        bool light_shadowed = shadows && LS.shadow;
        shadowed = shadowed || light_shadowed;
        float t;
        int light_tone = _pixel_cel_tone(LS.NoL, dot(NORMAL, LS.H), offset, threshold, light_shadowed,
            use_ramp, ramp, use_ilm_texture ? ilm.r : 0.0, use_ilm_texture ? ilm.b : 0.0, spec_threshold,
            highlight_threshold, t);
        if(light_tone > tone)
        {
            tone = light_tone;
            best_t = t;
        }
    }
    if(tone < 0)
    {
        tone = PIXEL_CEL_TONE_SHADOW;
    }

    vec3 rgb = tone == PIXEL_CEL_TONE_HIGHLIGHT
        ? mix(base.rgb * spec_boost, highlight_color, highlight_mix)
        : mix(shadow_color, base.rgb, best_t);
    if(use_ilm_texture && ilm.a <= 0.5)
    {
        rgb *= ilm.a;
    }
    color = vec4(rgb, base.a);
}

/*  META
    @meta: label=Pixel Cel Opacity;
    @use_cutout: default=false;
    @cutout: default=0.5;
*/
float pixel_cel_opacity(sampler2D texture_, int uv_index, bool use_cutout, float cutout)
{
    if(!use_cutout)
    {
        return 1.0;
    }
    return texture(texture_, UV[uv_index]).a >= cutout ? 1.0 : 0.0;
}

#endif //PIXEL_CEL_GLSL
```

Note: inner lines are not multiplied here by the 1 px rule's thinning; Task 7 decides inner line pixels from
`line_data.x`. The `rgb *= ilm.a` above is the texture's own dark line colour and is removed in Task 7 Step 5 when
Pixel Lines draws inner lines (until then it is the visible inner line).

Add at the end of `NPR_MeshShader.glsl`, after `#include "NPR_Pipeline/NPR_Shading2.glsl"`:
```glsl
#include "NPR_Pipeline/PixelCel.glsl"
```

- [ ] **Step 4: Run the check to verify it passes**

Run:
```bash
cd /h/GameDev/Malt
RENDER_TIMEOUT=200 bash tools/pixelart/render.sh /h/GameDev/Pixelizer/content/malt/testmalt.blend build/pixelart/P/pixel_cel_debug 1 pixel_cel_debug; echo EXIT $?
/h/GameDev/Pixelizer/.venv/Scripts/python tools/pixelart/compare_cel.py build/pixelart/P/pixel_cel_debug/frame_0001.png
H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart -q
```
Expected: render EXIT 0; `checked px` > 5000 and `mismatches 0`; all pytest tests pass. If a mismatch appears, find
the cause with the debug channels (do not loosen the check). Add the printed line to
`docs/pixelart/07-pixel-cel-results.md` under `## pixel_cel vs cel_ref`.

- [ ] **Step 5: Commit**

```bash
git add Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/PixelCel.glsl Malt/Pipelines/NPR_Pipeline/Shaders/NPR_MeshShader.glsl tools/pixelart/pixel_cel_debug.mesh.glsl tools/pixelart/compare_cel.py tools/pixelart/scenes.py docs/pixelart/07-pixel-cel-results.md
git commit -m "pixelart: pixel_cel GLSL node (2 tones, ramp, ASW ilm/Sss, KOF hue-shift shadows), checked per pixel against cel_ref"
```

---

### Task 5: Build Malt trees from a ConvertPlan

**Files:**
- Create: `BlenderMalt/PixelArtConvert.py`
- Modify: `tools/pixelart/scenes.py` (setups `pixel_cel_convert_asw`, `pixel_cel_convert_kof`, `_convert_all`)

**Interfaces:**
- Consumes: `detect`, `ConvertPlan` (Task 2), `PRESETS` (Task 3), node `pixel_cel` / `pixel_cel_opacity` (Task 4).
- Produces (used by Tasks 6, 8):
  - `describe_material(material) -> dict` (the Task 2 description; resolves paths with `bpy.path.abspath`).
  - `find_function(tree, function_name) -> str`: the library key whose function name is `function_name`
    (for example `'NPR_Pipeline - PixelCel - pixel_cel'`), raises `KeyError` with the close matches.
  - `build_tree(plan: ConvertPlan, preset: str, name: str) -> bpy.types.NodeTree` (a `MaltTree`, graph type Mesh).
  - `convert_material(material, preset='ASW', trees=None) -> (ConvertPlan, tree)`; `trees` is a dict
    `plan.key + preset -> tree` shared across one run.
  - Custom property on each tree: `tree['pixel_cel_set']` = JSON string of `{parameter key: value}` that the converter
    wrote (Task 6 uses it to keep hand edits).

- [ ] **Step 1: Write the failing render test**

Append to `tools/pixelart/scenes.py`:

```python
def _convert_all(scene, preset):
    from BlenderMalt import PixelArtConvert
    _setup_malt_ids()
    report = PixelArtConvert.convert_objects([o for o in scene.objects if o.type == 'MESH'], preset)
    print('PIXEL_CEL_REPORT', report, flush=True)
    return report


def pixel_cel_convert_asw(scene):
    ray_traced(scene)
    april = _collection_objects('GGXRD')
    _solo(scene, april)
    _frame_objects(scene, april, 256)
    _convert_all(scene, 'ASW')


def pixel_cel_convert_kof(scene):
    ray_traced(scene)
    april = _collection_objects('GGXRD')
    _solo(scene, april)
    _frame_objects(scene, april, 256)
    _convert_all(scene, 'KOF XIII')


def pixel_cel_convert_arthur(scene):
    ray_traced(scene)
    arthur = _collection_objects('arthurmodel')
    _solo(scene, arthur)
    _frame_objects(scene, arthur, 256)
    _convert_all(scene, 'ASW')


def pixel_cel_convert_dude(scene):
    ray_traced(scene)
    dude = _collection_objects('Dudemodel')
    _solo(scene, dude)
    _frame_objects(scene, dude, 256)
    _convert_all(scene, 'ASW')
```

Run:
```bash
cd /h/GameDev/Malt
RENDER_TIMEOUT=240 bash tools/pixelart/render.sh /h/GameDev/Pixelizer/content/malt/testmalt.blend build/pixelart/P/convert_asw 1 pixel_cel_convert_asw; echo EXIT $?
```
Expected: EXIT 1 with `ImportError: cannot import name 'PixelArtConvert'` in `log.txt`.

- [ ] **Step 2: Discover the library keys and the IO node names**

In the same GUI-run pattern, print the facts the builder depends on. Add a temporary setup (delete it after):

```python
def _probe_tree_api(scene):
    tree = bpy.data.node_groups.new('ProbeTree', 'MaltTree')
    tree.graph_type = 'Mesh'                      # replaces the tree with a copy of Malt's 'Mesh Node Tree Base'
    tree = bpy.data.node_groups['ProbeTree']
    print('PROBE nodes', [(n.bl_idname, n.name, getattr(n, 'io_type', ''), getattr(n, 'is_output', '')) for n in tree.nodes])
    for n in tree.nodes:
        print('PROBE sockets', n.name, [s.name for s in n.inputs], [s.name for s in n.outputs])
    keys = [k for k in tree.get_full_library()['functions'] if 'pixel_cel' in k.lower()]
    print('PROBE keys', keys)
    # How a main-pass custom output is stored (Task 7 adds 'Pixel Line Data' the same way)
    suz_out = next(n for n in bpy.data.node_groups['suz'].nodes if n.bl_idname == 'MaltIONode' and n.is_output)
    print('PROBE custom io', [(p, getattr(suz_out, p)) for p in dir(suz_out) if 'custom' in p.lower()])
    for item in getattr(suz_out, 'custom_parameters', []):
        print('PROBE custom item', item.name, [(p, getattr(item, p, None)) for p in ('name', 'type', 'io_type')])
```
Run it with `render.sh ... 1 _probe_tree_api` and copy the printed IO node names, socket names and keys into the
builder below where they differ from the expected `'MAIN PASS PIXEL SHADER Output'` / `'PRE PASS PIXEL SHADER Output'`
names, `Color` / `Line Color` / `Line Width` sockets, and key `'NPR_Pipeline - PixelCel - pixel_cel'`.

- [ ] **Step 3: Write the implementation**

```python
# BlenderMalt/PixelArtConvert.py
# Converts Blender materials to Malt Pixel Cel materials (docs/pixelart/05-pixel-cel-materials-spec.md).
# Never touches the original Cycles/EEVEE nodes: only material.malt.shader_nodes is set.
import json
import os

import bpy

from Malt.PixelArt.detect import detect
from Malt.PixelArt.presets import PRESETS

_BSDF_TYPES = {'BSDF_PRINCIPLED', 'BSDF_DIFFUSE'}


def _feeds_base(node, tree):
    # True when an image node reaches a BSDF base colour (or an XPS/other group's first colour input), through any
    # chain of nodes
    seen = set()
    stack = [node]
    while stack:
        current = stack.pop()
        if current.name in seen:
            continue
        seen.add(current.name)
        for output in current.outputs:
            for link in output.links:
                target, socket = link.to_node, link.to_socket
                if target.type in _BSDF_TYPES and socket.name in ('Base Color', 'Color'):
                    return True
                if target.type == 'GROUP' and socket.name.lower() in ('diffuse', 'base color', 'color', 'albedo'):
                    return True
                stack.append(target)
    return False


def describe_material(material):
    tree = material.node_tree if material.use_nodes else None
    images = []
    base_color = None
    if tree:
        for node in tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                uv_map = None
                vector = node.inputs.get('Vector')
                if vector and vector.links and vector.links[0].from_node.type == 'UVMAP':
                    uv_map = vector.links[0].from_node.uv_map or None
                images.append({
                    'name': node.image.name,
                    'filepath': bpy.path.abspath(node.image.filepath, library=node.image.library),
                    'colorspace': node.image.colorspace_settings.name,
                    'feeds_base': _feeds_base(node, tree),
                    'size': tuple(node.image.size),
                    'uv_map': uv_map,
                })
            if node.type in _BSDF_TYPES and base_color is None:
                socket = node.inputs.get('Base Color') or node.inputs.get('Color')
                if socket is not None and not socket.links:
                    base_color = tuple(socket.default_value)
    return {
        'name': material.name,
        'images': images,
        'base_color': base_color,
        'display_color': tuple(material.diffuse_color),
        'has_nodes': tree is not None,
    }


def find_function(tree, function_name):
    functions = tree.get_full_library()['functions']
    for key, function in functions.items():
        if function['name'] == function_name:
            return key
    close = [k for k in functions if function_name.split('_')[0] in k]
    raise KeyError(f'{function_name} not in the Malt library; close: {close[:10]}')


def _new_mesh_tree(name):
    tree = bpy.data.node_groups.new(name, 'MaltTree')
    tree.graph_type = 'Mesh'  # Malt replaces the empty tree with a copy of 'Mesh Node Tree Base', same name
    tree = bpy.data.node_groups[name]
    for node in list(tree.nodes):
        if node.bl_idname != 'MaltIONode':
            tree.nodes.remove(node)
    return tree


def _io_node(tree, io_type):
    for node in tree.nodes:
        if node.bl_idname == 'MaltIONode' and node.is_output and node.io_type == io_type:
            return node
    raise KeyError(f'no {io_type} output node in {tree.name}')


def _set(tree, node, socket_name, value, written):
    key = node.inputs[socket_name].get_source_global_reference().replace('"', '')
    params = tree.malt_parameters
    if isinstance(value, bpy.types.Image):
        params.textures[key].texture = value
        written[key] = 'image:' + value.name
    else:
        params[key] = value
        written[key] = value if not isinstance(value, tuple) else list(value)


def _load_image(path):
    for image in bpy.data.images:
        if image.filepath and os.path.normcase(bpy.path.abspath(image.filepath)) == os.path.normcase(path):
            return image
    if os.path.exists(path):
        return bpy.data.images.load(path, check_existing=True)
    return None


def _set_ramp(tree, node, stops, written):
    key = node.inputs['ramp'].get_source_global_reference().replace('"', '')
    ramp = tree.malt_parameters.gradients[key].texture.color_ramp
    ramp.interpolation = 'CONSTANT'
    while len(ramp.elements) > 1:
        ramp.elements.remove(ramp.elements[-1])
    ramp.elements[0].position = stops[0][0]
    ramp.elements[0].color = (stops[0][1],) * 3 + (1.0,)
    for position, value in stops[1:]:
        element = ramp.elements.new(position)
        element.color = (value,) * 3 + (1.0,)
    written[key] = [list(s) for s in stops]


def build_tree(plan, preset, name):
    tree = _new_mesh_tree(name)
    cel = tree.nodes.new('MaltFunctionNode')
    cel.function_type = find_function(tree, 'pixel_cel')
    cel.location = (-400, 0)
    main = _io_node(tree, 'MAIN_PASS_PIXEL_SHADER')
    tree.links.new(cel.outputs['color'], main.inputs['Color'])
    tree.links.new(cel.outputs['line_color'], main.inputs['Line Color'])

    written = {}
    values = dict(PRESETS[preset])
    stops = values.pop('ramp_stops')
    for socket_name, value in values.items():
        _set(tree, cel, socket_name, value, written)
    if stops:
        _set_ramp(tree, cel, stops, written)

    textures = plan.textures
    for texture_key, socket_flag, socket_texture in (
            ('base', 'use_base_texture', 'base_texture'),
            ('decal', 'use_base_texture', 'base_texture'),
            ('sss', 'use_shadow_texture', 'shadow_texture'),
            ('ilm', 'use_ilm_texture', 'ilm_texture')):
        if texture_key in textures:
            image = _load_image(textures[texture_key])
            if image is not None:
                if texture_key in ('sss', 'ilm'):
                    image.colorspace_settings.name = 'Non-Color' if texture_key == 'ilm' else image.colorspace_settings.name
                _set(tree, cel, socket_texture, image, written)
                _set(tree, cel, socket_flag, True, written)
    if not textures.get('base') and not textures.get('decal'):
        _set(tree, cel, 'base_color', tuple(plan.base_color), written)
    _set(tree, cel, 'use_vertex_color', bool(plan.use_vertex_color), written)
    if plan.style == 'asw_eyeshine':
        _set(tree, cel, 'unlit', True, written)
    if plan.style == 'asw_decal':
        _set(tree, cel, 'use_cutout', True, written)
        pre = _io_node(tree, 'PRE_PASS_PIXEL_SHADER')
        opacity = tree.nodes.new('MaltFunctionNode')
        opacity.function_type = find_function(tree, 'pixel_cel_opacity')
        opacity.location = (-400, 400)
        tree.links.new(opacity.outputs['result'], pre.inputs['Opacity Mask'])
        image = _load_image(textures['decal']) if 'decal' in textures else None
        if image is not None:
            _set(tree, opacity, 'texture_', image, written)
        _set(tree, opacity, 'use_cutout', True, written)
    tree['pixel_cel_set'] = json.dumps(written)
    tree['pixel_cel_preset'] = preset
    tree['pixel_cel_style'] = plan.style
    return tree


def convert_material(material, preset='ASW', trees=None):
    plan = detect(describe_material(material))
    trees = {} if trees is None else trees
    key = plan.key + '|' + preset
    if key not in trees:
        trees[key] = build_tree(plan, preset, f'PixelCel {preset} {material.name}')
    material.malt.material_type = 'Mesh'
    material.malt.shader_nodes = trees[key]
    return plan, trees[key]


def convert_objects(objects, preset='ASW'):
    trees = {}
    report = []
    done = set()
    for obj in objects:
        for slot in obj.material_slots:
            material = slot.material
            if material is None or material.name in done:
                continue
            done.add(material.name)
            plan, tree = convert_material(material, preset, trees)
            report.append((material.name, plan.style, sorted(plan.textures), plan.warnings, tree.name))
    return report
```

Note: `UV[uv_index]`: the converter leaves `uv_index` at 0. Malt's UV slot 0 is the mesh's first UV map (`UV1` on
April, the only one on Arthur). If the probe in Step 2 shows a different order, set `uv_index` from
`obj.data.uv_layers.find(plan.uv_map)` in `convert_objects` (pass the object to `build_tree`).

- [ ] **Step 4: Run the render tests to verify they pass**

Run:
```bash
cd /h/GameDev/Malt
for S in pixel_cel_convert_asw pixel_cel_convert_kof pixel_cel_convert_arthur pixel_cel_convert_dude; do RENDER_TIMEOUT=240 bash tools/pixelart/render.sh /h/GameDev/Pixelizer/content/malt/testmalt.blend build/pixelart/P/$S 1 $S; echo $S EXIT $?; grep PIXEL_CEL_REPORT build/pixelart/P/$S/stdout.txt; done
```
Expected: all EXIT 0; the April report lists `asw` for the body materials, `asw_decal` for `7_Decal*`,
`asw_eyeshine` for the eyeshine; Arthur `generic`; Dude `untextured`. Make a zoomed sheet:
```bash
/h/GameDev/Pixelizer/.venv/Scripts/python tools/pixelart/side_by_side.py build/pixelart/P/sheet_convert.png 0 0 256 256 3 ASW=build/pixelart/P/pixel_cel_convert_asw/frame_0001.png KOF=build/pixelart/P/pixel_cel_convert_kof/frame_0001.png
```
Look at it: April must show base colours, 2 tones (ASW) / 4 tones (KOF), no yellow default material, decals cut
out. Read the image yourself before claiming it works.

- [ ] **Step 5: Commit**

```bash
git add BlenderMalt/PixelArtConvert.py tools/pixelart/scenes.py
git commit -m "pixelart: build Pixel Cel Malt trees from the detected plan (ASW / KOF XIII presets)"
```

---

### Task 6: Operator, report, reconvert rules, Copy collection

**Files:**
- Modify: `BlenderMalt/PixelArtConvert.py`
- Modify: `BlenderMalt/__init__.py` (register / unregister the module)
- Modify: `tools/pixelart/scenes.py` (setups `pixel_cel_reconvert`, `pixel_cel_copy_collection`)

**Interfaces:**
- Consumes: Task 5 functions.
- Produces:
  - `update_tree(tree, plan, preset) -> list[str]`: rewrites only parameters whose current value equals the value in
    `tree['pixel_cel_set']`; returns the keys it kept because they were edited by hand.
  - `copy_collection(collection, suffix) -> bpy.types.Collection`: deep copy (objects and materials copied, mesh data
    and armatures shared, child collections copied), moved +1 m X per existing copy with that suffix.
  - `write_report(report) -> str`: text block `PixelArt Convert Report`, one line per material.
  - Operator `malt.convert_pixel_art` (`MALT_OT_convert_pixel_art`) with properties `preset` (EnumProperty in the
    operator only: fine, it is not a Render-graph socket), `copy_collection` (bool), and `setup_pixel_lines` (bool,
    used in Task 8). Menu entries: Object menu and the Malt material panel.
  - `original_hash(material) -> str`: hash of the original node tree (node types, names, socket default values, links).

- [ ] **Step 1: Write the failing render test**

```python
def pixel_cel_reconvert(scene):
    # Convert, hand-edit one input, add a node, reconvert: the edit and the node must survive; originals unchanged
    from BlenderMalt import PixelArtConvert
    ray_traced(scene)
    april = _collection_objects('GGXRD')
    _solo(scene, april)
    _frame_objects(scene, april, 256)
    materials = {s.material for o in april for s in o.material_slots if s.material}
    before = {m.name: PixelArtConvert.original_hash(m) for m in materials}
    _convert_all(scene, 'ASW')
    tree = bpy.data.materials['5_body_1_0_0.001'].malt.shader_nodes
    cel = next(n for n in tree.nodes if getattr(n, 'function_type', '').endswith('pixel_cel'))
    key = cel.inputs['threshold'].get_source_global_reference().replace('"', '')
    tree.malt_parameters[key] = 0.3
    tree.nodes.new('MaltFunctionNode').name = 'HandAdded'
    _convert_all(scene, 'ASW')
    assert abs(tree.malt_parameters[key] - 0.3) < 1e-6, 'hand edit lost'
    assert 'HandAdded' in tree.nodes, 'hand node lost'
    after = {m.name: PixelArtConvert.original_hash(m) for m in materials}
    assert before == after, 'original material nodes changed'
    shared = {m.malt.shader_nodes.name for m in materials if m.name.startswith('5_') and 'eyeshine' not in m.name}
    assert len(shared) == 1, f'expected one shared tree, got {shared}'
    print('RECONVERT_OK', flush=True)


def pixel_cel_copy_collection(scene):
    from BlenderMalt import PixelArtConvert
    ray_traced(scene)
    source = bpy.data.collections['GGXRD']
    copy = PixelArtConvert.copy_collection(source, 'KOF')
    april = _collection_objects('GGXRD')
    kof = [o for o in copy.all_objects if o.type == 'MESH']
    PixelArtConvert.convert_objects(april, 'ASW')
    PixelArtConvert.convert_objects(kof, 'KOF XIII')
    assert all(o.data is bpy.data.objects[o.name.rsplit('.KOF', 1)[0]].data for o in kof), 'mesh data must be shared'
    _solo(scene, april + kof)
    _frame_objects(scene, april + kof, 256)
    print('COPY_OK', flush=True)
```

Run:
```bash
cd /h/GameDev/Malt
RENDER_TIMEOUT=240 bash tools/pixelart/render.sh /h/GameDev/Pixelizer/content/malt/testmalt.blend build/pixelart/P/reconvert 1 pixel_cel_reconvert; echo EXIT $?
```
Expected: EXIT 1, `AttributeError: module 'BlenderMalt.PixelArtConvert' has no attribute 'original_hash'`.

- [ ] **Step 2: Write the implementation**

Add to `BlenderMalt/PixelArtConvert.py`:

```python
import hashlib


def original_hash(material):
    tree = material.node_tree
    if tree is None:
        return 'no-nodes'
    parts = []
    for node in sorted(tree.nodes, key=lambda n: n.name):
        parts.append(f'{node.name}:{node.type}:{getattr(getattr(node, "image", None), "name", "")}')
        for socket in node.inputs:
            value = getattr(socket, 'default_value', None)
            try:
                value = tuple(value)
            except TypeError:
                pass
            parts.append(f'  {socket.identifier}={value}')
    for link in tree.links:
        parts.append(f'{link.from_node.name}.{link.from_socket.identifier}->{link.to_node.name}.{link.to_socket.identifier}')
    return hashlib.sha1('\n'.join(parts).encode()).hexdigest()


def _current(tree, key):
    params = tree.malt_parameters
    if key in params.textures.keys():
        texture = params.textures[key].texture
        return 'image:' + texture.name if texture else None
    if key in params.gradients.keys():
        ramp = params.gradients[key].texture.color_ramp
        return [[round(e.position, 6), round(e.color[0], 6)] for e in ramp.elements]
    value = params.get(key)
    try:
        return list(value)
    except TypeError:
        return value


def _same(a, b):
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        return a is not None and b is not None and abs(float(a) - float(b)) < 1e-6
    return a == b


def update_tree(tree, plan, preset):
    # Rebuild into a scratch tree, then copy each value whose current value is still the one the converter wrote
    old = json.loads(tree.get('pixel_cel_set', '{}'))
    scratch = build_tree(plan, preset, tree.name + ' (scratch)')
    new = json.loads(scratch['pixel_cel_set'])
    kept = []
    for key, value in new.items():
        if key in old and not _same(_current(tree, key), old[key]):
            kept.append(key)
            continue
        params = tree.malt_parameters
        if isinstance(value, str) and value.startswith('image:'):
            params.textures[key].texture = bpy.data.images[value[len('image:'):]]
        elif key in scratch.malt_parameters.gradients.keys():
            src = scratch.malt_parameters.gradients[key].texture.color_ramp
            dst = params.gradients[key].texture.color_ramp
            dst.interpolation = src.interpolation
            while len(dst.elements) > 1:
                dst.elements.remove(dst.elements[-1])
            dst.elements[0].position, dst.elements[0].color = src.elements[0].position, src.elements[0].color
            for element in src.elements[1:]:
                dst.elements.new(element.position).color = element.color
        else:
            params[key] = value
    kept_values = {k: old[k] for k in kept}
    new.update(kept_values)
    tree['pixel_cel_set'] = json.dumps(new)
    bpy.data.node_groups.remove(scratch)
    return kept
```

Change `convert_material` so an existing Pixel Cel tree is updated instead of rebuilt:

```python
def convert_material(material, preset='ASW', trees=None):
    plan = detect(describe_material(material))
    trees = {} if trees is None else trees
    key = plan.key + '|' + preset
    if key not in trees:
        existing = material.malt.shader_nodes
        if existing is not None and existing.get('pixel_cel_preset') == preset and existing.get('pixel_cel_key') == plan.key:
            update_tree(existing, plan, preset)
            trees[key] = existing
        else:
            trees[key] = build_tree(plan, preset, f'PixelCel {preset} {material.name}')
            trees[key]['pixel_cel_key'] = plan.key
    material.malt.material_type = 'Mesh'
    material.malt.shader_nodes = trees[key]
    return plan, trees[key]
```

`copy_collection`, `write_report` and the operator:

```python
def copy_collection(collection, suffix):
    existing = [c for c in bpy.data.collections if c.name.startswith(collection.name + '.' + suffix)]
    offset = len(existing) + 1

    def copy(source, parent):
        new = bpy.data.collections.new(f'{source.name}.{suffix}')
        parent.children.link(new)
        for obj in source.objects:
            duplicate = obj.copy()  # object copied, obj.data (mesh / armature) shared
            duplicate.name = f'{obj.name}.{suffix}'
            for slot in duplicate.material_slots:
                if slot.material is not None:
                    slot.link = 'OBJECT'
                    slot.material = slot.material.copy()
                    slot.material.name = f'{slot.material.name.rsplit(".", 1)[0]}.{suffix}'
            if duplicate.parent is None:
                duplicate.location.x += float(offset)
            new.objects.link(duplicate)
        for child in source.children:
            copy(child, new)
        return new

    parent = next((c for c in bpy.data.collections if collection.name in c.children), bpy.context.scene.collection)
    result = copy(collection, parent)
    # Re-point copied objects to copied parents and armature modifiers to the copied armature
    names = {o.name.rsplit('.' + suffix, 1)[0]: o for o in result.all_objects}
    for obj in result.all_objects:
        if obj.parent is not None and obj.parent.name in names:
            obj.parent = names[obj.parent.name]
        for modifier in obj.modifiers:
            if modifier.type == 'ARMATURE' and modifier.object is not None and modifier.object.name in names:
                modifier.object = names[modifier.object.name]
    return result


def write_report(report):
    text = bpy.data.texts.get('PixelArt Convert Report') or bpy.data.texts.new('PixelArt Convert Report')
    text.clear()
    for name, style, textures, warnings, tree in report:
        text.write(f'{name}: {style}  textures={",".join(textures) or "-"}  tree={tree}\n')
        for warning in warnings:
            text.write(f'    warning: {warning}\n')
    return text.name


class MALT_OT_convert_pixel_art(bpy.types.Operator):
    """Convert the selected objects' materials (or the active collection) to Malt Pixel Cel materials"""
    bl_idname = 'malt.convert_pixel_art'
    bl_label = 'Convert to Malt Pixel Art'
    bl_options = {'REGISTER', 'UNDO'}

    preset: bpy.props.EnumProperty(name='Style', items=[('ASW', 'ASW (GGXrd)', ''), ('KOF XIII', 'KOF XIII', '')])
    copy_collection: bpy.props.BoolProperty(name='Copy collection', default=False,
        description='Convert a copy of the active collection, so both styles sit side by side')
    setup_pixel_lines: bpy.props.BoolProperty(name='Set up Pixel Lines', default=True,
        description='Use the 1 px Pixel Lines node in the world render layer graph')

    def execute(self, context):
        from BlenderMalt.MaltPipeline import setup_all_ids
        objects = [o for o in context.selected_objects if o.type == 'MESH']
        if self.copy_collection or not objects:
            collection = context.collection
            if self.copy_collection:
                collection = copy_collection(collection, 'KOF' if self.preset == 'KOF XIII' else 'ASW')
            objects = [o for o in collection.all_objects if o.type == 'MESH']
        setup_all_ids()
        report = convert_objects(objects, self.preset)
        if self.setup_pixel_lines:
            setup_pixel_lines(context.scene)
        name = write_report(report)
        warnings = sum(len(r[3]) for r in report)
        self.report({'WARNING' if warnings else 'INFO'},
            f'{len(report)} materials converted, {warnings} warnings (text block "{name}")')
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


def setup_pixel_lines(scene):
    # Implemented in Task 8 (render layer graph edit); a no-op until then
    return False


def _menu(self, context):
    self.layout.operator(MALT_OT_convert_pixel_art.bl_idname)


def register():
    bpy.utils.register_class(MALT_OT_convert_pixel_art)
    bpy.types.VIEW3D_MT_object.append(_menu)


def unregister():
    bpy.types.VIEW3D_MT_object.remove(_menu)
    bpy.utils.unregister_class(MALT_OT_convert_pixel_art)
```

In `BlenderMalt/__init__.py`, find the list of submodules that get `register()` called (search for `MaltMaterial`
in that file) and add `PixelArtConvert` to it the same way. In `BlenderMalt/MaltMaterial.py`, in the panel `draw`
(line with `context.material.malt.draw_ui(...)`), add `layout.operator('malt.convert_pixel_art')` above it.

Also in `convert_objects`, after the loop: nothing else; the operator writes the report.

- [ ] **Step 3: Run the render tests to verify they pass**

Run:
```bash
cd /h/GameDev/Malt
for S in pixel_cel_reconvert pixel_cel_copy_collection; do RENDER_TIMEOUT=300 bash tools/pixelart/render.sh /h/GameDev/Pixelizer/content/malt/testmalt.blend build/pixelart/P/$S 1 $S; echo $S EXIT $?; grep -E "RECONVERT_OK|COPY_OK|AssertionError" build/pixelart/P/$S/log.txt build/pixelart/P/$S/stdout.txt; done
```
Expected: both EXIT 0, `RECONVERT_OK` and `COPY_OK` printed, the copy render shows two Aprils side by side.

Idempotence check (success criterion 3): render `pixel_cel_convert_asw` twice into two folders and compare:
```bash
RENDER_TIMEOUT=240 bash tools/pixelart/render.sh /h/GameDev/Pixelizer/content/malt/testmalt.blend build/pixelart/P/asw_again 1 pixel_cel_convert_asw
/h/GameDev/Pixelizer/.venv/Scripts/python -c "import numpy as np; from PIL import Image; a=np.array(Image.open('build/pixelart/P/pixel_cel_convert_asw/frame_0001.png')); b=np.array(Image.open('build/pixelart/P/asw_again/frame_0001.png')); print('differing px', int((a!=b).any(2).sum()))"
```
Expected: `differing px 0`.

- [ ] **Step 4: Commit**

```bash
git add BlenderMalt/PixelArtConvert.py BlenderMalt/__init__.py BlenderMalt/MaltMaterial.py tools/pixelart/scenes.py
git commit -m "pixelart: Convert to Malt Pixel Art operator, report, reconvert keeps hand edits, Copy collection"
```

---

### Task 7: Pixel Lines render-layer node (exactly 1 px lines)

**Files:**
- Create: `Malt/Pipelines/NPR_Pipeline/Nodes/RenderLayer/PixelLines.py`
- Create: `Malt/Shaders/Passes/PixelLines.glsl`
- Modify: `tools/pixelart/scenes.py` (setups `pixel_lines_on`, `pixel_lines_off`, `pixel_lines_border`)
- Test: `tools/pixelart/line_check.py` (Task 1)

**Interfaces:**
- Consumes: `line_data` and `line_color` outputs of `pixel_cel` (Task 4), connected to main pass outputs
  `Line Color` and a custom main-pass output `Pixel Line Data` (vec4) by the converter. In `build_tree` (Task 5
  file) add the custom output to the main pass IO node the same way the Suzanne tree stores `Custom Output 1`
  (the Task 5 Step 2 probe prints the property and item fields: create one item named `Pixel Line Data` of type
  `vec4`, call `main.setup()` if the probe shows such a method, then link `cel.outputs['line_data']` to
  `main.inputs['Pixel Line Data']`). Verify with a GUI run that `main.inputs` lists `Pixel Line Data`.
- Produces: render-layer node `PixelLines` with inputs `Scene`, `Color`, `Line Color`, `Pixel Line Data`,
  `Normal Depth`, `ID`, `Depth Threshold` (float, default 0.1), `Min Line` (int, default 3) and output `Color`.

Algorithm (spec 3.2, the Pixelizer `contour_lines` method):
1. **Lattice pre pass:** render the opaque batches with the `PRE_PASS` shader into an `RGBA16UI` ID texture and an
   `RGBA32F` normal-depth texture of size `(2W+1, 2H+1)`, with the projection's x row scaled by `2W / (2W+1)` and the
   y row by `2H / (2H+1)` (then lattice point `(2i+1, 2j+1)` is the centre of pixel `(i, j)` and its 4-neighbours are
   the pixel's diamond points).
2. **Decide (shader `PIXEL_LINES_DECIDE`):** per pixel read the 5 lattice samples (centre, up, down, left, right).
   Two samples disagree when their `ID.x` differ, or both are covered and `|depth_a - depth_b| > Depth Threshold *
   min(depth_a, depth_b)`. A pixel is an outline candidate when any pair (centre vs each diamond point) disagrees.
   The fill pixel F is the pixel on the nearer (smaller depth, covered) side: the pixel itself when the centre sample
   is the nearer one, else the 4-neighbour across that diamond point. The outline draws only when F's
   `Pixel Line Data.y` is 1 (ASW `Col.A` switch). Inner line candidate: `Pixel Line Data.x < 0.5` at this pixel and
   it is a minimum across the line: `x <= x` of both neighbours along the axis (horizontal or vertical) where the
   value rises the most. Output: R = line (0/1), GB = F offset (+1, so 0..2), A = 1 for outline, 0.5 for inner.
3. **Thin (shader `PIXEL_LINES_THIN`):** remove the middle pixel of every L (exactly one horizontal and one vertical
   4-neighbour line pixel, no diagonal line pixel). Same rule as `line_check.l_corners`.
4. **Prune (shader `PIXEL_LINES_PRUNE`):** with `n8` = number of 8-neighbour line pixels: remove p when `n8(p) == 0`,
   or `n8(p) == 1` and that neighbour q has `n8(q) == 1` (exactly the 8-connected pieces under 3 px, `Min Line` 3).
5. **Composite:** colour = line ? `Line Color` at F (outline) or the fill's own colour x `ilm` line darkness (inner,
   read from `Pixel Line Data.x` at the pixel) : `Color`. Only line pixels change.

- [ ] **Step 1: Write the failing render test**

```python
def _use_pixel_lines(scene, enabled):
    # In memory: in every Render Layer graph, route the main pass through PixelLines instead of LineRender
    from BlenderMalt import PixelArtConvert
    PixelArtConvert.setup_pixel_lines(scene, enabled)


def pixel_lines_on(scene):
    ray_traced(scene)
    april = _collection_objects('GGXRD')
    _solo(scene, april)
    _frame_objects(scene, april, 256)
    _convert_all(scene, 'ASW')
    _use_pixel_lines(scene, True)


def pixel_lines_off(scene):
    ray_traced(scene)
    april = _collection_objects('GGXRD')
    _solo(scene, april)
    _frame_objects(scene, april, 256)
    _convert_all(scene, 'ASW')
    _use_pixel_lines(scene, False)


def pixel_lines_border(scene):
    # Review focus 5: the character cut by the frame border and two characters overlapping
    ray_traced(scene)
    april = _collection_objects('GGXRD')
    arthur = _collection_objects('arthurmodel')
    _solo(scene, april + arthur)
    camera = _frame_objects(scene, april, 256)
    camera.data.ortho_scale *= 0.6  # cut at the border
    _convert_all(scene, 'ASW')
    _use_pixel_lines(scene, True)


def pixel_lines_border_off(scene):
    pixel_lines_border(scene)
    _use_pixel_lines(scene, False)
```

Run:
```bash
cd /h/GameDev/Malt
RENDER_TIMEOUT=240 bash tools/pixelart/render.sh /h/GameDev/Pixelizer/content/malt/testmalt.blend build/pixelart/P/pixel_lines_on 1 pixel_lines_on; echo EXIT $?
```
Expected: EXIT 1, `TypeError: setup_pixel_lines() takes 1 positional argument but 2 were given` (Task 6 stub).

- [ ] **Step 2: Write the shaders**

```glsl
// Malt/Shaders/Passes/PixelLines.glsl
// 1 px line decision for the PixelLines node (docs/pixelart/05-pixel-cel-materials-spec.md, section 3.2).
// Only decides which pixels are lines (and their fill pixel); colours are composited in PIXEL_LINES_COMPOSITE.
#include "Common.glsl"

#ifdef PIXEL_SHADER

layout (location = 0) out vec4 OUT_RESULT;

#ifdef PIXEL_LINES_DECIDE
uniform usampler2D lattice_id;          // (2W+1, 2H+1)
uniform sampler2D lattice_normal_depth; // (2W+1, 2H+1), depth in .w
uniform sampler2D line_data;            // (W, H): x = inner line value, y = outline enable
uniform float depth_threshold;

bool _covered(uvec4 id) { return id.x != 0u; }

bool _disagree(ivec2 a, ivec2 b)
{
    uvec4 ia = texelFetch(lattice_id, a, 0);
    uvec4 ib = texelFetch(lattice_id, b, 0);
    if(ia.x != ib.x) return true;
    if(!_covered(ia)) return false;
    float da = texelFetch(lattice_normal_depth, a, 0).w;
    float db = texelFetch(lattice_normal_depth, b, 0).w;
    return abs(da - db) > depth_threshold * min(da, db);
}

void main()
{
    ivec2 p = ivec2(gl_FragCoord.xy);
    ivec2 size = textureSize(line_data, 0);
    ivec2 c = 2 * p + 1;
    ivec2 offsets[4] = ivec2[4](ivec2(0, 1), ivec2(0, -1), ivec2(-1, 0), ivec2(1, 0));
    OUT_RESULT = vec4(0.0, 1.0 / 2.0, 1.0 / 2.0, 0.0);

    // Outline: the 5 diamond samples disagree. F = the nearer covered side.
    float centre_depth = texelFetch(lattice_normal_depth, c, 0).w;
    bool centre_covered = _covered(texelFetch(lattice_id, c, 0));
    for(int k = 0; k < 4; k++)
    {
        ivec2 q = c + offsets[k];
        if(!_disagree(c, q)) continue;
        bool q_covered = _covered(texelFetch(lattice_id, q, 0));
        float q_depth = texelFetch(lattice_normal_depth, q, 0).w;
        bool centre_nearer = centre_covered && (!q_covered || centre_depth <= q_depth);
        ivec2 f = centre_nearer ? p : p + offsets[k];
        if(any(lessThan(f, ivec2(0))) || any(greaterThanEqual(f, size))) continue;
        if(texelFetch(line_data, f, 0).y < 0.5) continue;   // ASW Col.A switch: no outline here
        OUT_RESULT = vec4(1.0, vec2(f - p + 1) / 2.0, 1.0);
        return;
    }

    // Inner line: below 0.5 and a minimum across the line (1 px centre line of the texture stroke)
    float v = texelFetch(line_data, p, 0).x;
    if(v < 0.5)
    {
        float l = texelFetch(line_data, clamp(p + ivec2(-1, 0), ivec2(0), size - 1), 0).x;
        float r = texelFetch(line_data, clamp(p + ivec2(1, 0), ivec2(0), size - 1), 0).x;
        float d = texelFetch(line_data, clamp(p + ivec2(0, -1), ivec2(0), size - 1), 0).x;
        float u = texelFetch(line_data, clamp(p + ivec2(0, 1), ivec2(0), size - 1), 0).x;
        bool horizontal_rise = (l + r) >= (d + u);
        bool minimum = horizontal_rise ? (v <= l && v < r) : (v <= d && v < u);
        if(minimum)
        {
            OUT_RESULT = vec4(1.0, 0.5, 0.5, 0.5);
        }
    }
}
#endif //PIXEL_LINES_DECIDE

#if defined(PIXEL_LINES_THIN) || defined(PIXEL_LINES_PRUNE)
uniform sampler2D lines;

bool _line(ivec2 q)
{
    ivec2 size = textureSize(lines, 0);
    if(any(lessThan(q, ivec2(0))) || any(greaterThanEqual(q, size))) return false;
    return texelFetch(lines, q, 0).r > 0.5;
}

int _n8(ivec2 q)
{
    int n = 0;
    for(int y = -1; y <= 1; y++)
        for(int x = -1; x <= 1; x++)
            if((x != 0 || y != 0) && _line(q + ivec2(x, y))) n++;
    return n;
}

void main()
{
    ivec2 p = ivec2(gl_FragCoord.xy);
    vec4 value = texelFetch(lines, p, 0);
    OUT_RESULT = value;
    if(value.r < 0.5) return;
    #ifdef PIXEL_LINES_THIN
    {
        bool up = _line(p + ivec2(0, 1)), dn = _line(p + ivec2(0, -1));
        bool lf = _line(p + ivec2(-1, 0)), rt = _line(p + ivec2(1, 0));
        bool diag = _line(p + ivec2(-1, -1)) || _line(p + ivec2(1, -1)) || _line(p + ivec2(-1, 1)) || _line(p + ivec2(1, 1));
        int ortho = int(up) + int(dn) + int(lf) + int(rt);
        if((up != dn) && (lf != rt) && ortho == 2 && !diag)
        {
            OUT_RESULT.r = 0.0;
        }
    }
    #endif
    #ifdef PIXEL_LINES_PRUNE
    {
        int n = _n8(p);
        if(n == 0)
        {
            OUT_RESULT.r = 0.0;
        }
        else if(n == 1)
        {
            for(int y = -1; y <= 1; y++)
                for(int x = -1; x <= 1; x++)
                    if((x != 0 || y != 0) && _line(p + ivec2(x, y)) && _n8(p + ivec2(x, y)) == 1)
                        OUT_RESULT.r = 0.0;
        }
    }
    #endif
}
#endif //PIXEL_LINES_THIN || PIXEL_LINES_PRUNE

#ifdef PIXEL_LINES_COMPOSITE
uniform sampler2D color_texture;
uniform sampler2D line_color_texture;
uniform sampler2D line_data;
uniform sampler2D lines;

void main()
{
    ivec2 p = ivec2(gl_FragCoord.xy);
    vec4 color = texelFetch(color_texture, p, 0);
    vec4 l = texelFetch(lines, p, 0);
    OUT_RESULT = color;
    if(l.r < 0.5) return;
    if(l.a > 0.75)
    {
        ivec2 f = p + ivec2(round(l.gb * 2.0)) - 1;
        OUT_RESULT = vec4(texelFetch(line_color_texture, f, 0).rgb, 1.0);
    }
    else
    {
        OUT_RESULT = vec4(color.rgb * texelFetch(line_data, p, 0).x, color.a);
    }
}
#endif //PIXEL_LINES_COMPOSITE

#endif //PIXEL_SHADER
```

Note on the depth sample `.w` of `Normal Depth`: the pre pass writes `OUT_NORMAL_DEPTH.w = gl_FragCoord.z`
(non-linear). For the depth-step test, linearize first with the projection (Common.glsl has
`depth_to_z`/`linear_depth` helpers; search `Common/` for the exact name and use it on both samples).

- [ ] **Step 3: Write the node**

```python
# Malt/Pipelines/NPR_Pipeline/Nodes/RenderLayer/PixelLines.py
from Malt.GL.GL import *
from Malt.GL.Texture import Texture
from Malt.GL.RenderTarget import RenderTarget
from Malt.PipelineNode import PipelineNode
from Malt.PipelineParameters import Parameter, Type
from Malt.Scene import TextureShaderResource

_SHADERS = {}


def _shader(pipeline, define):
    if define not in _SHADERS:
        _SHADERS[define] = pipeline.compile_shader_from_source(f'#define {define}\n#include "Passes/PixelLines.glsl"')
    return _SHADERS[define]


def lattice_projection(projection, resolution):
    # Column-major 4x4: scale the x row by 2W/(2W+1) and the y row by 2H/(2H+1)
    w, h = resolution
    p = list(projection)
    sx, sy = 2.0 * w / (2.0 * w + 1.0), 2.0 * h / (2.0 * h + 1.0)
    for column in range(4):
        p[column * 4 + 0] *= sx
        p[column * 4 + 1] *= sy
    return tuple(p)


class PixelLines(PipelineNode):
    """
    Draws exactly 1 px lines (outline on the sub-pixel silhouette, diamond rule; inner lines from Pixel Line Data)
    and composites them over *Color*. Only line pixels change.
    """

    def __init__(self, pipeline):
        PipelineNode.__init__(self, pipeline)
        self.resolution = None

    @classmethod
    def reflect_inputs(cls):
        inputs = {}
        inputs['Scene'] = Parameter('Scene', Type.OTHER)
        inputs['Color'] = Parameter('', Type.TEXTURE)
        inputs['Line Color'] = Parameter('', Type.TEXTURE)
        inputs['Pixel Line Data'] = Parameter('', Type.TEXTURE)
        inputs['Depth Threshold'] = Parameter(0.1, Type.FLOAT)
        return inputs

    @classmethod
    def reflect_outputs(cls):
        outputs = {}
        outputs['Color'] = Parameter('', Type.TEXTURE)
        return outputs

    def setup_render_targets(self, resolution):
        w, h = resolution
        lattice = (2 * w + 1, 2 * h + 1)
        self.t_lattice_depth = Texture(lattice, GL_DEPTH_COMPONENT32F)
        self.t_lattice_normal_depth = Texture(lattice, GL_RGBA32F)
        self.t_lattice_id = Texture(lattice, GL_RGBA16UI, min_filter=GL_NEAREST, mag_filter=GL_NEAREST)
        self.fbo_lattice = RenderTarget([self.t_lattice_normal_depth, self.t_lattice_id], self.t_lattice_depth)
        self.t_lines = [Texture(resolution, GL_RGBA16F, min_filter=GL_NEAREST, mag_filter=GL_NEAREST) for _ in range(2)]
        self.fbo_lines = [RenderTarget([t]) for t in self.t_lines]
        self.t_color = Texture(resolution, GL_RGBA16F)
        self.fbo_color = RenderTarget([self.t_color])
        # Unused by opaque materials, but the pre pass shader declares them
        self.t_dummy_depth = Texture(lattice, GL_DEPTH_COMPONENT32F)
        self.t_dummy_id = Texture(lattice, GL_R16UI, min_filter=GL_NEAREST, mag_filter=GL_NEAREST)

    def execute(self, parameters):
        inputs = parameters['IN']
        outputs = parameters['OUT']
        scene = inputs['Scene']
        if self.pipeline.resolution != self.resolution:
            self.setup_render_targets(self.pipeline.resolution)
            self.resolution = self.pipeline.resolution
        w, h = self.resolution
        lattice = (2 * w + 1, 2 * h + 1)

        # 1. Lattice pre pass (opaque batches only)
        opaque_batches, _ = self.pipeline.get_scene_batches(scene)
        common = self.pipeline.common_buffer
        common.load(scene, lattice, (0, 0), self.pipeline.sample_count,
            projection=lattice_projection(scene.camera.projection_matrix, self.resolution))
        resources = scene.shader_resources.copy()
        resources['COMMON_UNIFORMS'] = common
        resources['IN_OPAQUE_DEPTH'] = TextureShaderResource('IN_OPAQUE_DEPTH', self.t_dummy_depth)
        resources['IN_TRANSPARENT_DEPTH'] = TextureShaderResource('IN_TRANSPARENT_DEPTH', self.t_dummy_depth)
        resources['IN_LAST_ID'] = TextureShaderResource('IN_LAST_ID', self.t_dummy_id)
        self.fbo_lattice.clear([(0, 0, 0, 1), (0, 0, 0, 0)], 1)
        self.pipeline.draw_scene_pass(self.fbo_lattice, opaque_batches, 'PRE_PASS',
            self.pipeline.default_shader['PRE_PASS'], resources)
        common.load(scene, self.resolution, self.pipeline.get_sample(scene.world_parameters['Samples.Width']),
            self.pipeline.sample_count)

        # 2-4. Decide, thin, prune
        decide = _shader(self.pipeline, 'PIXEL_LINES_DECIDE')
        decide.textures['lattice_id'] = self.t_lattice_id
        decide.textures['lattice_normal_depth'] = self.t_lattice_normal_depth
        decide.textures['line_data'] = inputs['Pixel Line Data']
        decide.uniforms['depth_threshold'].set_value(inputs['Depth Threshold'])
        common.shader_callback(decide)
        self.pipeline.draw_screen_pass(decide, self.fbo_lines[0])
        thin = _shader(self.pipeline, 'PIXEL_LINES_THIN')
        thin.textures['lines'] = self.t_lines[0]
        self.pipeline.draw_screen_pass(thin, self.fbo_lines[1])
        prune = _shader(self.pipeline, 'PIXEL_LINES_PRUNE')
        prune.textures['lines'] = self.t_lines[1]
        self.pipeline.draw_screen_pass(prune, self.fbo_lines[0])

        # 5. Composite
        composite = _shader(self.pipeline, 'PIXEL_LINES_COMPOSITE')
        composite.textures['color_texture'] = inputs['Color']
        composite.textures['line_color_texture'] = inputs['Line Color']
        composite.textures['line_data'] = inputs['Pixel Line Data']
        composite.textures['lines'] = self.t_lines[0]
        self.pipeline.draw_screen_pass(composite, self.fbo_color)
        outputs['Color'] = self.t_color


NODE = PixelLines
```

Note: the main pass must be drawn before PixelLines and must output `Pixel Line Data`; the PrePass node's
`PRE_PASS` render happens before. `common.load(...)` is restored after the lattice pass so later passes see the
normal resolution and AA sample offset.

`setup_pixel_lines(scene, enabled=True)` in `BlenderMalt/PixelArtConvert.py` (replaces the Task 6 stub): in every
Malt tree with `graph_type == 'Render Layer'` used by the world's Render graph, add a `PixelLines` node (Malt render
layer nodes are `MaltFunctionNode`s whose `function_type` is the node class name; check with the Task 5 probe by
printing `[n.function_type for n in tree.nodes]` of `Default Render Layer`: `'LineRender'`, `'MainPass'`, ...),
link `MainPass.Color -> PixelLines.Color`, `MainPass.Line Color -> PixelLines.Line Color`,
`MainPass.Pixel Line Data -> PixelLines.Pixel Line Data`, `PrePass.Scene -> PixelLines.Scene`, and move the links
that left `LineRender.Color` to leave `PixelLines.Color`. With `enabled=False` restore the LineRender links. Keep
LineRender in the tree (owner can switch back).

- [ ] **Step 4: Run the render tests to verify they pass**

Run:
```bash
cd /h/GameDev/Malt
for S in pixel_lines_on pixel_lines_off pixel_lines_border pixel_lines_border_off; do RENDER_TIMEOUT=300 bash tools/pixelart/render.sh /h/GameDev/Pixelizer/content/malt/testmalt.blend build/pixelart/P/$S 1 $S; echo $S EXIT $?; done
/h/GameDev/Pixelizer/.venv/Scripts/python tools/pixelart/line_check.py build/pixelart/P/pixel_lines_on/frame_0001.png build/pixelart/P/pixel_lines_off/frame_0001.png
/h/GameDev/Pixelizer/.venv/Scripts/python tools/pixelart/line_check.py build/pixelart/P/pixel_lines_border/frame_0001.png build/pixelart/P/pixel_lines_border_off/frame_0001.png
```
Expected: all EXIT 0; both checks print `'total': 0` and exit 0; `line px` > 500. Also check by eye on a 3x sheet
(`side_by_side.py`) that there is no line along the image border and lines between April and Arthur are 1 px. Then
3 animation frames (if the armature has an action: frames 1, 5, 10; else rotate the sun 10 degrees per frame in a
setup) also give `'total': 0`. Write all numbers into `docs/pixelart/07-pixel-cel-results.md` `## Pixel Lines`.

If `line_check` fails: find which rule (blocks, l_corners, isolated, short) and fix the decision at its cause; never
add a filter on colours.

- [ ] **Step 5: Inner lines move to Pixel Lines**

In `PixelCel.glsl`, delete the block `if(use_ilm_texture && ilm.a <= 0.5) { rgb *= ilm.a; }` (Pixel Lines now draws
the inner lines at 1 px). Update `cel_ref.cel_color`'s `line_mask` doc comment to say the reference keeps it for the
material-only path (Pixel Lines off). Re-run Task 4 Step 4 and this task's Step 4.

- [ ] **Step 6: Commit**

```bash
git add Malt/Pipelines/NPR_Pipeline/Nodes/RenderLayer/PixelLines.py Malt/Shaders/Passes/PixelLines.glsl BlenderMalt/PixelArtConvert.py Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/PixelCel.glsl Malt/PixelArt/cel_ref.py tools/pixelart/scenes.py docs/pixelart/07-pixel-cel-results.md
git commit -m "pixelart: Pixel Lines render-layer node, exactly 1 px outlines (lattice diamond rule) and inner lines"
```

---

### Task 8: End to end on April, KOF XIII tuning, owner review

**Files:**
- Modify: `Malt/PixelArt/presets.py` (tuned KOF XIII values)
- Modify: `tools/pixelart/scenes.py` (setup `pixel_cel_both_styles`)
- Modify: `docs/pixelart/07-pixel-cel-results.md`
- Create: `docs/pixelart/img/pixel_cel_*.png` (sheets)

**Interfaces:**
- Consumes: everything above.
- Produces: the owner review package (sheets + results note) and the final preset values.

- [ ] **Step 1: Render both styles side by side**

```python
def pixel_cel_both_styles(scene):
    from BlenderMalt import PixelArtConvert
    ray_traced(scene)
    source = bpy.data.collections['GGXRD']
    copy = PixelArtConvert.copy_collection(source, 'KOF')
    april = _collection_objects('GGXRD')
    kof = [o for o in copy.all_objects if o.type == 'MESH']
    PixelArtConvert.convert_objects(april, 'ASW')
    PixelArtConvert.convert_objects(kof, 'KOF XIII')
    PixelArtConvert.setup_pixel_lines(scene, True)
    _solo(scene, april + kof)
    _frame_objects(scene, april + kof, 256)
```

Run:
```bash
cd /h/GameDev/Malt
RENDER_TIMEOUT=300 bash tools/pixelart/render.sh /h/GameDev/Pixelizer/content/malt/testmalt.blend build/pixelart/P/both 1 pixel_cel_both_styles; echo EXIT $?
```
Expected: EXIT 0. Make a 3x sheet with `side_by_side.py` and copy it to `docs/pixelart/img/pixel_cel_both.png`.

- [ ] **Step 2: Compare with the references and tune KOF XIII**

Open `H:/GameDev/Pixelizer/content/malt/refs/april_ggxrd_1.png` and `april_ggxrd_2.webp` next to the ASW half: the
ASW half must show April's colours from `APRL_base`, the shadow from `APRL_Sss`, ilm inner lines, decals (hat text,
face details) cut out, 1 px near-black outlines. For KOF XIII, check 4 tones visible on the skirt and hat, shadows
shifted toward purple, coloured outlines. Change only the values in `PRESETS['KOF XIII']`; record every change and
the reason in the results note. Re-run Step 1 after each change. Stop after at most 4 rounds and hand over.

- [ ] **Step 3: Frame time and full checks**

Run the ASW render of April and the original Suzanne material render at 256 px (setups `pixel_cel_convert_asw` and
`lines_w1`), read `frame N.NNNs` from both `log.txt`, and write them into the results note (criterion: at most
+10 %; if it is more, record the number and the cause, do not hide it). Run `line_check.py` on the `both` render
against the same render with Pixel Lines off (add `pixel_cel_both_styles_off` that calls `setup_pixel_lines(scene,
False)`), expect `'total': 0`. Run all tests:
`H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart -q`.

- [ ] **Step 4: Results note and owner review**

Write `docs/pixelart/07-pixel-cel-results.md`: per success criterion of the spec (1-6, 5a, 5b) the measured result,
the sheet paths, the tuned KOF XIII values, and open items. Copy the note and sheets to
`H:/GameDev/Pixelizer/docs/malt/` (same file names, sheets in `docs/malt/img/`). Commit both repos, push the fork.

```bash
git add Malt/PixelArt/presets.py tools/pixelart/scenes.py docs/pixelart/07-pixel-cel-results.md docs/pixelart/img
git commit -m "pixelart: April in ASW and KOF XIII, tuned KOF preset, results for owner review"
git push origin pixelart
```

---

## Self-review notes (plan author)

- Spec coverage: 2.1 node -> Task 4; 2.2 converter -> Tasks 5-6; 2.3 tests -> Tasks 1-4; 3 rules -> Tasks 3-4;
  3.1 presets -> Tasks 3, 8; 3.2 lines -> Tasks 1, 7; 4.1-4.3 -> Tasks 2, 5, 6; 6 success criteria -> Tasks 6-8.
- Refinement against spec 2.2: the textures are inputs of the Pixel Cel node itself (not separate Image nodes),
  so a converted tree is one node + outputs; the owner can still open and change every input in the node editor.
- Decals use the decal texture as base colour with the cutout in the pre pass (spec 3, "Decal meshes").
