"""Phase 6 - lighting.

The Oval Office has no ceiling fixtures. Bulbs concealed in a trough at the top
of the cornice wash light upward onto the cove, and that indirect bounce is
essentially the whole lighting design. Getting this right matters more than any
other lighting decision in the project.

Run early and often: this only depends on the cornice geometry from phase 1, and
nothing else in the scene is judgeable until there is light in the room.

Daylight through the south windows is added once phase 2 has cut them - a sun
lamp is pointless while the wall is still solid.

Run with `exec(open(path).read())` inside Blender. Idempotent.
"""

import importlib
import math
import os
import sys

import bpy
from mathutils import Vector

_HERE = os.path.dirname(os.path.abspath(bpy.data.filepath)) if bpy.data.filepath else None
_SCRIPTS = os.path.join(_HERE, "scripts") if _HERE else None
if _SCRIPTS and _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import oo_common as oo  # noqa: E402

importlib.reload(oo)


PREFIX = "OO_Light"

COVE_LAMPS = 28
COVE_WATTS = 55.0  # per lamp
COVE_COLOUR = (1.000, 0.780, 0.545)  # roughly 2900 K, warm tungsten

# Lamps sit on the trough floor, behind the cornice lip. The inset must be
# SMALLER than the lip (nearer the wall) and the height BELOW the lip top, or
# they are visible from the room - or worse, buried inside the wall, which is
# what happened on the first attempt.
#
# Sight-line check from the camera at room centre, eye height 1.60 m: the lip's
# inner top edge sits at inset 0.240, z 5.100. A ray grazing that edge is at
# z 5.174 by the time it reaches the lamp's inset. The lamp at z 5.075 is below
# that, so it stays hidden for the whole 360.
TROUGH_INSET = 0.130
TROUGH_Z = oo.TROUGH_Z + 0.020


def build_cove_lights(coll):
    lamps = []
    for i in range(COVE_LAMPS):
        t = 2.0 * math.pi * i / COVE_LAMPS
        pos = oo.ellipse_point(t, TROUGH_INSET)

        data = bpy.data.lights.new(f"{PREFIX}_Cove_{i:02d}", type="AREA")
        data.shape = "RECTANGLE"
        data.size = 1.05  # along the wall
        data.size_y = 0.10  # across the trough
        data.energy = COVE_WATTS
        data.color = COVE_COLOUR

        # Shadows off. These lamps illuminate a smooth continuous cove, so they
        # cast nothing meaningful, and 28 shadow-casting lights is a large and
        # entirely wasted cost in EEVEE.
        data.use_shadow = False

        obj = bpy.data.objects.new(data.name, data)
        obj.location = (pos.x, pos.y, TROUGH_Z)

        # Aim up and inward, toward the cove surface above.
        inward = Vector((-pos.x, -pos.y, 0.0))
        inward.normalize()
        aim = (Vector((0.0, 0.0, 1.0)) * 0.88 + inward * 0.48).normalized()
        obj.rotation_euler = aim.to_track_quat("-Z", "Y").to_euler()

        coll.objects.link(obj)
        lamps.append(obj)
    return lamps


def build_world():
    world = bpy.data.worlds.get("OO_World") or bpy.data.worlds.new("OO_World")
    world.use_nodes = True
    bpy.context.scene.world = world

    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputWorld")
    out.location = (300, 0)
    bg = nodes.new("ShaderNodeBackground")
    bg.location = (0, 0)

    # Placeholder only. Replaced by a real outdoor HDRI once phase 2 has cut the
    # windows and there is somewhere for daylight to come through.
    bg.inputs["Color"].default_value = (0.42, 0.50, 0.62, 1.0)
    bg.inputs["Strength"].default_value = 0.35

    links.new(bg.outputs["Background"], out.inputs["Surface"])
    return world


def main():
    oo.purge(PREFIX)
    coll = oo.get_collection()

    lamps = build_cove_lights(coll)
    world = build_world()

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    ee = scene.eevee
    ee.use_raytracing = True
    ee.use_shadows = True
    if hasattr(ee, "ray_tracing_options"):
        ee.ray_tracing_options.use_denoise = True

    return {
        "cove_lamps": len(lamps),
        "watts_each": COVE_WATTS,
        "watts_total": round(COVE_WATTS * len(lamps), 1),
        "trough_z": round(TROUGH_Z, 3),
        "trough_inset": round(TROUGH_INSET, 3),
        "world": world.name,
        "shadows_on_cove_lamps": False,
    }


result = main()
