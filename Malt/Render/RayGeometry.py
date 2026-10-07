# Pure numpy helpers for ray traced shadows. Must not import OpenGL or other Malt GL modules.

import numpy as np


def mesh_triangles(mesh):
    # Returns the (T, 3, 3) float32 triangle vertices of a mesh with cpu_positions and cpu_indices
    positions = np.asarray(mesh.cpu_positions, dtype=np.float32).reshape(-1, 3)
    indices = np.asarray(mesh.cpu_indices).reshape(-1, 3)
    if len(indices) == 0:
        return np.zeros((0, 3, 3), dtype=np.float32)
    return positions[indices]


def mesh_triangle_normals(mesh):
    # Returns the (T, 3, 3) float32 vertex normals of each triangle (same order as mesh_triangles).
    # Meshes without cpu_normals get their flat face normal on all 3 vertices (no smooth-surface offset).
    indices = np.asarray(mesh.cpu_indices).reshape(-1, 3)
    if len(indices) == 0:
        return np.zeros((0, 3, 3), dtype=np.float32)
    normals = getattr(mesh, 'cpu_normals', None)
    if normals is not None:
        normals = np.asarray(normals, dtype=np.float32).reshape(-1, 3)
        if len(normals) == len(np.asarray(mesh.cpu_positions).reshape(-1, 3)):
            return normals[indices]
    tris = mesh_triangles(mesh)
    face = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    face /= np.maximum(np.linalg.norm(face, axis=1, keepdims=True), 1e-30)
    return np.repeat(face[:, None, :], 3, axis=1).astype(np.float32)


def smooth_surface_point(P, tri, normals, barycentric):
    # Shadow terminator fix (Hanika 2021). P on the flat triangle tri (3, 3), vertex normals (3, 3), barycentric (3,):
    # P' = P - sum(b_i * min(0, dot(P - V_i, n_i)) * n_i). Same as smooth_surface_point in RayShadows.glsl.
    P = np.asarray(P, dtype=np.float64)
    offset = np.zeros(3)
    for v, n, b in zip(np.asarray(tri, dtype=np.float64), np.asarray(normals, dtype=np.float64), barycentric):
        offset += b * min(0.0, float(np.dot(P - v, n))) * n
    return P - offset


def phong_tessellate(tris, normals, levels, alpha=0.75):
    # Splits each triangle into 4**levels and moves the new vertices onto the Phong tessellation surface
    # (Boubekeur and Alexa 2008) of its vertex normals, so shadow rays see a smooth surface, not the facets.
    # tris, normals: (T, 3, 3). Returns (T * 4**levels, 3, 3) triangles and their interpolated vertex normals.
    # float64 inside, one rounding to float32 at the end: the points of a shared edge only depend on its 2 vertices,
    # so both triangles get the same float32 vertices there (no cracks for the watertight test)
    if levels <= 0 or len(tris) == 0:
        return np.asarray(tris, dtype=np.float32).reshape(-1, 3, 3), np.asarray(normals, dtype=np.float32).reshape(-1, 3, 3)
    tris = np.asarray(tris, dtype=np.float64).reshape(-1, 3, 3)
    normals = np.asarray(normals, dtype=np.float64).reshape(-1, 3, 3)
    n = 2 ** int(levels)
    # Barycentric grid points (i, j) with i + j <= n, and the sub-triangles over them
    index = {}
    bary = []
    for i in range(n + 1):
        for j in range(n + 1 - i):
            index[(i, j)] = len(bary)
            bary.append(((n - i - j) / n, i / n, j / n))
    bary = np.array(bary, dtype=np.float64)
    sub = []
    for i in range(n):
        for j in range(n - i):
            sub.append((index[(i, j)], index[(i + 1, j)], index[(i, j + 1)]))
            if i + j < n - 1:
                sub.append((index[(i + 1, j)], index[(i + 1, j + 1)], index[(i, j + 1)]))
    sub = np.array(sub)

    # (T, P, 3) flat points and interpolated normals
    flat = np.einsum('pk,tkc->tpc', bary, tris)
    normal = np.einsum('pk,tkc->tpc', bary, normals)
    normal /= np.maximum(np.linalg.norm(normal, axis=2, keepdims=True), 1e-30)
    # Phong: average of the projections of the flat point onto the 3 vertex tangent planes
    projected = np.zeros_like(flat)
    for k in range(3):
        v = tris[:, k][:, None, :]
        nk = normals[:, k][:, None, :]
        d = np.sum((flat - v) * nk, axis=2, keepdims=True)
        projected += bary[None, :, k:k + 1] * (flat - d * nk)
    points = (1.0 - alpha) * flat + alpha * projected

    out_tris = points[:, sub].reshape(-1, 3, 3)
    out_normals = normal[:, sub].reshape(-1, 3, 3)
    return out_tris.astype(np.float32), out_normals.astype(np.float32)
