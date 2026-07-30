"""Phase 2a - cornice enrichment.

The swept shell from phase 1 gives the cornice its correct profile, but a swept
profile can only ever produce continuous ledges. The two courses that make a
classical cornice read as one - the dentils and the modillions - are rows of
separate blocks, and they have to be arrayed as geometry.

This matters more here than it would in most rooms. The camera spends the whole
360 with the cornice in the upper third of frame, lit by raking light from the
trough directly above it. Smooth ledges read as a plain plaster band.

Both courses are built as single merged meshes. Hundreds of separate objects
would cost far more for no benefit, since they are never touched individually.

Doors, windows and niches are cut in phase 2b, which is where the research
bearings are needed. This part needs none of that.

Run with `exec(open(path).read())` inside Blender. Idempotent.
"""

import importlib
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


PREFIX = "OO_Cornice"

# All from the photogrammetric solve in docs/research-findings.md, which counted
# repeats by band-pass zero-crossing on the unwrapped cornice ring at four radii
# in an upward-looking 2022 ceiling photograph, cross-checked by DFT.
#
# Two earlier passes were wrong. The first invented heavy modillion brackets from
# Gugler's "deep bracketed cornice". The second read a low-angle crop as oval
# bosses over a dentil course. It is neither: a Corinthian modillion cornice with
# a coffered soffit, each coffer holding a rosette, separated by fluted bracket
# blocks, over an egg-and-dart ovolo at exactly twice the frequency.
#
# The 2:1 ratio spotted in the second pass was right. Everything else was not.

MODILLION_COUNT = 126  # 126 +/- 2 from the solve
MODILLION_W = 0.080  # fluted bracket block, ~35% of the bay
MODILLION_H = 0.100
MODILLION_D = 0.070
MODILLION_Z = 4.880
MODILLION_FACE = 0.215

ROSETTE_D = 0.085  # patera sunk in each coffer between the brackets
ROSETTE_H = 0.085
ROSETTE_PROJ = 0.022
ROSETTE_Z = 4.895
ROSETTE_FACE = 0.200

EGG_COUNT = MODILLION_COUNT * 2  # 252, confirmed by a DFT peak at k ~ 248-258
EGG_W = 0.072
EGG_H = 0.052
EGG_D = 0.028
EGG_Z = 4.805
EGG_FACE = 0.160


def build_course(name, count, z, face_inset, coll, box=None, oval=None, taper=0.0,
                 half_bay_offset=False):
    verts, faces = [], []
    positions = oo.t_by_arclength(count)
    if half_bay_offset:
        positions = oo.t_by_arclength(count * 2)[1::2]
    for t in positions:
        tangent, inward, up = oo.local_frame(t)
        anchor = oo.ellipse_point(t, face_inset)
        centre = Vector((anchor.x, anchor.y, z))
        if box is not None:
            width, height, depth = box
            oo.add_box(verts, faces, centre, tangent, inward, up, width, depth, height)
        else:
            width, height, depth = oval
            oo.add_ellipsoid(verts, faces, centre, tangent, inward, up, width, height, depth)

    obj = oo.new_mesh_object(name, verts, faces, coll)

    if taper:
        # Slight chamfer so the blocks catch the raking light from the trough
        # above rather than reading as flat rectangles.
        mod = obj.modifiers.new("Bevel", "BEVEL")
        mod.width = taper
        mod.segments = 1
        mod.limit_method = "ANGLE"
        mod.angle_limit = 0.7

    return obj


def main():
    oo.purge(PREFIX)
    coll = oo.get_collection()

    circumference = oo.perimeter()

    modillions = build_course(
        f"{PREFIX}_Modillions", MODILLION_COUNT, MODILLION_Z, MODILLION_FACE, coll,
        box=(MODILLION_W, MODILLION_H, MODILLION_D), taper=0.004,
    )

    # Rosettes sit in the coffers BETWEEN the brackets, so the ring is offset by
    # half a bay. Without the offset every patera would be hidden behind a block.
    rosettes = build_course(
        f"{PREFIX}_Rosettes", MODILLION_COUNT, ROSETTE_Z, ROSETTE_FACE, coll,
        oval=(ROSETTE_D, ROSETTE_H, ROSETTE_PROJ), half_bay_offset=True,
    )
    oo.shade_smooth_by_angle(rosettes, degrees=50.0)

    eggs = build_course(
        f"{PREFIX}_EggAndDart", EGG_COUNT, EGG_Z, EGG_FACE, coll,
        oval=(EGG_W, EGG_H, EGG_D),
    )
    oo.shade_smooth_by_angle(eggs, degrees=50.0)

    plaster = bpy.data.materials.get("OO_Mat_Plaster")
    parts = (modillions, rosettes, eggs)
    for obj in parts:
        obj.data.materials.clear()
        if plaster is not None:
            obj.data.materials.append(plaster)

    return {
        "perimeter_m": round(circumference, 3),
        "modillions": MODILLION_COUNT,
        "modillion_pitch_m": round(circumference / MODILLION_COUNT, 4),
        "rosettes": MODILLION_COUNT,
        "eggs": EGG_COUNT,
        "egg_pitch_m": round(circumference / EGG_COUNT, 4),
        "total_faces": sum(len(o.data.polygons) for o in parts),
    }


result = main()
