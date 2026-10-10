# operator (T06) — differences from the plan code, status: done

Launch 1 (before the code): `AttributeError: module 'BlenderMalt.PixelArtConvert' has no attribute 'original_hash'`
(and `copy_collection`). Launch 2 and 3 after it; launch 3: RECONVERT_OK, COPY_OK, EXIT 0.

Differences from the plan code:
- `copy_collection`: `slot.link = 'OBJECT'` clears `slot.material` (it becomes None), so the plan's
  `slot.material.copy()` raised `AttributeError: 'NoneType' object has no attribute 'copy'`. Fix: keep the material in a
  local variable before the link change, assign the copy afterwards.
- `_current` and `update_tree`: Malt bools live in `params.bools[key].boolean` (see build-trees.md). The plan code read
  them with `params.get(key)` (None) and wrote them with `params[key] = value`. Both now use `params.bools`; without
  it every bool counted as "edited by hand" and was never updated.
- `PixelArtConvert` is added to `get_modules()` in `BlenderMalt/__init__.py` (the list that gets `register()`), as the
  plan says; the add-on reload also reloads this module.
- `layout.operator('malt.convert_pixel_art')` is added above `draw_ui` in `MALT_PT_MaterialSettings.draw`.
- `setup_pixel_lines` stays a no-op (Task 8).

Checks: reconvert keeps a hand-edited input (`threshold`=0.3) and a hand-added node; `original_hash` of the Cycles
nodes is unchanged; the 'GGXRD' body materials share one tree. The T06 `pixel_cel_convert_asw` render equals the T05
render (differing px 0).
Not tested: the operator itself (`invoke`/`execute`) and the panel button; only the functions it calls.
