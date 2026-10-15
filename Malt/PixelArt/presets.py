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
        'outline_shadow_only': False,
        'keep_junctions': True,
        'keep_tips': True,
        'keep_overlap_corners': True,
        # Palette ramps (spec 09 section 4): shadow slots as (hue shift deg, saturation x, value x) of the lit colour;
        # stops: N-1 descending light thresholds (slot 0 = lightest). ASW: lit, shadow (Sss).
        'palette_slots': [],                        # ASW: the shadow slot is lit x Sss
        'palette_stops': [0.5],
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
        # KOF XIII: lit edges keep their colour, the outline only on the darkest tone
        'outline_shadow_only': True,
        'keep_junctions': True,
        'keep_tips': True,
        'keep_overlap_corners': True,
        'palette_slots': [(8.0, 1.1, 0.78), (15.0, 1.25, 0.55), (22.0, 1.3, 0.4)],
        'palette_stops': [0.85, 0.5, 0.35, 0.2],    # highlight | lit | shadow | deep | darkest
    },
}
