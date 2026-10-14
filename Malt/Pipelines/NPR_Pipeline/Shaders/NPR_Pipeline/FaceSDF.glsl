// Malt/Pipelines/NPR_Pipeline/Shaders/NPR_Pipeline/FaceSDF.glsl
#ifndef FACE_SDF_GLSL
#define FACE_SDF_GLSL

#include "NPR_Lighting.glsl"
#include "PixelCel.glsl"

/*  META GLOBAL
    @meta: category=Shading;
*/

// Face SDF: anime face shadows from an angle-encoded SDF texture (CL SDF Tools, Pixelizer fork with pitch levels).
// Texture conventions (Pixelizer third_party/src/cl_sdf_tools/README.md, "Pixelizer fork changes"):
//   - export with Invert on: lit when sdf >= 1 - h/180, h = horizontal light angle, 0 = behind, 180 = front
//   - 0 is reserved for "always in shadow"
//   - the main texture covers light on the head's left (+X of a -Y facing head), the Flip texture the right
//   - pitch pack: R = level, G = light from above, B = light from below
// Textures are read texel-exact (no filtering), so the shadow edge is hard.

float _face_sdf_fetch(sampler2D tex, vec2 uv, int channel)
{
    ivec2 size = textureSize(tex, 0);
    ivec2 texel = clamp(ivec2(floor(fract(uv) * vec2(size))), ivec2(0), size - 1);
    return texelFetch(tex, texel, 0)[channel];
}

// Head frame in world space. forward = where the face looks, up = top of the head.
// Object axes: the Blender default head faces -Y with +Z up. Armature-deformed heads do not rotate MODEL:
// feed the head bone axes instead (for example with drivers on the inputs).
void _face_sdf_frame(bool use_object_axes, vec3 forward, vec3 up, out vec3 F, out vec3 U, out vec3 X)
{
    if(use_object_axes)
    {
        forward = (MODEL * vec4(0.0, -1.0, 0.0, 0.0)).xyz;
        up = (MODEL * vec4(0.0, 0.0, 1.0, 0.0)).xyz;
    }
    F = normalize(forward);
    U = normalize(up - F * dot(up, F));
    X = cross(U, F);   // the head's left: +X for a -Y facing, +Z up head
}

// Horizontal angle (0 = behind, 180 = front, negative = light on the right side) and elevation in degrees
void _face_sdf_angles(vec3 L, vec3 F, vec3 U, vec3 X, out float horizontal, out float elevation)
{
    horizontal = degrees(atan(dot(L, X), -dot(L, F)));
    elevation = degrees(asin(clamp(dot(L, U), -1.0, 1.0)));
}

// Lit test for one light direction L (surface to light, world space)
bool _face_sdf_lit(sampler2D sdf_texture, sampler2D flip_texture, vec2 uv, bool pitch_levels,
    float above_angle, float below_angle, vec3 L, vec3 F, vec3 U, vec3 X, out float sdf, out float threshold)
{
    float h, e;
    _face_sdf_angles(L, F, U, X, h, e);
    bool flip = h < 0.0;
    h = abs(h);
    float level = flip ? _face_sdf_fetch(flip_texture, uv, 0) : _face_sdf_fetch(sdf_texture, uv, 0);
    sdf = level;
    if(pitch_levels)
    {
        if(e >= 0.0)
        {
            float g = flip ? _face_sdf_fetch(flip_texture, uv, 1) : _face_sdf_fetch(sdf_texture, uv, 1);
            sdf = mix(level, g, clamp(e / max(above_angle, 1e-3), 0.0, 1.0));
        }
        else
        {
            float b = flip ? _face_sdf_fetch(flip_texture, uv, 2) : _face_sdf_fetch(sdf_texture, uv, 2);
            sdf = mix(level, b, clamp(-e / max(below_angle, 1e-3), 0.0, 1.0));
        }
    }
    threshold = 1.0 - h / 180.0;
    return sdf > 0.0 && sdf >= threshold;
}

/*  META
    @meta: label=Face SDF;
    @uv_index: default=0;
    @pitch_levels: default=true;
    @above_angle: default=45.0;
    @below_angle: default=45.0;
    @use_object_axes: default=true;
    @head_forward: default=vec3(0.0, -1.0, 0.0);
    @head_up: default=vec3(0.0, 0.0, 1.0);
    @light_group: default=1;
    @shadows: default=true;
    @self_shadows: default=false;
*/
void face_sdf(
    sampler2D sdf_texture, sampler2D flip_texture, int uv_index,
    bool pitch_levels, float above_angle, float below_angle,
    bool use_object_axes, vec3 head_forward, vec3 head_up,
    int light_group, bool shadows, bool self_shadows,
    out bool lit, out bool shadowed, out float horizontal_angle, out float elevation)
{
    vec3 F, U, X;
    _face_sdf_frame(use_object_axes, head_forward, head_up, F, U, X);
    vec2 uv = UV[uv_index];
    lit = false;
    shadowed = false;
    horizontal_angle = 0.0;
    elevation = 0.0;
    bool first = true;
    for(int i = 0; i < LIGHTS.lights_count; i++)
    {
        if(LIGHT_GROUP_INDEX(i) != light_group)
        {
            continue;
        }
        Light light = LIGHTS.lights[i];
        LitSurface LS = npr_lit_surface(POSITION, NORMAL, ID.x, light, i, shadows, self_shadows);
        if(first)
        {
            _face_sdf_angles(LS.L, F, U, X, horizontal_angle, elevation);
            first = false;
        }
        bool light_shadowed = shadows && LS.shadow;
        shadowed = shadowed || light_shadowed;
        float sdf, threshold;
        bool light_lit = _face_sdf_lit(sdf_texture, flip_texture, uv, pitch_levels, above_angle, below_angle,
            LS.L, F, U, X, sdf, threshold);
        lit = lit || (light_lit && !light_shadowed);
    }
}

/*  META
    @meta: label=Pixel Cel Face SDF;
    @base_color: subtype=Color; default=vec4(1.0);
    @use_base_texture: default=false;
    @use_shadow_texture: default=false;
    @uv_index: default=0;
    @nearest: default=false;
    @shadow_tint: subtype=Color; default=vec3(0.55, 0.5, 0.7);
    @shadow_from_hue_shift: default=false;
    @hue_shift: default=15.0;
    @shadow_saturation: default=1.25;
    @shadow_value: default=0.55;
    @pitch_levels: default=true;
    @above_angle: default=45.0;
    @below_angle: default=45.0;
    @use_object_axes: default=true;
    @head_forward: default=vec3(0.0, -1.0, 0.0);
    @head_up: default=vec3(0.0, 0.0, 1.0);
    @outline_from_base: default=false;
    @outline_value: default=0.1;
    @unlit: default=false;
    @light_group: default=1;
    @shadows: default=true;
    @self_shadows: default=false;
*/
// Same colour rules and outputs as Pixel Cel, but the lit/shadow decision comes from the face SDF instead of N.L,
// so the nose and cheeks do not throw stray shadow pixels. Two tones only (shadow, lit).
void pixel_cel_face_sdf(
    vec4 base_color, bool use_base_texture, sampler2D base_texture,
    bool use_shadow_texture, sampler2D shadow_texture,
    int uv_index, bool nearest,
    vec3 shadow_tint, bool shadow_from_hue_shift, float hue_shift, float shadow_saturation, float shadow_value,
    sampler2D sdf_texture, sampler2D flip_texture,
    bool pitch_levels, float above_angle, float below_angle,
    bool use_object_axes, vec3 head_forward, vec3 head_up,
    bool outline_from_base, float outline_value,
    bool unlit, int light_group, bool shadows, bool self_shadows,
    out vec4 color, out vec4 line_color, out vec4 line_data, out int tone, out bool shadowed)
{
    vec2 uv = UV[uv_index];
    vec4 base = base_color;
    if(use_base_texture)
    {
        base *= _pixel_cel_sample(base_texture, uv, nearest);
    }
    vec3 tint = use_shadow_texture ? _pixel_cel_sample(shadow_texture, uv, nearest).rgb : shadow_tint;
    vec3 shadow_color = shadow_from_hue_shift
        ? _pixel_cel_shifted_shadow(base.rgb, hue_shift, shadow_saturation, shadow_value)
        : base.rgb * tint;

    line_color = vec4(outline_from_base ? base.rgb * outline_value : vec3(outline_value), 1.0);
    line_data = vec4(1.0, 1.0, 0.0, 1.0);
    shadowed = false;

    if(unlit)
    {
        color = base;
        tone = PIXEL_CEL_TONE_LIT;
        return;
    }

    bool lit;
    float horizontal_angle, elevation;
    face_sdf(sdf_texture, flip_texture, uv_index, pitch_levels, above_angle, below_angle,
        use_object_axes, head_forward, head_up, light_group, shadows, self_shadows,
        lit, shadowed, horizontal_angle, elevation);
    tone = lit ? PIXEL_CEL_TONE_LIT : PIXEL_CEL_TONE_SHADOW;
    color = vec4(lit ? base.rgb : shadow_color, base.a);
}

#endif //FACE_SDF_GLSL
