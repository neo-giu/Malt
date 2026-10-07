#ifndef NPR_LIGHTING_GLSL
#define NPR_LIGHTING_GLSL

#include "Lighting/Lighting.glsl"
#include "Lighting/RayShadows.glsl"

uniform usampler2DArray SHADOWMAPS_ID_SPOT;
uniform usampler2DArray SHADOWMAPS_ID_SUN;
uniform usamplerCubeArray SHADOWMAPS_ID_POINT;

uniform sampler2DArray TRANSPARENT_SHADOWMAPS_DEPTH_SPOT;
uniform sampler2DArray TRANSPARENT_SHADOWMAPS_DEPTH_SUN;
uniform samplerCubeArray TRANSPARENT_SHADOWMAPS_DEPTH_POINT;

uniform usampler2DArray TRANSPARENT_SHADOWMAPS_ID_SPOT;
uniform usampler2DArray TRANSPARENT_SHADOWMAPS_ID_SUN;
uniform usamplerCubeArray TRANSPARENT_SHADOWMAPS_ID_POINT;

uniform sampler2DArray TRANSPARENT_SHADOWMAPS_COLOR_SPOT;
uniform sampler2DArray TRANSPARENT_SHADOWMAPS_COLOR_SUN;
uniform samplerCubeArray TRANSPARENT_SHADOWMAPS_COLOR_POINT;

layout(std140) uniform LIGHT_GROUPS
{
    //Use ivec4 so the ints are tightly packed
    ivec4 LIGHT_GROUP_INDEX[MAX_LIGHTS/4+1];
};
#define LIGHT_GROUP_INDEX(light_index) LIGHT_GROUP_INDEX[(light_index)/4][(light_index)%4]

layout(std140) uniform LIGHTS_CUSTOM_SHADING
{
    //Use ivec4 so the ints are tightly packed
    ivec4 CUSTOM_SHADING_INDEX[MAX_LIGHTS/4+1];
};
#define CUSTOM_SHADING_INDEX(light_index) CUSTOM_SHADING_INDEX[(light_index)/4][(light_index)%4];

uniform sampler2DArray IN_LIGHT_CUSTOM_SHADING;

/*  META
    @meta: internal=true;
    @position: subtype=Vector; default=POSITION;
    @normal: subtype=Normal; default=NORMAL;
    @id: default=ID[0];
*/
LitSurface npr_lit_surface(vec3 position, vec3 normal, uint id, Light light, int light_index, bool shadows, bool self_shadows)
{
    LitSurface S = lit_surface(position, normal, light, false);

    S.light_color = light.color * S.P;

    int custom_shading_index = CUSTOM_SHADING_INDEX(light_index);
    if(custom_shading_index >= 0)
    {
        S.light_color = texelFetch(IN_LIGHT_CUSTOM_SHADING, ivec3(screen_pixel(), custom_shading_index), 0).rgb;
    }

    if(!shadows)
    {
        return S;
    }

    if(light.type_index >= 0)
    {
        float bias = 1e-5;

        //Opaque shadow
        ShadowData shadow;
        uint shadow_id;
        //Transparent shadow
        ShadowData t_shadow;
        vec3 t_shadow_multiply;
        uint t_shadow_id;
        
        if(light.type == LIGHT_SPOT)
        {
            shadow = spot_shadow(position, light, SHADOWMAPS_DEPTH_SPOT, bias);
            vec2 uv = shadow.light_uv.xy;
            int index = light.type_index;

            if(!RAY_SHADOWS)
            {
                shadow_id = texture(SHADOWMAPS_ID_SPOT, vec3(uv, index)).x;
            }

            t_shadow = spot_shadow(position, light, TRANSPARENT_SHADOWMAPS_DEPTH_SPOT, bias);

            t_shadow_multiply = texture(TRANSPARENT_SHADOWMAPS_COLOR_SPOT, vec3(uv, index)).rgb;
            t_shadow_id = texture(TRANSPARENT_SHADOWMAPS_ID_SPOT, vec3(uv, index)).x;
        }
        if(light.type == LIGHT_SUN)
        {
            bias = 1e-3;
            
            shadow = sun_shadow(position, light, SHADOWMAPS_DEPTH_SUN, bias, S.cascade);
            vec2 uv = shadow.light_uv.xy;
            int index = light.type_index * LIGHTS.cascades_count + S.cascade;

            if(!RAY_SHADOWS)
            {
                shadow_id = texture(SHADOWMAPS_ID_SUN, vec3(uv, index)).x;
            }

            t_shadow = sun_shadow(position, light, TRANSPARENT_SHADOWMAPS_DEPTH_SUN, bias, S.cascade);

            t_shadow_multiply = texture(TRANSPARENT_SHADOWMAPS_COLOR_SUN, vec3(uv, index)).rgb;
            t_shadow_id = texture(TRANSPARENT_SHADOWMAPS_ID_SUN, vec3(uv, index)).x;
        }
        if(light.type == LIGHT_POINT)
        {
            shadow = point_shadow(position, light, SHADOWMAPS_DEPTH_POINT, bias);
            vec3 uv = shadow.light_uv;
            int index = light.type_index;

            if(!RAY_SHADOWS)
            {
                shadow_id = texture(SHADOWMAPS_ID_POINT, vec4(uv, index)).x;
            }

            t_shadow = point_shadow(position, light, TRANSPARENT_SHADOWMAPS_DEPTH_POINT, bias);

            t_shadow_multiply = texture(TRANSPARENT_SHADOWMAPS_COLOR_POINT, vec4(uv, index)).rgb;
            t_shadow_id = texture(TRANSPARENT_SHADOWMAPS_ID_POINT, vec4(uv, index)).x;
        }

        if(RAY_SHADOWS)
        {
            // One exact yes/no ray per pixel and light. The bias is the same number of pixels everywhere.
            vec3 geometric_normal = true_normal();
            float pixel_size = pixel_world_size(position);
            // Start on the smooth shadow surface (Phong tessellated BVH), found along the geometric normal within
            // 8 px, then lifted onto the vertex-normal surface (shadow terminator)
            vec3 surface = ray_smooth_origin(position, geometric_normal, 8.0 * pixel_size, id);
            if(dot(geometric_normal, S.L) < 0.0)
            {
                geometric_normal = -geometric_normal;
            }
            // Only a tiny normal offset (float safety). The real bias is a minimum hit distance along the ray, on
            // the receiver's own object: it ignores self-intersection without moving any shadow edge.
            vec3 ray_origin = surface + geometric_normal * 0.01 * pixel_size;
            vec3 ray_dir = -light.direction;
            float ray_t_max = 1e30;
            if(light.type != LIGHT_SUN)
            {
                vec3 to_light = light.position - ray_origin;
                float light_distance = length(to_light);
                ray_dir = to_light / max(light_distance, 1e-20);
                ray_t_max = light_distance * (1.0 - 1e-4);
            }
            int light_group = LIGHT_GROUP_INDEX(light_index);
            uint light_group_bit = (light_group >= 0 && light_group < 32) ? (1u << uint(light_group)) : 0u;
            float ray_dir_length = length(ray_dir);
            S.shadow = ray_occluded(ray_origin, ray_dir, ray_t_max, id, self_shadows, light_group_bit,
                RAY_BIAS_PX * pixel_size / max(ray_dir_length, 1e-20));
        }
        else
        {
            S.shadow = shadow.shadow;

            if(self_shadows == false && id == shadow_id)
            {
                S.shadow = false;
            }
        }
        
        S.shadow_multiply = S.shadow ? vec3(0) : vec3(1);

        if(!S.shadow && t_shadow.shadow)
        {
            if(self_shadows == false && id == t_shadow_id)
            {
                t_shadow.shadow = false;
            }

            if(t_shadow.shadow)
            {
                S.shadow = true;
                S.shadow_multiply = t_shadow_multiply;
            }
        }
    }

    return S;
}

#endif //NPR_LIGHTING_GLSL
