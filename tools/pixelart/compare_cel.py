# tools/pixelart/compare_cel.py
"""Per-pixel check of a pixel_cel_debug render against Malt/PixelArt/cel_ref.py.
    python compare_cel.py DEBUG.png
Debug channels: R = tone / 3, G = s = N.L * 0.5 + 0.5 (first sun), B = shadowed. Threshold 0.5, no ramp, offset 0.
Pixels whose s is within 2/255 of the threshold are skipped (8-bit quantization). Exit 1 on any mismatch."""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from Malt.PixelArt.cel_ref import cel_tone

a = np.array(Image.open(sys.argv[1]).convert('RGB')).astype(np.float64) / 255.0
covered = a.sum(axis=2) > 0
tone = np.rint(a[..., 0] * 3).astype(int)
s = a[..., 1]
shadowed = a[..., 2] > 0.5
checked = covered & (np.abs(s - 0.5) > 2.0 / 255.0)
bad = 0
for y, x in zip(*np.nonzero(checked)):
    expected = cel_tone((s[y, x] - 0.5) * 2.0, 0.0, 0.0, 0.5, bool(shadowed[y, x]))[0]
    bad += int(expected != tone[y, x])
print('checked px', int(checked.sum()), 'mismatches', bad)
sys.exit(1 if bad or not checked.any() else 0)
