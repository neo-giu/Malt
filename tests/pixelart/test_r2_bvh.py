import time

import numpy as np

from Malt.Render.RayBVH import build_bvh, occluded_ref, brute_occluded

ALL_GROUPS = 0xFFFFFFFF


def random_soup(rng, count, spread=10.0, size=1.5):
    centers = rng.uniform(-spread, spread, (count, 1, 3))
    tris = centers + rng.uniform(-size, size, (count, 3, 3))
    return tris.astype(np.float32)


def make_info(count, ids=None, mask=ALL_GROUPS):
    info = np.zeros((count, 2), dtype=np.uint32)
    info[:, 0] = np.arange(count) if ids is None else ids
    info[:, 1] = mask
    return info


def icosphere(subdiv):
    t = (1.0 + 5.0 ** 0.5) / 2.0
    verts = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
             (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    verts = [np.array(v, dtype=np.float64) / np.linalg.norm(v) for v in verts]
    faces = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2),
             (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11),
             (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    for _ in range(subdiv):
        cache = {}

        def midpoint(a, b):
            key = (min(a, b), max(a, b))
            if key not in cache:
                m = verts[a] + verts[b]
                verts.append(m / np.linalg.norm(m))
                cache[key] = len(verts) - 1
            return cache[key]
        new_faces = []
        for a, b, c in faces:
            ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
            new_faces += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        faces = new_faces
    verts = np.array(verts, dtype=np.float32)
    return verts, np.array(faces)


def test_random_rays_match_brute_force():
    rng = np.random.default_rng(1)
    tris = random_soup(rng, 500)
    info = make_info(500, ids=rng.integers(0, 8, 500), mask=rng.integers(0, 4, 500))
    bvh = build_bvh(tris, info)
    mismatches = 0
    hits = 0
    for _ in range(2000):
        origin = rng.uniform(-14, 14, 3)
        direction = rng.normal(size=3)
        t_max = float(rng.choice([1e30, rng.uniform(0.5, 20)]))
        self_id = int(rng.integers(0, 8))
        self_shadows = bool(rng.integers(0, 2))
        bit = int(rng.choice([1, 2]))
        a = occluded_ref(bvh, origin, direction, t_max, self_id, self_shadows, bit)
        b = brute_occluded(tris, info, origin, direction, t_max, self_id, self_shadows, bit)
        mismatches += a != b
        hits += b
    assert mismatches == 0
    assert 100 < hits < 1900  # the test is not trivially all-hit or all-miss


def test_watertight_icosphere():
    verts, faces = icosphere(2)
    tris = verts[faces]
    info = make_info(len(tris), ids=0)
    bvh = build_bvh(tris, info)
    targets = [v for v in verts]
    for f in faces:
        for i in range(3):
            targets.append((verts[f[i]] + verts[f[(i + 1) % 3]]) * 0.5)
    for target in targets:
        # Ray from outside through the target point and the centre
        origin = np.asarray(target, dtype=np.float64) * 5.0
        assert brute_occluded(tris, info, origin, -origin, 1e30, 1, True, 1)
        assert occluded_ref(bvh, origin, -origin, 1e30, 1, True, 1)


def test_two_sided():
    tri = np.array([[(0, 0, 0), (1, 0, 0), (0, 1, 0)]], dtype=np.float32)
    flipped = tri[:, [0, 2, 1]]
    origin, direction = (0.25, 0.25, 1.0), (0.0, 0.0, -1.0)
    for t in (tri, flipped):
        bvh = build_bvh(t, make_info(1))
        assert occluded_ref(bvh, origin, direction, 1e30, 5, True, 1)
        assert brute_occluded(t, make_info(1), origin, direction, 1e30, 5, True, 1)
    assert not occluded_ref(bvh, origin, direction, 0.5, 5, True, 1)  # t_max stops short
    assert not occluded_ref(bvh, origin, (0.0, 0.0, 1.0), 1e30, 5, True, 1)  # behind the ray


def test_group_mask_and_self_id():
    tri = np.array([[(0, 0, 0), (1, 0, 0), (0, 1, 0)]], dtype=np.float32)
    origin, direction = (0.25, 0.25, 1.0), (0.0, 0.0, -1.0)
    bvh = build_bvh(tri, make_info(1, ids=7, mask=0b10))
    assert not occluded_ref(bvh, origin, direction, 1e30, 3, True, 0b01)
    assert occluded_ref(bvh, origin, direction, 1e30, 3, True, 0b10)
    assert occluded_ref(bvh, origin, direction, 1e30, 3, False, 0b10)
    assert not occluded_ref(bvh, origin, direction, 1e30, 7, False, 0b10)
    assert occluded_ref(bvh, origin, direction, 1e30, 7, True, 0b10)


def test_empty():
    bvh = build_bvh(np.zeros((0, 3, 3), dtype=np.float32), np.zeros((0, 2), dtype=np.uint32))
    assert bvh.nodes.shape == (1, 8)
    assert bvh.tris.shape == (0, 4, 4)
    assert bvh.info.shape == (0, 4)
    assert not occluded_ref(bvh, (0, 0, 1), (0, 0, -1), 1e30, 0, True, 1)


def test_depth_and_every_triangle_in_one_leaf():
    rng = np.random.default_rng(2)
    count = 3000
    tris = random_soup(rng, count)
    info = make_info(count)
    bvh = build_bvh(tris, info)
    assert bvh.depth <= 48
    nodes_u = bvh.nodes.view(np.uint32)
    first, num = nodes_u[:, 3], nodes_u[:, 7]
    leaves = num > 0
    assert num[leaves].max() <= 4
    covered = np.zeros(count, dtype=int)
    for a, b in zip(first[leaves], num[leaves]):
        covered[a:a + b] += 1
    assert np.all(covered == 1)
    # Triangle order = leaf order, and info follows the triangles
    expected = tris  # ids were arange: info[:, 0] is the original index
    assert np.array_equal(bvh.tris[:, :3, :3], expected[bvh.info[:, 0]])
    assert sorted(bvh.info[:, 0]) == list(range(count))
    # Inner nodes: left child is this + 1, right child index is larger; bounds contain children
    inner = np.flatnonzero(~leaves)
    for i in inner[:200]:
        left, right = i + 1, first[i]
        assert right > left
        for c in (left, right):
            assert np.all(bvh.nodes[c, 0:3] >= bvh.nodes[i, 0:3])
            assert np.all(bvh.nodes[c, 4:7] <= bvh.nodes[i, 4:7])


def test_degenerate_identical_triangles():
    tri = np.array([[(0, 0, 0), (1, 0, 0), (0, 1, 0)]] * 100, dtype=np.float32)
    bvh = build_bvh(tri, make_info(100))
    assert bvh.depth <= 48
    assert occluded_ref(bvh, (0.2, 0.2, 1), (0, 0, -1), 1e30, 999, True, 1)


def test_build_time_120k():
    rng = np.random.default_rng(3)
    tris = random_soup(rng, 120000, spread=50.0, size=0.5)
    info = make_info(120000)
    start = time.perf_counter()
    bvh = build_bvh(tris, info)
    elapsed = time.perf_counter() - start
    print('BUILD_TIME_120k_s=%.3f depth=%d nodes=%d' % (elapsed, bvh.depth, len(bvh.nodes)))
    assert bvh.depth <= 48
    assert elapsed < 30
