# Malt/PixelArt/detect.py
# Source material style detection for the Pixel Cel converter. No bpy, no OpenGL (unit tested outside Blender).
import dataclasses
import os
import re

_ASW_BASE = re.compile(r'^(?P<prefix>.+?)_base(x)?$', re.IGNORECASE)
_DECAL = re.compile(r'_decal', re.IGNORECASE)
_NORMAL = re.compile(r'(nm|normal)', re.IGNORECASE)


@dataclasses.dataclass
class ConvertPlan:
    style: str
    textures: dict
    base_color: tuple
    uv_map: str = None
    use_vertex_color: bool = False
    warnings: list = dataclasses.field(default_factory=list)
    keep: bool = False

    @property
    def key(self):
        textures = ','.join(f'{k}={os.path.normcase(v)}' for k, v in sorted(self.textures.items()))
        return f'{self.style}|{textures}|{tuple(round(c, 4) for c in self.base_color)}'


_KEEP = re.compile(r'(^|[^a-z])(hands?|fingers?|gloves?|straps?)([^a-z]|$)', re.IGNORECASE)


_CAMEL = re.compile(r'(?<=[a-z])(?=[A-Z])')


def keep_by_name(material_name, object_names):
    # KEEP parts (Pixelizer keep.py): thin parts that must never vanish between pixel centres
    # '_' and camelCase humps split words: '5_hands_1', 'L_Finger_02' and 'BagStrap' match, 'Handle' does not
    return any(_KEEP.search(_CAMEL.sub(' ', n.replace('_', ' '))) for n in [material_name, *object_names])


def _norm(path):
    return path.replace('\\', '/')


def _stem(path):
    return os.path.splitext(os.path.basename(_norm(path)))[0]


def _sibling(folder, prefix, suffix, listdir):
    # A file named <prefix>_<suffix>.* in folder, case-insensitive; returns its path or None
    try:
        names = listdir(folder)
    except OSError:
        return None
    wanted = f'{prefix}_{suffix}'.lower()
    for name in sorted(names):
        if os.path.splitext(name)[0].lower() == wanted:
            return folder + '/' + name
    return None


def detect(description, listdir=os.listdir, exists=os.path.exists):
    name = description['name']
    images = description.get('images', []) if description.get('has_nodes', True) else []
    base_color = tuple(description.get('base_color') or description['display_color'])
    warnings = []
    for image in images:
        if not exists(image['filepath']):
            warnings.append(f"missing file: {_norm(image['filepath'])}")
    base_images = [i for i in images if i['feeds_base']]
    first = (base_images or images or [None])[0]
    uv_map = first['uv_map'] if first else None

    if 'eyeshine' in name.lower() and first:
        return ConvertPlan('asw_eyeshine', {'base': _norm(first['filepath'])}, base_color, uv_map, True, warnings)

    decal = next((i for i in images if _DECAL.search(_stem(i['name']))), None)
    if name.lower().startswith('7_decal') or decal:
        image = decal or first
        textures = {'decal': _norm(image['filepath'])} if image else {}
        return ConvertPlan('asw_decal', textures, base_color, uv_map, True, warnings)

    for image in base_images or images:
        match = _ASW_BASE.match(_stem(image['name']))
        if not match:
            continue
        folder = _norm(os.path.dirname(_norm(image['filepath'])))
        prefix = match.group('prefix')
        sss = _sibling(folder, prefix, 'sss', listdir)
        ilm = _sibling(folder, prefix, 'ilm', listdir)
        if sss or ilm or any(w.startswith('missing') for w in warnings):
            textures = {'base': _norm(image['filepath'])}
            if sss:
                textures['sss'] = sss
            else:
                warnings.append(f'no {prefix}_Sss texture: shadow tint colour used')
            if ilm:
                textures['ilm'] = ilm
            else:
                warnings.append(f'no {prefix}_ilm texture: neutral ilm used')
            return ConvertPlan('asw', textures, base_color, image['uv_map'] or uv_map, True, warnings)

    if images:
        srgb = [i for i in images if i['colorspace'] != 'Non-Color']
        if base_images:
            base = base_images[0]
        elif srgb:
            base = max(srgb, key=lambda i: i['size'][0] * i['size'][1])
            warnings.append(f"base colour image not traced: largest sRGB image {base['name']} used")
        else:
            base = None
        if base:
            textures = {'base': _norm(base['filepath'])}
            normal = next((i for i in images if i['colorspace'] == 'Non-Color' and _NORMAL.search(_stem(i['name']))), None)
            if normal:
                textures['normal'] = _norm(normal['filepath'])
            return ConvertPlan('generic', textures, base_color, base['uv_map'] or uv_map, False, warnings)

    return ConvertPlan('untextured', {}, base_color, uv_map, False, warnings)
