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
