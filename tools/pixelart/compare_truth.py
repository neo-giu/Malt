"""Compare a ray_debug render (R = N.L > 0, G = shadowed, B = origin search) with a Cycles truth render (lit > 0).

    python compare_truth.py DEBUG.png TRUTH.png OUT.png

Prints mismatch counts by cause and writes a 3x zoomed classification image:
  grey = agree lit, black = agree unlit, red = Malt lit / truth unlit, blue = Malt unlit / truth lit
  (blue with N.L <= 0 in Malt: terminator disagreement; blue with N.L > 0: false shadow (acne or bias))."""
import sys

import numpy as np
from PIL import Image

debug = np.array(Image.open(sys.argv[1]).convert('RGB')).astype(int)
truth = np.array(Image.open(sys.argv[2]).convert('RGB')).astype(int)
covered = debug.sum(axis=2) > 0
facing = debug[..., 0] > 127
shadowed = debug[..., 1] > 127
found = debug[..., 2] > 0
malt_lit = facing & ~shadowed
true_lit = truth.max(axis=2) > 8

out = np.zeros(debug.shape, dtype=np.uint8)
out[malt_lit & true_lit] = (150, 150, 150)
false_lit = covered & malt_lit & ~true_lit
false_dark = covered & ~malt_lit & true_lit
out[false_lit] = (255, 40, 40)
out[false_dark & facing] = (40, 120, 255)
out[false_dark & ~facing] = (40, 255, 255)
print('covered px', covered.sum(), ' malt lit', malt_lit.sum(), ' truth lit', (true_lit & covered).sum())
print('Malt lit, truth dark  :', false_lit.sum(), '  of these N.L>0 not shadowed, search not found:', (false_lit & ~found).sum())
print('Malt dark, truth lit  :', false_dark.sum())
print('   - shadow bit (N.L>0, ray hit)  :', (false_dark & facing).sum(), ' (search not found:', (false_dark & facing & ~found).sum(), ')')
print('   - terminator (N.L<=0 in Malt)  :', (false_dark & ~facing).sum())
print('truth lit, outside Malt coverage:', (true_lit & ~covered).sum())
z = 3
Image.fromarray(out).resize((out.shape[1] * z, out.shape[0] * z), Image.NEAREST).save(sys.argv[3])
