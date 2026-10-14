# tools/pixelart/sprite_lines.py
"""Line statistics of reference sprites: where do artists keep L corners and 2x2 line blocks?
    python sprite_lines.py OUT_DIR SPRITE.gif|png [SPRITE ...] [--lines r,g,b;r,g,b;...]
Line pixels = the darkest colour of each ramp. Ramps are found by grouping the palette by Oklab hue/chroma (k = 6),
unless --lines gives the line colours. Every frame of a GIF is used. Prints per sprite: line px, 2x2 blocks,
L corners, and the L corners sorted by situation; writes a 4x overlay per sprite (red = L corner, blue = block)."""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, 'H:/GameDev/Pixelizer/src')
from pixelizer.oklab import group_ramps, srgb_to_oklab   # noqa: E402

N4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
N8 = N4 + [(-1, -1), (-1, 1), (1, -1), (1, 1)]


def frames(path):
    im = Image.open(path)
    for i in range(getattr(im, 'n_frames', 1)):
        im.seek(i)
        yield np.array(im.convert('RGBA'))


def line_colours(images, groups=6):
    opaque = np.concatenate([a[a[..., 3] > 0][:, :3] for a in images])
    colours, counts = np.unique(opaque, axis=0, return_counts=True)
    keep = counts >= 3                      # stray colours (a few px) are not ramp members
    colours = colours[keep]
    ramps = group_ramps(colours, min(groups, len(colours)))
    return {tuple(int(v) for v in colours[r[-1]]) for r in ramps if r}   # r is sorted light -> dark


def shift(m, dy, dx):
    p = np.pad(m, 1)
    return p[1 + dy:1 + dy + m.shape[0], 1 + dx:1 + dx + m.shape[1]]


def analyse(a, lines):
    opaque = a[..., 3] > 0
    rgb = a[..., :3]
    L = opaque & np.isin(rgb.view([('', rgb.dtype)] * 3)[..., 0],
                         np.array(sorted(lines), dtype=rgb.dtype).view([('', rgb.dtype)] * 3)[:, 0])
    n = {d: shift(L, *d) for d in N8}
    bg = {d: ~shift(opaque, *d) for d in N8}
    up, dn, lf, rt = n[(-1, 0)], n[(1, 0)], n[(0, -1)], n[(0, 1)]
    diag = n[(-1, -1)] | n[(-1, 1)] | n[(1, -1)] | n[(1, 1)]
    ortho = up.astype(int) + dn + lf + rt
    count8 = ortho + n[(-1, -1)] + n[(-1, 1)] + n[(1, -1)] + n[(1, 1)]
    lcorner = L & (up ^ dn) & (lf ^ rt) & (ortho == 2) & ~diag
    block_tl = L & n[(0, 1)] & n[(1, 0)] & n[(1, 1)]
    block = block_tl | shift(block_tl, 0, -1) | shift(block_tl, -1, 0) | shift(block_tl, -1, -1)
    bg8 = sum(b.astype(int) for b in bg.values())
    ring = L & (bg[(-1, 0)] | bg[(1, 0)] | bg[(0, -1)] | bg[(0, 1)])
    # L corner situations
    convex = lcorner & (bg8 >= 5)            # the corner points out into the background (a silhouette tip)
    concave = lcorner & ring & (bg8 <= 2)    # an inner corner of the silhouette
    silhouette = lcorner & ring & ~convex & ~concave
    inner = lcorner & ~ring                  # inside the sprite: fold / overlap / crease lines
    # an inner L corner where two different surfaces meet (the colours across the corner differ a lot) = overlap
    lab = srgb_to_oklab(rgb.reshape(-1, 3)).reshape(rgb.shape)
    out_dir = np.zeros(L.shape + (2,), int)
    for dy, dx in N4:
        out_dir += np.where(((~shift(L, dy, dx)) & shift(opaque, dy, dx))[..., None], np.array([dy, dx]), 0)
    overlap = np.zeros_like(L)
    for y, x in zip(*np.nonzero(inner)):
        dy, dx = out_dir[y, x]
        y1, x1, y2, x2 = y + dy, x + dx, y - dy, x - dx       # the two fill pixels across the corner
        ok = all(0 <= v < s for v, s in ((y1, L.shape[0]), (x1, L.shape[1]), (y2, L.shape[0]), (x2, L.shape[1])))
        if ok and opaque[y1, x1] and opaque[y2, x2]:
            overlap[y, x] = np.linalg.norm(lab[y1, x1] - lab[y2, x2]) > 0.1
    return {
        'line': int(L.sum()), 'blocks': int(block_tl.sum()), 'block_px_ring': int((block & ring).sum()),
        'l_corners': int(lcorner.sum()), 'convex_tip': int(convex.sum()), 'concave': int(concave.sum()),
        'silhouette_other': int(silhouette.sum()), 'inner': int(inner.sum()), 'inner_overlap': int(overlap.sum()),
        'junction_px': int((L & (count8 >= 3)).sum()),
    }, L, lcorner, block


def main():
    args = sys.argv[1:]
    out = args.pop(0)
    lines_arg = None
    if '--lines' in args:
        i = args.index('--lines')
        lines_arg = {tuple(int(v) for v in c.split(',')) for c in args[i + 1].split(';')}
        del args[i:i + 2]
    os.makedirs(out, exist_ok=True)
    for path in args:
        images = list(frames(path))
        lines = lines_arg or line_colours(images)
        total = {}
        for k, a in enumerate(images):
            stats, L, lc, bl = analyse(a, lines)
            for key, v in stats.items():
                total[key] = total.get(key, 0) + v
            if k == 0:
                vis = a.copy()
                vis[L] = (40, 40, 40, 255)
                vis[bl] = (40, 90, 255, 255)
                vis[lc] = (255, 40, 40, 255)
                Image.fromarray(vis).resize((a.shape[1] * 4, a.shape[0] * 4), Image.NEAREST).save(
                    os.path.join(out, os.path.splitext(os.path.basename(path))[0] + '_lines.png'))
        lc = max(1, total['l_corners'])
        print(os.path.basename(path), 'frames', len(images), 'line colours', sorted(lines))
        print('  per frame: line px %.0f  2x2 blocks %.1f  L corners %.1f (%.1f per 100 line px)' % (
            total['line'] / len(images), total['blocks'] / len(images), total['l_corners'] / len(images),
            100.0 * total['l_corners'] / max(1, total['line'])))
        print('  L corners: convex tip %d%%  concave %d%%  other silhouette %d%%  inner %d%% (overlap %d%% of inner)' % (
            100 * total['convex_tip'] // lc, 100 * total['concave'] // lc, 100 * total['silhouette_other'] // lc,
            100 * total['inner'] // lc, 100 * total['inner_overlap'] // max(1, total['inner'])))
        print('  junction px per frame %.1f, block px on the silhouette %d%%' % (
            total['junction_px'] / len(images), 100 * total['block_px_ring'] // max(1, 4 * total['blocks'])))


if __name__ == '__main__':
    main()
