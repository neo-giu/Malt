"""Open a .blend with one test setup applied and KEEP Blender open (for looking at a setup by hand).

    BLENDER_USER_SCRIPTS=H:/GameDev/MaltDev/scripts  blender.exe FILE.blend --python tools/pixelart/open_setup.py -- SETUP

SETUP: a function name in tools/pixelart/scenes.py (for example pixel_pal_kof_l2). The edits are in memory only; the
file on disk changes only if you save. The 3D views switch to the camera in Rendered shading."""
import bpy, sys, os, traceback

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
setup = argv[0] if argv else ''


def _show_camera():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            space = area.spaces.active
            space.shading.type = 'RENDERED'
            region = next((r for r in area.regions if r.type == 'WINDOW'), None)
            if region is not None and space.region_3d.view_perspective != 'CAMERA':
                with bpy.context.temp_override(window=window, area=area, region=region):
                    bpy.ops.view3d.view_camera()


def _run():
    try:
        if setup:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import scenes
            after = getattr(scenes, setup)(bpy.context.scene)
            if callable(after):
                bpy.app.timers.register(lambda: (after(), None)[1], first_interval=10.0)
            print('OPEN_SETUP done', setup, flush=True)
        _show_camera()
    except Exception:
        traceback.print_exc()
    return None


bpy.app.timers.register(_run, first_interval=3.0, persistent=True)
