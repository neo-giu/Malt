# Pure numpy helpers for ray traced shadows. Must not import OpenGL or other Malt GL modules.

import numpy as np


def mesh_triangles(mesh):
    # Returns the (T, 3, 3) float32 triangle vertices of a mesh with cpu_positions and cpu_indices
    positions = np.asarray(mesh.cpu_positions, dtype=np.float32).reshape(-1, 3)
    indices = np.asarray(mesh.cpu_indices).reshape(-1, 3)
    if len(indices) == 0:
        return np.zeros((0, 3, 3), dtype=np.float32)
    return positions[indices]
