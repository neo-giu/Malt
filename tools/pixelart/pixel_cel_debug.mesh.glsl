// Debug material for pixel_cel (tools/pixelart/scenes.py: pixel_cel_debug). R = tone / 3, G = s of the first sun,
// B = shadowed. No textures, threshold 0.5, no ramp: compare with tools/pixelart/compare_cel.py.
#include "NPR_MeshShader.glsl"

void PRE_PASS_PIXEL_SHADER(inout PrePassOutput PPO){ }
void DEPTH_OFFSET(inout float depth_offset, inout bool offset_position){ }

#ifdef MAIN_PASS
layout (location = 0) out vec4 OUT_COLOR;
layout (location = 1) out vec4 OUT_LINE_COLOR;
layout (location = 2) out vec4 OUT_LINE_WIDTH;
uniform sampler2D DEBUG_TEXTURE;
uniform sampler1D DEBUG_RAMP;
#endif

void MAIN_PASS_PIXEL_SHADER()
{
    #ifdef MAIN_PASS
    {
        vec4 color, line_color, line_data;
        int tone;
        bool shadowed;
        pixel_cel(vec4(1), false, DEBUG_TEXTURE, false, DEBUG_TEXTURE, false, DEBUG_TEXTURE, false, 0.5,
            0, false, 0, false,
            vec3(0.55, 0.5, 0.7), false, 15.0, 1.25, 0.55,
            0.5, false, DEBUG_RAMP,
            0.5, 1.3,
            2.0, vec3(1.0, 0.97, 0.9), 0.0,
            false, 0.1, false,
            false, 1, true, true,
            color, line_color, line_data, tone, shadowed);
        float s = 0.0;
        for(int i = 0; i < LIGHTS.lights_count; i++)
        {
            if(LIGHTS.lights[i].type == LIGHT_SUN)
            {
                s = dot(NORMAL, -LIGHTS.lights[i].direction) * 0.5 + 0.5;
                break;
            }
        }
        OUT_COLOR = vec4(float(tone) / 3.0, s, shadowed ? 1.0 : 0.0, 1.0);
        // The Standard view transform encodes to sRGB: pre-decode so the PNG holds the raw values
        OUT_COLOR.rgb = srgb_to_linear(OUT_COLOR.rgb);
        OUT_LINE_COLOR = vec4(0.0);
        OUT_LINE_WIDTH = vec4(0.0);
    }
    #endif
}
