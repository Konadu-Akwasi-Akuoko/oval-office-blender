"""Phase 7 - camera rig, render settings and the 360 animation.

Independent of everything except the room dimensions, so it can be run early and
re-run whenever the shot needs adjusting.

The rig is an empty at room centre with the camera parented to it. Animating the
empty's Z rotation rather than the camera's own keeps the camera's framing
settings separate from the move, so lens and height can be changed without
touching the animation.

Run with `exec(open(path).read())` inside Blender. Idempotent.
"""

import importlib
import math
import os
import sys

import bpy

_HERE = os.path.dirname(os.path.abspath(bpy.data.filepath)) if bpy.data.filepath else None
_SCRIPTS = os.path.join(_HERE, "scripts") if _HERE else None
if _SCRIPTS and _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import oo_common as oo  # noqa: E402

importlib.reload(oo)


PREFIX = "OO_Cam"

EYE_HEIGHT = 1.60
LENS_MM = 24.0

# Tilt above horizontal, degrees. A level camera at eye height does not see the
# cornice at all: at 28 mm the vertical half-angle is 19.9 deg, which at the
# south wall 5.46 m away tops out at z 3.58 m, while the cornice starts at 4.62 m.
# The whole point of the shot is the cove, so the lens went wider and the camera
# tilts up. Revisit once the room has furniture and there is something at floor
# level worth holding in frame.
TILT_DEG = 7.0

# Distance the camera sits from the pivot. Zero is a pure nodal pan, which is
# what was approved. A small non-zero value adds parallax and makes the room read
# as more three-dimensional, at the cost of no longer being a true pivot in
# place. Left at zero deliberately - see docs/learnings.md.
ORBIT_RADIUS = 0.0

FPS = 30
DURATION_S = 20
FRAMES = FPS * DURATION_S  # 600

# Rotation is keyed to reach a full turn on FRAMES + 1, then the timeline ends at
# FRAMES. Frame 601 would be identical to frame 1, so rendering it would double
# a frame and produce a visible hitch on loop.
LOOP_KEY = FRAMES + 1


def build_rig():
    oo.purge(PREFIX)
    oo.purge("OO_Tmp")  # the workbench preview camera from phase 1

    coll = oo.get_collection()

    pivot = bpy.data.objects.new(PREFIX + "_Pivot", None)
    pivot.empty_display_type = "PLAIN_AXES"
    pivot.empty_display_size = 0.5
    pivot.location = (0.0, 0.0, EYE_HEIGHT)
    coll.objects.link(pivot)

    cam_data = bpy.data.cameras.new(PREFIX)
    cam_data.lens = LENS_MM
    cam_data.sensor_width = 36.0
    cam_data.clip_start = 0.05
    cam_data.clip_end = 100.0

    cam = bpy.data.objects.new(PREFIX, cam_data)
    # Local to the pivot: X+90 tips the camera from looking down to looking along
    # the horizon, Z+180 turns it from north to south so the shot opens on the
    # windows and the desk.
    cam.location = (0.0, -ORBIT_RADIUS, 0.0)
    cam.rotation_euler = (math.radians(90.0 + TILT_DEG), 0.0, math.radians(180.0))
    cam.parent = pivot
    coll.objects.link(cam)

    bpy.context.scene.camera = cam
    return pivot, cam


def animate(pivot):
    pivot.animation_data_clear()
    pivot.rotation_euler = (0.0, 0.0, 0.0)

    pivot.keyframe_insert("rotation_euler", index=2, frame=1)
    pivot.rotation_euler = (0.0, 0.0, 2.0 * math.pi)
    pivot.keyframe_insert("rotation_euler", index=2, frame=LOOP_KEY)

    # Linear throughout. Bezier easing would make the loop seam stutter, because
    # the speed at the end would not match the speed at the start.
    for fcurve in oo.action_fcurves(pivot):
        fcurve.extrapolation = "LINEAR"
        for kp in fcurve.keyframe_points:
            kp.interpolation = "LINEAR"
            kp.handle_left_type = kp.handle_right_type = "VECTOR"


def render_settings():
    scene = bpy.context.scene

    # Blender 5.2 dropped the "_NEXT" suffix; plain BLENDER_EEVEE *is* EEVEE Next.
    scene.render.engine = "BLENDER_EEVEE"

    scene.render.resolution_x = 3840
    scene.render.resolution_y = 2160
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = FRAMES
    scene.render.film_transparent = False

    ee = scene.eevee
    ee.taa_render_samples = 64
    ee.use_raytracing = True
    ee.use_shadows = True
    if hasattr(ee, "use_volumetric_shadows"):
        ee.use_volumetric_shadows = True

    # PNG sequence, not video. A 600-frame render is long enough that a crash
    # partway through must not lose everything - frames already on disk are kept
    # and the render resumes. ffmpeg encodes to mp4 afterwards.
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 15

    out = os.path.join(_HERE or "//", "renders", "frames", "oo_")
    scene.render.filepath = out

    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Base Contrast"
    return out


def main():
    pivot, cam = build_rig()
    animate(pivot)
    out = render_settings()

    scene = bpy.context.scene
    return {
        "pivot": pivot.name,
        "camera": cam.name,
        "lens_mm": cam.data.lens,
        "tilt_deg": TILT_DEG,
        "eye_height": EYE_HEIGHT,
        "orbit_radius": ORBIT_RADIUS,
        "frames": f"{scene.frame_start}-{scene.frame_end}",
        "fps": scene.render.fps,
        "loop_key_frame": LOOP_KEY,
        "degrees_per_frame": round(360.0 / FRAMES, 3),
        "resolution": f"{scene.render.resolution_x}x{scene.render.resolution_y}",
        "engine": scene.render.engine,
        "raytracing": scene.eevee.use_raytracing,
        "output": out,
    }


result = main()
