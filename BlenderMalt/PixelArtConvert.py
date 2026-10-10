# BlenderMalt/PixelArtConvert.py
# Converts Blender materials to Malt Pixel Cel materials (docs/pixelart/05-pixel-cel-materials-spec.md).
# Never touches the original Cycles/EEVEE nodes: only material.malt.shader_nodes is set.
import hashlib
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
    link_line_data(tree)

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


LINE_DATA = 'Pixel Line Data'


def _main_pass_custom_io(world):
    for graph_type in world.malt_graph_types:
        custom_pass = graph_type.custom_passes.get('Default')
        if custom_pass is not None and 'MAIN_PASS_PIXEL_SHADER' in custom_pass.io:
            return graph_type.name, custom_pass.io['MAIN_PASS_PIXEL_SHADER']
    raise KeyError('no Mesh main pass custom IO in the world')


def ensure_line_data_output(world=None):
    # The main pass gets a custom vec4 output 'Pixel Line Data' (pixel_cel line_data), read by the PixelLines node
    world = world or bpy.context.scene.world
    graph_name, io = _main_pass_custom_io(world)
    if LINE_DATA in io.outputs:
        return False
    item = io.outputs.add()
    item.name = LINE_DATA
    item.graph_type = graph_name
    item.io_type = 'MAIN_PASS_PIXEL_SHADER'
    item.is_output = True
    item.parameter = 'vec4'
    for tree in bpy.data.node_groups:
        if tree.bl_idname != 'MaltTree':
            continue
        for node in tree.nodes:
            if (node.bl_idname == 'MaltIONode' and node.is_output and node.io_type == 'MAIN_PASS_PIXEL_SHADER'
                    or getattr(node, 'function_type', '') == 'MainPass'):
                node.setup()
        if tree.graph_type == 'Mesh':
            tree.update_ext(force_track_shader_changes=False, force_update=True)
    return True


def link_line_data(tree):
    ensure_line_data_output()
    main = _io_node(tree, 'MAIN_PASS_PIXEL_SHADER')
    cel = next(n for n in tree.nodes if getattr(n, 'function_type', '') == find_function(tree, 'pixel_cel'))
    tree.links.new(cel.outputs['line_data'], main.inputs[LINE_DATA])


def original_hash(material):
    tree = material.node_tree
    if tree is None:
        return 'no-nodes'
    parts = []
    for node in sorted(tree.nodes, key=lambda n: n.name):
        parts.append(f'{node.name}:{node.type}:{getattr(getattr(node, "image", None), "name", "")}')
        for socket in node.inputs:
            value = getattr(socket, 'default_value', None)
            try:
                value = tuple(value)
            except TypeError:
                pass
            parts.append(f'  {socket.identifier}={value}')
    for link in tree.links:
        parts.append(f'{link.from_node.name}.{link.from_socket.identifier}->{link.to_node.name}.{link.to_socket.identifier}')
    return hashlib.sha1('\n'.join(parts).encode()).hexdigest()


def _current(tree, key):
    params = tree.malt_parameters
    if key in params.bools.keys():
        return params.bools[key].boolean
    if key in params.textures.keys():
        texture = params.textures[key].texture
        return 'image:' + texture.name if texture else None
    if key in params.gradients.keys():
        ramp = params.gradients[key].texture.color_ramp
        return [[round(e.position, 6), round(e.color[0], 6)] for e in ramp.elements]
    value = params.get(key)
    try:
        return list(value)
    except TypeError:
        return value


def _same(a, b):
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        return a is not None and b is not None and abs(float(a) - float(b)) < 1e-6
    return a == b


def update_tree(tree, plan, preset):
    # Rebuild into a scratch tree, then copy each value whose current value is still the one the converter wrote
    old = json.loads(tree.get('pixel_cel_set', '{}'))
    scratch = build_tree(plan, preset, tree.name + ' (scratch)')
    new = json.loads(scratch['pixel_cel_set'])
    kept = []
    for key, value in new.items():
        if key in old and not _same(_current(tree, key), old[key]):
            kept.append(key)
            continue
        params = tree.malt_parameters
        if isinstance(value, str) and value.startswith('image:'):
            params.textures[key].texture = bpy.data.images[value[len('image:'):]]
        elif isinstance(value, bool):
            params.bools[key].boolean = value
        elif key in scratch.malt_parameters.gradients.keys():
            src = scratch.malt_parameters.gradients[key].texture.color_ramp
            dst = params.gradients[key].texture.color_ramp
            dst.interpolation = src.interpolation
            while len(dst.elements) > 1:
                dst.elements.remove(dst.elements[-1])
            dst.elements[0].position, dst.elements[0].color = src.elements[0].position, src.elements[0].color
            for element in src.elements[1:]:
                dst.elements.new(element.position).color = element.color
        else:
            params[key] = value
    kept_values = {k: old[k] for k in kept}
    new.update(kept_values)
    tree['pixel_cel_set'] = json.dumps(new)
    bpy.data.node_groups.remove(scratch)
    return kept


def convert_material(material, preset='ASW', trees=None):
    plan = detect(describe_material(material))
    trees = {} if trees is None else trees
    key = plan.key + '|' + preset
    if key not in trees:
        existing = material.malt.shader_nodes
        if existing is not None and existing.get('pixel_cel_preset') == preset and existing.get('pixel_cel_key') == plan.key:
            update_tree(existing, plan, preset)
            trees[key] = existing
        else:
            trees[key] = build_tree(plan, preset, f'PixelCel {preset} {material.name}')
            trees[key]['pixel_cel_key'] = plan.key
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


# Metres between a collection and its copies (1 m makes April's arms overlap)
COPY_SPACING = 1.6


def copy_collection(collection, suffix):
    existing = [c for c in bpy.data.collections if c.name.startswith(collection.name + '.' + suffix)]
    offset = len(existing) + 1

    def copy(source, parent):
        new = bpy.data.collections.new(f'{source.name}.{suffix}')
        parent.children.link(new)
        for obj in source.objects:
            duplicate = obj.copy()  # object copied, obj.data (mesh / armature) shared
            duplicate.name = f'{obj.name}.{suffix}'
            for slot in duplicate.material_slots:
                material = slot.material
                if material is not None:
                    slot.link = 'OBJECT'  # setting the link clears the slot: assign the copy afterwards
                    slot.material = material.copy()
                    slot.material.name = f'{material.name.rsplit(".", 1)[0]}.{suffix}'
            if duplicate.parent is None:
                # delta_location: an action that keys location (April's armature) would undo a location offset
                duplicate.delta_location.x += offset * COPY_SPACING
            new.objects.link(duplicate)
        for child in source.children:
            copy(child, new)
        return new

    parent = next((c for c in bpy.data.collections if collection.name in c.children), bpy.context.scene.collection)
    result = copy(collection, parent)
    # Re-point copied objects to copied parents and armature modifiers to the copied armature
    names = {o.name.rsplit('.' + suffix, 1)[0]: o for o in result.all_objects}
    for obj in result.all_objects:
        if obj.parent is not None and obj.parent.name in names:
            obj.parent = names[obj.parent.name]
        for modifier in obj.modifiers:
            if modifier.type == 'ARMATURE' and modifier.object is not None and modifier.object.name in names:
                modifier.object = names[modifier.object.name]
    return result


def write_report(report):
    text = bpy.data.texts.get('PixelArt Convert Report') or bpy.data.texts.new('PixelArt Convert Report')
    text.clear()
    for name, style, textures, warnings, tree in report:
        text.write(f'{name}: {style}  textures={",".join(textures) or "-"}  tree={tree}\n')
        for warning in warnings:
            text.write(f'    warning: {warning}\n')
    return text.name


class MALT_OT_convert_pixel_art(bpy.types.Operator):
    """Convert the selected objects' materials (or the active collection) to Malt Pixel Cel materials"""
    bl_idname = 'malt.convert_pixel_art'
    bl_label = 'Convert to Malt Pixel Art'
    bl_options = {'REGISTER', 'UNDO'}

    preset: bpy.props.EnumProperty(name='Style', items=[('ASW', 'ASW (GGXrd)', ''), ('KOF XIII', 'KOF XIII', '')])
    copy_collection: bpy.props.BoolProperty(name='Copy collection', default=False,
        description='Convert a copy of the active collection, so both styles sit side by side')
    setup_pixel_lines: bpy.props.BoolProperty(name='Set up Pixel Lines', default=True,
        description='Use the 1 px Pixel Lines node in the world render layer graph')

    def execute(self, context):
        from BlenderMalt.MaltPipeline import setup_all_ids
        objects = [o for o in context.selected_objects if o.type == 'MESH']
        if self.copy_collection or not objects:
            collection = context.collection
            if self.copy_collection:
                collection = copy_collection(collection, 'KOF' if self.preset == 'KOF XIII' else 'ASW')
            objects = [o for o in collection.all_objects if o.type == 'MESH']
        setup_all_ids()
        report = convert_objects(objects, self.preset)
        if self.setup_pixel_lines:
            setup_pixel_lines(context.scene)
        name = write_report(report)
        warnings = sum(len(r[3]) for r in report)
        self.report({'WARNING' if warnings else 'INFO'},
            f'{len(report)} materials converted, {warnings} warnings (text block "{name}")')
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


def _function_node(tree, function_type):
    for node in tree.nodes:
        if getattr(node, 'function_type', '') == function_type:
            return node
    return None


def setup_pixel_lines(scene, enabled=True):
    # In memory: in every Render Layer graph, route the main pass through PixelLines instead of LineRender
    ensure_line_data_output(scene.world)
    done = False
    for tree in bpy.data.node_groups:
        if tree.bl_idname != 'MaltTree' or tree.graph_type != 'Render Layer':
            continue
        line, main, pre = (_function_node(tree, t) for t in ('LineRender', 'MainPass', 'PrePass'))
        if not (line and main and pre):
            continue
        pixel = _function_node(tree, 'PixelLines')
        if pixel is None:
            pixel = tree.nodes.new('MaltFunctionNode')
            pixel.function_type = find_function(tree, 'PixelLines')
            pixel.location = (line.location[0], line.location[1] - 300)
        main.setup()
        targets = [l.to_socket for l in tree.links if l.from_node in (line, pixel) and l.from_socket.name == 'Color']
        for source, name in ((main, 'Color'), (main, 'Line Color'), (main, LINE_DATA)):
            tree.links.new(source.outputs[name], pixel.inputs[name])
        tree.links.new(pre.outputs['Scene'], pixel.inputs['Scene'])
        for link in [l for l in tree.links if l.from_node in (line, pixel) and l.from_socket.name == 'Color']:
            tree.links.remove(link)
        for target in targets:
            tree.links.new((pixel if enabled else line).outputs['Color'], target)
        tree.update_ext(force_update=True)
        done = True
    return done


def _menu(self, context):
    self.layout.operator(MALT_OT_convert_pixel_art.bl_idname)


def register():
    bpy.utils.register_class(MALT_OT_convert_pixel_art)
    bpy.types.VIEW3D_MT_object.append(_menu)


def unregister():
    bpy.types.VIEW3D_MT_object.remove(_menu)
    bpy.utils.unregister_class(MALT_OT_convert_pixel_art)
