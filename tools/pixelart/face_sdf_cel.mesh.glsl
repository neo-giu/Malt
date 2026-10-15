// Look comparison (tools/pixelart/scenes.py: face_cel_* setups). Pixel Cel Face SDF; with FACE_SDF_PLAIN defined
// (face_sdf_plain.mesh.glsl) plain
// Pixel Cel (threshold 0.5, no ramp, the current working-tree signature). Same colours for both: white base, default
// shadow tint, no lines.
#include "NPR_MeshShader.glsl"

void PRE_PASS_PIXEL_SHADER(inout PrePassOutput PPO){ }
void DEPTH_OFFSET(inout float depth_offset, inout bool offset_position){ }

#ifdef MAIN_PASS
layout (location = 0) out vec4 OUT_COLOR;
layout (location = 1) out vec4 OUT_LINE_COLOR;
layout (location = 2) out vec4 OUT_LINE_WIDTH;
uniform sampler2D face_sdf_texture;
uniform sampler2D face_sdf_flip_texture;
uniform sampler2D NO_TEXTURE;
uniform sampler1D NO_RAMP_1D;
#endif

void MAIN_PASS_PIXEL_SHADER()
{
    #ifdef MAIN_PASS
    {
        vec4 color, line_color, line_data;
        int tone;
        bool shadowed;
        #ifndef FACE_SDF_PLAIN
        {
            pixel_cel_face_sdf(vec4(1), false, NO_TEXTURE, false, NO_TEXTURE, 0, false,
                vec3(0.55, 0.5, 0.7), false, 15.0, 1.25, 0.55,
                face_sdf_texture, face_sdf_flip_texture, true, 45.0, 45.0, true, vec3(0, -1, 0), vec3(0, 0, 1),
                false, 0.1, false, false, false, false, false, 1, true, false,
                color, line_color, line_data, tone, shadowed);
        }
        #else
        {
            vec4 ld;
            pixel_cel(vec4(1), false, NO_TEXTURE, false, NO_TEXTURE, false, NO_TEXTURE, false, 0.5,
                0, false, 0, false,
                vec3(0.55, 0.5, 0.7), false, 15.0, 1.25, 0.55,
                0.5, false, NO_RAMP_1D,
                0.5, 1.3,
                2.0, vec3(1.0, 0.97, 0.9), 0.0,
                false, 0.1, false,
                false, false, false,
                false, 1, true, true,
                false, NO_TEXTURE, ivec2(1, 1), 1, 0.0, NO_TEXTURE,
                color, line_color, ld, tone, shadowed);
        }
        #endif
        OUT_COLOR = color;
        OUT_LINE_COLOR = vec4(0.0);
        OUT_LINE_WIDTH = vec4(0.0);
    }
    #endif
}
