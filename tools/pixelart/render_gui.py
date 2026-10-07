"""Scripted GUI render with Malt (option B). Blender must run WITH a window (Malt cannot render in -b mode).

    BLENDER_USER_SCRIPTS=H:/GameDev/MaltDev/scripts  blender.exe FILE.blend --python tools/pixelart/render_gui.py -- OUT_DIR FRAMES [SETUP]

FRAMES: comma list ("1,5"). SETUP: optional function name in tools/pixelart/scenes.py, called with the scene before
rendering (in-memory edits only). Writes OUT_DIR/frame_NNNN.png and OUT_DIR/log.txt, then quits WITHOUT saving."""
import bpy, sys, os, time, traceback

argv = sys.argv[sys.argv.index("--") + 1:]
out_dir, frames = argv[0], [int(f) for f in argv[1].split(",")]
setup = argv[2] if len(argv) > 2 else None
os.makedirs(out_dir, exist_ok=True)
log = open(os.path.join(out_dir, "log.txt"), "w")


def L(*a):
    print(*a, file=log, flush=True)


def run():
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
    finally:
        log.close()
        bpy.ops.wm.quit_blender()   # never saves: the file is opened from disk and left unchanged
    return None


bpy.app.timers.register(run, first_interval=3.0)
