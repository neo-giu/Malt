# Per-frame world-space BVH of the opaque shadow casters, uploaded to 3 SSBOs for Shaders/Lighting/RayShadows.glsl.
# OpenGL is only imported when gpu=True, so the cache logic can be tested outside Blender.

import time

import numpy as np

from Malt.Render import RayBVH
from Malt.Render.RayGeometry import mesh_triangles, mesh_triangle_normals, phong_tessellate

# SSBO bindings, fixed (must match RayShadows.glsl)
BINDING_NODES = 0
BINDING_TRIANGLES = 1
BINDING_INFO = 2
BINDING_NORMALS = 3


def shadow_group_mask(groups):
    mask = 0
    for group in groups:
        if 0 <= group < 32:
            mask |= 1 << int(group)
    return mask


class RayShadows():

    def __init__(self, gpu=True):
        self.gpu = gpu
        self.enabled = False
        self.bias_px = 1.0
        self.smooth_levels = 0
        self.bvh = None
        self.key = None
        self.build_count = 0
        self.build_ms = 0.0
        self.triangle_count = 0
        self.normals = np.zeros((0, 3, 4), dtype=np.float32)
        self.ssbos = None

    def update(self, scene, opaque_batches):
        # Returns True when the BVH was rebuilt
        objects = []
        meshes = []
        for obj in scene.objects:
            if obj.material and obj.material in opaque_batches and obj.mesh is not None:
                # Scene.Mesh wraps the GL mesh (MeshCustomLoad), which holds the CPU copies
                mesh = getattr(obj.mesh, 'mesh', obj.mesh)
                if hasattr(mesh, 'cpu_positions') and hasattr(mesh, 'cpu_indices'):
                    objects.append(obj)
                    meshes.append(mesh)

        matrices = [np.asarray(obj.matrix, dtype=np.float32).reshape(4, 4) for obj in objects]
        groups = [shadow_group_mask(obj.material.parameters['Light Groups.Shadow']) for obj in objects]
        key = (
            scene.frame,
            tuple(m.tobytes() for m in matrices),
            tuple((id(mesh), id(mesh.cpu_positions), id(mesh.cpu_indices), id(getattr(mesh, 'cpu_normals', None))) for mesh in meshes),
            tuple(obj.parameters['ID'] for obj in objects),
            tuple(groups),
            self.smooth_levels,
        )
        if key == self.key:
            return False

        start = time.perf_counter()
        tris = []
        info = []
        normals = []
        for obj, mesh, matrix, mask in zip(objects, meshes, matrices, groups):
            local = mesh_triangles(mesh)
            if len(local) == 0:
                continue
            # Malt matrices are column-major, so the reshaped array is the transposed matrix
            world = (local @ matrix[:3, :3] + matrix[3, :3]).astype(np.float32)
            # Normals transform by the inverse transpose (row vectors: n @ inv(M3).T)
            try:
                normal_matrix = np.linalg.inv(matrix[:3, :3].astype(np.float64)).T
            except np.linalg.LinAlgError:
                normal_matrix = np.eye(3)
            world_normals = mesh_triangle_normals(mesh) @ normal_matrix
            world_normals /= np.maximum(np.linalg.norm(world_normals, axis=2, keepdims=True), 1e-30)
            world_tris, world_normals = phong_tessellate(world, world_normals, self.smooth_levels)
            tris.append(world_tris)
            normals.append(world_normals)
            info.append(np.tile(np.array([obj.parameters['ID'], mask], dtype=np.uint32), (len(world_tris), 1)))
        if tris:
            tris = np.concatenate(tris)
            info = np.concatenate(info)
            normals = np.concatenate(normals)
        else:
            tris = np.zeros((0, 3, 3), dtype=np.float32)
            info = np.zeros((0, 2), dtype=np.uint32)
            normals = np.zeros((0, 3, 3), dtype=np.float32)

        self.bvh = RayBVH.build_bvh(tris, info)
        # Vertex normals in leaf order, vec4 each (std430), for the smooth-surface ray origin
        self.normals = np.zeros((len(tris), 3, 4), dtype=np.float32)
        if len(tris):
            self.normals[:, :, :3] = normals[self.bvh.order]
        self.key = key
        self.build_count += 1
        self.triangle_count = len(tris)
        if self.gpu:
            self._upload(self.bvh)
        self.build_ms = (time.perf_counter() - start) * 1000.0
        print("RAY_SHADOWS build: %d triangles, depth %d, %.1f ms" % (self.triangle_count, self.bvh.depth, self.build_ms), flush=True)
        return True

    def _upload(self, bvh):
        if self.ssbos is None:
            from Malt.GL.Shader import SSBO
            self.ssbos = [SSBO(), SSBO(), SSBO(), SSBO()]
        # Never upload a zero sized buffer
        tris = bvh.tris if len(bvh.tris) > 0 else np.zeros((1, 4, 4), dtype=np.float32)
        info = bvh.info if len(bvh.info) > 0 else np.zeros((1, 4), dtype=np.uint32)
        normals = self.normals if len(self.normals) > 0 else np.zeros((1, 3, 4), dtype=np.float32)
        self.ssbos[0].load_array(np.ascontiguousarray(bvh.nodes))
        self.ssbos[1].load_array(np.ascontiguousarray(tris))
        self.ssbos[2].load_array(np.ascontiguousarray(info))
        self.ssbos[3].load_array(np.ascontiguousarray(normals))

    def shader_callback(self, shader):
        if 'RAY_SHADOWS' in shader.uniforms:
            shader.uniforms['RAY_SHADOWS'].set_value(1 if self.enabled else 0)
        if 'RAY_BIAS_PX' in shader.uniforms:
            shader.uniforms['RAY_BIAS_PX'].set_value(float(self.bias_px))
        if self.gpu and self.enabled and self.ssbos:
            for binding, ssbo in zip((BINDING_NODES, BINDING_TRIANGLES, BINDING_INFO, BINDING_NORMALS), self.ssbos):
                ssbo.bind(binding)
