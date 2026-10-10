# Python reference of the Pixel Cel shading rules (spec section 3). Same as PixelCel.glsl: keep them in sync.
import colorsys
import math

TONE_SHADOW = 0
TONE_MID = 1
TONE_LIT = 2
TONE_HIGHLIGHT = 3


def cel_tone(n_dot_l, n_dot_h, offset, threshold, shadowed, ramp=None, spec_mask=0.0, spec_size=0.0,
             spec_threshold=0.5, highlight_threshold=2.0):
    s = n_dot_l * 0.5 + 0.5 + offset
    if shadowed:
        return TONE_SHADOW, 0.0
    if ramp is not None:
        t = float(ramp(min(max(s, 0.0), 1.0)))
        tone = TONE_SHADOW if t < 0.25 else (TONE_MID if t < 0.75 else TONE_LIT)
    else:
        lit = s > threshold
        t = 1.0 if lit else 0.0
        tone = TONE_LIT if lit else TONE_SHADOW
    if tone == TONE_LIT:
        if s > highlight_threshold:
            tone = TONE_HIGHLIGHT
        exponent = 4.0 + (128.0 - 4.0) * spec_size
        if spec_mask > 0.0 and spec_mask * math.pow(max(n_dot_h, 0.0), exponent) > spec_threshold:
            tone = TONE_HIGHLIGHT
    return tone, t


def cel_color(base_rgb, shadow_rgb, tone, t, spec_boost=1.3, highlight_rgb=(1.0, 0.97, 0.9), highlight_mix=0.0,
              line_mask=1.0):
    if tone == TONE_HIGHLIGHT:
        color = tuple(b * spec_boost * (1.0 - highlight_mix) + h * highlight_mix for b, h in zip(base_rgb, highlight_rgb))
    else:
        color = tuple(s + (b - s) * t for b, s in zip(base_rgb, shadow_rgb))
    # line_mask: the material-only path (Pixel Lines off). With Pixel Lines the shader no longer darkens inner lines
    line = 1.0 if line_mask > 0.5 else line_mask
    return tuple(c * line for c in color)


def linear_to_srgb(rgb):
    return tuple(c * 12.92 if c <= 0.0031308 else 1.055 * math.pow(c, 1.0 / 2.4) - 0.055 for c in rgb)


def srgb_to_linear(rgb):
    return tuple(c / 12.92 if c <= 0.04045 else math.pow((c + 0.055) / 1.055, 2.4) for c in rgb)


def shifted_shadow(base_rgb, hue_shift_degrees, saturation, value):
    h, s, v = colorsys.rgb_to_hsv(*linear_to_srgb(base_rgb))
    target = 260.0 / 360.0
    d = target - h
    d -= round(d)  # shortest signed distance, in [-0.5, 0.5]
    step = min(hue_shift_degrees / 360.0, abs(d)) * (1.0 if d >= 0 else -1.0)
    h = (h + step) % 1.0
    s = min(max(s * saturation, 0.0), 1.0)
    v = v * value
    return srgb_to_linear(colorsys.hsv_to_rgb(h, s, v))
