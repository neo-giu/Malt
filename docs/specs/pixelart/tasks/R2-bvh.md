# R2-bvh — BVH build + reference traversal

Requirements: owner approved the spec and the plan, 2026-10-07. Do exactly the plan's **Task R2** in
`docs/pixelart/02-ray-shadows-plan.md` (Files, Interfaces, Steps). Global constraints and Review focus apply.
Depends on: R1          Size: M

## Read first (and only)
- docs/specs/pixelart/tasks/RULES.md
- docs/pixelart/02-ray-shadows-plan.md: header, Global constraints, Review focus, **Task R2**
- docs/pixelart/01-ray-shadows-spec.md: section 4
- Malt/Render/RayGeometry.py

## Do
Failing tests first (quote the failing line), implement, run the tests, one commit with the task's message. Keep the
plan's names and signatures; where its sketch is wrong, fix it and say so in the Report.

## Do not
- Edit files outside: Malt/Render/RayBVH.py, tests/pixelart/test_r2_bvh.py. If you need another file, report it and stop.
- Save or modify any `.blend` file.

## Done when
- [ ] pytest tests/pixelart passes (all R2 tests listed in the plan); quote build time for 120k random triangles

## Report (last message, max 15 lines)
First line DONE or BLOCKED: <reason>. Files changed · failing-test line · checks · anything the plan got wrong.
