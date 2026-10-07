# Pure numpy BVH build and reference traversal for ray traced shadows.
# Must not import OpenGL or other Malt GL modules.
# The traversal and the ray/triangle test here are the reference for Shaders/Lighting/RayShadows.glsl.

import numpy as np

BIN_COUNT = 12
LEAF_SIZE = 4
MAX_DEPTH = 48


class BVH():

    # nodes: (N, 8) float32: bmin.xyz, a, bmax.xyz, b (a and b are uint32 bit patterns).
    #   leaf when b > 0: a = first triangle, b = triangle count.
    #   inner: b = 0, a = right child index, left child = this node + 1.
    #   An empty BVH is one node with an inverted box (never hit), a = b = 0.
    # tris: (T, 4, 4) float32: v0, v1, v2 as vec4 (w = 0), in leaf order.
    # info: (T, 4) uint32: object id, shadow group bitmask, 0, 0.
    # depth: number of levels (a single leaf is 1).
    def __init__(self, nodes, tris, info, depth):
        self.nodes = nodes
        self.tris = tris
        self.info = info
        self.depth = depth


def _half_area(bmin, bmax):
    d = np.maximum(bmax - bmin, 0)
    return d[..., 0] * d[..., 1] + d[..., 1] * d[..., 2] + d[..., 2] * d[..., 0]


def _gather(starts, counts):
    # Concatenated index ranges, and the segment offset of each range in the result
    offsets = np.cumsum(counts) - counts
    total = int(counts.sum())
    idx = np.repeat(starts - offsets, counts) + np.arange(total)
    return idx, offsets


def _empty_bvh():
    nodes = np.zeros((1, 8), dtype=np.float32)
    nodes[0, 0:3] = 1e30
    nodes[0, 4:7] = -1e30
    return BVH(nodes, np.zeros((0, 4, 4), dtype=np.float32), np.zeros((0, 4), dtype=np.uint32), 1)


def build_bvh(tris, info):
    tris = np.ascontiguousarray(tris, dtype=np.float32).reshape(-1, 3, 3)
    info = np.asarray(info, dtype=np.uint32).reshape(-1, 2)
    count = len(tris)
    if count == 0:
        return _empty_bvh()

    lo = tris.min(axis=1)
    hi = tris.max(axis=1)
    centroid = (lo + hi) * 0.5
    order = np.arange(count)

    # Breadth-first, one numpy pass per level. Node ids of a level are contiguous.
    node_start = [np.array([0])]
    node_count = [np.array([count])]
    node_bmin = []
    node_bmax = []
    node_left = []  # BFS id of the left child (right = left + 1), -1 for leaves
    level_base = [0]
    next_base = 1
    depth = 0
    while True:
        starts, counts = node_start[depth], node_count[depth]
        n = len(starts)
        idx, offsets = _gather(starts, counts)
        node_bmin.append(np.minimum.reduceat(lo[order[idx]], offsets, axis=0))
        node_bmax.append(np.maximum.reduceat(hi[order[idx]], offsets, axis=0))
        split = (counts > LEAF_SIZE) & (depth < MAX_DEPTH - 1)
        left = np.full(n, -1)
        depth += 1
        if not split.any():
            node_left.append(left)
            break

        s_nodes = np.flatnonzero(split)
        s_starts, s_counts = starts[s_nodes], counts[s_nodes]
        m = len(s_nodes)
        idx, offsets = _gather(s_starts, s_counts)
        tri = order[idx]
        seg = np.repeat(np.arange(m), s_counts)
        c = centroid[tri]
        cmin = np.minimum.reduceat(c, offsets, axis=0)
        cmax = np.maximum.reduceat(c, offsets, axis=0)
        extent = cmax - cmin
        t_lo, t_hi = lo[tri], hi[tri]

        costs = np.full((m, 3, BIN_COUNT - 1), np.inf)
        bins = np.zeros((3, len(tri)), dtype=np.int64)
        for axis in range(3):
            scale = np.where(extent[:, axis] > 0, BIN_COUNT / np.maximum(extent[:, axis], 1e-30), 0.0)
            b = np.floor((c[:, axis] - cmin[seg, axis]) * scale[seg]).astype(np.int64)
            b = np.clip(b, 0, BIN_COUNT - 1)
            bins[axis] = b
            key = seg * BIN_COUNT + b
            srt = np.argsort(key, kind='stable')
            skey = key[srt]
            first = np.flatnonzero(np.concatenate(([True], skey[1:] != skey[:-1])))
            ukey = skey[first]
            bin_min = np.full((m * BIN_COUNT, 3), np.inf)
            bin_max = np.full((m * BIN_COUNT, 3), -np.inf)
            bin_cnt = np.zeros(m * BIN_COUNT)
            bin_min[ukey] = np.minimum.reduceat(t_lo[srt], first, axis=0)
            bin_max[ukey] = np.maximum.reduceat(t_hi[srt], first, axis=0)
            bin_cnt[ukey] = np.diff(np.append(first, len(srt)))
            bin_min = bin_min.reshape(m, BIN_COUNT, 3)
            bin_max = bin_max.reshape(m, BIN_COUNT, 3)
            bin_cnt = bin_cnt.reshape(m, BIN_COUNT)
            l_min = np.minimum.accumulate(bin_min, axis=1)[:, :-1]
            l_max = np.maximum.accumulate(bin_max, axis=1)[:, :-1]
            l_cnt = np.cumsum(bin_cnt, axis=1)[:, :-1]
            r_min = np.minimum.accumulate(bin_min[:, ::-1], axis=1)[:, ::-1][:, 1:]
            r_max = np.maximum.accumulate(bin_max[:, ::-1], axis=1)[:, ::-1][:, 1:]
            r_cnt = np.cumsum(bin_cnt[:, ::-1], axis=1)[:, ::-1][:, 1:]
            with np.errstate(invalid='ignore'):
                cost = np.where(l_cnt > 0, _half_area(l_min, l_max), 0) * l_cnt \
                    + np.where(r_cnt > 0, _half_area(r_min, r_max), 0) * r_cnt
            costs[:, axis] = np.where((l_cnt > 0) & (r_cnt > 0), cost, np.inf)

        flat = costs.reshape(m, -1)
        best = flat.argmin(axis=1)
        valid = np.isfinite(flat[np.arange(m), best])
        best_axis, best_bin = best // (BIN_COUNT - 1), best % (BIN_COUNT - 1)

        # Side of each triangle: SAH split, or an arbitrary halving when all centroids coincide
        sah_side = bins[best_axis[seg], np.arange(len(tri))] > best_bin[seg]
        position = np.arange(len(tri)) - offsets[seg]
        half_side = position >= (s_counts[seg] + 1) // 2
        side = np.where(valid[seg], sah_side, half_side)

        # Stable partition of every node range: left triangles first
        srt = np.argsort(seg * 2 + side, kind='stable')
        order[idx] = tri[srt]
        left_count = np.bincount(seg, weights=~side, minlength=m).astype(np.int64)

        child_start = np.empty(2 * m, dtype=np.int64)
        child_count = np.empty(2 * m, dtype=np.int64)
        child_start[0::2], child_start[1::2] = s_starts, s_starts + left_count
        child_count[0::2], child_count[1::2] = left_count, s_counts - left_count
        left[s_nodes] = next_base + 2 * np.arange(m)
        next_base += 2 * m
        node_left.append(left)
        level_base.append(level_base[-1] + n)
        node_start.append(child_start)
        node_count.append(child_count)

    # Relabel breadth-first ids to depth-first (left child = parent + 1)
    total = next_base
    bmin = np.concatenate(node_bmin)
    bmax = np.concatenate(node_bmax)
    start = np.concatenate(node_start[:depth])
    cnt = np.concatenate(node_count[:depth])
    lft = np.concatenate(node_left)
    size = np.ones(total, dtype=np.int64)
    for level in range(depth - 2, -1, -1):
        ids = np.arange(level_base[level], level_base[level + 1])
        inner = ids[lft[ids] >= 0]
        size[inner] = 1 + size[lft[inner]] + size[lft[inner] + 1]
    pos = np.zeros(total, dtype=np.int64)
    for level in range(depth - 1):
        ids = np.arange(level_base[level], level_base[level + 1])
        inner = ids[lft[ids] >= 0]
        pos[lft[inner]] = pos[inner] + 1
        pos[lft[inner] + 1] = pos[inner] + 1 + size[lft[inner]]

    nodes = np.zeros((total, 8), dtype=np.float32)
    nodes_u = nodes.view(np.uint32)
    nodes[pos, 0:3] = bmin
    nodes[pos, 4:7] = bmax
    is_inner = lft >= 0
    a = np.where(is_inner, pos[np.minimum(np.maximum(lft, 0) + 1, total - 1)], start)
    b = np.where(is_inner, 0, cnt)
    nodes_u[pos, 3] = a.astype(np.uint32)
    nodes_u[pos, 7] = b.astype(np.uint32)

    out_tris = np.zeros((count, 4, 4), dtype=np.float32)
    out_tris[:, :3, :3] = tris[order]
    out_info = np.zeros((count, 4), dtype=np.uint32)
    out_info[:, 0:2] = info[order]
    return BVH(nodes, out_tris, out_info, depth)


def _ray_setup(direction):
    d = np.asarray(direction, dtype=np.float32)
    kz = int(np.argmax(np.abs(d)))
    kx = (kz + 1) % 3
    ky = (kx + 1) % 3
    if d[kz] < 0:
        kx, ky = ky, kx
    return kx, ky, kz, d[kx] / d[kz], d[ky] / d[kz], np.float32(1.0) / d[kz]


def _hit_triangles(tri_v, origin, direction, t_max, setup):
    # Watertight ray/triangle test (Woop, Benthin, Wald 2013), two-sided, float32 with a float64
    # fallback when an edge function is exactly 0. tri_v: (K, 3, 3). Returns a (K,) bool mask: 0 < t <= t_max.
    kx, ky, kz, sx, sy, sz = setup
    o = np.asarray(origin, dtype=np.float32)
    rel = tri_v.astype(np.float32) - o
    a, b, c = rel[:, 0], rel[:, 1], rel[:, 2]

    def edges(a, b, c, sx, sy):
        ax, ay = a[:, kx] - sx * a[:, kz], a[:, ky] - sy * a[:, kz]
        bx, by = b[:, kx] - sx * b[:, kz], b[:, ky] - sy * b[:, kz]
        cx, cy = c[:, kx] - sx * c[:, kz], c[:, ky] - sy * c[:, kz]
        return cx * by - cy * bx, ax * cy - ay * cx, bx * ay - by * ax

    u, v, w = edges(a, b, c, sx, sy)
    zero = (u == 0) | (v == 0) | (w == 0)
    if zero.any():
        z = np.flatnonzero(zero)
        a64, b64, c64 = a[z].astype(np.float64), b[z].astype(np.float64), c[z].astype(np.float64)
        u[z], v[z], w[z] = [e.astype(np.float32) for e in edges(a64, b64, c64, np.float64(sx), np.float64(sy))]
        # float32 rounding of a double edge function can create a new zero: keep the sign of the double value
    ok = ~(((u < 0) | (v < 0) | (w < 0)) & ((u > 0) | (v > 0) | (w > 0)))
    det = u + v + w
    ok &= det != 0
    az, bz, cz = sz * a[:, kz], sz * b[:, kz], sz * c[:, kz]
    t_scaled = u * az + v * bz + w * cz
    with np.errstate(divide='ignore', invalid='ignore'):
        t = t_scaled / det
    return ok & (t > 0) & (t <= np.float32(t_max))


def _blockers(info, self_id, self_shadows, light_group_bit):
    mask = (info[:, 1] & np.uint32(light_group_bit)) != 0
    if not self_shadows:
        mask &= info[:, 0] != np.uint32(self_id)
    return mask


def brute_occluded(tris, info, origin, direction, t_max, self_id, self_shadows, light_group_bit):
    tris = np.asarray(tris, dtype=np.float32).reshape(-1, 3, 3)
    info = np.asarray(info, dtype=np.uint32)
    if len(tris) == 0:
        return False
    keep = _blockers(info, self_id, self_shadows, light_group_bit)
    if not keep.any():
        return False
    setup = _ray_setup(direction)
    return bool(_hit_triangles(tris[keep], origin, direction, t_max, setup).any())


def occluded_ref(bvh, origin, direction, t_max, self_id, self_shadows, light_group_bit):
    # Any-hit stack traversal, same as the GLSL one
    o = np.asarray(origin, dtype=np.float32)
    d = np.asarray(direction, dtype=np.float32)
    setup = _ray_setup(d)
    safe = np.where(d == 0, np.float32(1e-30), d)
    inv = np.float32(1.0) / safe
    t_max = np.float32(t_max)
    nodes = bvh.nodes
    nodes_u = nodes.view(np.uint32)
    stack = [0]
    while stack:
        i = stack.pop()
        if np.any(nodes[i, 0:3] > nodes[i, 4:7]):
            continue  # empty box
        t0 = (nodes[i, 0:3] - o) * inv
        t1 = (nodes[i, 4:7] - o) * inv
        t_near = np.max(np.minimum(t0, t1))
        t_far = np.min(np.maximum(t0, t1)) * np.float32(1.0000005)  # robust slab test
        if not (max(t_near, np.float32(0)) <= min(t_far, t_max)):
            continue
        count = int(nodes_u[i, 7])
        if count > 0:
            first = int(nodes_u[i, 3])
            sl = slice(first, first + count)
            keep = _blockers(bvh.info[sl], self_id, self_shadows, light_group_bit)
            if keep.any():
                v = bvh.tris[sl, :3, :3][keep]
                if _hit_triangles(v, o, d, t_max, setup).any():
                    return True
        else:
            stack.append(int(nodes_u[i, 3]))
            stack.append(i + 1)
    return False
