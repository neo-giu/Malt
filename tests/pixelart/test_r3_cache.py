import numpy as np

from Malt.Render.RayShadows import RayShadows


class FakeMesh():

    def __init__(self):
        self.cpu_positions = np.array([(0, 0, 0), (1, 0, 0), (0, 1, 0)], dtype=np.float32)
        self.cpu_indices = np.array([(0, 1, 2)], dtype=np.uint32)


class FakeMaterial():

    def __init__(self, groups=(1, 0, 0, 0)):
        self.parameters = {'Light Groups.Shadow': list(groups)}


class FakeObject():

    def __init__(self, matrix, mesh, material, id=1):
        self.matrix = matrix
        self.mesh = mesh
        self.material = material
        self.parameters = {'ID': id}


class FakeScene():

    def __init__(self, objects, frame=1):
        self.objects = objects
        self.frame = frame


def translation(x, y, z):
    # Column-major flat matrix, like Malt's Scene.Object.matrix
    return [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, x, y, z, 1]


def make():
    material = FakeMaterial()
    obj = FakeObject(translation(0, 0, 0), FakeMesh(), material)
    return RayShadows(gpu=False), FakeScene([obj]), {material: {}}, obj


def test_same_frame_builds_once():
    rs, scene, batches, obj = make()
    assert rs.update(scene, batches) is True
    assert rs.update(scene, batches) is False
    assert rs.build_count == 1


def test_moved_object_rebuilds():
    rs, scene, batches, obj = make()
    rs.update(scene, batches)
    obj.matrix = translation(0, 0, 3)
    assert rs.update(scene, batches) is True
    assert rs.build_count == 2
    assert rs.bvh.tris[0, 0, 2] == 3.0  # world-space triangle


def test_new_frame_rebuilds():
    rs, scene, batches, obj = make()
    rs.update(scene, batches)
    scene.frame = 2
    assert rs.update(scene, batches) is True


def test_no_opaque_objects_gives_empty_leaf():
    rs = RayShadows(gpu=False)
    assert rs.update(FakeScene([]), {}) is True
    assert rs.bvh.nodes.shape == (1, 8)
    assert len(rs.bvh.tris) == 0


def test_transparent_object_is_skipped():
    rs, scene, batches, obj = make()
    rs.update(FakeScene([obj]), {})
    assert len(rs.bvh.tris) == 0


def test_shadow_group_mask_and_id():
    rs = RayShadows(gpu=False)
    material = FakeMaterial((2, 3, 0, 0))
    obj = FakeObject(translation(0, 0, 0), FakeMesh(), material, id=7)
    rs.update(FakeScene([obj]), {material: {}})
    assert rs.bvh.info[0, 0] == 7
    assert rs.bvh.info[0, 1] == (1 << 2) | (1 << 3) | 1
