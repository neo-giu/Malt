# Malt/PixelArt/zones.py
# Zones and palette ramps for Pixel Cel (spec 09 section 4). No bpy, no OpenGL (unit tested outside Blender).
# Oklab and k-means ported from Pixelizer src/pixelizer/oklab.py.
import colorsys
import dataclasses
from collections import deque

import numpy as np

from .cel_ref import linear_to_srgb, shifted_shadow, srgb_to_linear
from .presets import PRESETS

_M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929], [0.2119034982, 0.6806995451, 0.1073969566],
                [0.0883024619, 0.2817188376, 0.6299787005]])
_M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468], [1.9779984951, -2.4285922050, 0.4505937099],
                [0.0259040371, 0.7827717662, -0.8086757660]])
MAX_SLOTS = 7
SAME_RAMP = 0.02   # Oklab distance under which two zones share one ramp


@dataclasses.dataclass
class Zone:
    material: str
    cluster: int
    rgb: tuple
    sss: tuple = None
    texels: int = 0


def srgb_to_oklab(rgb):
    c = np.asarray(rgb, np.float64) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return np.cbrt(lin @ _M1.T) @ _M2.T


def kmeans(points, k, seed=0, iters=50):
    rng = np.random.default_rng(seed)
    pts = np.asarray(points, np.float64)
    centres = [pts[rng.integers(len(pts))]]
    for _ in range(1, k):
        d = np.min(((pts[:, None] - np.array(centres)[None]) ** 2).sum(-1), 1)
        centres.append(pts[rng.choice(len(pts), p=d / d.sum())] if d.sum() > 0 else pts[rng.integers(len(pts))])
    c = np.array(centres)
    for _ in range(iters):
        lab = ((pts[:, None] - c[None]) ** 2).sum(-1).argmin(1)
        new = np.array([pts[lab == i].mean(0) if np.any(lab == i) else c[i] for i in range(k)])
        if np.allclose(new, c):
            break
        c = new
    return c, ((pts[:, None] - c[None]) ** 2).sum(-1).argmin(1)


def cluster_texture(rgba, k_max=8, seed=0, sample=20000):
    rgba = np.asarray(rgba)
    opaque = rgba[..., 3] >= 128
    labels = np.full(rgba.shape[:2], -1, int)
    if not opaque.any():
        return labels, np.zeros((0, 3), np.uint8)
    rgb = rgba[..., :3][opaque]
    lab = srgb_to_oklab(rgb)
    rng = np.random.default_rng(seed)
    pts = lab[rng.choice(len(lab), min(sample, len(lab)), replace=False)]
    # k: the smallest k whose inertia is under 15 % of k = 1 (elbow), at most k_max and the distinct colour count
    k_limit = min(k_max, len(np.unique(rgb, axis=0)))
    inertia1 = ((pts - pts.mean(0)) ** 2).sum()
    centres, k = pts.mean(0)[None], 1
    for k in range(1, k_limit + 1):
        centres, l = kmeans(pts, k, seed)
        if inertia1 == 0 or ((pts - centres[l]) ** 2).sum() <= 0.15 * inertia1:
            break
    assign = ((lab[:, None] - centres[None]) ** 2).sum(-1).argmin(1)
    labels[opaque] = assign
    used = sorted(set(assign.tolist()))
    remap = {old: new for new, old in enumerate(used)}
    labels[opaque] = [remap[v] for v in assign]
    means = np.array([rgb[labels[opaque] == i].mean(0) for i in range(len(used))])
    return labels, np.rint(means).astype(np.uint8)


def _components(labels, value):
    h, w = labels.shape
    seen = np.zeros_like(labels, bool)
    for y0, x0 in zip(*np.nonzero(labels == value)):
        if seen[y0, x0]:
            continue
        comp, queue = [], deque([(y0, x0)])
        seen[y0, x0] = True
        while queue:
            y, x = queue.popleft()
            comp.append((y, x))
            for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= ny < h and 0 <= nx < w and not seen[ny, nx] and labels[ny, nx] == value:
                    seen[ny, nx] = True
                    queue.append((ny, nx))
        yield comp


def merge_islands(labels, min_area=16):
    # 4-connected islands under min_area texels take the zone they share most border with (no-zone -1 never grows)
    out = np.array(labels, int, copy=True)
    h, w = out.shape
    for _ in range(5):
        changed = False
        for value in sorted(set(out.ravel().tolist()) - {-1}):
            for comp in list(_components(out, value)):
                if len(comp) >= min_area:
                    continue
                border = {}
                for y, x in comp:
                    for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                        if 0 <= ny < h and 0 <= nx < w and out[ny, nx] not in (value, -1):
                            border[out[ny, nx]] = border.get(out[ny, nx], 0) + 1
                if border:
                    target = max(sorted(border), key=border.get)
                    for y, x in comp:
                        out[y, x] = target
                    changed = True
        if not changed:
            break
    return out


def multiply_srgb(rgb, factor_rgb):
    lin = srgb_to_linear(tuple(c / 255.0 for c in rgb))
    f = srgb_to_linear(tuple(c / 255.0 for c in factor_rgb))
    return tuple(int(round(min(1.0, max(0.0, v)) * 255)) for v in linear_to_srgb(tuple(a * b for a, b in zip(lin, f))))


def _to8(lin_rgb):
    return tuple(int(round(min(1.0, max(0.0, v)) * 255)) for v in linear_to_srgb(lin_rgb))


def ramp_colours(preset, lit_rgb, sss_rgb=None):
    p = PRESETS[preset]
    lit = tuple(int(c) for c in lit_rgb)
    lin = srgb_to_linear(tuple(c / 255.0 for c in lit))
    if not p['palette_slots']:
        shadow = multiply_srgb(lit, sss_rgb) if sss_rgb is not None else _to8(tuple(c * 0.55 for c in lin))
        colours = [lit, shadow]
    else:
        highlight = _to8(tuple(min(1.0, c * 1.2) * 0.8 + w * 0.2 for c, w in zip(lin, (1.0, 0.97, 0.9))))
        colours = [highlight, lit] + [_to8(shifted_shadow(lin, h, s, v)) for h, s, v in p['palette_slots']]
        if sss_rgb is not None:
            colours[-1] = multiply_srgb(colours[-1], sss_rgb)   # ASW Sss, when present, is the deep shadow
    h, s, v = colorsys.rgb_to_hsv(*(c / 255.0 for c in colours[-1]))
    line = tuple(int(round(c * 255)) for c in colorsys.hsv_to_rgb(h, s, v * 0.6))
    return colours[:MAX_SLOTS], line


def group_zones(zones, n_ramps, seed=0):
    # zones closer than SAME_RAMP in Oklab share a ramp; then k-means groups the rest down to the budget
    lab = srgb_to_oklab(np.array([z.rgb for z in zones]))
    groups = []
    for i in range(len(zones)):
        for g in groups:
            if np.linalg.norm(lab[g[0]] - lab[i]) < SAME_RAMP:
                g.append(i)
                break
        else:
            groups.append([i])
    if len(groups) <= n_ramps:
        return groups
    _, labels = kmeans(lab[[g[0] for g in groups]], n_ramps, seed)
    merged = [sorted(i for k, g in enumerate(groups) if labels[k] == r for i in g) for r in range(n_ramps)]
    return [g for g in merged if g]


def build_palette(preset, zones, budget=40, seed=0):
    p = PRESETS[preset]
    slots = 2 if not p['palette_slots'] else 2 + len(p['palette_slots'])
    groups = group_zones(zones, max(1, budget // (slots + 1)), seed)
    ramps, zone_ramp = {}, {}
    for i, group in enumerate(groups):
        weights = np.array([max(1, zones[j].texels) for j in group], float)
        lit = np.rint((np.array([zones[j].rgb for j in group], float) * weights[:, None]).sum(0) / weights.sum())
        ssses = [zones[j].sss for j in group if zones[j].sss is not None]
        sss = tuple(np.rint(np.mean(ssses, 0)).astype(int)) if ssses else None
        colours, line = ramp_colours(preset, tuple(int(c) for c in lit), sss)
        name = f'ramp{i}'
        ramps[name] = {'colours': [list(map(int, c)) for c in colours], 'line': list(map(int, line)),
                       'stops': list(p['palette_stops'])[:len(colours) - 1]}
        for j in group:
            zone_ramp[f'{zones[j].material}/{zones[j].cluster}'] = name
    return {'version': 1, 'preset': preset, 'ramps': ramps, 'zone_ramp': zone_ramp}


def palette_strip(palette):
    names = list(palette['ramps'])
    strip = np.zeros((len(names), MAX_SLOTS + 1, 3), np.uint8)
    for r, name in enumerate(names):
        ramp = palette['ramps'][name]
        for s, c in enumerate(ramp['colours']):
            strip[r, s] = c
        strip[r, MAX_SLOTS] = ramp['line']
    return strip


def apply_strip(palette, strip):
    out = {**palette, 'ramps': {}}
    for r, (name, ramp) in enumerate(palette['ramps'].items()):
        out['ramps'][name] = {**ramp, 'colours': [list(map(int, strip[r, s])) for s in range(len(ramp['colours']))],
                              'line': list(map(int, strip[r, MAX_SLOTS]))}
    return out


def gpu_palette(palette):
    names = list(palette['ramps'])
    g = np.zeros((2 * len(names), MAX_SLOTS + 1, 4), np.uint8)
    for r, name in enumerate(names):
        ramp = palette['ramps'][name]
        for s, c in enumerate(ramp['colours']):
            g[2 * r, s, :3] = c
        g[2 * r, MAX_SLOTS, :3] = ramp['line']
        g[2 * r, :, 3] = 255
        for s, stop in enumerate(ramp['stops']):
            g[2 * r + 1, s, 0] = round(stop * 255)
        g[2 * r + 1, 0, 1] = len(ramp['colours'])
        g[2 * r + 1, :, 3] = 255
    return g


def ramp_index_texture(labels, material, palette):
    names = list(palette['ramps'])
    t = np.zeros(labels.shape, np.uint8)
    for cluster in sorted(set(labels.ravel().tolist()) - {-1}):
        ramp = palette['zone_ramp'].get(f'{material}/{cluster}')
        if ramp is not None:
            t[labels == cluster] = names.index(ramp) + 1
    return t


def zone_mips(index):
    # Mip levels of a ramp-index texture by majority vote of each 2x2 block (a zone never blends; spec 09 4.5).
    # Ties: the most common value of the block's top-left first order (top-left, top-right, bottom-left, bottom-right).
    # Odd sizes repeat the last row / column. Stops at 1x1.
    levels = [np.asarray(index, np.uint8)]
    while levels[-1].shape[0] > 1 or levels[-1].shape[1] > 1:
        a = levels[-1]
        if a.shape[0] % 2:
            a = np.vstack([a, a[-1:]])
        if a.shape[1] % 2:
            a = np.hstack([a, a[:, -1:]])
        quad = np.stack([a[0::2, 0::2], a[0::2, 1::2], a[1::2, 0::2], a[1::2, 1::2]], -1)   # h/2 x w/2 x 4
        counts = (quad[..., :, None] == quad[..., None, :]).sum(-1)                          # votes per child
        best = counts.argmax(-1)                                                             # first max = tie order
        levels.append(np.take_along_axis(quad, best[..., None], -1)[..., 0])
    return levels


def mip_atlas(levels):
    # All levels side by side in one image (Malt builds averaged mipmaps for images, so the levels are packed by hand):
    # level l at x = sum of the widths of levels < l, y = 0. Returns (atlas uint8 H x W_total, x offsets per level).
    h = levels[0].shape[0]
    offsets, x = [], 0
    for level in levels:
        offsets.append(x)
        x += level.shape[1]
    atlas = np.zeros((h, x), np.uint8)
    for level, ox in zip(levels, offsets):
        atlas[:level.shape[0], ox:ox + level.shape[1]] = level
    return atlas, offsets
