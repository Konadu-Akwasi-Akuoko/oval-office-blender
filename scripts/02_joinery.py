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

# Measured off reference/Barack_Obama_in_the_Oval_Office_view_from_the_west_corridor.jpg,
# cropped to the cornice and enlarged. The first pass invented a heavy bracketed
# cornice from Gugler's description of it as "deep bracketed" - the photograph
# shows something far more delicate: two fine enrichment courses, an upper row of
# small oval bosses and a bead-and-dentil course below at about half the pitch.
# Chunky modillions were wrong by roughly a factor of two in every dimension.

# Lower course: fine dentils, at the profile step at inset 0.150.
DENTIL_W = 0.052
DENTIL_H = 0.046
DENTIL_D = 0.024
DENTIL_PITCH = 0.095
DENTIL_Z = 4.748
DENTIL_FACE = 0.150

# Upper course: oval paterae, at roughly twice the dentil pitch.
OVAL_W = 0.086
OVAL_H = 0.056
OVAL_D = 0.030
OVAL_PITCH = 0.190
OVAL_Z = 4.858
OVAL_FACE = 0.230


def build_course(name, count, z, face_inset, coll, box=None, oval=None, taper=0.0):
    verts, faces = [], []
    for t in oo.t_by_arclength(count):
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
    n_dentils = int(round(circumference / DENTIL_PITCH))
    n_ovals = int(round(circumference / OVAL_PITCH))

    dentils = build_course(
        f"{PREFIX}_Dentils", n_dentils, DENTIL_Z, DENTIL_FACE, coll,
        box=(DENTIL_W, DENTIL_H, DENTIL_D), taper=0.003,
    )
    ovals = build_course(
        f"{PREFIX}_Ovals", n_ovals, OVAL_Z, OVAL_FACE, coll,
        oval=(OVAL_W, OVAL_H, OVAL_D),
    )
    oo.shade_smooth_by_angle(ovals, degrees=50.0)

    plaster = bpy.data.materials.get("OO_Mat_Plaster")
    for obj in (dentils, ovals):
        obj.data.materials.clear()
        if plaster is not None:
            obj.data.materials.append(plaster)

    return {
        "perimeter_m": round(circumference, 3),
        "dentils": n_dentils,
        "dentil_pitch_m": round(circumference / n_dentils, 4),
        "ovals": n_ovals,
        "oval_pitch_m": round(circumference / n_ovals, 4),
        "dentils_per_oval": round(n_dentils / n_ovals, 2),
        "total_faces": len(dentils.data.polygons) + len(ovals.data.polygons),
    }


result = main()
