// Debug material for the ray traced shadows (tools/pixelart/scenes.py: *_debug setups). Writes per pixel, for the
// first sun light:
//   R = smooth normal faces the light (dot(NORMAL, L) > 0)
//   G = npr_lit_surface says shadowed (the real code path, Ray Traced Shadows or shadow maps)
//   B = own-triangle search: 0 = not found (origin stays on the flat triangle), else 0.5 + 0.5 * min(lift / 1 px, 1)
#include "NPR_MeshShader.glsl"

void PRE_PASS_PIXEL_SHADER(inout PrePassOutput PPO){ }
void DEPTH_OFFSET(inout float depth_offset, inout bool offset_position){ }

#ifdef MAIN_PASS
layout (location = 0) out vec4 OUT_COLOR;
layout (location = 1) out vec4 OUT_LINE_COLOR;
layout (location = 2) out vec4 OUT_LINE_WIDTH;
#endif

void MAIN_PASS_PIXEL_SHADER()
{
    #ifdef MAIN_PASS
    {
        vec3 color = vec3(0.0);
        for(int i = 0; i < LIGHTS.lights_count; i++)
        {
            Light L = LIGHTS.lights[i];
            if(L.type != LIGHT_SUN)
            {
                continue;
            }
            LitSurface LS = npr_lit_surface(POSITION, NORMAL, ID.x, L, i, true, true);
            color.r = dot(NORMAL, LS.L) > 0.0 ? 1.0 : 0.0;
            color.g = LS.shadow ? 1.0 : 0.0;
            if(RAY_SHADOWS)
            {
                float pixel_size = pixel_world_size(POSITION);
                vec3 surface = ray_smooth_origin(POSITION, true_normal(), 8.0 * pixel_size, ID.x);
                color.b = surface == POSITION ? 0.0 : 0.5 + 0.5 * min(distance(surface, POSITION) / pixel_size, 1.0);
            }
            break;
        }
        OUT_COLOR = vec4(color, 1.0);
        OUT_LINE_COLOR = vec4(0.0);
        OUT_LINE_WIDTH = vec4(0.0);
    }
    #endif
}
