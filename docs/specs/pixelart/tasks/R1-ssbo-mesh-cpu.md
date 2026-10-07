# R1-ssbo-mesh-cpu — SSBO class + CPU triangles on meshes

Requirements: owner approved the spec and the plan, 2026-10-07. Do exactly the plan's **Task R1** in
`docs/pixelart/02-ray-shadows-plan.md` (Files, Interfaces, Steps). Global constraints and Review focus apply.
Depends on: -          Size: S

## Read first (and only)
- docs/specs/pixelart/tasks/RULES.md
- docs/pixelart/02-ray-shadows-plan.md: header, Global constraints, Review focus, **Task R1**
- docs/pixelart/01-ray-shadows-spec.md: section 4
- Malt/GL/Shader.py (UBO class ~line 130), Malt/Pipeline.py (load_mesh ~line 161), Malt/Utils.py (IBuffer)

## Do
Failing tests first (quote the failing line), implement, run the tests, one commit with the task's message. Keep the
plan's names and signatures; where its sketch is wrong, fix it and say so in the Report.

## Do not
- Edit files outside: Malt/GL/Shader.py, Malt/Pipeline.py, Malt/Render/RayGeometry.py, tests/pixelart/test_r1_mesh_cpu.py, tests/pixelart/conftest.py, tests/pixelart/ref/testmalt_f1.png. If you need another file, report it and stop.
- Save or modify any `.blend` file.

## Done when
- [ ] pytest tests/pixelart passes; testmalt.blend frame 1 dev render pixel-identical to tests/pixelart/ref/testmalt_f1.png (made before your change)

## Report (last message, max 15 lines)
First line DONE or BLOCKED: <reason>. Files changed · failing-test line · checks · anything the plan got wrong.
