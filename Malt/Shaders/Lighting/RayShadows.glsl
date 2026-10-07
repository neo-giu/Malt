#ifndef RAY_SHADOWS_GLSL
#define RAY_SHADOWS_GLSL

#include "Common.glsl"

/* META GLOBAL
    @meta: internal=true;
*/

// Layouts must match Malt/Render/RayBVH.py (BVH.nodes, BVH.tris, BVH.info). Bindings are fixed.
struct RayNode
{
    vec3 bmin;
    uint a;// leaf: first triangle. inner: right child index.
    vec3 bmax;
    uint b;// leaf: triangle count (> 0). inner: 0, the left child is this node + 1.
};

layout(std430, binding = 0) readonly buffer RAY_BVH_NODES
{
    RayNode RAY_NODES[];
};

layout(std430, binding = 1) readonly buffer RAY_TRIANGLES
{
    vec4 RAY_TRIS[];// 4 per triangle: v0, v1, v2, padding
};

layout(std430, binding = 2) readonly buffer RAY_TRIANGLE_INFO
{
    uvec4 RAY_INFO[];// object id, shadow group bitmask, 0, 0
};

uniform bool RAY_SHADOWS;
uniform float RAY_BIAS_PX;

// World size of one pixel at this position
float pixel_world_size(vec3 position)
{
    if(PROJECTION[3][3] == 1.0)
    {
        return 2.0 / (PROJECTION[1][1] * float(RESOLUTION.y));
    }
    float depth = length((CAMERA * vec4(position, 1.0)).xyz);
    return 2.0 * depth / (PROJECTION[1][1] * float(RESOLUTION.y));
}

// Watertight ray/triangle test (Woop, Benthin, Wald 2013), two-sided. Same as RayBVH._hit_triangles.
bool ray_triangle_hit(vec3 v0, vec3 v1, vec3 v2, vec3 origin, int kx, int ky, int kz, float sx, float sy, float sz, float t_max)
{
    vec3 a = v0 - origin;
    vec3 b = v1 - origin;
    vec3 c = v2 - origin;

    float ax = a[kx] - sx * a[kz];
    float ay = a[ky] - sy * a[kz];
    float bx = b[kx] - sx * b[kz];
    float by = b[ky] - sy * b[kz];
    float cx = c[kx] - sx * c[kz];
    float cy = c[ky] - sy * c[kz];

    float u = cx * by - cy * bx;
    float v = ax * cy - ay * cx;
    float w = bx * ay - by * ax;

    if(u == 0.0 || v == 0.0 || w == 0.0)
    {
        double dsx = double(sx);
        double dsy = double(sy);
        double dax = double(a[kx]) - dsx * double(a[kz]);
        double day = double(a[ky]) - dsy * double(a[kz]);
        double dbx = double(b[kx]) - dsx * double(b[kz]);
        double dby = double(b[ky]) - dsy * double(b[kz]);
        double dcx = double(c[kx]) - dsx * double(c[kz]);
        double dcy = double(c[ky]) - dsy * double(c[kz]);
        u = float(dcx * dby - dcy * dbx);
        v = float(dax * dcy - day * dcx);
        w = float(dbx * day - dby * dax);
    }

    if((u < 0.0 || v < 0.0 || w < 0.0) && (u > 0.0 || v > 0.0 || w > 0.0))
    {
        return false;
    }

    float det = u + v + w;
    if(det == 0.0)
    {
        return false;
    }

    float t_scaled = u * (sz * a[kz]) + v * (sz * b[kz]) + w * (sz * c[kz]);
    float t = t_scaled / det;
    return t > 0.0 && t <= t_max;
}

// Any-hit traversal. Same as RayBVH.occluded_ref. direction does not need to be normalized.
bool ray_occluded(vec3 origin, vec3 dir, float t_max, uint self_id, bool self_shadows, uint light_group_bit)
{
    vec3 adir = abs(dir);
    // First maximum, like numpy argmax
    int kz = 0;
    if(adir.y > adir[kz]) kz = 1;
    if(adir.z > adir[kz]) kz = 2;
    int kx = (kz + 1) % 3;
    int ky = (kx + 1) % 3;
    if(dir[kz] < 0.0)
    {
        int swap = kx;
        kx = ky;
        ky = swap;
    }
    float sx = dir[kx] / dir[kz];
    float sy = dir[ky] / dir[kz];
    float sz = 1.0 / dir[kz];

    vec3 safe_dir = mix(dir, vec3(1e-30), equal(dir, vec3(0.0)));
    vec3 inv = 1.0 / safe_dir;

    int stack[48];
    int stack_size = 0;
    stack[stack_size++] = 0;

    while(stack_size > 0)
    {
        int i = stack[--stack_size];
        RayNode node = RAY_NODES[i];

        if(any(greaterThan(node.bmin, node.bmax)))
        {
            continue;
        }

        vec3 t0 = (node.bmin - origin) * inv;
        vec3 t1 = (node.bmax - origin) * inv;
        float t_near = max(max(min(t0.x, t1.x), min(t0.y, t1.y)), min(t0.z, t1.z));
        float t_far = min(min(max(t0.x, t1.x), max(t0.y, t1.y)), max(t0.z, t1.z)) * 1.0000005;
        if(!(max(t_near, 0.0) <= min(t_far, t_max)))
        {
            continue;
        }

        if(node.b > 0u)
        {
            for(uint t = node.a; t < node.a + node.b; t++)
            {
                uvec4 info = RAY_INFO[t];
                if((info.y & light_group_bit) == 0u)
                {
                    continue;
                }
                if(!self_shadows && info.x == self_id)
                {
                    continue;
                }
                if(ray_triangle_hit(RAY_TRIS[t*4u].xyz, RAY_TRIS[t*4u+1u].xyz, RAY_TRIS[t*4u+2u].xyz,
                    origin, kx, ky, kz, sx, sy, sz, t_max))
                {
                    return true;
                }
            }
        }
        else
        {
            stack[stack_size++] = int(node.a);
            stack[stack_size++] = i + 1;
        }
    }
    return false;
}

#endif //RAY_SHADOWS_GLSL
