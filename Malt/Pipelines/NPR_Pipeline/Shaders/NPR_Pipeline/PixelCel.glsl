// Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/PixelCel.glsl
#ifndef PIXEL_CEL_GLSL
#define PIXEL_CEL_GLSL

#include "NPR_Lighting.glsl"
#include "Common/Color.glsl"

/*  META GLOBAL
    @meta: category=Shading;
*/

// Pixel Cel: cel-shaded pixel-art material (docs/pixelart/05-pixel-cel-materials-spec.md, section 3).
// Same rules as Malt/PixelArt/cel_ref.py: keep them in sync.

#define PIXEL_CEL_TONE_SHADOW 0
#define PIXEL_CEL_TONE_MID 1
#define PIXEL_CEL_TONE_LIT 2
#define PIXEL_CEL_TONE_HIGHLIGHT 3

vec4 _pixel_cel_sample(sampler2D tex, vec2 uv, bool nearest)
{
    if(nearest)
    {
        ivec2 size = textureSize(tex, 0);
        ivec2 texel = ivec2(floor(fract(uv) * vec2(size)));
        return texelFetch(tex, clamp(texel, ivec2(0), size - 1), 0);
    }
    return texture(tex, uv);
}

// KOF XIII shadow colour: hue moved toward blue-purple (260 degrees) by at most hue_shift degrees, then saturation
// and value scaled. HSV is in sRGB space (Malt rgb_to_hsv), like cel_ref.shifted_shadow.
vec3 _pixel_cel_shifted_shadow(vec3 base, float hue_shift, float saturation, float value)
{
    vec3 hsv = rgb_to_hsv(base);
    float d = 260.0 / 360.0 - hsv.x;
    d -= round(d);
    hsv.x = fract(hsv.x + min(hue_shift / 360.0, abs(d)) * (d >= 0.0 ? 1.0 : -1.0));
    hsv.y = clamp(hsv.y * saturation, 0.0, 1.0);
    hsv.z *= value;
    return hsv_to_rgb(hsv);
}

int _pixel_cel_tone(float n_dot_l, float n_dot_h, float offset, float threshold, bool light_shadowed,
    bool use_ramp, sampler1D ramp, float spec_mask, float spec_size, float spec_threshold, float highlight_threshold,
    out float t, out float s_out)
{
    float s = n_dot_l * 0.5 + 0.5 + offset;
    s_out = s;
    t = 0.0;
    if(light_shadowed)
    {
        return PIXEL_CEL_TONE_SHADOW;
    }
    int tone;
    if(use_ramp)
    {
        t = texture(ramp, clamp(s, 0.0, 1.0)).r;
        tone = t < 0.25 ? PIXEL_CEL_TONE_SHADOW : (t < 0.75 ? PIXEL_CEL_TONE_MID : PIXEL_CEL_TONE_LIT);
    }
    else
    {
        bool lit = s > threshold;
        t = lit ? 1.0 : 0.0;
        tone = lit ? PIXEL_CEL_TONE_LIT : PIXEL_CEL_TONE_SHADOW;
    }
    if(tone == PIXEL_CEL_TONE_LIT)
    {
        if(s > highlight_threshold)
        {
            tone = PIXEL_CEL_TONE_HIGHLIGHT;
        }
        float exponent = mix(4.0, 128.0, spec_size);
        if(spec_mask > 0.0 && spec_mask * pow(max(n_dot_h, 0.0), exponent) > spec_threshold)
        {
            tone = PIXEL_CEL_TONE_HIGHLIGHT;
        }
    }
    return tone;
}

int _pixel_cel_zone(sampler2D atlas, ivec2 size0, int levels, vec2 uv, float bias)
{
    // Level from the screen footprint of one pixel in level-0 texels (like GL's LOD), plus the material's bias.
    // The atlas holds the majority-vote levels side by side (level l at x = sum of the widths below l), read exactly.
    vec2 t = uv * vec2(size0);
    #ifdef PIXEL_SHADER
    float rho = max(length(dFdx(t)), length(dFdy(t)));
    #else
    float rho = 1.0;   // no derivatives outside the pixel stage
    #endif
    int level = clamp(int(floor(log2(max(rho, 1e-6)) + bias + 0.5)), 0, levels - 1);
    int x0 = 0;
    ivec2 size = size0;
    for(int l = 0; l < level; l++)
    {
        x0 += size.x;
        size = max((size + 1) / 2, ivec2(1));
    }
    ivec2 texel = clamp(ivec2(floor(fract(uv) * vec2(size))), ivec2(0), size - 1);
    // numpy builds the atlas top-down with every level at the top (rows 0..h_l-1); Blender stores images bottom-up,
    // so in GL rows level l spans size0.y - size.y .. size0.y - 1, and uv.y = 0 is the level's bottom row.
    return int(round(texelFetch(atlas, ivec2(x0 + texel.x, size0.y - size.y + texel.y), 0).r * 255.0));
}

int _pixel_cel_slot(sampler2D palette, int row, float s, bool shadowed, bool highlight, out int n_slots)
{
    vec4 meta = texelFetch(palette, ivec2(0, 2 * row + 1), 0);
    n_slots = int(round(meta.g * 255.0));
    if(shadowed) return n_slots - 1;
    if(highlight) return 0;
    int slot = 0;
    for(int i = 0; i < n_slots - 1; i++)
    {
        if(s < texelFetch(palette, ivec2(i, 2 * row + 1), 0).r) slot++;
    }
    return min(slot, n_slots - 1);
}

// Palette colours for the pixel's zone (spec 09 section 5). unlit: slot 1 (lit) of the ramp.
void _pixel_cel_palette(sampler2D zone_texture, ivec2 zone_size, int zone_levels, float zone_lod_bias,
    sampler2D palette, vec2 uv, bool unlit, float s, bool shadowed, bool highlight, bool outline_shadow_only,
    inout vec4 color, inout vec4 line_color, inout vec4 line_data)
{
    int zone = _pixel_cel_zone(zone_texture, zone_size, zone_levels, uv, zone_lod_bias);
    if(zone > 0)
    {
        int row = zone - 1, n_slots;
        int slot = _pixel_cel_slot(palette, row, s, shadowed, highlight, n_slots);
        if(unlit) slot = min(1, n_slots - 1);
        color = vec4(texelFetch(palette, ivec2(slot, 2 * row), 0).rgb, color.a);
        line_color = vec4(texelFetch(palette, ivec2(7, 2 * row), 0).rgb, 1.0);
        line_data.z = outline_shadow_only ? (slot != n_slots - 1 ? 1.0 : 0.5) : 0.0;
        line_data.w = 0.5;
    }
}

/*  META
    @meta: label=Pixel Cel;
    @base_color: subtype=Color; default=vec4(1.0);
    @use_base_texture: default=false;
    @use_shadow_texture: default=false;
    @use_ilm_texture: default=false;
    @use_cutout: default=false;
    @cutout: default=0.5;
    @uv_index: default=0;
    @use_vertex_color: default=false;
    @vertex_color_index: default=0;
    @nearest: default=false;
    @shadow_tint: subtype=Color; default=vec3(0.55, 0.5, 0.7);
    @shadow_from_hue_shift: default=false;
    @hue_shift: default=15.0;
    @shadow_saturation: default=1.25;
    @shadow_value: default=0.55;
    @threshold: default=0.5;
    @use_ramp: default=false;
    @spec_threshold: default=0.5;
    @spec_boost: default=1.3;
    @highlight_threshold: default=2.0;
    @highlight_color: subtype=Color; default=vec3(1.0, 0.97, 0.9);
    @highlight_mix: default=0.0;
    @outline_from_base: default=false;
    @outline_value: default=0.1;
    @outline_shadow_only: default=false;
    @keep_junctions: default=false;
    @keep_tips: default=false;
    @keep_overlap_corners: default=false;
    @unlit: default=false;
    @light_group: default=1;
    @shadows: default=true;
    @self_shadows: default=true;
    @use_palette: default=false;
    @zone_size: default=ivec2(1, 1);
    @zone_levels: default=1;
    @zone_lod_bias: default=0.0;
*/
void pixel_cel(
    vec4 base_color, bool use_base_texture, sampler2D base_texture,
    bool use_shadow_texture, sampler2D shadow_texture,
    bool use_ilm_texture, sampler2D ilm_texture,
    bool use_cutout, float cutout,
    int uv_index, bool use_vertex_color, int vertex_color_index, bool nearest,
    vec3 shadow_tint, bool shadow_from_hue_shift, float hue_shift, float shadow_saturation, float shadow_value,
    float threshold, bool use_ramp, sampler1D ramp,
    float spec_threshold, float spec_boost,
    float highlight_threshold, vec3 highlight_color, float highlight_mix,
    bool outline_from_base, float outline_value, bool outline_shadow_only,
    bool keep_junctions, bool keep_tips, bool keep_overlap_corners,
    bool unlit, int light_group, bool shadows, bool self_shadows,
    bool use_palette, sampler2D zone_texture, ivec2 zone_size, int zone_levels, float zone_lod_bias, sampler2D palette,
    out vec4 color, out vec4 line_color, out vec4 line_data, out int tone, out bool shadowed)
{
    vec2 uv = UV[uv_index];
    vec4 base = base_color;
    if(use_base_texture)
    {
        base *= _pixel_cel_sample(base_texture, uv, nearest);
    }
    vec3 tint = use_shadow_texture ? _pixel_cel_sample(shadow_texture, uv, nearest).rgb : shadow_tint;
    vec4 ilm = use_ilm_texture ? _pixel_cel_sample(ilm_texture, uv, nearest) : vec4(0.0, 0.5, 0.0, 1.0);
    vec4 vertex_color = use_vertex_color ? COLOR[vertex_color_index] : vec4(1.0);
    float offset = use_ilm_texture ? ilm.g * vertex_color.r - 0.5 : 0.0;
    vec3 shadow_color = shadow_from_hue_shift
        ? _pixel_cel_shifted_shadow(base.rgb, hue_shift, shadow_saturation, shadow_value)
        : base.rgb * tint;

    line_color = vec4(outline_from_base ? base.rgb * outline_value : vec3(outline_value), 1.0);
    float rule_bits = float(((use_vertex_color && vertex_color.a < 0.5) ? 0 : 1) | (keep_junctions ? 2 : 0) | (keep_tips ? 4 : 0)
        | (keep_overlap_corners ? 8 : 0));
    line_data = vec4(use_ilm_texture ? ilm.a : 1.0, rule_bits, 0.0, 1.0);
    shadowed = false;

    if(unlit)
    {
        color = base;
        tone = PIXEL_CEL_TONE_LIT;
        line_data.z = outline_shadow_only ? 1.0 : 0.0;
        if(use_palette)
        {
            _pixel_cel_palette(zone_texture, zone_size, zone_levels, zone_lod_bias, palette, uv, true, 0.0, false,
                false, outline_shadow_only, color, line_color, line_data);
        }
        return;
    }

    tone = -1;
    float best_t = 0.0;
    float best_s = 0.0;
    for(int i = 0; i < LIGHTS.lights_count; i++)
    {
        if(LIGHT_GROUP_INDEX(i) != light_group)
        {
            continue;
        }
        Light L = LIGHTS.lights[i];
        LitSurface LS = npr_lit_surface(POSITION, NORMAL, ID.x, L, i, shadows, self_shadows);
        bool light_shadowed = shadows && LS.shadow;
        shadowed = shadowed || light_shadowed;
        float t, light_s;
        int light_tone = _pixel_cel_tone(LS.NoL, dot(NORMAL, LS.H), offset, threshold, light_shadowed,
            use_ramp, ramp, use_ilm_texture ? ilm.r : 0.0, use_ilm_texture ? ilm.b : 0.0, spec_threshold,
            highlight_threshold, t, light_s);
        if(light_tone > tone)
        {
            tone = light_tone;
            best_t = t;
            best_s = light_s;
        }
    }
    if(tone < 0)
    {
        tone = PIXEL_CEL_TONE_SHADOW;
    }

    vec3 rgb = tone == PIXEL_CEL_TONE_HIGHLIGHT
        ? mix(base.rgb * spec_boost, highlight_color, highlight_mix)
        : mix(shadow_color, base.rgb, best_t);
    color = vec4(rgb, base.a);
    // KOF XIII: the outline keeps the pixel's own colour unless the pixel is in the darkest tone (PixelLines composite)
    line_data.z = outline_shadow_only ? (tone != PIXEL_CEL_TONE_SHADOW ? 1.0 : 0.5) : 0.0;
    if(use_palette)
    {
        _pixel_cel_palette(zone_texture, zone_size, zone_levels, zone_lod_bias, palette, uv, false, best_s,
            tone == PIXEL_CEL_TONE_SHADOW && shadowed, tone == PIXEL_CEL_TONE_HIGHLIGHT, outline_shadow_only,
            color, line_color, line_data);
    }
}

/*  META
    @meta: label=Pixel Cel Opacity;
    @use_cutout: default=false;
    @cutout: default=0.5;
*/
float pixel_cel_opacity(sampler2D texture_, int uv_index, bool use_cutout, float cutout)
{
    if(!use_cutout)
    {
        return 1.0;
    }
    return texture(texture_, UV[uv_index]).a >= cutout ? 1.0 : 0.0;
}

#define PIXEL_CEL_KEEP_BIT 1u

/*  META
    @meta: label=Pixel Cel Keep ID;
    @keep: default=false;
*/
// Pre pass ID with the KEEP bit (Pixel Lines: this part never vanishes between pixel centres)
uvec4 pixel_cel_keep_id(bool keep)
{
    uvec4 id = ID;
    if(keep)
    {
        id.w |= PIXEL_CEL_KEEP_BIT;
    }
    return id;
}

#endif //PIXEL_CEL_GLSL
