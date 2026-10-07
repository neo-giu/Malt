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

layout(std430, binding = 3) readonly buffer RAY_TRIANGLE_NORMALS
{
    vec4 RAY_NORMALS[];// 3 per triangle: world vertex normals n0, n1, n2 (w = 0)
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
bool ray_triangle_hit(vec3 v0, vec3 v1, vec3 v2, vec3 origin, int kx, int ky, int kz, float sx, float sy, float sz, float t_max,
    out float t, out vec3 barycentric)
{
    t = 0.0;
    barycentric = vec3(0.0);
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
    t = t_scaled / det;
    barycentric = vec3(u, v, w) / det;
    return t > 0.0 && t <= t_max;
}

void ray_setup(vec3 dir, out int kx, out int ky, out int kz, out float sx, out float sy, out float sz)
{
    vec3 adir = abs(dir);
    // First maximum, like numpy argmax
    kz = 0;
    if(adir.y > adir[kz]) kz = 1;
    if(adir.z > adir[kz]) kz = 2;
    kx = (kz + 1) % 3;
    ky = (kx + 1) % 3;
    if(dir[kz] < 0.0)
    {
        int swap = kx;
        kx = ky;
        ky = swap;
    }
    sx = dir[kx] / dir[kz];
    sy = dir[ky] / dir[kz];
    sz = 1.0 / dir[kz];
}

// Any-hit traversal. Same as RayBVH.occluded_ref. direction does not need to be normalized.
// Hits on object self_id with t <= self_t_min are ignored (self-intersection bias along the ray, not along the normal,
// so the bias never moves a shadow edge).
bool ray_occluded(vec3 origin, vec3 dir, float t_max, uint self_id, bool self_shadows, uint light_group_bit,
    float self_t_min)
{
    int kx, ky, kz;
    float sx, sy, sz;
    ray_setup(dir, kx, ky, kz, sx, sy, sz);

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
                float hit_t;
                vec3 hit_barycentric;
                if(ray_triangle_hit(RAY_TRIS[t*4u].xyz, RAY_TRIS[t*4u+1u].xyz, RAY_TRIS[t*4u+2u].xyz,
                    origin, kx, ky, kz, sx, sy, sz, t_max, hit_t, hit_barycentric))
                {
                    if(info.x != self_id || hit_t > self_t_min)
                    {
                        return true;
                    }
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

// Shadow terminator fix (Hanika 2021, "Hacking the shadow terminator"). Moves a point of a flat triangle onto the
// smooth surface its vertex normals describe: P' = P - sum(b_i * min(0, dot(P - V_i, n_i)) * n_i).
// Same as RayGeometry.smooth_surface_point.
vec3 smooth_surface_point(vec3 P, vec3 v0, vec3 v1, vec3 v2, vec3 n0, vec3 n1, vec3 n2, vec3 b)
{
    vec3 offset = vec3(0.0);
    offset += b.x * min(0.0, dot(P - v0, n0)) * n0;
    offset += b.y * min(0.0, dot(P - v1, n1)) * n1;
    offset += b.z * min(0.0, dot(P - v2, n2)) * n2;
    return P - offset;
}

// Finds the triangle of object self_id under the surface point P (closest-hit along -geometric_normal, from
// P + geometric_normal * search) and returns P moved onto the smooth surface. Returns P if no triangle is found.
vec3 ray_smooth_origin(vec3 P, vec3 geometric_normal, float search, uint self_id)
{
    vec3 origin = P + geometric_normal * search;
    vec3 dir = -geometric_normal;
    float t_max = 2.0 * search;

    int kx, ky, kz;
    float sx, sy, sz;
    ray_setup(dir, kx, ky, kz, sx, sy, sz);
    vec3 safe_dir = mix(dir, vec3(1e-30), equal(dir, vec3(0.0)));
    vec3 inv = 1.0 / safe_dir;

    // The surface point is at t = search: keep the hit closest to it
    float best = 1e30;
    uint best_tri = 0xFFFFFFFFu;
    vec3 best_barycentric = vec3(0.0);

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
                if(RAY_INFO[t].x != self_id)
                {
                    continue;
                }
                float hit_t;
                vec3 hit_barycentric;
                if(ray_triangle_hit(RAY_TRIS[t*4u].xyz, RAY_TRIS[t*4u+1u].xyz, RAY_TRIS[t*4u+2u].xyz,
                    origin, kx, ky, kz, sx, sy, sz, t_max, hit_t, hit_barycentric))
                {
                    float error = abs(hit_t - search);
                    if(error < best)
                    {
                        best = error;
                        best_tri = t;
                        best_barycentric = hit_barycentric;
                    }
                }
            }
        }
        else
        {
            stack[stack_size++] = int(node.a);
            stack[stack_size++] = i + 1;
        }
    }

    if(best_tri == 0xFFFFFFFFu)
    {
        return P;
    }
    uint t = best_tri;
    vec3 v0 = RAY_TRIS[t*4u].xyz;
    vec3 v1 = RAY_TRIS[t*4u+1u].xyz;
    vec3 v2 = RAY_TRIS[t*4u+2u].xyz;
    // The point on the found triangle, then onto the smooth surface
    vec3 b = best_barycentric;
    vec3 on_triangle = b.x * v0 + b.y * v1 + b.z * v2;
    return smooth_surface_point(on_triangle, v0, v1, v2,
        RAY_NORMALS[t*3u].xyz, RAY_NORMALS[t*3u+1u].xyz, RAY_NORMALS[t*3u+2u].xyz, b);
}

#endif //RAY_SHADOWS_GLSL
