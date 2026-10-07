"""side_by_side.py OUT.png X0 Y0 X1 Y1 ZOOM LABEL=IMAGE[:debug|:truth] ...  Crops, zooms (NEAREST), and labels images.
':debug' shows a ray_debug render as its lit mask (N.L > 0 and not shadowed), ':truth' a Cycles render as lit > 0."""
import sys

import numpy as np
from PIL import Image, ImageDraw


def load(spec):
    path, _, kind = spec.partition(':')
    a = np.array(Image.open(path).convert('RGB')).astype(int)
    if kind == 'debug':
        lit = (a[..., 0] > 127) & (a[..., 1] <= 127)
        cov = a.sum(axis=2) > 0
        a = np.where(lit[..., None], 230, np.where(cov[..., None], 70, 0)).repeat(3, axis=2) if False else \
            np.stack([np.where(lit, 230, np.where(cov, 70, 0))] * 3, axis=2)
    elif kind == 'truth':
        lit = a.max(axis=2) > 8
        a = np.stack([np.where(lit, 230, 70)] * 3, axis=2)
    return Image.fromarray(a.astype(np.uint8))


out = sys.argv[1]
x0, y0, x1, y1, zoom = map(int, sys.argv[2:7])
items = [arg.split('=', 1) for arg in sys.argv[7:]]
w, h = (x1 - x0) * zoom, (y1 - y0) * zoom
sheet = Image.new('RGB', (len(items) * (w + 8), h + 20), (40, 40, 40))
draw = ImageDraw.Draw(sheet)
for i, (label, spec) in enumerate(items):
    sheet.paste(load(spec).crop((x0, y0, x1, y1)).resize((w, h), Image.NEAREST), (i * (w + 8), 20))
    draw.text((i * (w + 8) + 4, 4), label, fill=(255, 255, 255))
sheet.save(out)
