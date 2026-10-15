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

// lines texture: r = line, gb = fill pixel offset (-2..2, stored as (offset + 2) / 4), a = kind. A removed line keeps its kind with r = 0: a removed
// silhouette pixel becomes background, a removed inner or overlap line shows its surface.
#define PIXEL_LINES_BACKGROUND 0.0
#define PIXEL_LINES_SURFACE 0.25
#define PIXEL_LINES_INNER 0.5
#define PIXEL_LINES_SILHOUETTE 0.875
#define PIXEL_LINES_OVERLAP 1.0
#define PIXEL_LINES_KEEP 0.78
#define PIXEL_LINES_KEEP_FILL 0.3
#define _IS_KEEP_FILL(v) (abs((v).a - PIXEL_LINES_KEEP_FILL) < 0.03)
#define _IS_SILHOUETTE(v) (abs((v).a - PIXEL_LINES_SILHOUETTE) < 0.05)
#define _IS_KEEP(v) (abs((v).a - PIXEL_LINES_KEEP) < 0.04)
#define _IS_RING(v) (_IS_SILHOUETTE(v) || _IS_KEEP(v))

#ifdef PIXEL_LINES_DECIDE
uniform usampler2D lattice_id;          // (2W+1, 2H+1)
uniform sampler2D lattice_normal_depth; // (2W+1, 2H+1), depth in .w
uniform sampler2D line_data;            // (W, H): x = inner line value, y = rule bits: outline 1, junctions 2, tips 4, overlap corners 8
uniform float depth_threshold;

bool _covered(uvec4 id) { return id.x != 0u; }
bool _keep(uvec4 id) { return (id.w & 1u) != 0u; }

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

// Coverage of pixel n, and F = the pixel whose colours n shows (offset -2..2).
// - its centre sample is covered: F = n;
// - a pinhole (all 4 neighbour centres covered): filled from the first neighbour, so no outline circles a missed sample;
// - KEEP: a KEEP part touches one of its 9 lattice samples and no pixel centre of the 3x3 around n shows that object
//   (the part would vanish here): F = the nearest pixel within 2 px whose centre shows it, else n.
bool _centre(ivec2 m, ivec2 size)
{
    if(any(lessThan(m, ivec2(0))) || any(greaterThanEqual(m, size))) return false;
    return _covered(texelFetch(lattice_id, 2 * m + 1, 0));
}

bool _coverage(ivec2 n, ivec2 size, out ivec2 f, out bool keep)
{
    f = n;
    uvec4 centre = texelFetch(lattice_id, 2 * n + 1, 0);
    keep = _covered(centre) && _keep(centre);
    if(_covered(centre)) return true;
    ivec2 o4[4] = ivec2[4](ivec2(0, 1), ivec2(0, -1), ivec2(-1, 0), ivec2(1, 0));
    if(_centre(n + o4[0], size) && _centre(n + o4[1], size) && _centre(n + o4[2], size) && _centre(n + o4[3], size))
    {
        f = n + o4[0];
        return true;
    }
    for(int dy = -1; dy <= 1; dy++)
    for(int dx = -1; dx <= 1; dx++)
    {
        uvec4 iq = texelFetch(lattice_id, 2 * n + 1 + ivec2(dx, dy), 0);
        if(!_covered(iq) || !_keep(iq)) continue;
        bool shown = false;
        for(int y = -1; y <= 1 && !shown; y++)
        for(int x = -1; x <= 1 && !shown; x++)
        {
            ivec2 m = n + ivec2(x, y);
            shown = (x != 0 || y != 0) && _centre(m, size) && texelFetch(lattice_id, 2 * m + 1, 0).x == iq.x;
        }
        if(shown) continue;   // the part shows next door: no fill needed, it does not vanish
        keep = true;
        float best = 1e9;
        for(int y = -2; y <= 2; y++)
        for(int x = -2; x <= 2; x++)
        {
            ivec2 m = n + ivec2(x, y);
            float d = float(x * x + y * y);
            if(d < best && _centre(m, size) && texelFetch(lattice_id, 2 * m + 1, 0).x == iq.x) { best = d; f = m; }
        }
        return true;
    }
    return false;
}

void main()
{
    ivec2 p = ivec2(gl_FragCoord.xy);
    ivec2 size = textureSize(line_data, 0);
    ivec2 c = 2 * p + 1;
    ivec2 offsets[4] = ivec2[4](ivec2(0, 1), ivec2(0, -1), ivec2(-1, 0), ivec2(1, 0));
    float centre_depth = _distance(c);
    bool centre_covered = _covered(texelFetch(lattice_id, c, 0));
    ivec2 fp;
    bool keep_p;
    bool covered = _coverage(p, size, fp, keep_p);
    // gb = fill pixel offset in -2..2 (a KEEP neighbour's source can be 2 px away)
    OUT_RESULT = vec4(0.0, vec2(fp - p + 2) / 4.0,
        covered ? (centre_covered ? PIXEL_LINES_SURFACE : PIXEL_LINES_KEEP_FILL) : PIXEL_LINES_BACKGROUND);

    // Silhouette outline OUTSIDE the model: a background pixel beside a covered pixel (4-neighbour). The fill is never
    // turned into line, so thin parts keep their colour, and no model pixel touches the background.
    if(!covered)
    {
        for(int k = 0; k < 4; k++)
        {
            ivec2 n = p + offsets[k];
            if(any(lessThan(n, ivec2(0))) || any(greaterThanEqual(n, size))) continue;
            ivec2 fn;
            bool keep_n;
            if(!_coverage(n, size, fn, keep_n)) continue;
            // ASW Col.A switch: no outline here. Only where a material wrote line_data (w > 0): a KEEP sliver with no
            // source pixel nearby has none, and still gets its outline
            vec4 ld = texelFetch(line_data, fn, 0);
            if(ld.w > 0.25 && (int(round(ld.y)) & 1) == 0) continue;
            // a KEEP neighbour's source can be 3 px from p: the encoding holds -2..2, so clamp (same object nearby)
            OUT_RESULT = vec4(1.0, vec2(clamp(fn - p, ivec2(-2), ivec2(2)) + 2) / 4.0,
                keep_n ? PIXEL_LINES_KEEP : PIXEL_LINES_SILHOUETTE);
            return;
        }
        return;
    }

    // Overlap: two covered samples of the diamond disagree (another part, or a depth step). F = the nearer side.
    for(int k = 0; k < 4; k++)
    {
        ivec2 q = c + offsets[k];
        if(!_disagree(c, q)) continue;
        bool q_covered = _covered(texelFetch(lattice_id, q, 0));
        if(!centre_covered || !q_covered) continue;   // silhouette edges: handled above
        float q_depth = _distance(q);
        bool centre_nearer = centre_covered && (!q_covered || centre_depth <= q_depth);
        ivec2 f = centre_nearer ? p : p + offsets[k];
        if(any(lessThan(f, ivec2(0))) || any(greaterThanEqual(f, size))) continue;
        if((int(round(texelFetch(line_data, f, 0).y)) & 1) == 0) continue;   // ASW Col.A switch: no outline here
        // KOF XIII L2: a shadow-only near part skips the overlap line where the far part is lit (line_data.z 1; darkest 0.5)
        ivec2 far = f == p ? p + offsets[k] : p;
        if(texelFetch(line_data, f, 0).z > 0.25 && texelFetch(line_data, clamp(far, ivec2(0), size - 1), 0).z > 0.75)
            continue;
        OUT_RESULT = vec4(1.0, vec2(f - p + 2) / 4.0, PIXEL_LINES_OVERLAP);
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
            OUT_RESULT = vec4(1.0, 0.5, 0.5, PIXEL_LINES_INNER);
        }
    }
}
#endif //PIXEL_LINES_DECIDE

#if defined(PIXEL_LINES_THIN) || defined(PIXEL_LINES_PRUNE) || defined(PIXEL_LINES_ZS) || defined(PIXEL_LINES_BLOCK)
uniform sampler2D lines;
uniform int zs_sub;
uniform int block_corner;
uniform sampler2D line_data;            // rule bits in .y (see PIXEL_LINES_DECIDE)

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

bool _surface(ivec2 q)
{
    // a covered pixel, line or not: outline (ring) pixels lie outside the model, every other kind is a model pixel.
    // Lines count too, so two pixels removed in one pass can never expose the model together.
    ivec2 size = textureSize(lines, 0);
    if(any(lessThan(q, ivec2(0))) || any(greaterThanEqual(q, size))) return false;
    vec4 v = texelFetch(lines, q, 0);
    return v.a > 0.1 && !_IS_RING(v);
}


// Corner rules A-C: bits of line_data.y at the fill pixel of q (outline 1, junctions 2, tips 4, overlap corners 8)
int _rules(ivec2 q)
{
    ivec2 size = textureSize(lines, 0);
    if(any(lessThan(q, ivec2(0))) || any(greaterThanEqual(q, size))) return 0;
    ivec2 f = q + ivec2(round(texelFetch(lines, q, 0).gb * 4.0)) - 2;
    if(any(lessThan(f, ivec2(0))) || any(greaterThanEqual(f, size))) return 0;
    return int(round(texelFetch(line_data, f, 0).y));
}

// no model here: outside the frame, uncovered, or a removed ring pixel
bool _background(ivec2 q)
{
    ivec2 size = textureSize(lines, 0);
    if(any(lessThan(q, ivec2(0))) || any(greaterThanEqual(q, size))) return true;
    vec4 v = texelFetch(lines, q, 0);
    return v.r < 0.5 && (v.a < 0.1 || _IS_RING(v));
}

int _kind_class(vec4 v)
{
    return _IS_RING(v) ? 0 : (v.a > 0.95 ? 1 : 2);   // ring, overlap, inner
}

// An L corner (one vertical and one horizontal line neighbour, no diagonal) that rule B (pointed tip: 5+ of 8 neighbours
// are background) or rule C (an overlap pixel, or it joins two different kinds) keeps.
bool _kept_corner(ivec2 p, vec4 value)
{
    bool up = _line(p + ivec2(0, 1)), dn = _line(p + ivec2(0, -1));
    bool lf = _line(p + ivec2(-1, 0)), rt = _line(p + ivec2(1, 0));
    bool diag = _line(p + ivec2(-1, -1)) || _line(p + ivec2(1, -1)) || _line(p + ivec2(-1, 1)) || _line(p + ivec2(1, 1));
    if(!((up != dn) && (lf != rt) && !diag)) return false;
    int rules = _rules(p);
    if((rules & 4) != 0)
    {
        int far = 0;
        for(int y = -1; y <= 1; y++)
            for(int x = -1; x <= 1; x++)
                if((x != 0 || y != 0) && _background(p + ivec2(x, y))) far++;
        if(far >= 5) return true;
    }
    if((rules & 8) != 0)
    {
        int own = _kind_class(value);
        int vertical = _kind_class(texelFetch(lines, p + ivec2(0, up ? 1 : -1), 0));
        int horizontal = _kind_class(texelFetch(lines, p + ivec2(lf ? -1 : 1, 0), 0));
        if(own == 1 || vertical != horizontal) return true;
    }
    return false;
}

// Rule A: the 2x2 block at o holds a junction when 3+ separate line runs meet on its 12 pixel ring. A block inside a 3x3
// all-line square is never a junction (its ring is mostly one run).
bool _junction_block(ivec2 o)
{
    for(int sy = -1; sy <= 1; sy++)
        for(int sx = -1; sx <= 1; sx++)
        {
            bool square = true;
            for(int y = 0; y < 3 && square; y++)
                for(int x = 0; x < 3 && square; x++)
                    square = _line(o + ivec2(sx + x, sy + y));
            if(square) return false;
        }
    ivec2 ring[12] = ivec2[12](ivec2(-1, -1), ivec2(0, -1), ivec2(1, -1), ivec2(2, -1), ivec2(2, 0), ivec2(2, 1),
        ivec2(2, 2), ivec2(1, 2), ivec2(0, 2), ivec2(-1, 2), ivec2(-1, 1), ivec2(-1, 0));
    int runs = 0;
    bool previous = _line(o + ring[11]);
    for(int i = 0; i < 12; i++)
    {
        bool current = _line(o + ring[i]);
        if(current && !previous) runs++;
        previous = current;
    }
    return runs >= 3;
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
        if((up != dn) && (lf != rt) && ortho == 2 && !diag && !_kept_corner(p, value))
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
        if(b >= 2 && b <= 6 && a == 1 && keep && !_kept_corner(p, value))
        {
            OUT_RESULT.r = 0.0;
        }
    }
    #endif
    #ifdef PIXEL_LINES_BLOCK
    {
        // Zhang-Suen keeps 2x2 blocks where 3 or more lines meet. Remove the pixel at corner block_corner of such a block
        // when it is a simple point (Yokoi 8-connectivity number 1): no line piece splits and no hole opens.
        ivec2 o = p - ivec2(block_corner & 1, block_corner >> 1);
        bool block = _line(o) && _line(o + ivec2(1, 0)) && _line(o + ivec2(0, 1)) && _line(o + ivec2(1, 1));
        ivec2 d[8] = ivec2[8](ivec2(0, 1), ivec2(1, 1), ivec2(1, 0), ivec2(1, -1), ivec2(0, -1), ivec2(-1, -1), ivec2(-1, 0), ivec2(-1, 1));
        int empty[8];
        int b = 0;
        for(int i = 0; i < 8; i++)
        {
            empty[i] = _line(p + d[i]) ? 0 : 1;
            b += 1 - empty[i];
        }
        int yokoi = 0;
        for(int k = 0; k < 8; k += 2)
            yokoi += empty[k] - empty[k] * empty[(k + 1) % 8] * empty[(k + 2) % 8];
        // rule A: a junction spot (3+ line runs on the ring of the block) stays
        if(block && b >= 2 && yokoi == 1 && !((_rules(p) & 2) != 0 && _junction_block(o)))
        {
            OUT_RESULT.r = 0.0;
        }
    }
    #endif
    #ifdef PIXEL_LINES_PRUNE
    {
        int n = _n8(p);
        if(!_IS_KEEP(value))   // a KEEP pixel is never pruned
        {
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
    }
    #endif
    // A removed silhouette pixel becomes background: allowed only when no surface pixel would then touch the
    // background with a side (nothing of the model outside the outline)
    if(OUT_RESULT.r < 0.5 && _IS_RING(value) &&
       (_surface(p + ivec2(0, 1)) || _surface(p + ivec2(0, -1)) || _surface(p + ivec2(-1, 0)) || _surface(p + ivec2(1, 0))))
    {
        OUT_RESULT = value;
    }
}
#endif //PIXEL_LINES_THIN || PIXEL_LINES_PRUNE || PIXEL_LINES_ZS || PIXEL_LINES_BLOCK

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
    ivec2 f = clamp(p + ivec2(round(l.gb * 4.0)) - 2, ivec2(0), textureSize(lines, 0) - 1);
    OUT_RESULT = color;
    if(l.r < 0.5)
    {
        // A removed outline pixel is background. So is a pixel the lattice sees uncovered (the lattice decides the
        // silhouette). A KEEP fill pixel shows the colour of its source pixel.
        if(_IS_RING(l) || l.a < 0.1) OUT_RESULT = vec4(0.0);
        else if(_IS_KEEP_FILL(l)) OUT_RESULT = vec4(texelFetch(color_texture, f, 0).rgb, 1.0);
        return;
    }
    #ifdef PIXEL_LINES_DEBUG
    {
        OUT_RESULT = _IS_KEEP(l) ? vec4(1, 1, 0, 1) : (l.a > 0.95 ? vec4(1, 0.5, 0, 1) : (l.a > 0.75 ? vec4(1, 0, 1, 1) : vec4(0, 1, 1, 1)));
        return;
    }
    #endif
    if(l.a > 0.75)
    {
        // KOF XIII: an outline on a pixel that is not in the darkest tone keeps its own colour (line_data.z)
        OUT_RESULT = texelFetch(line_data, f, 0).z > 0.75
            ? vec4(texelFetch(color_texture, f, 0).rgb, 1.0)
            : vec4(texelFetch(line_color_texture, f, 0).rgb, 1.0);
    }
    else
    {
        vec4 ld = texelFetch(line_data, p, 0);
        OUT_RESULT = (ld.w > 0.0 && ld.w < 0.75) ? vec4(texelFetch(line_color_texture, p, 0).rgb, color.a)
            : vec4(color.rgb * ld.x, color.a);
    }
}
#endif //PIXEL_LINES_COMPOSITE

#endif //PIXEL_SHADER
