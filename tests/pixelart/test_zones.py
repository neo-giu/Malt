import numpy as np
import pytest

from Malt.PixelArt import zones as Z


def _two_colour_texture():
    a = np.zeros((32, 32, 4), np.uint8)
    a[..., 3] = 255
    a[:, :16, :3] = (250, 220, 170)   # skin
    a[:, 16:, :3] = (40, 90, 150)     # blue
    return a


def test_kmeans_is_deterministic():
    pts = np.random.default_rng(1).random((500, 3))
    c1, l1 = Z.kmeans(pts, 4, seed=3)
    c2, l2 = Z.kmeans(pts, 4, seed=3)
    assert np.array_equal(l1, l2) and np.allclose(c1, c2)


def test_cluster_texture_finds_two_zones():
    labels, centres = Z.cluster_texture(_two_colour_texture())
    assert len(centres) == 2
    assert len(set(labels[:, :16].ravel())) == 1 and len(set(labels[:, 16:].ravel())) == 1
    assert labels[0, 0] != labels[0, 31]


def test_transparent_texels_get_no_zone():
    a = _two_colour_texture()
    a[:4, :, 3] = 0
    a[:4, :, :3] = (0, 0, 0)            # black under alpha 0 must not become a cluster
    labels, centres = Z.cluster_texture(a)
    assert (labels[:4] == -1).all() and len(centres) == 2


def test_merge_islands_removes_specks():
    labels = np.zeros((20, 20), int)
    labels[5:7, 5:7] = 1                # 4 texels
    labels[10:16, 10:16] = 2            # 36 texels
    out = Z.merge_islands(labels, min_area=16)
    assert (out[5:7, 5:7] == 0).all() and (out[10:16, 10:16] == 2).all()


def test_untextured_material_is_one_zone():
    p = Z.build_palette('ASW', [Z.Zone('Dude', 0, (120, 130, 140), None, 1)])
    assert len(p['ramps']) == 1
    (ramp,) = p['ramps'].values()
    assert ramp['colours'][0] == [120, 130, 140] and len(ramp['colours']) == 2


def test_asw_ramp_shadow_mean():
    zs = [Z.Zone('a', 0, (200, 100, 100), (128, 128, 128), 10), Z.Zone('b', 0, (202, 100, 100), (64, 64, 64), 10)]
    p = Z.build_palette('ASW', zs, budget=6)
    (ramp,) = p['ramps'].values()
    lit, shadow = ramp['colours']
    assert lit == [201, 100, 100]
    # shadow = lit x mean Sss (96 / 255), multiplied in linear light
    assert shadow == list(Z.multiply_srgb(lit, (96, 96, 96)))


def test_kof_ramp_is_light_to_dark_with_hue_shift():
    colours, line = Z.ramp_colours('KOF XIII', (240, 200, 160))
    values = [max(c) for c in colours]
    assert len(colours) == 5 and values == sorted(values, reverse=True)
    assert max(line) < values[-1]


def test_budget_limits_colours():
    zs = [Z.Zone(f'm{i}', 0, (i * 20 % 255, 100, 255 - i * 20 % 255), None, 10) for i in range(12)]
    p = Z.build_palette('KOF XIII', zs, budget=40)
    total = sum(len(r['colours']) + 1 for r in p['ramps'].values())
    assert total <= 40


def test_strip_round_trip_keeps_edits():
    p = Z.build_palette('ASW', [Z.Zone('Dude', 0, (120, 130, 140), None, 1)])
    strip = Z.palette_strip(p)
    strip[0, 0] = (10, 20, 30)          # owner edit in Aseprite
    q = Z.apply_strip(p, strip)
    (ramp,) = q['ramps'].values()
    assert ramp['colours'][0] == [10, 20, 30]


def test_gpu_palette_layout():
    p = Z.build_palette('KOF XIII', [Z.Zone('Dude', 0, (120, 130, 140), None, 1)])
    g = Z.gpu_palette(p)
    (ramp,) = p['ramps'].values()
    assert g.shape == (2, 8, 4)
    assert list(g[0, 0, :3]) == ramp['colours'][0] and list(g[0, 7, :3]) == ramp['line']
    assert g[1, 0, 1] == len(ramp['colours'])
    assert [int(v) for v in g[1, :4, 0]] == [round(s * 255) for s in ramp['stops']]


def test_ramp_index_texture():
    labels, _ = Z.cluster_texture(_two_colour_texture())
    zones = [Z.Zone('m', int(c), (0, 0, 0), None, 1) for c in sorted(set(labels.ravel()))]
    p = Z.build_palette('ASW', zones)
    t = Z.ramp_index_texture(labels, 'm', p)
    assert t.dtype == np.uint8 and t.min() >= 1


def test_zone_mips_majority_vote_never_blends():
    t = np.array([[1, 1, 2, 2],
                  [1, 3, 2, 2],
                  [4, 4, 5, 6],
                  [4, 4, 7, 8]], np.uint8)
    levels = Z.zone_mips(t)
    assert [l.shape for l in levels] == [(4, 4), (2, 2), (1, 1)]
    assert levels[1].tolist() == [[1, 2], [4, 5]]      # 3-of-4 majority; 5,6,7,8 tie -> top-left 5
    assert set(np.unique(levels[1])) <= set(np.unique(t))


def test_zone_mips_odd_size():
    levels = Z.zone_mips(np.ones((5, 3), np.uint8))
    assert [l.shape for l in levels] == [(5, 3), (3, 2), (2, 1), (1, 1)]


def test_mip_atlas_offsets():
    levels = Z.zone_mips(np.arange(16, dtype=np.uint8).reshape(4, 4))
    atlas, offsets = Z.mip_atlas(levels)
    assert offsets == [0, 4, 6] and atlas.shape == (4, 7)
    assert np.array_equal(atlas[:2, 4:6], levels[1])
