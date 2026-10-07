import numpy as np

from Malt.Render.RayGeometry import mesh_triangles


class FakeMesh():

    def __init__(self, positions, indices):
        self.cpu_positions = np.array(positions, dtype=np.float32).reshape(-1, 3)
        self.cpu_indices = np.array(indices, dtype=np.uint32).reshape(-1, 3)


def test_unit_quad_vertices_in_order():
    mesh = FakeMesh([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [(0, 1, 2), (0, 2, 3)])
    tris = mesh_triangles(mesh)
    assert tris.shape == (2, 3, 3)
    assert tris.dtype == np.float32
    expected = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 0, 0), (1, 1, 0), (0, 1, 0)]
    assert np.array_equal(tris.reshape(-1, 3), np.array(expected, dtype=np.float32))


def test_empty_mesh():
    mesh = FakeMesh([], [])
    tris = mesh_triangles(mesh)
    assert tris.shape == (0, 3, 3)
    assert tris.dtype == np.float32
