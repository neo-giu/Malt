# Spec: Pixel Cel materials and the Malt material converter (2026-10-10)

Status: design approved in chat (sections 1-4), spec for owner review.
Sub-project 1 of 3 of the sprite pipeline (1 materials, 2 sprite export, 3 shadow smoothing).

## 1. Goal

Imported characters become Malt cel-shaded pixel-art materials with one click and no hand work.
Final use: game sprites (sub-project 2 renders and exports them).

Sources that v1 must handle (Arthur now has his materials and textures in the file again: re-inspect at
implementation start):

| Style | Example in `testmalt.blend` | Inputs |
|---|---|---|
| ASW (Arc System Works, GGXrd) | collection `GGXRD` (April) | `*_base*`, `*_Sss*`, `*_ilm*`, `*_decal*` textures, vertex colour `Col` |
| Generic textured | `arthurmodel` (UMVC3 Arthur) | a base colour texture, optional normal map |
| Untextured | `Dudemodel` | a colour |

Tones: 2 (lit, shadow) by default; a ramp input per material adds N bands.
Tool form: a button in Blender (operator in the fork's BlenderMalt add-on), also callable from scripts.

Two **style presets** (section 3.1): **ASW** (GGXrd: 2 tones, Sss shadow, ilm lines) and **KOF XIII** (painted sprite
look: 4 tones with hue-shifted shadows, a highlight band, coloured outlines). The converter applies one preset; with
"Copy collection" on, it first duplicates the collection (objects and materials copied, mesh data shared) and converts
the copy, so both interpretations of a character sit side by side.

References (local only, not in git): `H:/GameDev/Pixelizer/content/malt/refs/april_ggxrd_1.png`, `april_ggxrd_2.webp`.

## 2. Components

### 2.1 `Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/PixelCel.glsl`

One Malt library function, shown as the node **Pixel Cel**.

Inputs:

| Input | Type | Default | ASW source | Others |
|---|---|---|---|---|
| Base | vec4 | white | base texture | base texture or colour |
| Shadow Tint | vec3 | (0.55, 0.5, 0.7) | Sss texture | colour input |
| Offset | float | 0 | `ilm.G * Col.R - 0.5` | 0 |
| Threshold | float | 0.5 | input | input |
| Ramp | sampler1D | none | - | optional |
| Use Ramp | bool | false | - | input |
| Spec Mask | float | 0 | ilm.R | 0 |
| Spec Size | float | 0 | ilm.B | 0 |
| Spec Threshold | float | 0.5 | input | - |
| Spec Boost | float | 1.3 | input | - |
| Line Mask | float | 1 | ilm.A | 1 |
| Unlit | bool | false | true for eyeshine | false |
| Light Group | int | 1 | | |
| Shadows | bool | true | | |
| Self Shadows | bool | true | | |

Outputs: Color (vec4), Shadowed (bool, any sun shadows the pixel), Tone (int: 0 shadow, 1 lit, 2 specular; band index
with a ramp).

### 2.2 `BlenderMalt/PixelArtConvert.py`

- Style detection (section 4), texture lookup on disk, node tree build, report.
- Operator `MALT_OT_convert_pixel_art` ("Convert to Malt Pixel Art"): in the Malt material panel and the Object menu.
  Works on the selected objects; with none selected, on the active collection.
- Pure-Python parts (detection, file lookup, input values) live in a module with no `bpy` import, so they are unit
  tested outside Blender: `BlenderMalt/PixelArtDetect.py`.

### 2.3 Tests

- `tests/pixelart/test_pixel_cel_detect.py`: detection and file lookup on material layouts given as dicts.
- `tests/pixelart/test_pixel_cel_ref.py`: Python reference `pixel_cel_ref` of the shading rules (section 3).
- Render setups in `tools/pixelart/scenes.py` (section 6).

## 3. Shading rules

Per sun light `L` in the light group (several suns: the result with the highest tone wins):

1. `s = (dot(N, L) * 0.5 + 0.5) + Offset`.
2. `shadowed = Shadows and npr_lit_surface(...).shadow` (ray traced or shadow maps, as set on SceneLighting).
3. 2-tone: `lit = s > Threshold and not shadowed`; `color = lit ? Base : Base * Shadow Tint`.
4. Ramp (Use Ramp on): `t = shadowed ? 0 : ramp(s).r`; `color = Base * mix(Shadow Tint, 1, t)`. Constant
   interpolation in the gradient gives hard bands. Tone = band index.
5. Specular (lit pixels only): `Spec Mask * pow(max(dot(N, H), 0), mix(4, 128, Spec Size)) > Spec Threshold` ->
   `color = Base * Spec Boost`, tone 2.
6. Inner lines: `color *= Line Mask > 0.5 ? 1 : Line Mask` (line pixels keep the texture's dark value, all others 1).
7. Unlit: `color = Base`, tone 1.

The ASW offset reading (`ilm.G * Col.R - 0.5`: 0 = always shadow, 0.5 = neutral, 1 = nearly always lit) is checked
on April's textures before it is fixed; the check result goes into the results note.

### 3.1 Style presets

The presets only set Pixel Cel inputs and the ramp; the node is the same.

| Input | ASW | KOF XIII |
|---|---|---|
| Use Ramp | off (2 tones) | on, 4 bands, constant interpolation |
| Ramp (s -> t) | - | s < 0.35: 0 (deep shadow); < 0.5: 0.45 (shadow); < 0.85: 1 (lit); else 1 + highlight |
| Shadow Tint | Sss texture (ASW) / colour | hue shift: shadow = base rotated 15 degrees toward blue-purple, saturation x1.25, value x0.55 (ASW Sss, when present, is used as the deep shadow) |
| Highlight | ilm specular | top band: base x1.2 toward warm white, also on generic materials |
| Inner lines | ilm A | ilm A |
| Outline colour | near black (0.1) | base x0.35, hue kept (coloured outline), black where it meets the background |
| Outline width | 1 px x Col.A | 1 px x Col.A, minimum 1 px everywhere |

New Pixel Cel inputs for the KOF XIII preset: `Hue Shift` (degrees), `Shadow Saturation`, `Shadow Value`,
`Highlight Color`, and on the Line Width path `Outline From Base` (bool) and `Outline Value`. Defaults keep the ASW
behaviour, so ASW materials are unchanged by these inputs.

The KOF XIII numbers above are starting values, tuned once by eye against KOF XIII sprites; the tuned values become the
preset defaults and are written into the results note.

Texture sampling: smooth with mipmaps by default (detail below a sprite pixel averages instead of flickering);
nearest is an input on the Image nodes. Palette reduction is sub-project 2.

Outline: Malt `Line Width` node, width = `Line Width` input (default 1 px) times `Col.A` for ASW.
Decal meshes: alpha cutout at 0.5 (Opacity Mask in the pre pass, no blending).

## 4. Converter

### 4.1 Detection (per material, first match wins)

1. **ASW eyeshine**: material name contains `eyeshine`. Unlit, base texture.
2. **ASW decal**: name starts with `7_Decal` or an image matches `*_decal*`. Decal texture, cutout.
3. **ASW**: an image node file name matches `<prefix>_base*` (including `baseX`) and `<prefix>_Sss*` or
   `<prefix>_ilm*` exists in the same folder on disk (case-insensitive). A missing Sss -> Shadow Tint colour input;
   a missing ilm -> neutral (G 0.5, R 0, B 0, A 1).
4. **Generic textured**: an image node connected (directly, or through Mix / Mapping / group nodes) to the base colour
   of a Principled BSDF, a Diffuse BSDF or an XPS shader group. When the trace fails: the largest sRGB image in the
   material, and the report says so.
5. **Untextured**: the BSDF base colour value, else the material's viewport display colour.

### 4.2 Inputs read

- UV map: the one the image node uses, else the active UV map.
- Vertex colour `Col` (ASW only).
- Normal map (generic only): a Non-Color image with `nm` or `normal` in the name, through Malt `Normal_Map`.
  Off by default (one checkbox): on sprites it often adds noise.

### 4.3 Rules

- The original Cycles/EEVEE material nodes are never changed or deleted; the converter only sets the material's Malt
  node tree. Check: a hash of every original node tree is equal before and after.
- One Malt tree per distinct texture set (April's materials that share `APRL_base` share one tree).
- Reconvert is idempotent and keeps hand edits: the converter stores the value it set for each input in a custom
  property on the tree; on reconvert it overwrites an input only when its current value still equals the stored one.
  Nodes and links added by hand are kept.
- Missing image files: the material converts with neutral inputs; the report lists it.
- Copy collection (option, off by default): duplicates the collection with its child collections, copies objects and
  materials (suffix `.KOF` or `.ASW`), keeps mesh data and armatures shared, and moves the copy 1 m along +X per
  existing copy. The original collection is not changed.
- Report after each run: material -> style -> textures -> warnings, in the Info area and in the text block
  `PixelArt Convert Report`.

### 4.4 Out of scope (v1)

Outline z-offset from `Col.G/B`, Sss baked into `baseX` variants, custom Malt light shaders, sprite export, palettes.

## 5. Constraints

- Never save or modify the owner's `.blend` files from tests; render tests use the copies in
  `H:/GameDev/Pixelizer/content/malt/` with in-memory edits only. The converter itself is a tool the owner runs and
  saves.
- No post-pass filters in the materials.
- Enum inputs do not register as Render-graph sockets; material node inputs use bool/int/float.

## 6. Tests and success criteria

Render setup `pixel_cel_convert`: runs the converter on the three collections in memory, then renders each character
with an orthographic camera framed on it, 256 px tall. Debug variant writes Shadowed and Tone per pixel; each pixel is
checked against `pixel_cel_ref`.

Success:

1. April converts with no hand work: 2 tones from base + Sss, ilm inner lines, outlines, decals cut out. The owner
   judges it side by side with a GGXrd reference image of April.
2. Arthur and Dude convert with no errors, 2 tones, no noise or flicker at sprite size (3 frames of the armature
   animation, if any, compared).
3. Converting twice gives identical trees and an identical render (0 differing pixels).
4. Original materials unchanged (hash check).
5. A ramp added by hand to one material gives N bands and survives a reconvert.
5a. April converted twice, ASW and KOF XIII (Copy collection), renders side by side; the owner judges the KOF XIII copy
    against KOF XIII sprites (4 tones, hue-shifted shadows, coloured outlines visible at 256 px).
6. All unit tests pass. Frame time at most +10 % against the current Suzanne material at the same resolution.
