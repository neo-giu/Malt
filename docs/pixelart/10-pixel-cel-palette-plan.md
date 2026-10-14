# Pixel Cel Palette + KEEP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> In this repo the tasks run as cards: `docs/specs/pixelpal/tasks/` (RULES.md applies).

**Goal:** Converted characters render only colours from one owner-editable palette (texture picks the ramp, cel shading
picks the slot), KOF XIII follows the Kim line rules, and thin parts (fingers) never vanish (KEEP).

**Architecture:** A pure-Python module `Malt/PixelArt/zones.py` clusters each base texture in Oklab into zones, groups
zones into ramps and writes the palette (JSON text + PNG strip + a GPU palette image). Pixel Cel gets palette inputs
(zone texture, palette image) and returns palette colours only. Pixel Lines gets KEEP (conservative coverage for tagged
parts, read from a bit in the pre-pass ID) and the KOF L2 rule (overlap line only over a dark far side).

**Tech Stack:** Python 3.13 + numpy (core, tested with pytest), Blender 5.2 bpy (converter), GLSL in Malt's NPR
pipeline, render checks through `tools/pixelart/render.sh`.

**Spec:** `docs/pixelart/09-pixel-cel-palette-spec.md` (approved 2026-10-14), base spec
`docs/pixelart/05-pixel-cel-materials-spec.md`. KEEP comes from the Pixelizer renderer
(`H:/GameDev/Pixelizer/src/pixelizer/keep.py`: "parts tagged KEEP never vanish between pixel centres"), asked for by
the owner on 2026-10-14 after the outline-ring fix made April's fingers disappear.

## Global Constraints

- Every line is exactly 1 px; no line width input; Col.A only switches the outline on or off.
- Nothing of the model outside the outline: `line_check.py --marker` must report `outside 0`.
- No post-pass filter on colours. Zones are cleaned on the texture (island merge), never on the frame.
- Never save or modify `.blend` files from tests; render from `H:/GameDev/Pixelizer/content/malt/` copies, in memory.
- Never change or delete the original Cycles/EEVEE material nodes.
- Blender launches: max 3 per card, setups batched with a comma list; `py_compile` every edited .py before a launch.
- Enum inputs do not work as node sockets: bool/int/float only.
- Palette budget default 40 colours per character (lines included).

## Review Focus

1. A material with no base texture (Dude, untextured): one zone with the base colour; must still render palette-only.
   Test: `test_untextured_material_is_one_zone` (Task 2) and the Dude frame in the Task 4 palette check.
2. A base texture with alpha (APRL_base has mean alpha 0.16; decals): transparent texels belong to no zone and never
   pull the k-means. Test: `test_transparent_texels_get_no_zone` (Task 2).
3. The owner edits the PNG strip in Aseprite and reconverts: edited colours must survive and reach the render.
   Test: `test_strip_round_trip_keeps_edits` (Task 2) and setup `pixel_pal_edit` (Task 4).
4. A KEEP part thinner than a pixel where no neighbouring pixel centre shows the same object (fingertip): the pixel
   still shows a line. Check: KEEP marker pixels in the hands box > 0 for both presets (Task 1).
5. Two materials whose clusters land in one ramp with different Sss shadows (ASW): the ramp shadow is the mean of
   their Sss cluster means, and the frame still holds palette colours only. Test: `test_asw_ramp_shadow_mean` (Task 2).

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/PixelCel.glsl` | KEEP id function; palette inputs | 1, 3 |
| `Malt/Shaders/Passes/PixelLines.glsl` | KEEP coverage and protection; L2 far-side rule; palette inner lines | 1, 3, 5 |
| `Malt/PixelArt/detect.py` | `keep_by_name` | 1 |
| `Malt/PixelArt/zones.py` (new) | Oklab k-means, island merge, ramps, palette JSON/PNG/GPU arrays | 2 |
| `Malt/PixelArt/cel_ref.py` | `palette_slot` reference | 3 |
| `Malt/PixelArt/presets.py` | palette slots and stops per preset | 2, 5 |
| `BlenderMalt/PixelArtConvert.py` | KEEP wiring; palette build and wiring per collection | 1, 4 |
| `tools/pixelart/line_check.py` | KEEP marker colour, KEEP exemption | 1 |
| `tools/pixelart/palette_check.py` (new) | frame colours ⊆ palette | 4 |
| `tools/pixelart/scenes.py` | setups (append only) | 1, 4, 5 |
| `tests/pixelart/test_zones.py` (new), `test_pixel_cel_detect.py`, `test_line_check.py`, `test_pixel_cel_ref.py` | tests | 1-3 |
| `docs/pixelart/07-pixel-cel-results.md` | measured results | 1, 4, 5 |

---

### Task 1: KEEP — thin parts never vanish

**Files:**
- Modify: `Malt/PixelArt/detect.py`, `tests/pixelart/test_pixel_cel_detect.py`
- Modify: `Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/PixelCel.glsl` (new function only)
- Modify: `Malt/Shaders/Passes/PixelLines.glsl`
- Modify: `BlenderMalt/PixelArtConvert.py` (`build_tree`, `update_tree`, report)
- Modify: `tools/pixelart/line_check.py`, `tests/pixelart/test_line_check.py`
- Modify: `tools/pixelart/scenes.py` (append), `docs/pixelart/07-pixel-cel-results.md`

**Interfaces:**
- Produces: `detect.keep_by_name(material_name: str, object_names: list[str]) -> bool`; `ConvertPlan.keep: bool`
  (default False); GLSL `uvec4 pixel_cel_keep_id(bool keep)`; lines-texture kind `PIXEL_LINES_KEEP 0.78`;
  marker colour yellow `(255, 255, 0)` for KEEP line pixels; `line_check.marker_mask(image)` includes yellow;
  `line_check.keep_mask(image)`; `line_violations(mask, exempt=None)`.
- Consumes: kinds and `_IS_SILHOUETTE` from `PixelLines.glsl` (commit d5f29d4); `_pre_pass_node(tree)`.

- [ ] **Step 1: Write the failing tests**

`tests/pixelart/test_pixel_cel_detect.py`, append:

```python
from Malt.PixelArt.detect import keep_by_name


def test_keep_by_name_hands_fingers_straps():
    assert keep_by_name('5_hands_1_0_0.001', ['5_hands_1_0_0.001'])
    assert keep_by_name('Body', ['L_Finger_02'])
    assert keep_by_name('BagStrap', [])
    assert keep_by_name('Glove_mat', [])
    assert not keep_by_name('5_body_1_0_0.001', ['5_body_1_0_0.001'])
    assert not keep_by_name('Shoulder', ['Handle'])   # 'hand' only as a whole word part, not in 'Handle'
```

`tests/pixelart/test_line_check.py`, append:

```python
def test_keep_pixels_are_lines_and_exempt_from_short_and_isolated():
    from line_check import marker_mask, keep_mask
    a = np.zeros((3, 5, 3), dtype=np.uint8)
    a[1, 1] = (255, 255, 0)               # a lone KEEP pixel
    a[1, 3] = (255, 0, 255)               # a lone outline pixel
    mask, keep = marker_mask(a), keep_mask(a)
    assert mask[1, 1] and mask[1, 3] and keep[1, 1] and not keep[1, 3]
    v = line_violations(mask, exempt=keep)
    assert v['isolated'] == 1 and v['short'] == 1   # only the outline pixel counts
```

- [ ] **Step 2: Run them, see them fail**

Run: `H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart/test_pixel_cel_detect.py tests/pixelart/test_line_check.py -q`
Expected: FAIL, `ImportError: cannot import name 'keep_by_name'` and `cannot import name 'keep_mask'`.

- [ ] **Step 3: Implement detection and the check tool**

`Malt/PixelArt/detect.py`: add the field `keep: bool = False` to `ConvertPlan` (after `use_vertex_color`; it is NOT part
of `key`), and:

```python
_KEEP = re.compile(r'(^|[^a-z])(hands?|fingers?|gloves?|straps?)([^a-z]|$)', re.IGNORECASE)


def keep_by_name(material_name, object_names):
    # KEEP parts (Pixelizer keep.py): thin parts that must never vanish between pixel centres
    return any(_KEEP.search(n.replace('_', ' ')) for n in [material_name, *object_names])
```

(`replace('_', ' ')` makes `5_hands_1` and `L_Finger_02` match the word rule; `Handle` does not.)

`tools/pixelart/line_check.py`: `marker_mask` also takes yellow; add `keep_mask`; `line_violations` takes `exempt`:

```python
def keep_mask(image):
    a = np.asarray(image).astype(int)[..., :3]
    return (a[..., 0] == 255) & (a[..., 1] == 255) & (a[..., 2] == 0)
```

In `marker_mask` return `magenta | cyan | keep_mask(image)`. In `line_violations(mask, exempt=None)`: `isolated` and
`short` skip pixels / components that touch `exempt` (`exempt` None = nothing exempt); blocks and l_corners still count
everywhere. The CLI `--marker` path passes `exempt=keep_mask(image)`.

- [ ] **Step 4: Run the tests, see them pass**

Same command as Step 2. Expected: all pass (detect 10, line_check 8).

- [ ] **Step 5: GLSL — KEEP id function (PixelCel.glsl, before `#endif //PIXEL_CEL_GLSL`)**

```glsl
#define PIXEL_CEL_KEEP_BIT 1u

/*  META
    @meta: label=Pixel Cel Keep ID;
    @keep: default=false;
*/
// Pre pass ID with the KEEP bit (Pixel Lines: this part never vanishes between pixel centres)
uvec4 pixel_cel_keep_id(bool keep)
{
    uvec4 id = ID;
    if(keep)
    {
        id.w |= PIXEL_CEL_KEEP_BIT;
    }
    return id;
}
```

- [ ] **Step 6: GLSL — KEEP in Pixel Lines (PixelLines.glsl)**

Kinds: add `#define PIXEL_LINES_KEEP 0.78` and `#define _IS_KEEP(v) (abs((v).a - PIXEL_LINES_KEEP) < 0.04)`; add
`#define _IS_RING(v) (_IS_SILHOUETTE(v) || _IS_KEEP(v))`. Replace every `_IS_SILHOUETTE(` use outside the macro
definitions with `_IS_RING(` (the ring rules apply to KEEP pixels too).

DECIDE, add `bool _keep(uvec4 id) { return (id.w & 1u) != 0u; }` and, right after `OUT_RESULT = ...` initialisation:

```glsl
    // KEEP: conservative coverage. An uncovered pixel shows a KEEP part that touches any of its 9 lattice samples;
    // F = the nearest pixel whose centre shows the same object (its colours), else the pixel itself.
    if(!centre_covered)
    {
        for(int dy = -1; dy <= 1; dy++)
        for(int dx = -1; dx <= 1; dx++)
        {
            uvec4 iq = texelFetch(lattice_id, c + ivec2(dx, dy), 0);
            if(!_covered(iq) || !_keep(iq)) continue;
            ivec2 f = p;
            ivec2 order[8] = ivec2[8](ivec2(0, 1), ivec2(0, -1), ivec2(-1, 0), ivec2(1, 0),
                                      ivec2(1, 1), ivec2(-1, 1), ivec2(1, -1), ivec2(-1, -1));
            for(int i = 0; i < 8; i++)
            {
                ivec2 n = p + order[i];
                if(any(lessThan(n, ivec2(0))) || any(greaterThanEqual(n, size))) continue;
                if(texelFetch(lattice_id, 2 * n + 1, 0).x == iq.x) { f = n; break; }
            }
            OUT_RESULT = vec4(1.0, vec2(f - p + 1) / 2.0, PIXEL_LINES_KEEP);
            return;
        }
    }
```

In the silhouette branch, the kind is `_keep(texelFetch(lattice_id, c, 0)) ? PIXEL_LINES_KEEP : PIXEL_LINES_SILHOUETTE`.

THIN/ZS/BLOCK/PRUNE: PRUNE never removes a KEEP pixel (wrap the PRUNE block body in `if(!_IS_KEEP(value))`).

COMPOSITE: the outline path reads the fill colour at F: replace `vec4(color.rgb, 1.0)` with
`vec4(texelFetch(color_texture, f, 0).rgb, 1.0)`. DEBUG: `_IS_KEEP(l) ? vec4(1, 1, 0, 1) : (l.a > 0.75 ? magenta : cyan)`.

- [ ] **Step 7: Converter wiring (PixelArtConvert.py)**

In `describe_material` callers: `convert_material(material, preset, trees, object_names)` gets the names of the objects
using the material (from `convert_objects`); set `plan.keep = keep_by_name(material.name, object_names)` after
`detect(...)`. `ConvertPlan.key` stays as is, and `build_tree` adds the KEEP id node when `plan.keep`:

```python
    if plan.keep:
        pre = _pre_pass_node(tree)
        keep = tree.nodes.new('MaltFunctionNode')
        keep.function_type = find_function(tree, 'pixel_cel_keep_id')
        keep.location = (-400, 600)
        _set(tree, keep, 'keep', True, written)
        tree.links.new(keep.outputs['result'], next(s for s in pre.inputs if s.name.lower().endswith('id')))
```

Trees are keyed by `plan.key + '|' + preset`: append `'|keep'` when `plan.keep` so a KEEP material never shares a tree
with a non-KEEP one. The report line gains `'keep'` in its warnings column when set.

If Malt cannot link a `uvec4` function output to the pre pass `id` input (graph error in stdout.txt, or the input name
differs), print the pre pass IO node's input names and types, write them into the mechanics note, and use the name
found; if `uvec4` outputs are not supported at all, report `BLOCKED: uvec4 output` with the error line.

- [ ] **Step 8: Render setups (scenes.py, append)**

```python
def _hands_box(scene, objects):
    # pixel box of the given objects in the current camera (x0, y0, x1, y1), PNG rows (y down)
    from bpy_extras.object_utils import world_to_camera_view
    w, h = scene.render.resolution_x, scene.render.resolution_y
    xs, ys = [], []
    for obj in objects:
        for corner in obj.bound_box:
            co = world_to_camera_view(scene, scene.camera, obj.matrix_world @ mathutils.Vector(corner))
            xs.append(co.x * w); ys.append((1.0 - co.y) * h)
    print('HANDS_BOX', int(min(xs)), int(min(ys)), int(max(xs)) + 1, int(max(ys)) + 1, flush=True)


def pixel_keep(scene, keep=True):
    from BlenderMalt import PixelArtConvert
    ray_traced(scene)
    april = _collection_objects('GGXRD')
    _solo(scene, april)
    _frame_objects(scene, april, 256)
    _setup_malt_ids()
    PixelArtConvert.convert_objects(april, 'ASW')
    if not keep:
        for tree in bpy.data.node_groups:
            for node in getattr(tree, 'nodes', []):
                if node.bl_idname == 'MaltFunctionNode' and 'keep_id' in str(node.function_type):
                    tree.links.remove(node.outputs['result'].links[0])
    _use_pixel_lines(scene, True)
    _hands_box(scene, [o for o in april if 'hand' in o.name.lower()])


def pixel_keep_off(scene):
    pixel_keep(scene, False)
```

(`mathutils` is imported at the top of scenes.py with `bpy`; add the import if missing.)

- [ ] **Step 9: Verify with one debug launch and one colour launch**

```
cd /h/GameDev/Malt && PIXEL_LINES_DEBUG=1 RENDER_TIMEOUT=600 bash tools/pixelart/render.sh /h/GameDev/Pixelizer/content/malt/testmalt.blend build/pixelart/P/keep_marker 1 pixel_keep,pixel_keep_off,pixel_cel_both_styles,pixel_lines_border
RENDER_TIMEOUT=600 bash tools/pixelart/render.sh /h/GameDev/Pixelizer/content/malt/testmalt.blend build/pixelart/P/keep 1 pixel_keep,pixel_keep_off,pixel_cel_debug
```

Checks, each quoted in the Report:
- `line_check.py --marker` on the 4 marker frames: `'total': 0` and `outside 0`.
- KEEP: in the HANDS_BOX of `pixel_keep` (from its log), yellow px > 0, and opaque px of `pixel_keep` >= opaque px of
  `pixel_keep_off` in that box (print both counts).
- `compare_cel.py build/pixelart/P/keep/pixel_cel_debug/frame_0001.png` -> mismatches 0.
- A 8x zoom of the hands box, on vs off (`side_by_side.py`), read by you: fingers visible with KEEP.

- [ ] **Step 10: Results note and commit**

Append the numbers to `docs/pixelart/07-pixel-cel-results.md` ("KEEP" section, max 12 lines).

```bash
git add Malt BlenderMalt tools tests docs/pixelart/07-pixel-cel-results.md docs/specs/pixelpal/mechanics
git commit -m "Pixel Lines: KEEP parts (hands, fingers, straps) never vanish: conservative coverage from the pre-pass KEEP bit"
```

---

### Task 2: zones.py — zones, ramps and the palette (pure Python)

**Files:**
- Create: `Malt/PixelArt/zones.py`, `tests/pixelart/test_zones.py`
- Modify: `Malt/PixelArt/presets.py`, `tests/pixelart/test_pixel_cel_ref.py` (preset keys test)

**Interfaces:**
- Produces:
  - `srgb_to_oklab(rgb uint8 [...,3]) -> float [...,3]`; `kmeans(points, k, seed=0, iters=50) -> (centres, labels)`
  - `cluster_texture(rgba: uint8 HxWx4, k_max=8, seed=0, sample=20000) -> (labels int HxW (-1 = transparent), centres uint8 kx3)`
  - `merge_islands(labels: int HxW, min_area=16) -> int HxW`
  - `Zone(material: str, cluster: int, rgb: tuple[int,int,int], sss: tuple|None, texels: int)` (dataclass)
  - `group_zones(zones: list[Zone], n_ramps: int, seed=0) -> list[list[int]]` (zone indices per ramp)
  - `ramp_colours(preset: str, lit_rgb, sss_rgb=None) -> (colours: list[(r,g,b)] light->dark, line: (r,g,b))`
  - `build_palette(preset: str, zones: list[Zone], budget=40, seed=0) -> dict` (the spec section 3 JSON, plus
    `"zone_ramp": {"<material>/<cluster>": "<ramp name>"}`)
  - `palette_strip(palette) -> uint8 [R, 8, 3]`; `apply_strip(palette, strip) -> dict` (colours read back)
  - `gpu_palette(palette) -> uint8 [2R, 8, 4]` (row 2r: slot colours, column 7 = line; row 2r+1: R = stop x 255 in
    columns 0..5, G of column 0 = slot count)
  - `ramp_index_texture(labels, material, palette) -> uint8 HxW` (ramp index + 1, 0 = no zone)
- Consumes: `cel_ref.shifted_shadow`, `cel_ref.srgb_to_linear`, `cel_ref.linear_to_srgb`; `PRESETS[...]['palette_slots']`,
  `PRESETS[...]['palette_stops']`.

- [ ] **Step 1: Preset keys (presets.py)** — add to both presets:

```python
        # Palette ramps (spec 09 section 4): shadow slots as (hue shift deg, saturation x, value x) of the lit colour;
        # stops: N-1 descending light thresholds (slot 0 = lightest). ASW: lit, shadow (Sss).
        'palette_slots': [],                        # ASW: the shadow slot is lit x Sss
        'palette_stops': [0.5],
```

and for KOF XIII:

```python
        'palette_slots': [(8.0, 1.1, 0.78), (15.0, 1.25, 0.55), (22.0, 1.3, 0.4)],
        'palette_stops': [0.85, 0.5, 0.35, 0.2],    # highlight | lit | shadow | deep | darkest
```

The converter's preset loop must skip keys starting with `palette_` (they are not node inputs): change
`for socket_name, value in values.items():` to skip `socket_name.startswith('palette_')`.

- [ ] **Step 2: Write the failing tests (`tests/pixelart/test_zones.py`)**

```python
import numpy as np
import pytest

from Malt.PixelArt import zones as Z


def _two_colour_texture():
    a = np.zeros((32, 32, 4), np.uint8)
    a[..., 3] = 255
    a[:, :16, :3] = (250, 220, 170)   # skin
    a[:, 16:, :3] = (40, 90, 150)     # blue
    return a


def test_kmeans_is_deterministic():
    pts = np.random.default_rng(1).random((500, 3))
    c1, l1 = Z.kmeans(pts, 4, seed=3)
    c2, l2 = Z.kmeans(pts, 4, seed=3)
    assert np.array_equal(l1, l2) and np.allclose(c1, c2)


def test_cluster_texture_finds_two_zones():
    labels, centres = Z.cluster_texture(_two_colour_texture())
    assert len(centres) == 2
    assert len(set(labels[:, :16].ravel())) == 1 and len(set(labels[:, 16:].ravel())) == 1
    assert labels[0, 0] != labels[0, 31]


def test_transparent_texels_get_no_zone():
    a = _two_colour_texture()
    a[:4, :, 3] = 0
    a[:4, :, :3] = (0, 0, 0)            # black under alpha 0 must not become a cluster
    labels, centres = Z.cluster_texture(a)
    assert (labels[:4] == -1).all() and len(centres) == 2


def test_merge_islands_removes_specks():
    labels = np.zeros((20, 20), int)
    labels[5:7, 5:7] = 1                # 4 texels
    labels[10:16, 10:16] = 2            # 36 texels
    out = Z.merge_islands(labels, min_area=16)
    assert (out[5:7, 5:7] == 0).all() and (out[10:16, 10:16] == 2).all()


def test_untextured_material_is_one_zone():
    p = Z.build_palette('ASW', [Z.Zone('Dude', 0, (120, 130, 140), None, 1)])
    assert len(p['ramps']) == 1
    (ramp,) = p['ramps'].values()
    assert ramp['colours'][0] == [120, 130, 140] and len(ramp['colours']) == 2


def test_asw_ramp_shadow_mean():
    zs = [Z.Zone('a', 0, (200, 100, 100), (128, 128, 128), 10), Z.Zone('b', 0, (202, 100, 100), (64, 64, 64), 10)]
    p = Z.build_palette('ASW', zs, budget=6)
    (ramp,) = p['ramps'].values()
    lit, shadow = ramp['colours']
    assert lit == [201, 100, 100]
    # shadow = lit x mean Sss (96 / 255), multiplied in linear light
    assert shadow == list(Z.multiply_srgb(lit, (96, 96, 96)))


def test_kof_ramp_is_light_to_dark_with_hue_shift():
    colours, line = Z.ramp_colours('KOF XIII', (240, 200, 160))
    values = [max(c) for c in colours]
    assert len(colours) == 5 and values == sorted(values, reverse=True)
    assert max(line) < values[-1]


def test_budget_limits_colours():
    zs = [Z.Zone(f'm{i}', 0, (i * 20 % 255, 100, 255 - i * 20 % 255), None, 10) for i in range(12)]
    p = Z.build_palette('KOF XIII', zs, budget=40)
    total = sum(len(r['colours']) + 1 for r in p['ramps'].values())
    assert total <= 40


def test_strip_round_trip_keeps_edits():
    p = Z.build_palette('ASW', [Z.Zone('Dude', 0, (120, 130, 140), None, 1)])
    strip = Z.palette_strip(p)
    strip[0, 0] = (10, 20, 30)          # owner edit in Aseprite
    q = Z.apply_strip(p, strip)
    (ramp,) = q['ramps'].values()
    assert ramp['colours'][0] == [10, 20, 30]


def test_gpu_palette_layout():
    p = Z.build_palette('KOF XIII', [Z.Zone('Dude', 0, (120, 130, 140), None, 1)])
    g = Z.gpu_palette(p)
    (ramp,) = p['ramps'].values()
    assert g.shape == (2, 8, 4)
    assert list(g[0, 0, :3]) == ramp['colours'][0] and list(g[0, 7, :3]) == ramp['line']
    assert g[1, 0, 1] == len(ramp['colours'])
    assert [int(v) for v in g[1, :4, 0]] == [round(s * 255) for s in ramp['stops']]


def test_ramp_index_texture():
    labels, _ = Z.cluster_texture(_two_colour_texture())
    zones = [Z.Zone('m', int(c), (0, 0, 0), None, 1) for c in sorted(set(labels.ravel()))]
    p = Z.build_palette('ASW', zones)
    t = Z.ramp_index_texture(labels, 'm', p)
    assert t.dtype == np.uint8 and t.min() >= 1
```

- [ ] **Step 3: Run, see them fail**

Run: `H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart/test_zones.py -q`
Expected: FAIL, `ImportError: cannot import name 'zones'`.

- [ ] **Step 4: Implement `Malt/PixelArt/zones.py`**

```python
# Malt/PixelArt/zones.py
# Zones and palette ramps for Pixel Cel (spec 09 section 4). No bpy, no OpenGL (unit tested outside Blender).
# Oklab and k-means ported from Pixelizer src/pixelizer/oklab.py.
import colorsys
import dataclasses
from collections import deque

import numpy as np

from .cel_ref import linear_to_srgb, shifted_shadow, srgb_to_linear
from .presets import PRESETS

_M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929], [0.2119034982, 0.6806995451, 0.1073969566],
                [0.0883024619, 0.2817188376, 0.6299787005]])
_M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468], [1.9779984951, -2.4285922050, 0.4505937099],
                [0.0259040371, 0.7827717662, -0.8086757660]])
MAX_SLOTS = 7


@dataclasses.dataclass
class Zone:
    material: str
    cluster: int
    rgb: tuple
    sss: tuple = None
    texels: int = 0


def srgb_to_oklab(rgb):
    c = np.asarray(rgb, np.float64) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return np.cbrt(lin @ _M1.T) @ _M2.T


def kmeans(points, k, seed=0, iters=50):
    rng = np.random.default_rng(seed)
    pts = np.asarray(points, np.float64)
    centres = [pts[rng.integers(len(pts))]]
    for _ in range(1, k):
        d = np.min(((pts[:, None] - np.array(centres)[None]) ** 2).sum(-1), 1)
        centres.append(pts[rng.choice(len(pts), p=d / d.sum())] if d.sum() > 0 else pts[rng.integers(len(pts))])
    c = np.array(centres)
    for _ in range(iters):
        lab = ((pts[:, None] - c[None]) ** 2).sum(-1).argmin(1)
        new = np.array([pts[lab == i].mean(0) if np.any(lab == i) else c[i] for i in range(k)])
        if np.allclose(new, c):
            break
        c = new
    return c, ((pts[:, None] - c[None]) ** 2).sum(-1).argmin(1)


def cluster_texture(rgba, k_max=8, seed=0, sample=20000):
    rgba = np.asarray(rgba)
    opaque = rgba[..., 3] >= 128
    labels = np.full(rgba.shape[:2], -1, int)
    if not opaque.any():
        return labels, np.zeros((0, 3), np.uint8)
    rgb = rgba[..., :3][opaque]
    lab = srgb_to_oklab(rgb)
    rng = np.random.default_rng(seed)
    pts = lab[rng.choice(len(lab), min(sample, len(lab)), replace=False)]
    # k: the smallest k whose inertia is under 15 % of k = 1 (elbow), at most k_max and the distinct colour count
    k_limit = min(k_max, len(np.unique(rgb, axis=0)))
    inertia1 = ((pts - pts.mean(0)) ** 2).sum()
    centres, k = pts.mean(0)[None], 1
    for k in range(1, k_limit + 1):
        centres, l = kmeans(pts, k, seed)
        if inertia1 == 0 or ((pts - centres[l]) ** 2).sum() <= 0.15 * inertia1:
            break
    assign = ((lab[:, None] - centres[None]) ** 2).sum(-1).argmin(1)
    labels[opaque] = assign
    used = sorted(set(assign.tolist()))
    remap = {old: new for new, old in enumerate(used)}
    labels[opaque] = [remap[v] for v in assign]
    means = np.array([rgb[labels[opaque] == i].mean(0) for i in range(len(used))])
    return labels, np.rint(means).astype(np.uint8)


def _components(labels, value):
    h, w = labels.shape
    seen = np.zeros_like(labels, bool)
    for y0, x0 in zip(*np.nonzero(labels == value)):
        if seen[y0, x0]:
            continue
        comp, queue = [], deque([(y0, x0)])
        seen[y0, x0] = True
        while queue:
            y, x = queue.popleft()
            comp.append((y, x))
            for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= ny < h and 0 <= nx < w and not seen[ny, nx] and labels[ny, nx] == value:
                    seen[ny, nx] = True
                    queue.append((ny, nx))
        yield comp


def merge_islands(labels, min_area=16):
    # 4-connected islands under min_area texels take the zone they share most border with (no-zone -1 never grows)
    out = np.array(labels, int, copy=True)
    h, w = out.shape
    for _ in range(5):
        changed = False
        for value in sorted(set(out.ravel().tolist()) - {-1}):
            for comp in list(_components(out, value)):
                if len(comp) >= min_area:
                    continue
                border = {}
                for y, x in comp:
                    for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                        if 0 <= ny < h and 0 <= nx < w and out[ny, nx] not in (value, -1):
                            border[out[ny, nx]] = border.get(out[ny, nx], 0) + 1
                if border:
                    target = max(sorted(border), key=border.get)
                    for y, x in comp:
                        out[y, x] = target
                    changed = True
        if not changed:
            break
    return out


def multiply_srgb(rgb, factor_rgb):
    lin = srgb_to_linear(tuple(c / 255.0 for c in rgb))
    f = srgb_to_linear(tuple(c / 255.0 for c in factor_rgb))
    return tuple(int(round(min(1.0, max(0.0, v)) * 255)) for v in linear_to_srgb(tuple(a * b for a, b in zip(lin, f))))


def _to8(lin_rgb):
    return tuple(int(round(min(1.0, max(0.0, v)) * 255)) for v in linear_to_srgb(lin_rgb))


def ramp_colours(preset, lit_rgb, sss_rgb=None):
    p = PRESETS[preset]
    lit = tuple(int(c) for c in lit_rgb)
    lin = srgb_to_linear(tuple(c / 255.0 for c in lit))
    if not p['palette_slots']:
        shadow = multiply_srgb(lit, sss_rgb) if sss_rgb is not None else _to8(tuple(c * 0.55 for c in lin))
        colours = [lit, shadow]
    else:
        highlight = _to8(tuple(min(1.0, c * 1.2) * 0.8 + w * 0.2 for c, w in zip(lin, (1.0, 0.97, 0.9))))
        colours = [highlight, lit] + [_to8(shifted_shadow(lin, h, s, v)) for h, s, v in p['palette_slots']]
        if sss_rgb is not None:
            colours[-1] = multiply_srgb(colours[-1], sss_rgb)   # ASW Sss, when present, is the deep shadow
    h, s, v = colorsys.rgb_to_hsv(*(c / 255.0 for c in colours[-1]))
    line = tuple(int(round(c * 255)) for c in colorsys.hsv_to_rgb(h, s, v * 0.6))
    return colours[:MAX_SLOTS], line


def group_zones(zones, n_ramps, seed=0):
    if len(zones) <= n_ramps:
        return [[i] for i in range(len(zones))]
    lab = srgb_to_oklab(np.array([z.rgb for z in zones]))
    _, labels = kmeans(lab, n_ramps, seed)
    groups = [sorted(np.nonzero(labels == g)[0].tolist()) for g in range(n_ramps)]
    return [g for g in groups if g]


def build_palette(preset, zones, budget=40, seed=0):
    p = PRESETS[preset]
    slots = 2 if not p['palette_slots'] else 2 + len(p['palette_slots'])
    groups = group_zones(zones, max(1, budget // (slots + 1)), seed)
    ramps, zone_ramp = {}, {}
    for i, group in enumerate(groups):
        weights = np.array([max(1, zones[j].texels) for j in group], float)
        lit = np.rint((np.array([zones[j].rgb for j in group], float) * weights[:, None]).sum(0) / weights.sum())
        ssses = [zones[j].sss for j in group if zones[j].sss is not None]
        sss = tuple(np.rint(np.mean(ssses, 0)).astype(int)) if ssses else None
        colours, line = ramp_colours(preset, tuple(int(c) for c in lit), sss)
        name = f'ramp{i}'
        ramps[name] = {'colours': [list(map(int, c)) for c in colours], 'line': list(map(int, line)),
                       'stops': list(p['palette_stops'])[:len(colours) - 1]}
        for j in group:
            zone_ramp[f'{zones[j].material}/{zones[j].cluster}'] = name
    return {'version': 1, 'preset': preset, 'ramps': ramps, 'zone_ramp': zone_ramp}


def palette_strip(palette):
    names = list(palette['ramps'])
    strip = np.zeros((len(names), MAX_SLOTS + 1, 3), np.uint8)
    for r, name in enumerate(names):
        ramp = palette['ramps'][name]
        for s, c in enumerate(ramp['colours']):
            strip[r, s] = c
        strip[r, MAX_SLOTS] = ramp['line']
    return strip


def apply_strip(palette, strip):
    out = {**palette, 'ramps': {}}
    for r, (name, ramp) in enumerate(palette['ramps'].items()):
        out['ramps'][name] = {**ramp, 'colours': [list(map(int, strip[r, s])) for s in range(len(ramp['colours']))],
                              'line': list(map(int, strip[r, MAX_SLOTS]))}
    return out


def gpu_palette(palette):
    names = list(palette['ramps'])
    g = np.zeros((2 * len(names), MAX_SLOTS + 1, 4), np.uint8)
    for r, name in enumerate(names):
        ramp = palette['ramps'][name]
        for s, c in enumerate(ramp['colours']):
            g[2 * r, s, :3] = c
        g[2 * r, MAX_SLOTS, :3] = ramp['line']
        g[2 * r, :, 3] = 255
        for s, stop in enumerate(ramp['stops']):
            g[2 * r + 1, s, 0] = round(stop * 255)
        g[2 * r + 1, 0, 1] = len(ramp['colours'])
        g[2 * r + 1, :, 3] = 255
    return g


def ramp_index_texture(labels, material, palette):
    names = list(palette['ramps'])
    t = np.zeros(labels.shape, np.uint8)
    for cluster in sorted(set(labels.ravel().tolist()) - {-1}):
        ramp = palette['zone_ramp'].get(f'{material}/{cluster}')
        if ramp is not None:
            t[labels == cluster] = names.index(ramp) + 1
    return t
```

- [ ] **Step 5: Run the tests, see them pass**

Run: `H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart -q`
Expected: all pass (zones 11 new). Fix the code, never the tests, if one fails; record what differed in the
mechanics note.

- [ ] **Step 6: Check the real April textures (no Blender)**

```
H:/GameDev/Pixelizer/.venv/Scripts/python -I -c "import sys; sys.path.insert(0, 'H:/GameDev/Malt'); import numpy as np; from PIL import Image; from Malt.PixelArt import zones as Z; a = np.array(Image.open('H:/Blender/gultygear/GGXrd - April/APRL_baseX.png').convert('RGBA')); l, c = Z.cluster_texture(a); m = Z.merge_islands(l); print('clusters', len(c), 'changed by merge', int((l != m).sum()))"
```

Quote the printed line in the Report (expected: 4-8 clusters, a few hundred texels merged).

- [ ] **Step 7: Commit**

```bash
git add Malt/PixelArt/zones.py Malt/PixelArt/presets.py BlenderMalt/PixelArtConvert.py tests/pixelart
git commit -m "Pixel Cel: zones.py (Oklab k-means zones, island merge, palette ramps, strip and GPU layouts)"
```

---

### Task 3: Pixel Cel palette shading (GLSL + reference)

**Files:**
- Modify: `Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/PixelCel.glsl`, `Malt/Shaders/Passes/PixelLines.glsl`
  (composite inner lines only)
- Modify: `Malt/PixelArt/cel_ref.py`, `tests/pixelart/test_pixel_cel_ref.py`
- Modify: `tools/pixelart/pixel_cel_debug.mesh.glsl`, `tools/pixelart/face_sdf_cel.mesh.glsl` (new call arguments)

**Interfaces:**
- Produces: `cel_ref.palette_slot(s, stops, n_slots, shadowed, highlight) -> int`; Pixel Cel inputs `use_palette`
  (bool, default false), `zone_texture` (sampler2D), `palette` (sampler2D); `line_data.w = 0.5` when the palette is on.
- Consumes: `gpu_palette` layout (Task 2): row 2r colours (column 7 line), row 2r+1 stops (R x 255, columns 0..5) and
  slot count (G of column 0); zone texture R = ramp index + 1 (8-bit, 0 = none).

- [ ] **Step 1: Failing reference test (`tests/pixelart/test_pixel_cel_ref.py`, append)**

```python
from Malt.PixelArt.cel_ref import palette_slot


def test_palette_slot():
    stops = [0.85, 0.5, 0.35, 0.2]                 # 5 slots, light -> dark
    assert palette_slot(0.9, stops, 5, False, False) == 0
    assert palette_slot(0.6, stops, 5, False, False) == 1
    assert palette_slot(0.4, stops, 5, False, False) == 2
    assert palette_slot(0.1, stops, 5, False, False) == 4
    assert palette_slot(0.9, stops, 5, True, False) == 4      # shadowed: straight to the darkest slot
    assert palette_slot(0.6, stops, 5, False, True) == 0      # specular highlight: slot 0
    assert palette_slot(0.6, [0.5], 2, False, False) == 0 and palette_slot(0.4, [0.5], 2, False, False) == 1
```

- [ ] **Step 2: Run, see it fail** — `pytest tests/pixelart/test_pixel_cel_ref.py -q`: `ImportError: palette_slot`.

- [ ] **Step 3: Reference (cel_ref.py)**

```python
def palette_slot(s, stops, n_slots, shadowed, highlight):
    # spec 09 section 5: slot 0 = lightest; shadowed -> darkest; stops descending
    if shadowed:
        return n_slots - 1
    if highlight:
        return 0
    return min(sum(1 for stop in stops if s < stop), n_slots - 1)
```

- [ ] **Step 4: GLSL (PixelCel.glsl)**

META: `@use_palette: default=false;`. New parameters after `bool unlit, int light_group, bool shadows, bool self_shadows,`:
`bool use_palette, sampler2D zone_texture, sampler2D palette,` (before the `out` parameters). Helper:

```glsl
int _pixel_cel_slot(sampler2D palette, int row, float s, bool shadowed, bool highlight, out int n_slots)
{
    vec4 meta = texelFetch(palette, ivec2(0, 2 * row + 1), 0);
    n_slots = int(round(meta.g * 255.0));
    if(shadowed) return n_slots - 1;
    if(highlight) return 0;
    int slot = 0;
    for(int i = 0; i < n_slots - 1; i++)
    {
        if(s < texelFetch(palette, ivec2(i, 2 * row + 1), 0).r) slot++;
    }
    return min(slot, n_slots - 1);
}
```

At the end of `pixel_cel` (after `color` and `line_data.z` are set), when `use_palette`:

```glsl
    if(use_palette)
    {
        ivec2 zsize = textureSize(zone_texture, 0);
        int zone = int(round(texelFetch(zone_texture, clamp(ivec2(uv * vec2(zsize)), ivec2(0), zsize - 1), 0).r * 255.0));
        if(zone > 0)
        {
            int row = zone - 1, n_slots;
            float s_best = best_s;   // the s of the light that gave the best tone (keep it next to best_t in the loop)
            int slot = _pixel_cel_slot(palette, row, s_best, tone == PIXEL_CEL_TONE_SHADOW && shadowed,
                                       tone == PIXEL_CEL_TONE_HIGHLIGHT, n_slots);
            color = vec4(texelFetch(palette, ivec2(slot, 2 * row), 0).rgb, base.a);
            line_color = vec4(texelFetch(palette, ivec2(7, 2 * row), 0).rgb, 1.0);
            line_data.z = outline_shadow_only ? (slot != n_slots - 1 ? 1.0 : 0.5) : 0.0;
            line_data.w = 0.5;
        }
    }
```

`_pixel_cel_tone` must return `s` too: add an `out float s_out` parameter (set to `s`), and keep `best_s` beside
`best_t` in the light loop. Unlit with palette: slot 1 (lit) of its ramp, `line_data.z` as for lit. Note: the zone
texture is read with `texelFetch` at level 0 (nearest, never blended: Malt builds averaged mipmaps for images, which
would mix ramp indices). The island merge of Task 2 is the speck control; spec 09 section 4.5's majority mips are
dropped for now (say so in the Report).

- [ ] **Step 4b: line_data.z encoding (both shaders)** — `line_data.z`: 0 = outline everywhere (ASW), 0.5 =
shadow-only material in its darkest tone/slot, 1 = shadow-only material not in its darkest tone/slot. Change the two
existing writes in PixelCel.glsl and FaceSDF.glsl from `? 1.0 : 0.0` to
`outline_shadow_only ? (<not darkest> ? 1.0 : 0.5) : 0.0`, and the composite test in PixelLines.glsl from `.z > 0.5`
to `.z > 0.75` (the L1 rule is unchanged; Task 5's L2 rule needs to know the material is shadow-only).

- [ ] **Step 5: Composite inner lines (PixelLines.glsl)** — inner line pixels of palette materials take the line
colour: in the `else` branch of the composite, `texelFetch(line_data, p, 0).w < 0.75 ? vec4(texelFetch(line_color_texture, p, 0).rgb, color.a) : <current>`.

- [ ] **Step 6: Update the two test shader calls** (`pixel_cel_debug.mesh.glsl`, `face_sdf_cel.mesh.glsl`): insert
`false, DEBUG_TEXTURE, DEBUG_TEXTURE,` (resp. `NO_TEXTURE`) after `false, 1, true, true,` / the matching unlit-group
arguments, so the debug renders use no palette.

- [ ] **Step 7: Verify** — pytest all pass; one launch
`RENDER_TIMEOUT=600 bash tools/pixelart/render.sh ... build/pixelart/P/pal_glsl 1 pixel_cel_debug,face_sdf_l120,pixel_cel_both_styles`:
EXIT 0, no GLSL error in stdout.txt, `compare_cel` 0 mismatches, `face_sdf_check.py` 0.29 %, both_styles frame
identical to `build/pixelart/P/ring/pixel_cel_both_styles/frame_0001.png` (palette off: 0 differing px).

- [ ] **Step 8: Commit** — `git commit -m "Pixel Cel: palette inputs (zone texture picks the ramp, the light picks the slot)"`

---

### Task 4: Converter builds and wires the palette; palette check

**Files:**
- Modify: `BlenderMalt/PixelArtConvert.py`, `tools/pixelart/scenes.py` (append)
- Create: `tools/pixelart/palette_check.py`

**Interfaces:**
- Produces: `PixelArtConvert.build_collection_palette(objects, preset, budget=40) -> (palette dict, images dict)`;
  text block `PixelCel Palette <collection>` (JSON), image `PixelCel Palette <collection>` (strip, 8 x R),
  `PixelCel GPU Palette <collection>` (8 x 2R, Non-Color, nearest), `PixelCel Zones <material>` (R8 ramp index,
  Non-Color); `convert_objects(objects, preset, palette=True)`; the line `PALETTE_REPORT <ramps> <colours>` in stdout.
- Consumes: zones.py (Task 2), Pixel Cel palette inputs (Task 3), `ConvertPlan.textures['base'|'sss']`.

- [ ] **Step 1: palette_check.py (failing run first)**

```python
# tools/pixelart/palette_check.py
"""Frame colours must be palette colours.  python palette_check.py FRAME.png PALETTE.json
Every opaque pixel's sRGB value must be a ramp colour or a line colour of the palette. Exit 1 otherwise."""
import json
import sys

import numpy as np
from PIL import Image

frame = np.array(Image.open(sys.argv[1]).convert('RGBA'))
palette = json.load(open(sys.argv[2]))
allowed = {tuple(c) for r in palette['ramps'].values() for c in r['colours'] + [r['line']]}
opaque = frame[..., 3] > 0
colours, counts = np.unique(frame[opaque][:, :3], axis=0, return_counts=True)
foreign = [(tuple(map(int, c)), int(n)) for c, n in zip(colours, counts) if tuple(map(int, c)) not in allowed]
print('colours', len(colours), 'palette', len(allowed), 'foreign colours', len(foreign),
      'foreign px', sum(n for _, n in foreign), foreign[:8])
sys.exit(1 if foreign else 0)
```

Run it on `build/pixelart/P/ring/pixel_cel_both_styles/frame_0001.png` with a one-ramp JSON written by hand
(`{"ramps": {"r": {"colours": [[0,0,0]], "line": [0,0,0]}}}` in the scratch folder): expected exit 1 with hundreds
of foreign colours (quote the line).

- [ ] **Step 2: build_collection_palette (PixelArtConvert.py)**

```python
def _image_rgba(image):
    w, h = image.size
    px = np.empty(w * h * 4, np.float32)
    image.pixels.foreach_get(px)
    # Blender pixels are bottom-up floats in the image's colour space: flip to top-down uint8 (sRGB bytes)
    return np.flipud(np.rint(px.reshape(h, w, 4) * 255).astype(np.uint8))


def _new_image(name, array, non_color=True):
    h, w = array.shape[:2]
    rgba = np.zeros((h, w, 4), np.float32)
    rgba[..., :array.shape[2] if array.ndim == 3 else 1] = (array if array.ndim == 3 else array[..., None]) / 255.0
    rgba[..., 3] = 1.0
    image = bpy.data.images.get(name) or bpy.data.images.new(name, w, h, alpha=True)
    if tuple(image.size) != (w, h):
        image.scale(w, h)
    image.colorspace_settings.name = 'Non-Color' if non_color else 'sRGB'
    image.pixels.foreach_set(np.flipud(rgba).ravel())
    image.pack()
    return image


def build_collection_palette(objects, preset, budget=40):
    from Malt.PixelArt import zones as Z
    plans, zones, labels = {}, [], {}
    for obj in objects:
        for slot in obj.material_slots:
            m = slot.material
            if m is None or m.name in plans:
                continue
            plan = detect(describe_material(m))
            plans[m.name] = plan
            base = plan.textures.get('base') or plan.textures.get('decal')
            image = _load_image(base) if base else None
            if image is None:
                zones.append(Z.Zone(m.name, 0, tuple(int(round(c * 255)) for c in linear_to_srgb(plan.base_color[:3])), None, 1))
                labels[m.name] = None
                continue
            rgba = _image_rgba(image)
            lab, centres = Z.cluster_texture(rgba)
            lab = Z.merge_islands(lab)
            sss_img = _load_image(plan.textures['sss']) if 'sss' in plan.textures else None
            sss = _image_rgba(sss_img)[..., :3] if sss_img is not None else None
            for c in range(len(centres)):
                sel = lab == c
                if not sel.any():
                    continue
                rgb = tuple(int(v) for v in np.rint(rgba[..., :3][sel].mean(0)))
                s = tuple(int(v) for v in np.rint(sss[sel].mean(0))) if sss is not None and sss.shape[:2] == lab.shape else None
                zones.append(Z.Zone(m.name, c, rgb, s, int(sel.sum())))
            labels[m.name] = lab
    collection = objects[0].users_collection[0].name if objects else 'scene'
    text_name = f'PixelCel Palette {collection}'
    palette = Z.build_palette(preset, zones, budget)
    old = bpy.data.texts.get(text_name)
    strip_image = bpy.data.images.get(text_name)
    if old is not None and strip_image is not None:
        # reconvert: owner edits in the strip (Aseprite) win over the generated colours
        saved = json.loads(old.as_string())
        if saved.get('preset') == preset and list(saved['ramps']) == list(palette['ramps']):
            palette = Z.apply_strip(saved, _image_rgba(strip_image)[..., :3])
    text = old or bpy.data.texts.new(text_name)
    text.from_string(json.dumps(palette, indent=1))
    images = {'strip': _new_image(text_name, Z.palette_strip(palette), non_color=False),
              'gpu': _new_image(f'PixelCel GPU Palette {collection}', Z.gpu_palette(palette))}
    for name, lab in labels.items():
        if lab is None:
            t = np.full((1, 1), 1 + list(palette['ramps']).index(palette['zone_ramp'][f'{name}/0']), np.uint8)
        else:
            t = Z.ramp_index_texture(lab, name, palette)
        images[name] = _new_image(f'PixelCel Zones {name}', t)
    ramps = len(palette['ramps'])
    print('PALETTE_REPORT', ramps, sum(len(r['colours']) + 1 for r in palette['ramps'].values()), flush=True)
    return palette, images
```

(`linear_to_srgb` from `Malt.PixelArt.cel_ref`; `json`, `numpy as np` imports at the top.) The strip image is the
owner's editing surface: when `apply_strip` reads it back, the strip's sRGB bytes are the colours.

In `convert_objects(objects, preset='ASW', palette=True)`: when `palette`, call `build_collection_palette` first and,
for each converted tree, `_set(tree, cel, 'use_palette', True, written)`, `_set(tree, cel, 'palette', images['gpu'], written)`,
`_set(tree, cel, 'zone_texture', images[material.name], written)`. Trees become per material when the palette is on
(the zone texture is per material): key = `plan.key + '|' + preset + '|' + material.name`.

Image sampling: the GPU palette and zone images are read with `texelFetch`; check that Malt uploads them without
colour conversion (Non-Color). If a frame colour is off by a few values from the JSON in Step 4, the image is being
converted: record what you found in the mechanics note and fix the upload setting, not the check.

- [ ] **Step 3: Setups (scenes.py, append)**

```python
def pixel_pal_asw(scene):
    ray_traced(scene)
    april = _collection_objects('GGXRD')
    _solo(scene, april)
    _frame_objects(scene, april, 256)
    _setup_malt_ids()
    from BlenderMalt import PixelArtConvert
    PixelArtConvert.convert_objects(april, 'ASW')
    _use_pixel_lines(scene, True)
    _dump_palette('GGXRD')


def _dump_palette(collection):
    import os
    text = bpy.data.texts[f'PixelCel Palette {collection}']
    path = os.path.join(os.environ.get('RENDER_OUT', '.'), f'palette_{collection}.json')
    with open(path, 'w') as f:
        f.write(text.as_string())
    print('PALETTE_FILE', path, flush=True)


def pixel_pal_kof(scene):
    ray_traced(scene)
    april = _collection_objects('GGXRD')
    _solo(scene, april)
    _frame_objects(scene, april, 256)
    _setup_malt_ids()
    from BlenderMalt import PixelArtConvert
    PixelArtConvert.convert_objects(april, 'KOF XIII')
    _use_pixel_lines(scene, True)
    _dump_palette('GGXRD')


def pixel_pal_dude(scene):
    ray_traced(scene)
    dude = _collection_objects('Dudemodel')
    _solo(scene, dude)
    _frame_objects(scene, dude, 256)
    _setup_malt_ids()
    from BlenderMalt import PixelArtConvert
    PixelArtConvert.convert_objects(dude, 'ASW')
    _use_pixel_lines(scene, True)
    _dump_palette('Dudemodel')


def pixel_pal_edit(scene):
    # owner edit round trip: convert, paint the first strip pixel red, reconvert, the render must show it
    pixel_pal_asw(scene)
    import numpy as np
    from BlenderMalt import PixelArtConvert
    strip = bpy.data.images['PixelCel Palette GGXRD']
    px = np.empty(len(strip.pixels), np.float32)
    strip.pixels.foreach_get(px)
    w, h = strip.size
    px.reshape(h, w, 4)[h - 1, 0, :3] = (1.0, 0.0, 0.0)    # top row, first slot
    strip.pixels.foreach_set(px)
    PixelArtConvert.convert_objects(_collection_objects('GGXRD'), 'ASW')
    _dump_palette('GGXRD')
```

`render_gui.py` must export `RENDER_OUT` (the setup's output folder) into `os.environ` before calling the setup: add
that one line in `setup_one` (fence: render_gui.py, this line only).

- [ ] **Step 4: Verify (2 launches)**

```
RENDER_TIMEOUT=900 bash tools/pixelart/render.sh /h/GameDev/Pixelizer/content/malt/testmalt.blend build/pixelart/P/pal 1 pixel_pal_asw,pixel_pal_kof,pixel_pal_dude,pixel_pal_edit
PIXEL_LINES_DEBUG=1 RENDER_TIMEOUT=900 bash tools/pixelart/render.sh /h/GameDev/Pixelizer/content/malt/testmalt.blend build/pixelart/P/pal_marker 1 pixel_pal_asw,pixel_pal_kof
```

- `palette_check.py build/pixelart/P/pal/<setup>/frame_0001.png build/pixelart/P/pal/<setup>/palette_<coll>.json`
  for the 4 setups: exit 0, foreign colours 0, colours <= 40.
- `pixel_pal_edit`: the frame holds (255, 0, 0) pixels (count > 0).
- `line_check.py --marker` on the 2 marker frames: total 0, outside 0.
- A 4x zoom sheet of asw / kof / dude, read by you.

- [ ] **Step 5: Commit** — `git commit -m "Pixel Cel: converter builds the collection palette (JSON + strip + zone textures); palette_check"`

---

### Task 5: KOF XIII L2 rule, tuning round, owner review package

**Files:**
- Modify: `Malt/Shaders/Passes/PixelLines.glsl` (overlap decision), `Malt/PixelArt/presets.py` (KOF values),
  `tools/pixelart/scenes.py` (append), `docs/pixelart/07-pixel-cel-results.md`, `docs/pixelart/img/pixel_pal_*.png`

**Interfaces:**
- Consumes: `line_data.z` encoding (0 / 0.5 / 1, Task 3 Step 4b); marker check from Task 1.

- [ ] **Step 1: L2 (PixelLines.glsl, DECIDE overlap loop)** — after `f` is chosen, the far side is
`ivec2 far = f == p ? p + offsets[k] : p;`. Skip the overlap line when the far side is not in its darkest slot and
the near side asks for shadow-only outlines:

```glsl
        // KOF XIII L2: a shadow-only near part draws the overlap line only where the far part is in its darkest slot
        if(texelFetch(line_data, f, 0).z > 0.25 && texelFetch(line_data, clamp(far, ivec2(0), size - 1), 0).z > 0.75)
            continue;
```

(`line_data.z` encoding from Task 3 Step 4b: ASW is 0, so ASW never skips.)

- [ ] **Step 2: L2 check** — in `scenes.py` add `pixel_pal_kof_l2` = `pixel_pal_kof` (same scene); with
`PIXEL_LINES_DEBUG=1` its marker frame and the colour frame of `pixel_pal_kof` give, per magenta pixel inside the
silhouette, the far-side colour; write `tools/pixelart/l2_check.py MARKER COLOUR PALETTE.json` that counts overlap
line pixels (magenta with no background 4-neighbour) whose 4-neighbours on the far side are all lit-slot colours of
their ramp (not the darkest). Expected 0.

- [ ] **Step 3: Tuning round (max 2 launches)** — compare `pixel_pal_kof` with the KOF XIII sprites
`H:/GameDev/Pixelizer/refs/kof13/kim.gif` and `king.gif` (read frame 0 of each; colours per character 34-43, 5-7 per
ramp, hue shift into the shadows). Adjust only `palette_slots`, `palette_stops` and `outline_value` of 'KOF XIII'.
Write before/after numbers (colours, ramps, slots used per ramp) into the results note.

- [ ] **Step 4: Owner package** — sheet `docs/pixelart/img/pixel_pal_both.png`: April ASW | April KOF XIII | Dude, 3x;
results note section "Palette (spec 09)" with every success criterion of spec 09 section 2 and its measured result.

- [ ] **Step 5: Commit** — `git commit -m "Pixel Cel: KOF XIII L2 overlap rule, palette tuning, results"`. Do not push.
