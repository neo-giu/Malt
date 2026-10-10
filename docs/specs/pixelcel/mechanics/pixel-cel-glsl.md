# pixel-cel-glsl (T04)

Differences from plan Task 4: none in the code. `PixelCel.glsl`, the debug shader, `compare_cel.py` and the
`scenes.py` setup are the plan's text verbatim (the scenes.py `_debug_shader` was written with the same body).

- Failing run before the node existed: `pixel_cel_debug.mesh.glsl(23) : error C1503: undefined variable "pixel_cel"`.
- Missing include gives a different, misleading failure: with the include line in `NPR_MeshShader.glsl` but no
  `PixelCel.glsl` file, stdout.txt shows `Can't open include file "NPR_Pipeline/PixelCel.glsl"` and the setup
  asserts `no SceneLighting node with a Ray Traced Shadows input`, because the Render graph fails to load.
- Debug PNG colours: yellow-green = lit tone (R 2/3, G s), blue = shadowed (B 1).
- `python` on PATH is the Windows Store stub: use `H:/GameDev/Pixelizer/.venv/Scripts/python` for every script.
- Render takes about 9 s once Blender is up. The first attempt hit RENDER_TIMEOUT=300 on the failing shader.
