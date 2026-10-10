# Pixel Cel input values per style preset (spec section 3.1). Keys are pixel_cel input names (PixelCel.glsl).
# There is no line width anywhere: every line is exactly 1 px (spec section 3.2).

PRESETS = {
    'ASW': {
        'use_ramp': False,
        'ramp_stops': [],
        'threshold': 0.5,
        'shadow_from_hue_shift': False,
        'hue_shift': 15.0,
        'shadow_saturation': 1.25,
        'shadow_value': 0.55,
        'spec_threshold': 0.5,
        'spec_boost': 1.3,
        'highlight_threshold': 2.0,
        'highlight_mix': 0.0,
        'outline_from_base': False,
        'outline_value': 0.01,
    },
    'KOF XIII': {
        'use_ramp': True,
        'ramp_stops': [(0.0, 0.0), (0.35, 0.45), (0.5, 1.0)],
        'threshold': 0.5,
        'shadow_from_hue_shift': True,
        'hue_shift': 15.0,
        'shadow_saturation': 1.25,
        'shadow_value': 0.55,
        'spec_threshold': 0.5,
        'spec_boost': 1.2,
        'highlight_threshold': 0.85,
        'highlight_mix': 0.2,
        'outline_from_base': True,
        'outline_value': 0.1,
    },
}
