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


def render_one(setup, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "log.txt"), "w") as log:
        def L(*a):
            print(*a, file=log, flush=True)
        try:
            import Malt
            L("MALT_FILE", Malt.__file__)
            s = bpy.context.scene
            if setup:
                sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                import scenes
                getattr(scenes, setup)(s)
                L("setup", setup)
            L("engine", s.render.engine, "res", s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage)
            s.render.image_settings.file_format = "PNG"
            s.render.image_settings.color_mode = "RGBA"
            for f in frames:
                s.frame_set(f)
                s.render.filepath = os.path.join(out_dir, f"frame_{f:04d}.png")
                t = time.time()
                bpy.ops.render.render(write_still=True)
                L("frame", f, "%.3fs" % (time.time() - t), os.path.exists(s.render.filepath))
        except Exception:
            L(traceback.format_exc())


def run():
    i = state['index']
    if len(setups) <= 1:
        render_one(setups[0] if setups else None, out_root)
    else:
        render_one(setups[i], os.path.join(out_root, setups[i]))
    state['index'] = i + 1
    if state['index'] < len(setups):
        # Fresh copy of the file for the next setup (setups edit the scene in memory); never saved
        bpy.ops.wm.open_mainfile(filepath=blend_path, load_ui=False)
        return 3.0
    bpy.ops.wm.quit_blender()   # never saves: the file is opened from disk and left unchanged
    return None


bpy.app.timers.register(run, first_interval=3.0, persistent=True)
