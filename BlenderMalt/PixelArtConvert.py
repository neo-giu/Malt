# BlenderMalt/PixelArtConvert.py
# Converts Blender materials to Malt Pixel Cel materials (docs/pixelart/05-pixel-cel-materials-spec.md).
# Never touches the original Cycles/EEVEE nodes: only material.malt.shader_nodes is set.
import json
import os

import bpy

from Malt.PixelArt.detect import detect
from Malt.PixelArt.presets import PRESETS

_BSDF_TYPES = {'BSDF_PRINCIPLED', 'BSDF_DIFFUSE'}


def _feeds_base(node, tree):
    # True when an image node reaches a BSDF base colour (or an XPS/other group's first colour input), through any
    # chain of nodes
    seen = set()
    stack = [node]
    while stack:
        current = stack.pop()
        if current.name in seen:
            continue
        seen.add(current.name)
        for output in current.outputs:
            for link in output.links:
                target, socket = link.to_node, link.to_socket
                if target.type in _BSDF_TYPES and socket.name in ('Base Color', 'Color'):
                    return True
                if target.type == 'GROUP' and socket.name.lower() in ('diffuse', 'base color', 'color', 'albedo'):
                    return True
                stack.append(target)
    return False


def describe_material(material):
    tree = material.node_tree if material.use_nodes else None
    images = []
    base_color = None
    if tree:
        for node in tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                uv_map = None
                vector = node.inputs.get('Vector')
                if vector and vector.links and vector.links[0].from_node.type == 'UVMAP':
                    uv_map = vector.links[0].from_node.uv_map or None
                images.append({
                    'name': node.image.name,
                    'filepath': bpy.path.abspath(node.image.filepath, library=node.image.library),
                    'colorspace': node.image.colorspace_settings.name,
                    'feeds_base': _feeds_base(node, tree),
                    'size': tuple(node.image.size),
                    'uv_map': uv_map,
                })
            if node.type in _BSDF_TYPES and base_color is None:
                socket = node.inputs.get('Base Color') or node.inputs.get('Color')
                if socket is not None and not socket.links:
                    base_color = tuple(socket.default_value)
    return {
        'name': material.name,
        'images': images,
        'base_color': base_color,
        'display_color': tuple(material.diffuse_color),
        'has_nodes': tree is not None,
    }


def find_function(tree, function_name):
    functions = tree.get_full_library()['functions']
    for key, function in functions.items():
        if function['name'] == function_name:
            return key
    close = [k for k in functions if function_name.split('_')[0] in k]
    raise KeyError(f'{function_name} not in the Malt library; close: {close[:10]}')


def _new_mesh_tree(name):
    tree = bpy.data.node_groups.new(name, 'MaltTree')
    tree.graph_type = 'Mesh'  # Malt replaces the empty tree with a copy of 'Mesh Node Tree Base', same name
    tree = bpy.data.node_groups[name]
    for node in list(tree.nodes):
        if node.bl_idname != 'MaltIONode':
            tree.nodes.remove(node)
    return tree


def _io_node(tree, io_type):
    for node in tree.nodes:
        if node.bl_idname == 'MaltIONode' and node.is_output and node.io_type == io_type:
            return node
    raise KeyError(f'no {io_type} output node in {tree.name}')


def _pre_pass_node(tree):
    # the Mesh base tree only has the main pass output: add the pre pass output when needed
    for node in tree.nodes:
        if node.bl_idname == 'MaltIONode' and node.is_output and node.io_type == 'PRE_PASS_PIXEL_SHADER':
            return node
    node = tree.nodes.new('MaltIONode')
    node.name = 'PRE PASS PIXEL SHADER Output'
    node.is_output = True
    node.io_type = 'PRE_PASS_PIXEL_SHADER'
    node.location = (0, 400)
    return node


def _set(tree, node, socket_name, value, written):
    key = node.inputs[socket_name].get_source_global_reference().replace('"', '')
    params = tree.malt_parameters
    if isinstance(value, bpy.types.Image):
        params.textures[key].texture = value
        written[key] = 'image:' + value.name
    elif isinstance(value, bool):
        # Malt keeps bool parameters in their own collection, not as ID properties
        params.bools[key].boolean = value
        written[key] = value
    else:
        params[key] = value
        written[key] = value if not isinstance(value, tuple) else list(value)


def _load_image(path):
    for image in bpy.data.images:
        if image.filepath and os.path.normcase(bpy.path.abspath(image.filepath)) == os.path.normcase(path):
            return image
    if os.path.exists(path):
        return bpy.data.images.load(path, check_existing=True)
    return None


def _set_ramp(tree, node, stops, written):
    key = node.inputs['ramp'].get_source_global_reference().replace('"', '')
    ramp = tree.malt_parameters.gradients[key].texture.color_ramp
    ramp.interpolation = 'CONSTANT'
    while len(ramp.elements) > 1:
        ramp.elements.remove(ramp.elements[-1])
    ramp.elements[0].position = stops[0][0]
    ramp.elements[0].color = (stops[0][1],) * 3 + (1.0,)
    for position, value in stops[1:]:
        element = ramp.elements.new(position)
        element.color = (value,) * 3 + (1.0,)
    written[key] = [list(s) for s in stops]


def build_tree(plan, preset, name):
    tree = _new_mesh_tree(name)
    cel = tree.nodes.new('MaltFunctionNode')
    cel.function_type = find_function(tree, 'pixel_cel')
    cel.location = (-400, 0)
    main = _io_node(tree, 'MAIN_PASS_PIXEL_SHADER')
    tree.links.new(cel.outputs['color'], main.inputs['Color'])
    tree.links.new(cel.outputs['line_color'], main.inputs['Line Color'])

    written = {}
    values = dict(PRESETS[preset])
    stops = values.pop('ramp_stops')
    for socket_name, value in values.items():
        _set(tree, cel, socket_name, value, written)
    if stops:
        _set_ramp(tree, cel, stops, written)

    textures = plan.textures
    for texture_key, socket_flag, socket_texture in (
            ('base', 'use_base_texture', 'base_texture'),
            ('decal', 'use_base_texture', 'base_texture'),
            ('sss', 'use_shadow_texture', 'shadow_texture'),
            ('ilm', 'use_ilm_texture', 'ilm_texture')):
        if texture_key in textures:
            image = _load_image(textures[texture_key])
            if image is not None:
                if texture_key in ('sss', 'ilm'):
                    image.colorspace_settings.name = 'Non-Color' if texture_key == 'ilm' else image.colorspace_settings.name
                _set(tree, cel, socket_texture, image, written)
                _set(tree, cel, socket_flag, True, written)
    if not textures.get('base') and not textures.get('decal'):
        _set(tree, cel, 'base_color', tuple(plan.base_color), written)
    _set(tree, cel, 'use_vertex_color', bool(plan.use_vertex_color), written)
    if plan.style == 'asw_eyeshine':
        _set(tree, cel, 'unlit', True, written)
    if plan.style == 'asw_decal':
        _set(tree, cel, 'use_cutout', True, written)
        pre = _pre_pass_node(tree)
        opacity = tree.nodes.new('MaltFunctionNode')
        opacity.function_type = find_function(tree, 'pixel_cel_opacity')
        opacity.location = (-400, 400)
        tree.links.new(opacity.outputs['result'], next(s for s in pre.inputs if s.name.lower().endswith('opacity')))
        image = _load_image(textures['decal']) if 'decal' in textures else None
        if image is not None:
            _set(tree, opacity, 'texture_', image, written)
        _set(tree, opacity, 'use_cutout', True, written)
    tree['pixel_cel_set'] = json.dumps(written)
    tree['pixel_cel_preset'] = preset
    tree['pixel_cel_style'] = plan.style
    # Malt only updates trees shown in an editor: write the generated shader of a script-built tree ourselves
    tree.update_ext(force_track_shader_changes=False, force_update=True)
    return tree


def convert_material(material, preset='ASW', trees=None):
    plan = detect(describe_material(material))
    trees = {} if trees is None else trees
    key = plan.key + '|' + preset
    if key not in trees:
        trees[key] = build_tree(plan, preset, f'PixelCel {preset} {material.name}')
    material.malt.material_type = 'Mesh'
    material.malt.shader_nodes = trees[key]
    return plan, trees[key]


def convert_objects(objects, preset='ASW'):
    trees = {}
    report = []
    done = set()
    for obj in objects:
        for slot in obj.material_slots:
            material = slot.material
            if material is None or material.name in done:
                continue
            done.add(material.name)
            plan, tree = convert_material(material, preset, trees)
            report.append((material.name, plan.style, sorted(plan.textures), plan.warnings, tree.name))
    from BlenderMalt import MaltMaterial
    # Compile the shaders of the materials just assigned, synchronously: a render right after a conversion must not
    # run before the shaders exist
    MaltMaterial.track_shader_changes(force_update=True, async_compilation=False)
    return report
