"""Checks the 1 px line rule on a line mask.  python line_check.py WITH.png WITHOUT.png
The line mask is the set of pixels that differ between a render with lines and the same render without lines.
python line_check.py --marker DEBUG.png: the mask is the magenta / cyan pixels of a PIXEL_LINES_DEBUG=1 render (exact,
also where a line has the colour of the surface under it)."""
import sys

import numpy as np


def line_mask(with_lines, without_lines):
    a = np.asarray(with_lines).astype(int)
    b = np.asarray(without_lines).astype(int)
    if a.ndim == 3:
        return np.abs(a[..., :3] - b[..., :3]).max(axis=2) > 0
    return a != b


def marker_mask(image):
    a = np.asarray(image).astype(int)[..., :3]
    magenta = (a[..., 0] == 255) & (a[..., 1] == 0) & (a[..., 2] == 255)
    cyan = (a[..., 0] == 0) & (a[..., 1] == 255) & (a[..., 2] == 255)
    return magenta | cyan


def outside_pixels(image, lines):
    # covered pixels that are not lines and touch the background with a side (model outside the outline)
    covered = np.asarray(image)[..., 3] > 0
    n = _neighbours(~covered)
    return covered & ~lines & (n['up'] | n['dn'] | n['lf'] | n['rt'])


def _neighbours(mask):
    p = np.pad(mask, 1)
    return {
        'up': p[:-2, 1:-1], 'dn': p[2:, 1:-1], 'lf': p[1:-1, :-2], 'rt': p[1:-1, 2:],
        'ul': p[:-2, :-2], 'ur': p[:-2, 2:], 'dl': p[2:, :-2], 'dr': p[2:, 2:],
    }


def _components(mask):
    # 8-connected components: list of pixel lists
    todo = set(zip(*np.nonzero(mask)))
    out = []
    while todo:
        comp, stack = [], [todo.pop()]
        while stack:
            y, x = stack.pop()
            comp.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    q = (y + dy, x + dx)
                    if q in todo:
                        todo.remove(q)
                        stack.append(q)
        out.append(comp)
    return out


def line_violations(mask):
    mask = np.asarray(mask, dtype=bool)
    n = _neighbours(mask)
    blocks = int((mask[:-1, :-1] & mask[1:, :-1] & mask[:-1, 1:] & mask[1:, 1:]).sum())
    ortho = n['up'].astype(int) + n['dn'] + n['lf'] + n['rt']
    diag = n['ul'] | n['ur'] | n['dl'] | n['dr']
    l_corners = int((mask & (n['up'] ^ n['dn']) & (n['lf'] ^ n['rt']) & (ortho == 2) & ~diag).sum())
    count8 = ortho + n['ul'] + n['ur'] + n['dl'] + n['dr']
    isolated = int((mask & (count8 == 0)).sum())
    short = sum(len(c) for c in _components(mask) if len(c) < 3)
    return {'blocks': blocks, 'l_corners': l_corners, 'isolated': isolated, 'short': short,
            'total': blocks + l_corners + isolated + short}


if __name__ == '__main__':
    from PIL import Image
    outside = 0
    if sys.argv[1] == '--marker':
        image = np.array(Image.open(sys.argv[2]).convert('RGBA'))
        mask = marker_mask(image)
        outside = int(outside_pixels(image, mask).sum())
    else:
        with_lines = np.array(Image.open(sys.argv[1]).convert('RGB'))
        without_lines = np.array(Image.open(sys.argv[2]).convert('RGB'))
        mask = line_mask(with_lines, without_lines)
    result = line_violations(mask)
    print('line px', int(mask.sum()), result, 'outside', outside)
    sys.exit(1 if result['total'] > 0 or outside > 0 else 0)
