"""Setup functions for tools/pixelart/render_gui.py. Each takes the bpy scene and edits it IN MEMORY only (never saved).

box_plane, lit_sphere, cube_contact: replace the scene content with a test setup, Ray Traced Shadows on, Grid Size 1.
ray_traced, shadow_maps: keep the scene, only switch Ray Traced Shadows (Grid Size 1 for both, to compare like with like)."""
import math

import bpy


def _setup_malt_ids():
    # Objects, lights and meshes made by script get no Malt parameters (e.g. 'Light Group') until Malt sets them up
    from BlenderMalt.MaltPipeline import setup_all_ids
    setup_all_ids()


def _set_shadow_mode(scene, ray_traced):
    _setup_malt_ids()
    world = scene.world
    world.malt_parameters['Samples.Grid Size'] = 1
    tree = world.malt_parameters.graphs['Render'].graph
    found = False
    for node in tree.nodes:
        if 'Ray Traced Shadows' in node.inputs:
            key = node.inputs['Ray Traced Shadows'].get_source_global_reference().replace('"', '')
            tree.malt_parameters.bools[key].boolean = ray_traced
            found = True
    assert found, "no SceneLighting node with a Ray Traced Shadows input in the Render graph"


def ray_traced(scene):
    _set_shadow_mode(scene, True)


def shadow_maps(scene):
    _set_shadow_mode(scene, False)


def _clear(scene):
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def _add(scene, name, data):
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    return obj


def _mesh(name, vertices, faces):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    return mesh


def _quad(name, half):
    return _mesh(name, [(-half, -half, 0), (half, -half, 0), (half, half, 0), (-half, half, 0)], [(0, 1, 2, 3)])


def _cube(name, half):
    v = [(x * half, y * half, z * half) for z in (-1, 1) for y in (-1, 1) for x in (-1, 1)]
    f = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    return _mesh(name, v, f)


def _sphere(name, radius, rings=32, segments=64):
    v = [(0, 0, radius)]
    for i in range(1, rings):
        a = math.pi * i / rings
        for j in range(segments):
            b = 2 * math.pi * j / segments
            v.append((radius * math.sin(a) * math.cos(b), radius * math.sin(a) * math.sin(b), radius * math.cos(a)))
    v.append((0, 0, -radius))
    f = []
    for j in range(segments):
        f.append((0, 1 + j, 1 + (j + 1) % segments))
    for i in range(rings - 2):
        for j in range(segments):
            a = 1 + i * segments + j
            b = 1 + i * segments + (j + 1) % segments
            f.append((a, a + segments, b + segments, b))
    last = len(v) - 1
    for j in range(segments):
        f.append((last, last - segments + (j + 1) % segments, last - segments + j))
    return _mesh(name, v, f)


def _sun(scene, rotation_x_degrees, rotation_z_degrees=0.0):
    data = bpy.data.lights.new('Sun', 'SUN')
    data.energy = 3.0
    sun = _add(scene, 'Sun', data)
    sun.rotation_euler = (math.radians(rotation_x_degrees), 0, math.radians(rotation_z_degrees))
    return sun


def _camera(scene, location, rotation_degrees, ortho_scale=None, lens=50.0):
    data = bpy.data.cameras.new('Camera')
    if ortho_scale:
        data.type = 'ORTHO'
        data.ortho_scale = ortho_scale
    else:
        data.lens = lens
    camera = _add(scene, 'Camera', data)
    camera.location = location
    camera.rotation_euler = [math.radians(a) for a in rotation_degrees]
    scene.camera = camera
    return camera


def _square_render(scene, size=360):
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    scene.render.resolution_percentage = 100


def box_plane(scene):
    # Top-down orthographic camera, 4 m over 360 px (90 px/m). Caster: 1 m quad at z=1, sun tilted 30 degrees around X
    # (light travels towards +y), so on the ground the shadow is the caster shifted by tan(30) m along +y.
    _clear(scene)
    _square_render(scene)
    _add(scene, 'Ground', _quad('Ground', 10.0))
    caster = _add(scene, 'Caster', _quad('Caster', 0.5))
    caster.location = (0, 0, 1)
    _sun(scene, 30)
    _camera(scene, (0, 0, 10), (0, 0, 0), ortho_scale=4.0)
    ray_traced(scene)


def lit_sphere(scene):
    # A sphere alone: the only shadow it can receive is its own, so any shadowed lit-side pixel is acne.
    _clear(scene)
    _square_render(scene)
    sphere = _add(scene, 'Sphere', _sphere('Sphere', 1.0))
    sphere.location = (0, 0, 0)
    _sun(scene, 90, 90)  # light travels towards -x: the right half (x > 0) is lit, the terminator is the plane x = 0
    _camera(scene, (0, -6, 2), (90 - math.degrees(math.atan2(2, 6)), 0, 0), ortho_scale=None, lens=60.0)
    ray_traced(scene)


def cube_contact(scene):
    # 1 m cube resting on a plane, top-down orthographic, sun tilted 30 degrees around X: the shadow starts at the
    # cube's +y edge (y=0.5) and must have no lit row between the cube and the shadow.
    _clear(scene)
    _square_render(scene)
    _add(scene, 'Ground', _quad('Ground', 10.0))
    cube = _add(scene, 'Cube', _cube('Cube', 0.5))
    cube.location = (0, 0, 0.5)
    _sun(scene, 30)
    _camera(scene, (0, 0, 10), (0, 0, 0), ortho_scale=4.0)
    ray_traced(scene)


def lit_sphere_maps(scene):
    # lit_sphere with shadow maps, as the reference for the ray traced one
    lit_sphere(scene)
    shadow_maps(scene)


def _no_subdivision(scene):
    # In memory only: turn off every Subdivision Surface modifier (low-poly shadow terminator test)
    for obj in scene.objects:
        for modifier in obj.modifiers:
            if modifier.type == 'SUBSURF':
                modifier.show_viewport = False
                modifier.show_render = False


def ray_traced_nosubd(scene):
    _no_subdivision(scene)
    ray_traced(scene)


def shadow_maps_nosubd(scene):
    _no_subdivision(scene)
    shadow_maps(scene)


def _subdivision_level(scene, level):
    for obj in scene.objects:
        for modifier in obj.modifiers:
            if modifier.type == 'SUBSURF':
                modifier.levels = level
                modifier.render_levels = level


def ray_traced_subd1(scene):
    _subdivision_level(scene, 1)
    ray_traced(scene)


def shadow_maps_subd1(scene):
    _subdivision_level(scene, 1)
    shadow_maps(scene)


def ray_traced_subd4(scene):
    _subdivision_level(scene, 4)
    ray_traced(scene)


def shadow_maps_subd4(scene):
    _subdivision_level(scene, 4)
    shadow_maps(scene)


def _set_node_input(scene, name, value):
    tree = scene.world.malt_parameters.graphs['Render'].graph
    for node in tree.nodes:
        if name in node.inputs:
            key = node.inputs[name].get_source_global_reference().replace('"', '')
            tree.malt_parameters[key] = value


def ray_traced_subd1_noshadow(scene):
    # Diagnostic: a huge bias moves every ray origin far off the surface, so (almost) nothing is shadowed.
    # Shows what the ramp alone draws.
    _subdivision_level(scene, 1)
    ray_traced(scene)
    _set_node_input(scene, 'Ray Bias (px)', 100000.0)


def ray_traced_subd4_noshadow(scene):
    _subdivision_level(scene, 4)
    ray_traced(scene)
    _set_node_input(scene, 'Ray Bias (px)', 100000.0)


def ray_traced_subd1_flatshadow(scene):
    # Shadow geometry = the triangles as they are (no Phong tessellation), to compare with the default 2 levels
    _subdivision_level(scene, 1)
    ray_traced(scene)
    _set_node_input(scene, 'Ray Smooth Levels', 0)
