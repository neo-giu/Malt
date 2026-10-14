// Debug material for face_sdf (tools/pixelart/scenes.py: face_sdf_* setups). R = Face SDF lit, G = N.L > 0 for the
// first light (no shadows), B = 0. With an unpainted SDF both must agree: yellow = both lit, black = both shadow,
// red / green = disagreement. Textures: face_sdf_texture (pitch pack) and face_sdf_flip_texture, set by the setup
// (lowercase: Malt hides all-caps uniforms as private).
#include "NPR_MeshShader.glsl"

void PRE_PASS_PIXEL_SHADER(inout PrePassOutput PPO){ }
void DEPTH_OFFSET(inout float depth_offset, inout bool offset_position){ }

#ifdef MAIN_PASS
layout (location = 0) out vec4 OUT_COLOR;
layout (location = 1) out vec4 OUT_LINE_COLOR;
layout (location = 2) out vec4 OUT_LINE_WIDTH;
uniform sampler2D face_sdf_texture;
uniform sampler2D face_sdf_flip_texture;
#endif

void MAIN_PASS_PIXEL_SHADER()
{
    #ifdef MAIN_PASS
    {
        bool lit, shadowed;
        float h, e;
        face_sdf(face_sdf_texture, face_sdf_flip_texture, 0, true, 45.0, 45.0, true, vec3(0, -1, 0), vec3(0, 0, 1),
            1, false, false, lit, shadowed, h, e);
        LitSurface LS = npr_lit_surface(POSITION, NORMAL, ID.x, LIGHTS.lights[0], 0, false, false);
        OUT_COLOR = vec4(lit ? 1.0 : 0.0, LS.NoL > 0.0 ? 1.0 : 0.0, 0.0, 1.0);
        OUT_LINE_COLOR = vec4(0.0);
        OUT_LINE_WIDTH = vec4(0.0);
    }
    #endif
}
