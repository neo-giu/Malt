# tools/pixelart/palette_check.py
"""Frame colours must be palette colours.  python palette_check.py FRAME.png PALETTE.json
Every opaque pixel's sRGB value must be a ramp colour or a line colour of the palette. Exit 1 otherwise."""
import json
import sys

import numpy as np
from PIL import Image

frame = np.array(Image.open(sys.argv[1]).convert('RGBA'))
palette = json.load(open(sys.argv[2]))
allowed = {tuple(c) for r in palette['ramps'].values() for c in r['colours'] + [r['line']]}
opaque = frame[..., 3] > 0
colours, counts = np.unique(frame[opaque][:, :3], axis=0, return_counts=True)
foreign = [(tuple(map(int, c)), int(n)) for c, n in zip(colours, counts) if tuple(map(int, c)) not in allowed]
print('colours', len(colours), 'palette', len(allowed), 'foreign colours', len(foreign),
      'foreign px', sum(n for _, n in foreign), foreign[:8])
sys.exit(1 if foreign else 0)
