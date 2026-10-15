# Zones mechanics (T02)

Differences from plan Task 2 as written:
- `group_zones`: the plan returns one ramp per zone when zones <= ramp budget. `test_asw_ramp_shadow_mean` (budget 6 ->
  2 ramps, 2 zones) then gets 2 ramps, not 1. Fix: zones closer than `SAME_RAMP` = 0.02 Oklab join one ramp first;
  k-means on the group representatives only runs when more groups than the budget remain.
- Everything else in the plan code ran as written (75 of 76 tests passed before the fix).
- The plain `python` on PATH is the Windows Store stub; use the Pixelizer venv python for scripts.

Step 6 on APRL_baseX.png: `clusters 3 changed by merge 763`. The plan expected 4-8 clusters and a few hundred texels.
3 clusters = the elbow rule (inertia under 15 % of k = 1) stopped early on this texture. Orchestrator fix: zones are
now the dominant flat colours (Oklab 0.02 cells by area, each >= 0.5 % and >= 0.05 apart, at most k_max), then Lloyd
steps. April: 8 zones (skin, blue, brown, cream, yellow, black, dark brown, white), 1392 texels changed by the merge.
