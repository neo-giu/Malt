# Pixel Cel results

## Line probe (Malt Line Width = 1)

Setups `lines_w1` and `lines_off`, 356x256, `tools/pixelart/line_check.py` (exit 1):

```
line px 1302 {'blocks': 0, 'l_corners': 4, 'isolated': 12, 'short': 16, 'total': 32}
```

Malt Line Width = 1 breaks the 1 px rule: isolated dots, short pieces and L corners.

## pixel_cel vs cel_ref

`tools/pixelart/compare_cel.py` on `pixel_cel_debug` (356x256, Suzanne, ray traced shadows):

```
checked px 35280 mismatches 0
```

## Pixel Lines
April, ASW preset, 256 px high, ray traced shadows. Line mask = Pixel Lines on minus off (off: Line Width 0).

| Setup pair | line px | blocks | l_corners | isolated | short | total |
|---|---|---|---|---|---|---|
| pixel_lines_on / _off (decision, thin, prune only) | 1530 | 44 | 0 | 0 | 0 | 44 |
| pixel_lines_border / _border_off (same) | 1960 | 79 | 0 | 0 | 0 | 79 |
| pixel_lines_on / _off (+ Zhang-Suen x3, thin, prune) | 1457 | 0 | 0 | 0 | 0 | 0 |
| pixel_lines_border / _border_off (same) | 1878 | 0 | 0 | 0 | 0 | 0 |

`compare_cel` on pixel_cel_debug: 35280 checked px, 0 mismatches. Border render: 2 / 4 line px on the top / bottom row,
31 / 31 on the left / right column (object edges that meet the border, no line along the whole border).
Not done: 3 animation frames.
