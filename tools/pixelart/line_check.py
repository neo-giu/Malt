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
    return magenta | cyan | overlap_mask(image) | keep_mask(image)


def keep_mask(image):
    a = np.asarray(image).astype(int)[..., :3]
    return (a[..., 0] == 255) & (a[..., 1] == 255) & (a[..., 2] == 0)


def overlap_mask(image):
    a = np.asarray(image).astype(int)[..., :3]
    # the shader writes (1, 0.5, 0); the frame is sRGB encoded, so green is 188 (128 in a linear PNG)
    return (a[..., 0] == 255) & ((a[..., 1] == 188) | (a[..., 1] == 128)) & (a[..., 2] == 0)


def marker_kinds(image):
    # one char per pixel: 's' silhouette (magenta), 'o' overlap (orange), 'i' inner (cyan), 'k' KEEP (yellow), '.' none
    a = np.asarray(image).astype(int)[..., :3]
    kinds = np.full(a.shape[:2], '.')
    kinds[(a[..., 0] == 0) & (a[..., 1] == 255) & (a[..., 2] == 255)] = 'i'
    kinds[(a[..., 0] == 255) & (a[..., 1] == 0) & (a[..., 2] == 255)] = 's'
    kinds[overlap_mask(image)] = 'o'
    kinds[keep_mask(image)] = 'k'
    return kinds


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


_RING12 = [(-1, -1), (-1, 0), (-1, 1), (-1, 2), (0, 2), (1, 2), (2, 2), (2, 1), (2, 0), (2, -1), (1, -1), (0, -1)]


def _ring_runs(mask, y, x):
    # separate line runs on the 12 pixels around the 2x2 block at (y, x); outside the frame is no line
    h, w = mask.shape
    v = [0 <= y + dy < h and 0 <= x + dx < w and bool(mask[y + dy, x + dx]) for dy, dx in _RING12]
    return sum(1 for i in range(12) if v[i] and not v[i - 1])


def _junction_blocks(mask):
    # 2x2 blocks where 3+ line runs meet on the ring (rule A); a block inside a 3x3 all-line square never counts
    h, w = mask.shape
    out = np.zeros((max(h - 1, 0), max(w - 1, 0)), dtype=bool)
    square = np.zeros(mask.shape, dtype=bool)
    if h >= 3 and w >= 3:
        s3 = np.ones((h - 2, w - 2), dtype=bool)
        for dy in range(3):
            for dx in range(3):
                s3 &= mask[dy:h - 2 + dy, dx:w - 2 + dx]
        for dy in range(3):
            for dx in range(3):
                square[dy:h - 2 + dy, dx:w - 2 + dx] |= s3
    blocks = mask[:-1, :-1] & mask[1:, :-1] & mask[:-1, 1:] & mask[1:, 1:]
    for y, x in zip(*np.nonzero(blocks)):
        if not square[y:y + 2, x:x + 2].any() and _ring_runs(mask, y, x) >= 3:
            out[y, x] = True
    return out


def line_violations(mask, exempt=None, surface=None, kinds=None, rules=(), background=None):
    # surface: covered pixels that are not lines. An L corner beside a surface pixel is a needed corner: removing it
    # would put that surface pixel beside the background (model outside the outline), so it is not counted.
    # rules (corner rules A-C; tips and overlap_corners need kinds: 's' silhouette, 'o' overlap, 'i' inner, 'k' KEEP):
    # junctions = a 2x2 block with 3+ line runs on its ring; tips = an L corner with 5+ of 8 neighbours in background;
    # overlap_corners = an L corner that is an overlap pixel or joins two different kinds.
    mask = np.asarray(mask, dtype=bool)
    exempt = np.zeros_like(mask) if exempt is None else np.asarray(exempt, dtype=bool)
    background = None if background is None else np.asarray(background, dtype=bool)
    n = _neighbours(mask)
    block = mask[:-1, :-1] & mask[1:, :-1] & mask[:-1, 1:] & mask[1:, 1:]
    if 'junctions' in rules:
        block &= ~_junction_blocks(mask)
    if surface is not None:
        # a needed block: each of its 4 pixels touches a surface pixel (a 2 px notch or a 2 px gap between two parts);
        # removing one would put the model beside the background
        s4 = _neighbours(np.asarray(surface, dtype=bool))
        touch = s4['up'] | s4['dn'] | s4['lf'] | s4['rt']
        block &= ~(touch[:-1, :-1] & touch[1:, :-1] & touch[:-1, 1:] & touch[1:, 1:])
    blocks = int(block.sum())
    ortho = n['up'].astype(int) + n['dn'] + n['lf'] + n['rt']
    diag = n['ul'] | n['ur'] | n['dl'] | n['dr']
    corner = mask & (n['up'] ^ n['dn']) & (n['lf'] ^ n['rt']) & (ortho == 2) & ~diag
    if surface is not None:
        s = _neighbours(np.asarray(surface, dtype=bool))
        corner &= ~(s['up'] | s['dn'] | s['lf'] | s['rt'])
    h, w = mask.shape
    for y, x in zip(*np.nonzero(corner)):
        if 'tips' in rules and background is not None:
            far = sum(1 for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy or dx)
                      and (not (0 <= y + dy < h and 0 <= x + dx < w) or background[y + dy, x + dx]))
            if far >= 5:
                corner[y, x] = False
                continue
        if 'overlap_corners' in rules and kinds is not None:
            joined = {'s' if kinds[y + dy, x + dx] == 'k' else kinds[y + dy, x + dx] for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))
                      if 0 <= y + dy < h and 0 <= x + dx < w and mask[y + dy, x + dx]}
            if kinds[y, x] == 'o' or len(joined) > 1:
                corner[y, x] = False
    l_corners = int(corner.sum())
    count8 = ortho + n['ul'] + n['ur'] + n['dl'] + n['dr']
    isolated = int((mask & ~exempt & (count8 == 0)).sum())
    short = sum(len(c) for c in _components(mask) if len(c) < 3 and not any(exempt[y, x] for y, x in c))
    return {'blocks': blocks, 'l_corners': l_corners, 'isolated': isolated, 'short': short,
            'total': blocks + l_corners + isolated + short}


if __name__ == '__main__':
    from PIL import Image
    args = sys.argv[1:]
    rules = ()
    if '--rules' in args:
        i = args.index('--rules')
        rules = tuple(r for r in args[i + 1].split(',') if r)
        del args[i:i + 2]
    outside = 0
    exempt = surface = kinds = background = None
    if args[0] == '--marker':
        image = np.array(Image.open(args[1]).convert('RGBA'))
        mask = marker_mask(image)
        exempt = keep_mask(image)
        surface = (image[..., 3] > 0) & ~mask
        kinds, background = marker_kinds(image), image[..., 3] == 0
        outside = int(outside_pixels(image, mask).sum())
    else:
        with_lines = np.array(Image.open(args[0]).convert('RGB'))
        without_lines = np.array(Image.open(args[1]).convert('RGB'))
        mask = line_mask(with_lines, without_lines)
    result = line_violations(mask, exempt, surface, kinds, rules, background)
    print('line px', int(mask.sum()), result, 'outside', outside)
    if rules:
        # what each rule keeps: blocks / L corners counted without the rule minus with it (A junctions, B tips, C overlap)
        plain = line_violations(mask, exempt, surface, kinds, (), background)
        per100 = 100.0 / max(int(mask.sum()), 1)
        for rule, key in (('junctions', 'blocks'), ('tips', 'l_corners'), ('overlap_corners', 'l_corners')):
            kept = plain[key] - line_violations(mask, exempt, surface, kinds, (rule,), background)[key]
            print(f'kept by {rule}: {kept} ({kept * per100:.2f} per 100 line px)')
    sys.exit(1 if result['total'] > 0 or outside > 0 else 0)
