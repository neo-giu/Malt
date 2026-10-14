# Spec: Pixel Cel palette ramps and the KOF XIII rules (2026-10-14)

Status: for owner review. Approved in chat as a direction (2026-10-10: "yeah we need that, but first we gotta fix the
outlines"; outlines fixed in d5f29d4). Changes `05-pixel-cel-materials-spec.md` sections 3 and 3.1.

## 1. Problem (owner review 1)

- Textures add colours instead of steering the cel shading: smooth sampling blends texels and painted texture lines into
  in-between colours (ASW frame: 669 colours; dark specks off the outline on the face and hair).
- The KOF XIII preset ignores the conventions set in the Kim work (`Pixelizer docs/superpowers/specs/2026-10-07-kim-
  real-content-design.md`, sections 2 and 6): palette ramps, shadow straight to the darkest slot, outline only on the
  shadow side, overlap lines only over a dark back part.

## 2. Goal

Every pixel of a converted character is a colour from one small palette that the owner can edit. The texture only
chooses WHICH ramp a pixel uses (its zone); the cel shading chooses the slot in that ramp. Both presets, all lines 1 px.

Success:
1. The rendered frame holds only palette colours (count checked per frame), at most the palette size (default budget
   40 per character, KOF XIII sprites use 34-43).
2. No texture speck: a zone island smaller than `min_zone_area` texels is merged into its surroundings when the zones
   are built (texture side, not a post pass on the frame).
3. KOF XIII rules (section 5) hold, each with a per-pixel check.
4. line_check total 0 and outside 0 (marker check) for both presets; compare_cel 0 mismatches.
5. Owner judges April ASW against the GGXrd reference and April KOF against the KOF XIII sprites (Kim, King).

## 3. Palette file (same format as the Kim `zones.json`)

One JSON text block per converted collection, `PixelCel Palette <collection>` (Blender text, saved with the file,
editable in Blender's text editor), plus a PNG strip `PixelCel Palette <collection>.png` (one row per ramp: slots light
-> dark, then the line colour) that Aseprite can edit; the converter reads the PNG back when it is newer.

    {"version": 1, "preset": "KOF XIII", "ramps": {"skin": {"colours": [[...] x N], "line": [...], "stops": [...]}, ...},
     "zones": {"<material>": {"texture": "<base image>", "ramp_of_cluster": {"0": "skin", "1": "hair"}}}}

- `colours`: N slots light -> dark (ASW N = 2: lit, shadow; KOF XIII N = 5 by default, 4-7 allowed).
- `line`: the ramp's line colour (outline and inner lines in that zone).
- `stops`: N-1 ascending light thresholds, like ColorRamp stops with constant interpolation.

## 4. Building the zones (converter, Python, no bpy in the core)

New pure module `Malt/PixelArt/zones.py` (tested outside Blender):
1. Base texture -> Oklab -> seeded k-means (k-means++), k from the texture (elbow, max 8 per material); method ported
   from Pixelizer `src/pixelizer/oklab.py` (`kmeans`, `group_ramps`).
2. Islands under `min_zone_area` texels (default 16) are merged into the neighbouring cluster they share most border with.
3. Clusters of all materials of the collection are grouped into ramps by Oklab hue and chroma (`group_ramps`); the
   budget limits the ramp count.
4. Ramp colours: ASW lit = cluster mean, shadow = cluster mean x Sss (cluster mean of the Sss texture). KOF XIII: lit =
   cluster mean, darker slots by the existing hue shift (`shifted_shadow`: toward 260 degrees, saturation x1.25, value
   steps), lightest slot = the highlight. Line = darkest slot x 0.6 value, hue kept.
5. Output: a zone index texture per material (R8, nearest, mip levels by majority vote, so a zone never blends) and the
   palette (section 3).

## 5. Shading with a palette (Pixel Cel)

New inputs: `Zone Texture` (sampler2D, nearest), `Palette` (sampler2D, ramps x slots), `Use Palette` (bool). With Use
Palette on:
- `slot` from the light value `s` (section 3 of spec 05, with the ASW offset) and the ramp's stops.
- Shadowed (ray or map shadow) -> the darkest slot, no banding (KOF XIII and ASW alike).
- Specular / highlight -> slot 0 only where the ilm specular rule says so.
- `color = Palette[ramp(zone), slot]`; `line_color = Palette[ramp(zone), line]`; inner lines (ilm A) use the line colour.
- Base, Sss and ilm textures still drive the zone, the shadow ramp and the ilm rules; they no longer reach the colour.

## 6. Lines, KOF XIII rules (from the Kim spec, section 6)

- L1 silhouette: line colour only where the pixel is in its darkest slot; lit edges keep their colour (done, d5f29d4,
  now by slot instead of tone).
- L2 overlap: the nearer part's pixel takes the nearer part's line colour only where the farther part (the other side
  of the edge) is in its darkest slot. Needs the far side's slot: Pixel Line Data carries the slot, the decision reads
  it on the far sample's pixel.
- Pixel-perfect and all section 3.2 rules unchanged; ASW keeps outlines everywhere (near black, Col.A switch).

## 7. Tests

- `tests/pixelart/test_zones.py`: k-means determinism, island merge, ramp grouping within budget, PNG round trip.
- Render checks (one batch per round): unique colours of the frame are a subset of the palette; L1/L2 per-pixel checks
  on the marker render; line_check + outside; compare_cel.

## 8. Out of scope

Palette animation, per-frame palette swaps, dithering, sprite export (sub-project 2), face SDF painting.

## 9. Build order (card waves)

| Wave | Cards | Result |
|---|---|---|
| 1 | zones.py + tests; palette file read/write | zones and palette for April from the converter, no render change |
| 2 | Pixel Cel palette inputs; converter wiring; colour-subset check | April ASW and KOF in palette colours |
| 3 | L2 far-side slot; KOF tuning round against Kim/King; results note | owner review package |

About half a day of card waves.
