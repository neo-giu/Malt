# Rules for pixelart cards (Malt fork, branch `pixelart`)

- Read the plan `docs/pixelart/02-ray-shadows-plan.md` (header, Global constraints, Review focus, your Task) and the
  spec `docs/pixelart/01-ray-shadows-spec.md` section 4 before coding.
- Python for tests: `H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart -q` (numpy + pytest).
  Never `pip install` anything. Pure-numpy modules (`Malt/Render/RayGeometry.py`, `Malt/Render/RayBVH.py`) must not
  import OpenGL, bpy or other Malt GL modules; tests import them with the repo root on `sys.path`
  (`tests/pixelart/conftest.py` may insert it).
- Blender renders (only when your card asks): `bash tools/pixelart/render.sh FILE.blend OUT_DIR FRAMES [SETUP]`.
  It opens a Blender window for ~15 s, renders with this fork's code (dev install at `H:/GameDev/MaltDev/scripts`,
  junctions into this checkout) and quits WITHOUT saving. Output dirs go under `build/pixelart/` (gitignored).
  A GLSL compile error shows in `OUT_DIR/stdout.txt` and in the render (Malt's error colour); check both.
- NEVER save, modify, move or copy over any `.blend` file outside `build/`. Owner files are read-only
  (e.g. `D:/DocuBKP/Blender/testmalt.blend`). In-memory edits in `tools/pixelart/scenes.py` are fine.
- Never edit the release add-on in `%APPDATA%/Blender Foundation/Blender/5.2/scripts/addons/BlenderMalt`.
- Match the surrounding Malt code style (4-space indent, existing naming). No unrelated refactors.
- Commit only the files in your card's fence.
