# line-check (T01)

Differences from plan Task 1:

- `test_l_corner_fails`: the plan's mask `['#...','##..','.##.','..##']` is a clean staircase. Every
  pixel in it has a diagonal neighbour, so `l_corners` is 0 and the test failed against the plan's
  own implementation. The mask is now `['#...','##..','....','....']` (one real L, no diagonal).
  `line_check.py` is unchanged from the plan.
- Probe result: `l_corners` is 4, not "about 12" as the plan expected. `isolated` 12 and `line px` 1302
  match. `short` is 16, `total` 32. Exit 1 as expected.
- `scenes.py` probe helpers were already committed (cfd37ed), so there is no change to that file.
