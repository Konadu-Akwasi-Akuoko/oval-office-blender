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

# 28 lamps at 1.05 m across a 31.2 m perimeter left 60 mm gaps between pools,
# which showed as soft vertical scalloping down the wall. 44 lamps put the
# spacing at 0.71 m against the same 1.05 m width, so each pool overlaps its
# neighbours by a third and the wash reads as continuous.
COVE_LAMPS = 44
COVE_WATTS = 35.0  # per lamp, lowered to keep total output roughly constant
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


def build_irradiance_volume(coll):
    """A light probe volume covering the room.

    Without this, EEVEE Next has essentially no diffuse bounce. Its raytracing
    is screen-space, so light that leaves the cove and should come back down the
    walls simply never arrives - the first lit test render was a nearly black
    room for this reason, not because the lamps were too weak.

    This is the single most important setting for an interior in EEVEE, and it
    has to be baked. An unbaked volume does nothing at all.
    """
    probe = bpy.data.lightprobes.new(f"{PREFIX}_Irradiance", type="VOLUME")
    obj = bpy.data.objects.new(f"{PREFIX}_Irradiance", probe)

    # Sized slightly beyond the shell so the samples nearest the walls sit
    # outside the geometry and do not leak shadow inward.
    obj.location = (0.0, 0.0, oo.CEIL_CENTRE / 2.0)
    obj.scale = (oo.SEMI_X + 0.4, oo.SEMI_Y + 0.4, oo.CEIL_CENTRE / 2.0 + 0.4)

    # Sample grid. Denser across the floor plan than vertically, because the
    # interesting gradient is the fall-off from the windows across the room, not
    # anything happening between knee and shoulder height.
    # A 16x18x10 grid left large blotchy smudges across the walls - the grid was
    # coarse enough that interpolating between samples showed. These values are
    # roughly 0.35 m spacing, which resolves cleanly. Bake time goes up but it is
    # a one-off, not a per-frame cost.
    probe.resolution_x = 26
    probe.resolution_y = 32
    probe.resolution_z = 14

    probe.capture_world = True
    probe.capture_indirect = True
    probe.capture_emission = True
    probe.bake_samples = 1024

    # Pulls samples off surfaces before they are read, which is what stops light
    # leaking through the walls from the world outside.
    probe.normal_bias = 0.05
    probe.capture_distance = 14.0
    probe.dilation_radius = 1.0
    probe.dilation_threshold = 0.5

    coll.objects.link(obj)
    return obj


def main():
    oo.purge(PREFIX)
    coll = oo.get_collection()

    lamps = build_cove_lights(coll)
    world = build_world()
    probe = build_irradiance_volume(coll)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    ee = scene.eevee
    ee.use_raytracing = True
    ee.use_shadows = True
    ee.gi_diffuse_bounces = 4
    if hasattr(ee, "ray_tracing_options"):
        ee.ray_tracing_options.use_denoise = True

    return {
        "cove_lamps": len(lamps),
        "watts_each": COVE_WATTS,
        "watts_total": round(COVE_WATTS * len(lamps), 1),
        "trough_z": round(TROUGH_Z, 3),
        "trough_inset": round(TROUGH_INSET, 3),
        "world": world.name,
        "probe": probe.name,
        "shadows_on_cove_lamps": False,
    }


result = main()
