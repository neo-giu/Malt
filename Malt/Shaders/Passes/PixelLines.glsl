// 1 px line decision for the PixelLines node (docs/pixelart/05-pixel-cel-materials-spec.md, section 3.2).
// Only decides which pixels are lines (and their fill pixel); colours are composited in PIXEL_LINES_COMPOSITE.
#include "Common.glsl"

#ifdef VERTEX_SHADER
void main()
{
    DEFAULT_SCREEN_VERTEX_SHADER();
}
#endif //VERTEX_SHADER

#ifdef PIXEL_SHADER

layout (location = 0) out vec4 OUT_RESULT;

#ifdef PIXEL_LINES_DECIDE
uniform usampler2D lattice_id;          // (2W+1, 2H+1)
uniform sampler2D lattice_normal_depth; // (2W+1, 2H+1), depth in .w
uniform sampler2D line_data;            // (W, H): x = inner line value, y = outline enable
uniform float depth_threshold;

bool _covered(uvec4 id) { return id.x != 0u; }

float _distance(ivec2 a)
{
    // the pre pass stores the screen depth: linearize it
    return abs(depth_to_z(texelFetch(lattice_normal_depth, a, 0).w));
}

bool _disagree(ivec2 a, ivec2 b)
{
    uvec4 ia = texelFetch(lattice_id, a, 0);
    uvec4 ib = texelFetch(lattice_id, b, 0);
    if(ia.x != ib.x) return true;
    if(!_covered(ia)) return false;
    float da = _distance(a);
    float db = _distance(b);
    return abs(da - db) > depth_threshold * min(da, db);
}

void main()
{
    ivec2 p = ivec2(gl_FragCoord.xy);
    ivec2 size = textureSize(line_data, 0);
    ivec2 c = 2 * p + 1;
    ivec2 offsets[4] = ivec2[4](ivec2(0, 1), ivec2(0, -1), ivec2(-1, 0), ivec2(1, 0));
    OUT_RESULT = vec4(0.0, 1.0 / 2.0, 1.0 / 2.0, 0.0);

    // Outline: the 5 diamond samples disagree. F = the nearer covered side.
    float centre_depth = _distance(c);
    bool centre_covered = _covered(texelFetch(lattice_id, c, 0));
    for(int k = 0; k < 4; k++)
    {
        ivec2 q = c + offsets[k];
        if(!_disagree(c, q)) continue;
        bool q_covered = _covered(texelFetch(lattice_id, q, 0));
        float q_depth = _distance(q);
        bool centre_nearer = centre_covered && (!q_covered || centre_depth <= q_depth);
        ivec2 f = centre_nearer ? p : p + offsets[k];
        if(any(lessThan(f, ivec2(0))) || any(greaterThanEqual(f, size))) continue;
        if(texelFetch(line_data, f, 0).y < 0.5) continue;   // ASW Col.A switch: no outline here
        OUT_RESULT = vec4(1.0, vec2(f - p + 1) / 2.0, 1.0);
        return;
    }

    // Inner line: below 0.5 and a minimum across the line (1 px centre line of the texture stroke)
    if(!centre_covered) return;
    float v = texelFetch(line_data, p, 0).x;
    if(v < 0.5)
    {
        float l = texelFetch(line_data, clamp(p + ivec2(-1, 0), ivec2(0), size - 1), 0).x;
        float r = texelFetch(line_data, clamp(p + ivec2(1, 0), ivec2(0), size - 1), 0).x;
        float d = texelFetch(line_data, clamp(p + ivec2(0, -1), ivec2(0), size - 1), 0).x;
        float u = texelFetch(line_data, clamp(p + ivec2(0, 1), ivec2(0), size - 1), 0).x;
        bool horizontal_rise = (l + r) >= (d + u);
        bool minimum = horizontal_rise ? (v <= l && v < r) : (v <= d && v < u);
        if(minimum)
        {
            OUT_RESULT = vec4(1.0, 0.5, 0.5, 0.5);
        }
    }
}
#endif //PIXEL_LINES_DECIDE

#if defined(PIXEL_LINES_THIN) || defined(PIXEL_LINES_PRUNE) || defined(PIXEL_LINES_ZS)
uniform sampler2D lines;
uniform int zs_sub;

bool _line(ivec2 q)
{
    ivec2 size = textureSize(lines, 0);
    if(any(lessThan(q, ivec2(0))) || any(greaterThanEqual(q, size))) return false;
    return texelFetch(lines, q, 0).r > 0.5;
}

int _n8(ivec2 q)
{
    int n = 0;
    for(int y = -1; y <= 1; y++)
        for(int x = -1; x <= 1; x++)
            if((x != 0 || y != 0) && _line(q + ivec2(x, y))) n++;
    return n;
}

void main()
{
    ivec2 p = ivec2(gl_FragCoord.xy);
    vec4 value = texelFetch(lines, p, 0);
    OUT_RESULT = value;
    if(value.r < 0.5) return;
    #ifdef PIXEL_LINES_THIN
    {
        bool up = _line(p + ivec2(0, 1)), dn = _line(p + ivec2(0, -1));
        bool lf = _line(p + ivec2(-1, 0)), rt = _line(p + ivec2(1, 0));
        bool diag = _line(p + ivec2(-1, -1)) || _line(p + ivec2(1, -1)) || _line(p + ivec2(-1, 1)) || _line(p + ivec2(1, 1));
        int ortho = int(up) + int(dn) + int(lf) + int(rt);
        if((up != dn) && (lf != rt) && ortho == 2 && !diag)
        {
            OUT_RESULT.r = 0.0;
        }
    }
    #endif
    #ifdef PIXEL_LINES_ZS
    {
        // Zhang-Suen sub iteration: thins the 2 px wide runs (2x2 blocks) the decision leaves where a third surface sits
        // between two sample points. N = +y, clockwise.
        ivec2 d[8] = ivec2[8](ivec2(0, 1), ivec2(1, 1), ivec2(1, 0), ivec2(1, -1), ivec2(0, -1), ivec2(-1, -1), ivec2(-1, 0), ivec2(-1, 1));
        bool n[8];
        int b = 0, a = 0;
        for(int i = 0; i < 8; i++)
        {
            n[i] = _line(p + d[i]);
            b += int(n[i]);
        }
        for(int i = 0; i < 8; i++)
            if(!n[i] && n[(i + 1) % 8]) a++;
        bool keep = zs_sub == 0
            ? (!(n[0] && n[2] && n[4]) && !(n[2] && n[4] && n[6]))
            : (!(n[0] && n[2] && n[6]) && !(n[0] && n[4] && n[6]));
        if(b >= 2 && b <= 6 && a == 1 && keep)
        {
            OUT_RESULT.r = 0.0;
        }
    }
    #endif
    #ifdef PIXEL_LINES_PRUNE
    {
        int n = _n8(p);
        if(n == 0)
        {
            OUT_RESULT.r = 0.0;
        }
        else if(n == 1)
        {
            for(int y = -1; y <= 1; y++)
                for(int x = -1; x <= 1; x++)
                    if((x != 0 || y != 0) && _line(p + ivec2(x, y)) && _n8(p + ivec2(x, y)) == 1)
                        OUT_RESULT.r = 0.0;
        }
    }
    #endif
}
#endif //PIXEL_LINES_THIN || PIXEL_LINES_PRUNE || PIXEL_LINES_ZS

#ifdef PIXEL_LINES_COMPOSITE
uniform sampler2D color_texture;
uniform sampler2D line_color_texture;
uniform sampler2D line_data;
uniform sampler2D lines;

void main()
{
    ivec2 p = ivec2(gl_FragCoord.xy);
    vec4 color = texelFetch(color_texture, p, 0);
    vec4 l = texelFetch(lines, p, 0);
    OUT_RESULT = color;
    if(l.r < 0.5) return;
    if(l.a > 0.75)
    {
        ivec2 f = p + ivec2(round(l.gb * 2.0)) - 1;
        OUT_RESULT = vec4(texelFetch(line_color_texture, f, 0).rgb, 1.0);
    }
    else
    {
        OUT_RESULT = vec4(color.rgb * texelFetch(line_data, p, 0).x, color.a);
    }
}
#endif //PIXEL_LINES_COMPOSITE

#endif //PIXEL_SHADER
