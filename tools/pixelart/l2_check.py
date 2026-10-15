# tools/pixelart/l2_check.py
"""KOF XIII L2 check.  python l2_check.py MARKER.png COLOUR.png PALETTE.json
MARKER = PIXEL_LINES_DEBUG=1 render, COLOUR = normal render of the same setup. An overlap line pixel (orange in the
marker) must have a darkest-slot pixel beside it (4-neighbour, not a line, not background). Count the overlap line
pixels whose such neighbours are all lit-slot colours (not the darkest of their ramp). Exit 1 if any."""
import json
import sys

import numpy as np
from PIL import Image

from line_check import marker_mask, overlap_mask


def l2_violations(marker, colour, palette):
    lit, dark = set(), set()
    for ramp in palette['ramps'].values():
        lit.update(tuple(c) for c in ramp['colours'][:-1])
        dark.add(tuple(ramp['colours'][-1]))
    lit -= dark
    lines = marker_mask(marker)
    covered = np.asarray(colour)[..., 3] > 0
    rgb = np.asarray(colour)[..., :3]
    bad = []
    for y, x in zip(*np.nonzero(overlap_mask(marker))):
        far = []
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            q = (y + dy, x + dx)
            if 0 <= q[0] < rgb.shape[0] and 0 <= q[1] < rgb.shape[1] and covered[q] and not lines[q]:
                far.append(tuple(int(v) for v in rgb[q]))
        if far and not any(c in dark for c in far) and all(c in lit for c in far):
            bad.append((int(y), int(x)))
    return bad, int(overlap_mask(marker).sum())


if __name__ == '__main__':
    marker = np.array(Image.open(sys.argv[1]).convert('RGBA'))
    colour = np.array(Image.open(sys.argv[2]).convert('RGBA'))
    bad, total = l2_violations(marker, colour, json.load(open(sys.argv[3])))
    print('overlap line px', total, 'over a lit far part', len(bad), bad[:8])
    sys.exit(1 if bad else 0)
