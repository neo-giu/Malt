# Palette converter mechanics (T04)

Differences from plan Task 4 as written:
- GPU palette image rows: Blender images are bottom-up, so `_new_image` (flips) put numpy row 2r at GL row 2R-1-2r. The
  shader reads GL row 2*row (colours) and 2*row+1 (stops). First render: every pixel (188,22,0) = the stops row read as
  colours (stop 0.5 -> 188 after the sRGB output encode, slot count 2/255 -> 22). Fix: `_new_image(top_down=False)` for
  the GPU palette (row 0 = ramp 0 colours). The zone atlas keeps the flip (the shader already accounts for it).
- Colour space: the output transform encodes linear -> sRGB, so palette colour rows are stored LINEAR in a float
  image (`float_buffer=True`, Non-Color). Stop rows stay raw. With a byte image the dark colours would be off.
  Result: asw, kof, edit, bias frames hold exactly the JSON colours (foreign 0).
- `image.pixels` of a byte sRGB image (the strip) returns bytes / 255 without a transform: the plan's `_image_rgba`
  readback is right. The edit round trip works (1952 px of (255,0,0)).
- `update_tree` replaced `pixel_cel_set` with the new keys only, which dropped the palette keys: it now keeps old keys the
  scratch tree does not write (so a hand-set `zone_lod_bias` survives a reconvert).
- `zone_size` (ivec2) set through `_set` as a tuple works (`params[key] = tuple`), no other collection needed.
- Palette inputs are only set when the value still equals what was written (hand edits stay), via `_set_palette`.
- `from Malt.PixelArt import zones as Z` is a module-level import (the helper `_gpu_palette_array` needs it).

Open (not solved, 3 launches used):
- pixel_pal_dude fails palette_check: 2 foreign colours, 13757 px, (121,42,15) and (91,30,9). They are ramp1 (116,40,14)
  and (87,28,8) x 1.095 in linear light. Cause: `_pixel_cel_palette` keeps `color.a` of the base texture
  (arthur_tex01_bmout.png has alpha 233 on the body), the frame pixel has alpha 233, and the PNG writer un-premultiplies.
  Fix needs PixelCel.glsl (outside this card): in the palette path write `color = vec4(rgb, 1.0)` where the texel is
  opaque, or decide how texture alpha should work with a palette. ASW April has alpha 1, so it passes.
- Marker check: `line_check.py --marker` without `--rules` reports total 1 (one junction 2x2 block) on both frames; with
  `--rules junctions,tips,overlap_corners` (the owner's corner rules) total 0, outside 0.
- Palette quality: April ASW gets 11 ramps / 33 colours; ramps 5, 8, 9, 10 are near-black texture clusters (decals, eye
  parts). Within budget, not tuned.
- Boundary pairs inside the silhouette: asw 5200, asw_bias 5172 (bias 2 is lower, but only by 0.5 %: April's zones
  are large, so the level barely changes them).

Orchestrator follow-up:
- Alpha: `_pixel_cel_palette` now writes alpha 1.0. dude_dbg: palette_check exit 0, foreign 0, 3 colours.
- The Dude is flat because its mesh has NO UV map (a sculpt: `uv_layers` empty), so the texture is read at one point.
  The plain (non-palette) conversion is flat too. Asset problem, not the converter. Use April / Kim for palette tests.
