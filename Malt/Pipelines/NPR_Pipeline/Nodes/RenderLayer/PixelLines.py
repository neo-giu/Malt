import os

from Malt.GL.GL import *
from Malt.GL.Texture import Texture
from Malt.GL.RenderTarget import RenderTarget
from Malt.PipelineNode import PipelineNode
from Malt.PipelineParameters import Parameter, Type
from Malt.Scene import TextureShaderResource

_SHADERS = {}


def _shader(pipeline, define):
    if define not in _SHADERS:
        _SHADERS[define] = pipeline.compile_shader_from_source(f'#define {define}\n#include "Passes/PixelLines.glsl"')
    return _SHADERS[define]


def lattice_projection(projection, resolution):
    # Column-major 4x4: scale the x row by 2W/(2W+1) and the y row by 2H/(2H+1)
    w, h = resolution
    p = list(projection)
    sx, sy = 2.0 * w / (2.0 * w + 1.0), 2.0 * h / (2.0 * h + 1.0)
    for column in range(4):
        p[column * 4 + 0] *= sx
        p[column * 4 + 1] *= sy
    return tuple(p)


class PixelLines(PipelineNode):
    """
    Draws exactly 1 px lines (outline on the sub-pixel silhouette, diamond rule; inner lines from Pixel Line Data)
    and composites them over *Color*. Only line pixels change.
    """

    def __init__(self, pipeline):
        PipelineNode.__init__(self, pipeline)
        self.resolution = None

    @classmethod
    def reflect_inputs(cls):
        inputs = {}
        inputs['Scene'] = Parameter('Scene', Type.OTHER)
        inputs['Color'] = Parameter('', Type.TEXTURE)
        inputs['Line Color'] = Parameter('', Type.TEXTURE)
        inputs['Pixel Line Data'] = Parameter('', Type.TEXTURE)
        inputs['Depth Threshold'] = Parameter(0.1, Type.FLOAT)
        return inputs

    @classmethod
    def reflect_outputs(cls):
        outputs = {}
        outputs['Color'] = Parameter('', Type.TEXTURE)
        return outputs

    def setup_render_targets(self, resolution):
        w, h = resolution
        lattice = (2 * w + 1, 2 * h + 1)
        self.t_lattice_depth = Texture(lattice, GL_DEPTH_COMPONENT32F)
        self.t_lattice_normal_depth = Texture(lattice, GL_RGBA32F, min_filter=GL_NEAREST, mag_filter=GL_NEAREST)
        self.t_lattice_id = Texture(lattice, GL_RGBA16UI, min_filter=GL_NEAREST, mag_filter=GL_NEAREST)
        self.fbo_lattice = RenderTarget([self.t_lattice_normal_depth, self.t_lattice_id], self.t_lattice_depth)
        self.t_lines = [Texture(resolution, GL_RGBA16F, min_filter=GL_NEAREST, mag_filter=GL_NEAREST) for _ in range(2)]
        self.fbo_lines = [RenderTarget([t]) for t in self.t_lines]
        self.t_color = Texture(resolution, GL_RGBA16F)
        self.fbo_color = RenderTarget([self.t_color])
        # Unused by opaque materials, but the pre pass shader declares them
        self.t_dummy_depth = Texture(lattice, GL_DEPTH_COMPONENT32F)
        self.t_dummy_id = Texture(lattice, GL_R16UI, min_filter=GL_NEAREST, mag_filter=GL_NEAREST)

    def thin_and_prune(self, thin, prune, line_data):
        # lines[0] -> thin -> lines[1] -> prune -> lines[0]
        thin.textures['lines'] = self.t_lines[0]
        thin.textures['line_data'] = line_data
        self.pipeline.draw_screen_pass(thin, self.fbo_lines[1])
        prune.textures['lines'] = self.t_lines[1]
        self.pipeline.draw_screen_pass(prune, self.fbo_lines[0])

    def execute(self, parameters):
        inputs = parameters['IN']
        outputs = parameters['OUT']
        scene = inputs['Scene']
        if scene is None or not inputs['Pixel Line Data']:
            outputs['Color'] = inputs['Color']
            return
        if self.pipeline.resolution != self.resolution:
            self.setup_render_targets(self.pipeline.resolution)
            self.resolution = self.pipeline.resolution
        w, h = self.resolution
        lattice = (2 * w + 1, 2 * h + 1)

        # 1. Lattice pre pass (opaque batches only)
        opaque_batches, _ = self.pipeline.get_scene_batches(scene)
        common = self.pipeline.common_buffer
        common.load(scene, lattice, (0, 0), self.pipeline.sample_count,
            projection=lattice_projection(scene.camera.projection_matrix, self.resolution))
        resources = scene.shader_resources.copy()
        resources['COMMON_UNIFORMS'] = common
        resources['IN_OPAQUE_DEPTH'] = TextureShaderResource('IN_OPAQUE_DEPTH', self.t_dummy_depth)
        resources['IN_TRANSPARENT_DEPTH'] = TextureShaderResource('IN_TRANSPARENT_DEPTH', self.t_dummy_depth)
        resources['IN_LAST_ID'] = TextureShaderResource('IN_LAST_ID', self.t_dummy_id)
        self.fbo_lattice.clear([(0, 0, 0, 1), (0, 0, 0, 0)], 1)
        self.pipeline.draw_scene_pass(self.fbo_lattice, opaque_batches, 'PRE_PASS',
            self.pipeline.default_shader['PRE_PASS'], resources)

        # 2-4. Decide, thin, prune (at the lattice projection, so depth_to_z sees the same z rows)
        decide = _shader(self.pipeline, 'PIXEL_LINES_DECIDE')
        decide.textures['lattice_id'] = self.t_lattice_id
        decide.textures['lattice_normal_depth'] = self.t_lattice_normal_depth
        decide.textures['line_data'] = inputs['Pixel Line Data']
        decide.uniforms['depth_threshold'].set_value(inputs['Depth Threshold'])
        common.shader_callback(decide)
        common.load(scene, self.resolution, self.pipeline.get_sample(scene.world_parameters['Samples.Width']),
            self.pipeline.sample_count)
        self.pipeline.draw_screen_pass(decide, self.fbo_lines[0])
        thin = _shader(self.pipeline, 'PIXEL_LINES_THIN')
        prune = _shader(self.pipeline, 'PIXEL_LINES_PRUNE')
        zs = _shader(self.pipeline, 'PIXEL_LINES_ZS')
        self.thin_and_prune(thin, prune, inputs['Pixel Line Data'])
        # Thin the 2 px wide runs (Zhang-Suen), then drop the L steps and short pieces again
        for _ in range(3):
            for sub in range(2):
                zs.textures['lines'] = self.t_lines[sub]
                zs.textures['line_data'] = inputs['Pixel Line Data']
                zs.uniforms['zs_sub'].set_value(sub)
                self.pipeline.draw_screen_pass(zs, self.fbo_lines[1 - sub])
        # Break the 2x2 blocks left at line junctions, one block corner per pass (lines[0] -> 1 -> 0 -> 1 -> 0)
        block = _shader(self.pipeline, 'PIXEL_LINES_BLOCK')
        for corner in range(4):
            block.textures['lines'] = self.t_lines[corner % 2]
            block.textures['line_data'] = inputs['Pixel Line Data']
            block.uniforms['block_corner'].set_value(corner)
            self.pipeline.draw_screen_pass(block, self.fbo_lines[1 - corner % 2])
        self.thin_and_prune(thin, prune, inputs['Pixel Line Data'])

        # 5. Composite
        # PIXEL_LINES_DEBUG=1 (test renders only): outline px magenta, inner line px cyan, for tools/pixelart/line_check.py --marker
        debug = '\n#define PIXEL_LINES_DEBUG' if os.environ.get('PIXEL_LINES_DEBUG') == '1' else ''
        composite = _shader(self.pipeline, 'PIXEL_LINES_COMPOSITE' + debug)
        composite.textures['color_texture'] = inputs['Color']
        composite.textures['line_color_texture'] = inputs['Line Color']
        composite.textures['line_data'] = inputs['Pixel Line Data']
        composite.textures['lines'] = self.t_lines[0]
        self.pipeline.draw_screen_pass(composite, self.fbo_color)
        outputs['Color'] = self.t_color


NODE = PixelLines
