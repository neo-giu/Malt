"""Scripted GUI render with Malt (option B). Blender must run WITH a window (Malt cannot render in -b mode).

    BLENDER_USER_SCRIPTS=H:/GameDev/MaltDev/scripts  blender.exe FILE.blend --python tools/pixelart/render_gui.py -- OUT_DIR FRAMES [SETUP[,SETUP...]]

FRAMES: comma list ("1,5"). SETUP: optional function name(s) in tools/pixelart/scenes.py, called with the scene before
rendering (in-memory edits only). One setup: writes OUT_DIR/frame_NNNN.png and OUT_DIR/log.txt. Several setups (one
Blender launch for all): the file is reloaded from disk before each setup, and each writes OUT_DIR/<setup>/frame_NNNN.png
and OUT_DIR/<setup>/log.txt. Quits WITHOUT saving."""
import bpy, sys, os, time, traceback

argv = sys.argv[sys.argv.index("--") + 1:]
out_root, frames = argv[0], [int(f) for f in argv[1].split(",")]
setups = [s for s in argv[2].split(",") if s] if len(argv) > 2 else []
blend_path = bpy.data.filepath
os.makedirs(out_root, exist_ok=True)
state = {'index': 0}


def _visible_material_paths():
    paths = set()
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and not obj.hide_render:
            for slot in obj.material_slots:
                if slot.material is not None:
                    path = slot.material.malt.get_source_path()
                    if path:
                        paths.add(path)
    return paths


def _ready():
    # Malt may restart its server after a setup (new node trees, appended data): that clears every compiled shader.
    # Ready = a live bridge and every visible material compiled.
    from BlenderMalt import MaltPipeline, MaltMaterial
    if MaltPipeline.get_bridge(force_creation=True) is None:
        return False, 'no bridge'
    MaltMaterial.track_shader_changes(force_update=True, async_compilation=False)
    missing = [p for p in _visible_material_paths() if MaltMaterial._MATERIALS.get(p) is None]
    return not missing, f'{len(missing)} materials not compiled'


def _log(out_dir):
    return open(os.path.join(out_dir, "log.txt"), "a")


def setup_one(setup, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    os.environ['RENDER_OUT'] = out_dir
    with open(os.path.join(out_dir, "log.txt"), "w") as log:
        try:
            import Malt
            print("MALT_FILE", Malt.__file__, file=log, flush=True)
            if setup:
                sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                import scenes
                # A setup may return a callable: it runs once the materials are compiled (for example to assign
                # textures to shader uniforms, which exist only after a compile), then the wait starts again
                after = getattr(scenes, setup)(bpy.context.scene)
                state['after_ready'] = after if callable(after) else None
                print("setup", setup, file=log, flush=True)
            return True
        except Exception:
            print(traceback.format_exc(), file=log, flush=True)
            return False


def render_frames(out_dir):
    with _log(out_dir) as log:
        try:
            s = bpy.context.scene
            print("engine", s.render.engine, "res", s.render.resolution_x, s.render.resolution_y,
                  s.render.resolution_percentage, file=log, flush=True)
            s.render.image_settings.file_format = "PNG"
            s.render.image_settings.color_mode = "RGBA"
            for f in frames:
                s.frame_set(f)
                s.render.filepath = os.path.join(out_dir, f"frame_{f:04d}.png")
                t = time.time()
                bpy.ops.render.render(write_still=True)
                print("frame", f, "%.3fs" % (time.time() - t), os.path.exists(s.render.filepath), file=log, flush=True)
        except Exception:
            print(traceback.format_exc(), file=log, flush=True)


def _out_dir(i):
    return out_root if len(setups) <= 1 else os.path.join(out_root, setups[i])


def run():
    # State machine on a persistent timer: setup -> wait until Malt is ready -> render -> reload file -> next setup
    i = state['index']
    phase = state.get('phase', 'setup')
    out_dir = _out_dir(i)
    if phase == 'setup':
        ok = setup_one(setups[i] if setups else None, out_dir)
        state['phase'], state['waited'] = ('wait' if ok else 'next'), 0.0
        return 0.5
    if phase == 'wait':
        try:
            ready, why = _ready()
        except Exception:
            ready, why = False, traceback.format_exc()
        if not ready and state['waited'] < 60.0:
            state['waited'] += 0.5
            return 0.5
        if ready and state.get('after_ready'):
            after, state['after_ready'] = state['after_ready'], None
            with _log(out_dir) as log:
                try:
                    after()
                    print("after_ready done", file=log, flush=True)
                except Exception:
                    print(traceback.format_exc(), file=log, flush=True)
                    state['phase'] = 'next'
                    return 0.1
            return 0.5
        with _log(out_dir) as log:
            print("ready" if ready else "NOT READY after 60 s: " + why, "waited %.1fs" % state['waited'], file=log, flush=True)
        render_frames(out_dir)
        state['phase'] = 'next'
        return 0.1
    # next
    state['index'], state['phase'] = i + 1, 'setup'
    if state['index'] < max(1, len(setups)):
        # Fresh copy of the file for the next setup (setups edit the scene in memory); never saved
        bpy.ops.wm.open_mainfile(filepath=blend_path, load_ui=False)
        return 3.0
    bpy.ops.wm.quit_blender()   # never saves: the file is opened from disk and left unchanged
    return None


bpy.app.timers.register(run, first_interval=3.0, persistent=True)
