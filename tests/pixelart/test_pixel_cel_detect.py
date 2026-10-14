# tests/pixelart/test_pixel_cel_detect.py
from Malt.PixelArt.detect import detect

APRIL_DIR = 'H:/Blender/gultygear/GGXrd - April'
APRIL_FILES = ['APRL_Sss.png', 'APRL_base.png', 'APRL_baseX.png', 'APRL_decal.png', 'APRL_decalX.png',
               'APRL_ilm.png', 'xps.xps']


def _fs(files_by_dir):
    def listdir(path):
        return files_by_dir.get(path.replace('\\', '/').rstrip('/'), [])

    def exists(path):
        path = path.replace('\\', '/')
        folder, _, name = path.rpartition('/')
        return name in files_by_dir.get(folder, [])
    return listdir, exists


def _image(name, filepath, feeds_base=True, colorspace='sRGB', size=(1024, 1024), uv_map='UV1'):
    return {'name': name, 'filepath': filepath, 'colorspace': colorspace, 'feeds_base': feeds_base,
            'size': size, 'uv_map': uv_map}


def _material(name, images=(), base_color=None, has_nodes=True):
    return {'name': name, 'images': list(images), 'base_color': base_color,
            'display_color': (0.8, 0.8, 0.8, 1.0), 'has_nodes': has_nodes}


def test_april_body_is_asw():
    listdir, exists = _fs({APRIL_DIR: APRIL_FILES})
    m = _material('5_body_1_0_0.001', [_image('APRL_baseX.png', APRIL_DIR + '\\APRL_baseX.png')])
    plan = detect(m, listdir, exists)
    assert plan.style == 'asw'
    assert plan.textures['base'].endswith('APRL_baseX.png')
    assert plan.textures['sss'].endswith('APRL_Sss.png')
    assert plan.textures['ilm'].endswith('APRL_ilm.png')
    assert plan.use_vertex_color and plan.uv_map == 'UV1' and plan.warnings == []


def test_april_decal_and_eyeshine():
    listdir, exists = _fs({APRIL_DIR: APRIL_FILES})
    decal = detect(_material('7_DecalFace_1_0_0.001', [_image('APRL_decalX.png', APRIL_DIR + '/APRL_decalX.png')]),
                   listdir, exists)
    assert decal.style == 'asw_decal' and decal.textures['decal'].endswith('APRL_decalX.png')
    shine = detect(_material('5_eyeshine_1_0_0.001', [_image('APRL_baseX.png', APRIL_DIR + '/APRL_baseX.png')]),
                   listdir, exists)
    assert shine.style == 'asw_eyeshine'


def test_asw_missing_sss_falls_back_with_warning():
    listdir, exists = _fs({APRIL_DIR: ['APRL_base.png', 'APRL_ilm.png']})
    plan = detect(_material('5_head', [_image('APRL_base.png', APRIL_DIR + '/APRL_base.png')]), listdir, exists)
    assert plan.style == 'asw' and 'sss' not in plan.textures
    assert any('Sss' in w for w in plan.warnings)


def test_generic_textured_arthur():
    d = 'H:/Blender/umvc3_arthur_by_jsrremix_db29n16/UMVC3 Arthur'
    listdir, exists = _fs({d: ['arthur_tex01_bmout.png', 'arthur_tex01_nmout.png']})
    m = _material('24_+mesh81', [
        _image('arthur_tex01_bmout.png', d + '/arthur_tex01_bmout.png'),
        _image('arthur_tex01_nmout.png', d + '/arthur_tex01_nmout.png', feeds_base=False, colorspace='Non-Color'),
    ])
    plan = detect(m, listdir, exists)
    assert plan.style == 'generic'
    assert plan.textures['base'].endswith('bmout.png') and plan.textures['normal'].endswith('nmout.png')
    assert not plan.use_vertex_color


def test_generic_fallback_largest_srgb_image():
    listdir, exists = _fs({'C:/t': ['small.png', 'big.png']})
    m = _material('m', [_image('small.png', 'C:/t/small.png', feeds_base=False, size=(64, 64)),
                        _image('big.png', 'C:/t/big.png', feeds_base=False, size=(512, 512))])
    plan = detect(m, listdir, exists)
    assert plan.style == 'generic' and plan.textures['base'].endswith('big.png')
    assert any('largest' in w for w in plan.warnings)


def test_untextured_uses_base_color_then_display_color():
    assert detect(_material('dude', base_color=(0.2, 0.3, 0.4, 1.0))).base_color == (0.2, 0.3, 0.4, 1.0)
    plan = detect(_material('dude'))
    assert plan.style == 'untextured' and plan.base_color == (0.8, 0.8, 0.8, 1.0)


def test_no_nodes_material():
    plan = detect(_material('plain', has_nodes=False))
    assert plan.style == 'untextured' and plan.warnings == []


def test_relative_and_missing_paths():
    listdir, exists = _fs({})
    m = _material('5_body', [_image('APRL_base.png', 'H:/nowhere/APRL_base.png')])
    plan = detect(m, listdir, exists)
    assert plan.style in ('asw', 'generic')
    assert any('missing' in w for w in plan.warnings)


def test_shared_key():
    listdir, exists = _fs({APRIL_DIR: APRIL_FILES})
    a = detect(_material('5_body', [_image('APRL_baseX.png', APRIL_DIR + '/APRL_baseX.png')]), listdir, exists)
    b = detect(_material('5_hat', [_image('APRL_baseX.png', APRIL_DIR + '/APRL_baseX.png')]), listdir, exists)
    assert a.key == b.key


from Malt.PixelArt.detect import keep_by_name


def test_keep_by_name_hands_fingers_straps():
    assert keep_by_name('5_hands_1_0_0.001', ['5_hands_1_0_0.001'])
    assert keep_by_name('Body', ['L_Finger_02'])
    assert keep_by_name('BagStrap', [])
    assert keep_by_name('Glove_mat', [])
    assert not keep_by_name('5_body_1_0_0.001', ['5_body_1_0_0.001'])
    assert not keep_by_name('Shoulder', ['Handle'])   # 'hand' only as a whole word part, not in 'Handle'
