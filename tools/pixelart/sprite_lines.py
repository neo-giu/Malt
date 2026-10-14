# tools/pixelart/sprite_lines.py
"""Line statistics of reference sprites: where do artists keep L corners and 2x2 line blocks?
    python sprite_lines.py OUT_DIR SPRITE.gif|png [SPRITE ...] [--lines r,g,b;r,g,b;...]
Line pixels = dark strokes at most 2 px wide (stroke_mask), or the colours --lines gives. Every frame of a GIF is used. Prints per sprite: line px, 2x2 blocks,
L corners, and the L corners sorted by situation; writes a 4x overlay per sprite (red = L corner, blue = block)."""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, 'H:/GameDev/Pixelizer/src')
from pixelizer.oklab import srgb_to_oklab   # noqa: E402

N4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
N8 = N4 + [(-1, -1), (-1, 1), (1, -1), (1, 1)]


def frames(path):
    im = Image.open(path)
    for i in range(getattr(im, 'n_frames', 1)):
        im.seek(i)
        yield np.array(im.convert('RGBA'))


def shift(m, dy, dx, fill=False):
    p = np.pad(m, 1, constant_values=fill)
    return p[1 + dy:1 + dy + m.shape[0], 1 + dx:1 + dx + m.shape[1]]


def shift2(m, dy, dx, fill):
    p = np.pad(m, 2, constant_values=fill)
    return p[2 + dy:2 + dy + m.shape[0], 2 + dx:2 + dx + m.shape[1]]


def stroke_mask(a, delta=0.12):
    # Line pixels by shape, no palette needed: a dark stroke at most 2 px wide with lighter pixels (Oklab L at least
    # delta brighter) on both sides across it, in one of 4 directions. Background counts as light, so silhouette lines
    # are found and solid dark fills (hair, belts) are not.
    opaque = a[..., 3] > 0
    light = np.where(opaque, srgb_to_oklab(a[..., :3].reshape(-1, 3)).reshape(a.shape[:2] + (3,))[..., 0], 2.0)
    line = np.zeros(opaque.shape, bool)
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        sides = []
        for s in (1, -1):
            n1 = shift2(light, s * dy, s * dx, 2.0)
            n2 = shift2(light, 2 * s * dy, 2 * s * dx, 2.0)
            # 1 px: the neighbour is lighter; 2 px: the neighbour is as dark as p and the next one is lighter
            sides.append((n1 - light > delta) | ((np.abs(n1 - light) < delta / 2) & (n2 - light > delta)))
        line |= sides[0] & sides[1]
    return opaque & line


def colour_mask(a, lines):
    rgb = a[..., :3].astype(int)
    key = (rgb[..., 0] << 16) | (rgb[..., 1] << 8) | rgb[..., 2]
    return (a[..., 3] > 0) & np.isin(key, [(r << 16) | (g << 8) | b for r, g, b in lines])


def analyse(a, L):
    opaque = a[..., 3] > 0
    rgb = a[..., :3]
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



def classify_blocks(L, opaque):
    # 2x2 line blocks outside solid fills, sorted by the line branches on the 12-pixel ring around them:
    # junction = 3+ branches meet; bend = 2 branches less than 90 degrees apart around the ring; run = a straight stroke
    n8 = sum(shift(L, *d).astype(int) for d in N8)
    fill = L & (n8 >= 7)
    near = fill.copy()
    for d in N8:
        near |= shift(fill, *d)
    tl = L & shift(L, 0, 1) & shift(L, 1, 0) & shift(L, 1, 1)
    out = {'blocks': 0, 'junction': 0, 'bend': 0, 'run': 0, 'end': 0, 'on_silhouette': 0}
    h, w = L.shape
    for y, x in zip(*np.nonzero(tl)):
        if near[y:y + 2, x:x + 2].any():
            continue
        out['blocks'] += 1
        ring = [(y - 1, x - 1), (y - 1, x), (y - 1, x + 1), (y - 1, x + 2), (y, x + 2), (y + 1, x + 2), (y + 2, x + 2),
                (y + 2, x + 1), (y + 2, x), (y + 2, x - 1), (y + 1, x - 1), (y, x - 1)]
        inside = [0 <= py < h and 0 <= px < w for py, px in ring]
        v = [inside[i] and bool(L[ring[i]]) for i in range(12)]
        starts = [i for i in range(12) if v[i] and not v[i - 1]]
        if any(inside[i] and not opaque[ring[i]] for i in range(12)) or not all(inside):
            out['on_silhouette'] += 1
        if len(starts) >= 3:
            out['junction'] += 1
        elif len(starts) == 2:
            d = (starts[1] - starts[0]) % 12
            out['bend' if min(d, 12 - d) <= 4 else 'run'] += 1
        else:
            out['end'] += 1
    return out

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
        total = {}
        for k, a in enumerate(images):
            stats, L, lc, bl = analyse(a, colour_mask(a, lines_arg) if lines_arg else stroke_mask(a))
            stats.update({'b_' + k: v for k, v in classify_blocks(L, a[..., 3] > 0).items()})
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
        print(os.path.basename(path), 'frames', len(images), 'lines by', 'colour' if lines_arg else 'stroke shape')
        print('  per frame: line px %.0f  2x2 blocks %.1f  L corners %.1f (%.1f per 100 line px)' % (
            total['line'] / len(images), total['blocks'] / len(images), total['l_corners'] / len(images),
            100.0 * total['l_corners'] / max(1, total['line'])))
        print('  L corners: convex tip %d%%  concave %d%%  other silhouette %d%%  inner %d%% (overlap %d%% of inner)' % (
            100 * total['convex_tip'] // lc, 100 * total['concave'] // lc, 100 * total['silhouette_other'] // lc,
            100 * total['inner'] // lc, 100 * total['inner_overlap'] // max(1, total['inner'])))
        tb = max(1, total['b_blocks'])
        print('  thin-line 2x2 blocks %.1f per frame (%.1f per 100 line px): junction %d%%  run %d%%  bend %d%%  end %d%%'
              '  on silhouette %d%%' % (total['b_blocks'] / len(images), 100.0 * total['b_blocks'] / max(1, total['line']),
              100 * total['b_junction'] // tb, 100 * total['b_run'] // tb, 100 * total['b_bend'] // tb,
              100 * total['b_end'] // tb, 100 * total['b_on_silhouette'] // tb))
        print('  junction px per frame %.1f, block px on the silhouette %d%%' % (
            total['junction_px'] / len(images), 100 * total['block_px_ring'] // max(1, 4 * total['blocks'])))


if __name__ == '__main__':
    main()
