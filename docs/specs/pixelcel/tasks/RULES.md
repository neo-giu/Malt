# Card rules (pixelcel)

Every card obeys these rules. A card may add to them, never relax them.

## Paths
- Repo: `H:/GameDev/Malt` (Malt fork, branch `pixelart`). Spec: `docs/pixelart/05-pixel-cel-materials-spec.md`.
  Plan: `docs/pixelart/06-pixel-cel-plan.md` (each card = one plan task; the task section has the code and checks).
- Pure Python core: `Malt/PixelArt/` (no `bpy`, no OpenGL imports). Blender side: `BlenderMalt/PixelArtConvert.py`.
- Shaders: `Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/PixelCel.glsl`, `Malt/Shaders/Passes/PixelLines.glsl`.
- Test tools and render setups: `tools/pixelart/` (`scenes.py` setups, `render.sh`, `line_check.py`, ...).
- Tests: `tests/pixelart/`. Render output: `build/pixelart/P/` (not in git).
- Knowledge notes: `docs/specs/pixelcel/mechanics/<slug>.md` (max 40 lines each).

## Commands (one per Bash call is safest)
- Fast checks (the runner repeats these after you commit):
  `H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart -q`
- One test file: `H:/GameDev/Pixelizer/.venv/Scripts/python -m pytest tests/pixelart/<file>.py -q`
- Render (opens a Blender WINDOW, renders, quits without saving; 1-5 minutes). Always give the Bash call a timeout of
  600000 ms:
  `cd /h/GameDev/Malt && RENDER_TIMEOUT=300 bash tools/pixelart/render.sh /h/GameDev/Pixelizer/content/malt/testmalt.blend build/pixelart/P/<name> 1 <setup>`
  Exit 1 = a Python traceback (read `build/pixelart/P/<name>/log.txt`) or a Malt graph error (`stdout.txt`).
  Shader compile errors are in `stdout.txt`: grep it for `ERROR`, `error`, `0(`.
- **Blender launches are limited (owner rule): at most 3 render.sh launches per card, retries included.** Batch
  every setup a check step needs into ONE launch with a comma list (they render one after another, the file is
  reloaded between them, output in `<out>/<setup>/`):
  `RENDER_TIMEOUT=600 bash tools/pixelart/render.sh /h/GameDev/Pixelizer/content/malt/testmalt.blend build/pixelart/P/<batch> 1 setup_a,setup_b,setup_c`
  The plan's per-setup render commands are replaced by these batches: use `build/pixelart/P/<batch>/<setup>/frame_0001.png`
  wherever the plan names `build/pixelart/P/<setup>/frame_0001.png`. Before a re-render, find the cause in log.txt /
  stdout.txt first; never render to "try something". When the 3 launches are used up, commit what works and report
  `BLOCKED: launch limit` with the last error.
- Read data from a .blend without rendering (Malt cannot RENDER in background mode, reading is fine):
  `BLENDER_USER_SCRIPTS=H:/GameDev/MaltDev/scripts "H:/SteamLibrary/steamapps/common/Blender/blender.exe" -b <file> --python <script>`
- Look at a render: zoom it with `tools/pixelart/side_by_side.py`, then use the Read tool on the PNG.

## Hard rules from the owner
- Every line is exactly 1 px thick. No line width input, no thickness variation, for any reason.
- Never save or modify `.blend` files. Render only from the `H:/GameDev/Pixelizer/content/malt/` copies, edits in
  memory only (setup functions). Never touch `D:/` originals or the add-on in `%APPDATA%`.
- Never change or delete the original Cycles/EEVEE material nodes.
- No post-pass filters on colours. Fix causes at the source; measure every change.
- Enum inputs do not work as Render-graph sockets: use bool/int/float.

## Code conventions
- Python 3.13, 4-space indent, match the surrounding Malt code: short comments, no docstring essays.
- GLSL: Malt style (`/* META ... */` blocks for node inputs, `_name` for hidden helpers).
- Every new behaviour gets a test (pytest, or a render setup + check script) in the same commit. Write the test or
  check first and run it before any implementation exists; quote its failing line in the Report.
- When the plan's code does not work as written (Malt API differs), fix it and say exactly what differed in the
  Report and in a mechanics note.

## Never
- Edit files outside your card's fence. If you need one, stop and report `BLOCKED: needs <file> because <reason>`.
- Weaken or delete an existing test or check to make it pass.
- Guess a fact you can check with one command. Say "not confirmed" in the Report if you could not check.
- git push, branch, reset, rebase, stash, checkout of other commits; background commands.

## Report (last message, max 15 lines)
First line `DONE` or `BLOCKED: <reason>`. Then: files changed · what was done · what was not and why ·
each "Done when" check with its result · any deviation from the card or the plan.
