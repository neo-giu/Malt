"""Score face_sdf_* debug renders (R = Face SDF lit, G = N.L > 0) and build a contact sheet.

    python tools/pixelart/face_sdf_check.py OUT_DIR

For each OUT_DIR/face_sdf_*/frame_0001.png: covered pixels (alpha > 0), agree, SDF-only lit (red), N.L-only lit
(green). Also writes OUT_DIR/sheet.png: debug renders in a row, then each face_cel_* above its face_plain_* twin."""
import os
import sys

import numpy as np
from PIL import Image


def load(path):
    return np.asarray(Image.open(path).convert('RGBA')).astype(np.float32) / 255.0


def score(path):
    im = load(path)
    covered = im[..., 3] > 0.0
    sdf = im[..., 0] > 0.5
    lambert = im[..., 1] > 0.5
    n = int(covered.sum())
    red = int((covered & sdf & ~lambert).sum())
    green = int((covered & ~sdf & lambert).sum())
    return n, red, green


def sheet(out_dir, names, scale=2):
    tiles = []
    for row in names:
        images = [load(os.path.join(out_dir, n, 'frame_0001.png')) for n in row]
        tiles.append(np.concatenate(images, axis=1))
    width = max(t.shape[1] for t in tiles)
    tiles = [np.pad(t, ((0, 0), (0, width - t.shape[1]), (0, 0))) for t in tiles]
    img = np.concatenate(tiles, axis=0)
    img[..., :3] = img[..., :3] * img[..., 3:] + 0.25 * (1.0 - img[..., 3:])   # grey background
    out = Image.fromarray((img[..., :3] * 255.0 + 0.5).astype(np.uint8))
    out = out.resize((out.width * scale, out.height * scale), Image.NEAREST)
    out.save(os.path.join(out_dir, 'sheet.png'))


def main(out_dir):
    debug = sorted(d for d in os.listdir(out_dir) if d.startswith('face_sdf_'))
    for name in debug:
        n, red, green = score(os.path.join(out_dir, name, 'frame_0001.png'))
        print('%-16s covered %6d  disagree %5d (%.2f%%)  sdf-only %5d  n.l-only %5d'
              % (name, n, red + green, 100.0 * (red + green) / max(n, 1), red, green))
    looks = sorted(d[len('face_cel_'):] for d in os.listdir(out_dir) if d.startswith('face_cel_'))
    rows = [debug] + [['face_cel_' + k, 'face_plain_' + k] for k in looks]
    sheet(out_dir, rows)


if __name__ == '__main__':
    main(sys.argv[1])
