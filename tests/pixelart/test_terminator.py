import numpy as np

from Malt.Render.RayGeometry import smooth_surface_point, mesh_triangle_normals, phong_tessellate
from Malt.Render import RayBVH
from Malt.Render.RayShadows import RayShadows

TRI = np.array([(0, 0, 0), (1, 0, 0), (0, 1, 0)], dtype=np.float64)


def point(b):
    return np.asarray(b) @ TRI


def test_flat_normals_keep_the_point():
    normals = np.tile((0, 0, 1.0), (3, 1))
    for b in [(1, 0, 0), (0.2, 0.3, 0.5), (1 / 3, 1 / 3, 1 / 3)]:
        assert np.allclose(smooth_surface_point(point(b), TRI, normals, b), point(b))


def test_vertices_stay_put():
    # At a vertex the point is on that vertex's tangent plane: no offset
    normals = np.array([(-1, -1, 1), (1, 0, 1), (0, 1, 1)], dtype=np.float64)
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    for i in range(3):
        b = np.eye(3)[i]
        assert np.allclose(smooth_surface_point(TRI[i], TRI, normals, b), TRI[i])


def test_convex_normals_lift_the_inside_outwards():
    # Normals tilted away from the centre (a convex patch, like a low-poly sphere): the centre moves up (+z)
    centre = TRI.mean(axis=0)
    normals = TRI - centre + (0, 0, 1.0)
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    lifted = smooth_surface_point(centre, TRI, normals, (1 / 3, 1 / 3, 1 / 3))
    assert lifted[2] > 1e-3


def test_continuous_across_a_shared_edge():
    # Two triangles sharing the edge (1,0,0)-(0,1,0) with shared vertex normals give the same point on that edge
    a = TRI
    b = np.array([(1, 0, 0), (1, 1, 0.2), (0, 1, 0)], dtype=np.float64)
    n = {(1, 0, 0): (0.3, -0.2, 1), (0, 1, 0): (-0.2, 0.3, 1), (0, 0, 0): (-0.5, -0.5, 1), (1, 1, 0.2): (0.4, 0.4, 1)}
    na = np.array([n[tuple(v)] for v in a], dtype=np.float64)
    nb = np.array([n[tuple(v)] for v in b], dtype=np.float64)
    na /= np.linalg.norm(na, axis=1, keepdims=True)
    nb /= np.linalg.norm(nb, axis=1, keepdims=True)
    for s in (0.1, 0.5, 0.8):
        p = (1 - s) * a[1] + s * a[2]
        pa = smooth_surface_point(p, a, na, (0, 1 - s, s))
        pb = smooth_surface_point(p, b, nb, (1 - s, 0, s))
        assert np.allclose(pa, pb)


class Mesh():

    def __init__(self):
        self.cpu_positions = np.array([(0, 0, 0), (1, 0, 0), (0, 1, 0), (5, 5, 0), (6, 5, 0), (5, 6, 0)], dtype=np.float32)
        self.cpu_indices = np.array([(0, 1, 2), (3, 4, 5)], dtype=np.uint32)
        n = np.array([(0, 0, 1), (0, 1, 1), (1, 0, 1), (0, 0, -1), (0, -1, -1), (-1, 0, -1)], dtype=np.float32)
        self.cpu_normals = n / np.linalg.norm(n, axis=1, keepdims=True)


class Material():
    parameters = {'Light Groups.Shadow': [1, 0, 0, 0]}


class Obj():

    def __init__(self, matrix):
        self.matrix = matrix
        self.mesh = Mesh()
        self.material = Material()
        self.parameters = {'ID': 7}


class Scene():

    def __init__(self, objects):
        self.objects = objects
        self.frame = 1


def test_normals_follow_the_bvh_leaf_order_and_the_object_matrix():
    # Non-uniform scale (x2 in x): normals use the inverse transpose
    matrix = [2, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 3, 0, 0, 1]
    obj = Obj(matrix)
    rs = RayShadows(gpu=False)
    rs.smooth_levels = 0
    rs.update(Scene([obj]), {obj.material: None})
    local_normals = mesh_triangle_normals(obj.mesh)
    expected = local_normals @ np.linalg.inv(np.diag([2.0, 1, 1])).T
    expected /= np.linalg.norm(expected, axis=2, keepdims=True)
    for out_index, in_index in enumerate(rs.bvh.order):
        assert np.allclose(rs.normals[out_index, :, :3], expected[in_index], atol=1e-6)
    assert np.allclose(rs.normals[:, :, 3], 0)


def test_mesh_without_normals_gets_face_normals():
    mesh = Mesh()
    del mesh.cpu_normals
    n = mesh_triangle_normals(mesh)
    assert np.allclose(n[0], [(0, 0, 1)] * 3)


def test_tessellation_of_flat_normals_stays_flat_and_counts_4_per_level():
    normals = np.tile((0, 0, 1.0), (1, 3, 1))
    out, out_n = phong_tessellate(TRI[None], normals, 2)
    assert out.shape == (16, 3, 3) and out_n.shape == (16, 3, 3)
    assert np.allclose(out[..., 2], 0)
    area = 0.5 * np.linalg.norm(np.cross(out[:, 1] - out[:, 0], out[:, 2] - out[:, 0]), axis=1)
    assert np.isclose(area.sum(), 0.5)


def _icosahedron_with_normals():
    t = (1 + 5 ** 0.5) / 2
    v = np.array([(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
                  (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)], dtype=np.float64)
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
         (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10),
         (8, 6, 7), (9, 8, 1)]
    tris = v[np.array(f)]
    return tris, tris.copy()  # unit sphere: vertex normal = vertex position


def test_tessellated_sphere_is_closer_to_the_sphere_and_watertight():
    tris, normals = _icosahedron_with_normals()
    out, _ = phong_tessellate(tris, normals, 2)
    centres = out.mean(axis=1)
    flat_centres = tris.mean(axis=1)
    # The smooth surface bulges out towards the sphere
    assert np.linalg.norm(centres, axis=1).mean() > np.linalg.norm(flat_centres, axis=1).mean() + 0.02
    # Shared edges give bitwise identical vertices: every output vertex position appears in >= 2 triangles,
    # and rays from the centre outwards always hit
    verts = {tuple(p) for p in out.reshape(-1, 3).tolist()}
    assert len(verts) == 10 * 16 + 2
    info = np.tile((1, 1), (len(out), 1)).astype(np.uint32)
    bvh = RayBVH.build_bvh(out, info)
    rng = np.random.default_rng(1)
    targets = np.concatenate([out.reshape(-1, 3), rng.normal(size=(300, 3))])
    for d in targets:
        assert RayBVH.occluded_ref(bvh, np.zeros(3, dtype=np.float32), d.astype(np.float32), 1e30, 0, True, 1)
