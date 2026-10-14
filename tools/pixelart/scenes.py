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


def box_plane(scene, sun_degrees=30):
    # Top-down orthographic camera, 4 m over 360 px (90 px/m). Caster: 1 m quad at z=1, sun tilted 30 degrees around X
    # (light travels towards +y), so on the ground the shadow is the caster shifted by tan(30) m along +y.
    _clear(scene)
    _square_render(scene)
    _add(scene, 'Ground', _quad('Ground', 10.0))
    caster = _add(scene, 'Caster', _quad('Caster', 0.5))
    caster.location = (0, 0, 1)
    _sun(scene, sun_degrees)
    _camera(scene, (0, 0, 10), (0, 0, 0), ortho_scale=4.0)
    ray_traced(scene)


def box_plane_60(scene):
    box_plane(scene, 60)


def box_plane_80(scene):
    box_plane(scene, 80)


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


# --- Diagnosis (handoff Step 1) ---------------------------------------------------------------------------------------

def _debug_material(scene):
    # In memory: every mesh slot gets the ray_debug.mesh.glsl material (R = N.L > 0, G = shadowed, B = origin search)
    import os
    material = bpy.data.materials.new('RayDebug')
    material.malt.material_type = 'Mesh'
    material.malt.shader_source = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ray_debug.mesh.glsl')
    for obj in scene.objects:
        if obj.type == 'MESH':
            if len(obj.material_slots) == 0:
                obj.data.materials.append(material)
            for slot in obj.material_slots:
                slot.link = 'OBJECT'
                slot.material = material
    _setup_malt_ids()
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0


def ray_debug_subd4(scene):
    _subdivision_level(scene, 4)
    ray_traced(scene)
    _debug_material(scene)


def maps_debug_subd4(scene):
    _subdivision_level(scene, 4)
    shadow_maps(scene)
    _debug_material(scene)


def cycles_truth_subd4(scene):
    _subdivision_level(scene, 4)
    cycles_truth(scene)


def cycles_truth_subd1(scene):
    _subdivision_level(scene, 1)
    cycles_truth(scene)


def ray_debug_subd1(scene):
    _subdivision_level(scene, 1)
    ray_traced(scene)
    _debug_material(scene)


def ray_debug(scene):
    # The file's own subdivision levels
    ray_traced(scene)
    _debug_material(scene)


def cycles_truth(scene):
    # Ground truth: Cycles, hard sun (angle 0), direct light only, all samples at the pixel centre (filter 0.01 px).
    # White = lit (smooth N.L > 0 and not shadowed), black = not lit.
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 4
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.use_denoising = False
    scene.cycles.max_bounces = 0
    scene.cycles.filter_width = 0.01
    scene.cycles.pixel_filter_type = 'BOX'
    scene.render.film_transparent = True  # alpha = coverage
    world = bpy.data.worlds.new('Black')
    try:
        world.use_nodes = True
    except Exception:
        pass
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.0
    scene.world = world
    material = bpy.data.materials.new('Truth')
    try:
        material.use_nodes = True
    except Exception:
        pass
    for obj in scene.objects:
        if obj.type == 'MESH':
            if len(obj.material_slots) == 0:
                obj.data.materials.append(material)
            for slot in obj.material_slots:
                slot.link = 'OBJECT'
                slot.material = material
        if obj.type == 'LIGHT':
            if obj.data.type == 'SUN':
                obj.data.angle = 0.0
                obj.data.energy = 10.0
            else:
                obj.hide_render = True
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'


# --- Line probe (Pixel Cel plan, task 1) -------------------------------------------------------------------------------

def _set_line_width(scene, width):
    # In memory: every Line Width (line_width_2) node of every Malt mesh tree gets width_scale = width, Pixel units
    for tree in bpy.data.node_groups:
        if tree.bl_idname != 'MaltTree':
            continue
        for node in tree.nodes:
            if getattr(node, 'function_type', '').endswith('line_width_2'):
                key = node.inputs['width_scale'].get_source_global_reference().replace('"', '')
                tree.malt_parameters[key] = float(width)
                # Materials keep their own copy of the tree parameters (the material panel values)
                for material in bpy.data.materials:
                    if material.malt.shader_nodes is tree and key in material.malt_parameters.keys():
                        material.malt_parameters[key] = float(width)




def _frame_objects(scene, objects, height_px=256, margin=0.05):
    # In memory: a new orthographic front camera (looking along +Y) framing the world bounding box of objects.
    # Resolution: height_px tall, width from the box aspect (even number of pixels).
    import mathutils
    points = []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        points += [evaluated.matrix_world @ mathutils.Vector(corner) for corner in evaluated.bound_box]
    xs, ys, zs = [p.x for p in points], [p.y for p in points], [p.z for p in points]
    width, height = max(xs) - min(xs), max(zs) - min(zs)
    height_world = max(height, 1e-6) * (1.0 + 2.0 * margin)
    width_world = max(width, 1e-6) * (1.0 + 2.0 * margin)
    width_px = max(2, int(math.ceil(height_px * width_world / height_world / 2.0)) * 2)
    scene.render.resolution_x = width_px
    scene.render.resolution_y = height_px
    scene.render.resolution_percentage = 100
    center = ((max(xs) + min(xs)) / 2, min(ys) - 10.0, (max(zs) + min(zs)) / 2)
    camera = _camera(scene, center, (90, 0, 0), ortho_scale=max(height_world, width_world))
    camera.data.sensor_fit = 'AUTO'
    camera.data.clip_end = 1000.0
    return camera


def _solo(scene, objects):
    # In memory: hide every other mesh object from the render
    keep = set(o.name for o in objects)
    for obj in scene.objects:
        if obj.type == 'MESH' and obj.name not in keep:
            obj.hide_render = True
    # The kept objects' collections (and their parents) must render
    parents = {child.name: coll for coll in bpy.data.collections for child in coll.children}
    for obj in objects:
        obj.hide_render = False
        for coll in obj.users_collection:
            while coll is not None:
                coll.hide_render = False
                coll = parents.get(coll.name)


def _collection_objects(name):
    collection = bpy.data.collections[name]
    return [obj for obj in collection.all_objects if obj.type == 'MESH']


def lines_w1(scene):
    ray_traced(scene)
    _solo(scene, [bpy.data.objects['Suzanne']])
    _frame_objects(scene, [bpy.data.objects['Suzanne']], 256)
    _set_line_width(scene, 1.0)


def lines_off(scene):
    ray_traced(scene)
    _solo(scene, [bpy.data.objects['Suzanne']])
    _frame_objects(scene, [bpy.data.objects['Suzanne']], 256)
    _set_line_width(scene, 0.0)


def _debug_shader(scene, filename):
    import os
    material = bpy.data.materials.new('PixelCelDebug')
    material.malt.material_type = 'Mesh'
    material.malt.shader_source = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    for obj in scene.objects:
        if obj.type == 'MESH':
            if len(obj.material_slots) == 0:
                obj.data.materials.append(material)
            for slot in obj.material_slots:
                slot.link = 'OBJECT'
                slot.material = material
    _setup_malt_ids()
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0


def pixel_cel_debug(scene):
    # Suzanne alone, 256 px, ray traced shadows, the pixel_cel debug material
    ray_traced(scene)
    suzanne = [bpy.data.objects['Suzanne']]
    _solo(scene, suzanne)
    _frame_objects(scene, suzanne, 256)
    _debug_shader(scene, 'pixel_cel_debug.mesh.glsl')


def _convert_all(scene, preset):
    from BlenderMalt import PixelArtConvert
    _setup_malt_ids()
    report = PixelArtConvert.convert_objects([o for o in scene.objects if o.type == 'MESH'], preset)
    print('PIXEL_CEL_REPORT', report, flush=True)
    return report


def pixel_cel_convert_asw(scene):
    ray_traced(scene)
    april = _collection_objects('GGXRD')
    _solo(scene, april)
    _frame_objects(scene, april, 256)
    _convert_all(scene, 'ASW')


def pixel_cel_convert_kof(scene):
    ray_traced(scene)
    april = _collection_objects('GGXRD')
    _solo(scene, april)
    _frame_objects(scene, april, 256)
    _convert_all(scene, 'KOF XIII')


def pixel_cel_convert_arthur(scene):
    ray_traced(scene)
    arthur = _collection_objects('arthurmodel')
    _solo(scene, arthur)
    _frame_objects(scene, arthur, 256)
    _convert_all(scene, 'ASW')


def pixel_cel_convert_dude(scene):
    ray_traced(scene)
    dude = _collection_objects('Dudemodel')
    _solo(scene, dude)
    _frame_objects(scene, dude, 256)
    _convert_all(scene, 'ASW')


def pixel_cel_reconvert(scene):
    # Convert, hand-edit one input, add a node, reconvert: the edit and the node must survive; originals unchanged
    from BlenderMalt import PixelArtConvert
    ray_traced(scene)
    april = _collection_objects('GGXRD')
    _solo(scene, april)
    _frame_objects(scene, april, 256)
    materials = {s.material for o in april for s in o.material_slots if s.material}
    before = {m.name: PixelArtConvert.original_hash(m) for m in materials}
    _convert_all(scene, 'ASW')
    tree = bpy.data.materials['5_body_1_0_0.001'].malt.shader_nodes
    cel = next(n for n in tree.nodes if getattr(n, 'function_type', '').endswith('pixel_cel'))
    key = cel.inputs['threshold'].get_source_global_reference().replace('"', '')
    tree.malt_parameters[key] = 0.3
    tree.nodes.new('MaltFunctionNode').name = 'HandAdded'
    _convert_all(scene, 'ASW')
    assert abs(tree.malt_parameters[key] - 0.3) < 1e-6, 'hand edit lost'
    assert 'HandAdded' in tree.nodes, 'hand node lost'
    after = {m.name: PixelArtConvert.original_hash(m) for m in materials}
    assert before == after, 'original material nodes changed'
    shared = {m.malt.shader_nodes.name for m in materials if m.name.startswith('5_') and 'eyeshine' not in m.name}
    assert len(shared) == 1, f'expected one shared tree, got {shared}'
    print('RECONVERT_OK', flush=True)


def pixel_cel_copy_collection(scene):
    from BlenderMalt import PixelArtConvert
    ray_traced(scene)
    source = bpy.data.collections['GGXRD']
    copy = PixelArtConvert.copy_collection(source, 'KOF')
    april = _collection_objects('GGXRD')
    kof = [o for o in copy.all_objects if o.type == 'MESH']
    PixelArtConvert.convert_objects(april, 'ASW')
    PixelArtConvert.convert_objects(kof, 'KOF XIII')
    assert all(o.data is bpy.data.objects[o.name.rsplit('.KOF', 1)[0]].data for o in kof), 'mesh data must be shared'
    _solo(scene, april + kof)
    _frame_objects(scene, april + kof, 256)
    print('COPY_OK', flush=True)


# --- Pixel Lines (Pixel Cel plan, task 7) ------------------------------------------------------------------------------

def _use_pixel_lines(scene, enabled):
    # In memory: in every Render Layer graph, route the main pass through PixelLines instead of LineRender.
    # Off also sets the converted trees' Line Width to 0, so the 'off' render has no lines at all (the line mask is on - off).
    from BlenderMalt import PixelArtConvert
    assert PixelArtConvert.setup_pixel_lines(scene, enabled), 'no Render Layer graph with LineRender/MainPass/PrePass'
    if enabled:
        return
    count = 0
    for tree in bpy.data.node_groups:
        if tree.bl_idname != 'MaltTree' or 'pixel_cel_set' not in tree.keys():
            continue
        main = next(n for n in tree.nodes if n.bl_idname == 'MaltIONode' and n.is_output
                    and n.io_type == 'MAIN_PASS_PIXEL_SHADER')
        key = main.inputs['Line Width'].get_source_global_reference().replace('"', '')
        tree.malt_parameters[key] = 0.0
        count += 1
        for material in bpy.data.materials:
            if material.malt.shader_nodes is tree and key in material.malt_parameters.keys():
                material.malt_parameters[key] = 0.0
    print('LINE_WIDTH_ZEROED trees', count, flush=True)


def pixel_lines_on(scene):
    ray_traced(scene)
    april = _collection_objects('GGXRD')
    _solo(scene, april)
    _frame_objects(scene, april, 256)
    _convert_all(scene, 'ASW')
    _use_pixel_lines(scene, True)


def pixel_lines_off(scene):
    ray_traced(scene)
    april = _collection_objects('GGXRD')
    _solo(scene, april)
    _frame_objects(scene, april, 256)
    _convert_all(scene, 'ASW')
    _use_pixel_lines(scene, False)


def pixel_lines_border(scene, enabled=True):
    # Review focus 5: the character cut by the frame border and two characters overlapping
    ray_traced(scene)
    april = _collection_objects('GGXRD')
    arthur = _collection_objects('arthurmodel')
    _solo(scene, april + arthur)
    camera = _frame_objects(scene, april, 256)
    camera.data.ortho_scale *= 0.6  # cut at the border
    _convert_all(scene, 'ASW')
    _use_pixel_lines(scene, enabled)


def pixel_lines_border_off(scene):
    pixel_lines_border(scene, False)


# --- Both styles (Pixel Cel plan, task 8) ------------------------------------------------------------------------------

def pixel_cel_both_styles(scene, enabled=True):
    from BlenderMalt import PixelArtConvert
    ray_traced(scene)
    copy = PixelArtConvert.copy_collection(bpy.data.collections['GGXRD'], 'KOF')
    scene.frame_set(scene.frame_current)
    roots = [o for o in copy.all_objects if o.parent is None]
    # The copy must stay beside the original after frame_set (an action keys the armature location)
    print('COPY_OFFSET', sorted({round(o.matrix_world.translation.x - bpy.data.objects[o.name.rsplit('.KOF', 1)[0]]
                                     .matrix_world.translation.x, 3) for o in roots}), flush=True)
    april = _collection_objects('GGXRD')
    kof = [o for o in copy.all_objects if o.type == 'MESH']
    _setup_malt_ids()
    PixelArtConvert.convert_objects(april, 'ASW')
    PixelArtConvert.convert_objects(kof, 'KOF XIII')
    _use_pixel_lines(scene, enabled)
    _solo(scene, april + kof)
    _frame_objects(scene, april + kof, 256)


def pixel_cel_both_styles_off(scene):
    pixel_cel_both_styles(scene, False)


# --- Face SDF (Pixelizer third_party CL SDF fork, pitch-packed texture) ------------------------------------------------
# Suzanne alone with one sun at a head-space light direction: h = horizontal angle (0 = behind, 180 = front, positive =
# the head's left, +X), e = elevation (+ = above). The SDF is the unpainted one made by the add-on from Suzanne itself
# (content/malt/face_sdf/suzanne), so the Face SDF result must match N.L > 0 wherever no interpolation is involved.
FACE_SDF_DIR = 'H:/GameDev/Pixelizer/content/malt/face_sdf/suzanne/SDF'


def _face_sdf_scene(scene, h, e, shader):
    import os
    import mathutils
    ray_traced(scene)
    suzanne = bpy.data.objects['Suzanne']
    _solo(scene, [suzanne])
    for obj in list(scene.objects):
        if obj.type == 'LIGHT':
            bpy.data.objects.remove(obj, do_unlink=True)
    hr, er = math.radians(h), math.radians(e)
    to_light = mathutils.Vector((math.sin(hr) * math.cos(er), math.cos(hr) * math.cos(er), math.sin(er)))
    sun = _sun(scene, 0.0)
    sun.rotation_euler = (-to_light).to_track_quat('-Z', 'Y').to_euler()
    _frame_objects(scene, [suzanne], 256)
    _debug_shader(scene, shader)
    material = suzanne.material_slots[0].material
    # Shader-source materials keep their uniforms in material.malt.parameters, which exist only after Malt compiled
    # the shader: render_gui calls this back once the materials are ready
    if shader == 'face_sdf_plain.mesh.glsl':
        return None   # plain Pixel Cel never reads the SDF, so its uniforms are compiled out
    return lambda: _face_sdf_textures(material)


def _face_sdf_textures(material):
    import os
    assert not material.malt.compiler_error, material.malt.compiler_error
    textures = material.malt.parameters.textures
    for uniform, name in (('face_sdf_texture', 'T_Face_SDF_Pitch.png'),
                         ('face_sdf_flip_texture', 'T_Face_SDF_Pitch_Flip.png')):
        image = bpy.data.images.load(os.path.join(FACE_SDF_DIR, name), check_existing=True)
        image.colorspace_settings.name = 'Non-Color'
        if uniform not in textures.keys():
            from BlenderMalt import MaltMaterial
            compiled = MaltMaterial._MATERIALS.get(material.malt.get_source_path())
            raise AssertionError('no %s texture parameter; textures %s; rna %s; compiled parameters %s' % (
                uniform, list(textures.keys()), list(material.malt.parameters.get_rna().keys()),
                compiled and list(compiled.parameters.keys())))
        textures[uniform].texture = image
    material.update_tag()


_FACE_SDF_LIGHTS = {'l120': (120, 0), 'l60': (60, 0), 'r120': (-120, 0), 'u45': (120, 45), 'u30': (120, 30),
                    'd45': (120, -45)}
for _key, (_h, _e) in _FACE_SDF_LIGHTS.items():
    globals()['face_sdf_' + _key] = (lambda h, e: lambda scene: _face_sdf_scene(
        scene, h, e, 'face_sdf_debug.mesh.glsl'))(_h, _e)
    globals()['face_cel_' + _key] = (lambda h, e: lambda scene: _face_sdf_scene(
        scene, h, e, 'face_sdf_cel.mesh.glsl'))(_h, _e)
    globals()['face_plain_' + _key] = (lambda h, e: lambda scene: _face_sdf_scene(
        scene, h, e, 'face_sdf_plain.mesh.glsl'))(_h, _e)
