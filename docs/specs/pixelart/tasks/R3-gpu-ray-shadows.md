# R3-gpu-ray-shadows — GPU ray shadows + Shadow Mode + render checks

Requirements: owner approved the spec and the plan, 2026-10-07. Do exactly the plan's **Task R3** in
`docs/pixelart/02-ray-shadows-plan.md` (Files, Interfaces, Steps). Global constraints and Review focus apply.
Depends on: R2          Size: L

## Read first (and only)
- docs/specs/pixelart/tasks/RULES.md
- docs/pixelart/02-ray-shadows-plan.md: header, Global constraints, Review focus, **Task R3**
- docs/pixelart/01-ray-shadows-spec.md: section 4
- Malt/Render/RayBVH.py, Malt/Render/RayGeometry.py, Malt/Render/Lighting.py (LightsBuffer), Malt/Shaders/Lighting/Lighting.glsl, Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/NPR_Lighting.glsl, Malt/Pipelines/NPR_Pipeline/Nodes/Render/SceneLighting.py, Malt/Pipelines/NPR_Pipeline/NPR_Pipeline.py (how SceneLighting resources reach shaders), Malt/PipelineParameters.py (enum inputs), tools/pixelart/render_gui.py

## Do
Failing tests first (quote the failing line), implement, run the tests, one commit with the task's message. Keep the
plan's names and signatures; where its sketch is wrong, fix it and say so in the Report.

## Do not
- Edit files outside: Malt/Render/RayShadows.py, Malt/Shaders/Lighting/RayShadows.glsl, Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/NPR_Lighting.glsl, Malt/Pipelines/NPR_Pipeline/Nodes/Render/SceneLighting.py, tools/pixelart/scenes.py, tests/pixelart/test_r3_cache.py. If you need another file, report it and stop.
- Save or modify any `.blend` file.

## Done when
- [ ] pytest tests/pixelart passes; renders of box_plane, lit_sphere, cube_contact and testmalt.blend (both modes) in build/pixelart/R3/ with the plan's numeric checks quoted; no GLSL errors in stdout.txt

## Report (last message, max 15 lines)
First line DONE or BLOCKED: <reason>. Files changed · failing-test line · checks · anything the plan got wrong.
