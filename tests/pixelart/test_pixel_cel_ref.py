import colorsys

import pytest

from Malt.PixelArt.cel_ref import (TONE_SHADOW, TONE_MID, TONE_LIT, TONE_HIGHLIGHT, cel_tone, cel_color,
                                   shifted_shadow, linear_to_srgb, srgb_to_linear)
from Malt.PixelArt.presets import PRESETS


@pytest.mark.parametrize('n_dot_l, offset, shadowed, tone', [
    (1.0, 0.0, False, TONE_LIT),
    (0.01, 0.0, False, TONE_LIT),       # s = 0.505 > 0.5
    (-0.01, 0.0, False, TONE_SHADOW),   # s = 0.495
    (1.0, 0.0, True, TONE_SHADOW),      # ray shadow wins
    (0.2, -0.5, False, TONE_SHADOW),    # ASW ilm.G = 0: always shadow
    (-0.8, 0.5, False, TONE_LIT),       # ilm.G = 1: nearly always lit
])
def test_two_tone(n_dot_l, offset, shadowed, tone):
    assert cel_tone(n_dot_l, 0.0, offset, 0.5, shadowed)[0] == tone


def test_ramp_bands_from_kof_preset():
    stops = PRESETS['KOF XIII']['ramp_stops']

    def ramp(s):
        value = stops[0][1]
        for position, v in stops:
            if s >= position:
                value = v
        return value
    assert cel_tone(-0.5, 0.0, 0.0, 0.5, False, ramp)[0] == TONE_SHADOW     # s = 0.25
    assert cel_tone(-0.1, 0.0, 0.0, 0.5, False, ramp)[0] == TONE_MID        # s = 0.45
    assert cel_tone(0.4, 0.0, 0.0, 0.5, False, ramp)[0] == TONE_LIT         # s = 0.7
    tone, t = cel_tone(0.9, 0.0, 0.0, 0.5, False, ramp, highlight_threshold=0.85)
    assert tone == TONE_HIGHLIGHT and t == 1.0                              # s = 0.95


def test_specular_only_on_lit():
    assert cel_tone(0.5, 1.0, 0.0, 0.5, False, spec_mask=1.0, spec_size=0.0)[0] == TONE_HIGHLIGHT
    assert cel_tone(-0.5, 1.0, 0.0, 0.5, False, spec_mask=1.0, spec_size=0.0)[0] == TONE_SHADOW


def test_colors():
    base, shadow = (0.8, 0.6, 0.4), (0.2, 0.1, 0.3)
    assert cel_color(base, shadow, TONE_SHADOW, 0.0) == pytest.approx(shadow)
    assert cel_color(base, shadow, TONE_LIT, 1.0) == pytest.approx(base)
    assert cel_color(base, shadow, TONE_MID, 0.45) == pytest.approx(tuple(s + (b - s) * 0.45 for b, s in zip(base, shadow)))
    assert cel_color(base, shadow, TONE_HIGHLIGHT, 1.0, spec_boost=1.25) == pytest.approx(tuple(b * 1.25 for b in base))
    assert cel_color(base, shadow, TONE_LIT, 1.0, line_mask=0.2) == pytest.approx(tuple(b * 0.2 for b in base))
    assert cel_color(base, shadow, TONE_LIT, 1.0, line_mask=0.7) == pytest.approx(base)  # above 0.5: no line


def test_shifted_shadow_moves_hue_toward_purple_and_darkens():
    base = srgb_to_linear((0.9, 0.6, 0.3))  # warm orange
    h0, s0, v0 = colorsys.rgb_to_hsv(*linear_to_srgb(base))
    h1, s1, v1 = colorsys.rgb_to_hsv(*linear_to_srgb(shifted_shadow(base, 15.0, 1.25, 0.55)))
    assert abs(((h1 - h0 + 0.5) % 1.0) - 0.5) == pytest.approx(15.0 / 360.0, abs=1e-3)
    assert v1 == pytest.approx(v0 * 0.55, abs=1e-3) and s1 == pytest.approx(min(1.0, s0 * 1.25), abs=1e-3)


def test_presets_have_the_same_inputs_and_no_line_width():
    asw, kof = PRESETS['ASW'], PRESETS['KOF XIII']
    assert set(asw) == set(kof)
    assert not any('width' in k for k in asw)
    assert asw['use_ramp'] is False and kof['use_ramp'] is True
    assert asw['ramp_stops'] == [] and len(kof['ramp_stops']) == 3
    assert asw['outline_shadow_only'] is False and kof['outline_shadow_only'] is True
