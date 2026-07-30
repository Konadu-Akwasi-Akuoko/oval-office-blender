"""Phase 4a - the fireplace breast and the 1909 Taft mantel.

Neoclassical marble, made for President Taft's office in 1909 and salvaged after
the 1929 West Wing fire. Dimensions from docs/research-findings.md.

What is modelled and what is faked follows the research, which is sound: the
carved relief on this mantel is under 8 mm deep, so displacement is wasted
unless the camera comes within a metre - and it never does, since it sits at
room centre. Geometry is spent only on silhouette: the two fluted Ionic columns,
the shelf profile, the dentil course, the rosette end blocks and the raised
tablet. Paterae, festoons, bow-knots and guttae are left to the material.

Run after 02c_niches.py so the wall is already solid.
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


PREFIX = "OO_Fire"

BREAST_W = 2.20  # flat chord panel let into the curved north wall
# Only as tall as it needs to be. A full-height breast rendered as a huge slab
# behind the mantel; above the shelf the curved wallpapered wall should simply
# carry on, which is what the reference photographs show.
BREAST_H = 1.45
MANTEL_W = 1.95
MANTEL_H = 1.30
MANTEL_D = 0.22
HEARTH_W = 2.00
HEARTH_D = 0.45
FIREBOX_W = 1.07
FIREBOX_H = 0.76
COLUMN_X = 0.735  # centre of each column, either side of the axis
SHELF_Z = 1.265

# The mantel front lands about here once the flat breast is set into the ellipse.
FACE_Y = 5.24

MARBLE = (0.937, 0.929, 0.902, 1.0)


def frame():
    """North wall, on the axis. Tangent is +X, into-wall is +Y."""
    origin = Vector((0.0, FACE_Y, 0.0))
    return origin, Vector((1.0, 0.0, 0.0)), Vector((0.0, 1.0, 0.0)), Vector((0.0, 0.0, 1.0))


def build_breast(coll):
    """Flat panel faired into the curved wall.

    The mantel is flat and the wall is not. Over a 2.2 m chord the ellipse bows
    about 135 mm, so a flat mantel set straight against it would gape at the
    ends. The breast gives it something flat to sit on.

    It is finished as WALL, not as marble - wainscot below the chair rail and
    wallpaper above - so it disappears into the room. Left as marble it read as
    a huge slab hung behind the fireplace.
    """
    origin, tangent, into, up = frame()
    v, f = [], []
    oo.add_box(v, f, origin + up * (oo.RAIL_H / 2.0), tangent, into, up,
               BREAST_W, 0.30, oo.RAIL_H)
    lower = oo.new_mesh_object(f"{PREFIX}_BreastDado", v, f, coll)

    v, f = [], []
    oo.add_box(v, f, origin + up * ((oo.RAIL_H + BREAST_H) / 2.0), tangent, into, up,
               BREAST_W, 0.30, BREAST_H - oo.RAIL_H)
    upper = oo.new_mesh_object(f"{PREFIX}_BreastWall", v, f, coll)
    return lower, upper


def build_mantel(coll):
    origin, tangent, into, up = frame()
    back = -into  # toward the room
    v, f = [], []

    def box(x, z, w, d, h):
        oo.add_box(v, f, origin + tangent * x + up * z, tangent, back, up, w, d, h)

    # Plain marble field either side of the firebox, and the lintel above it.
    for side in (-1, 1):
        box(side * (FIREBOX_W / 2.0 + 0.22) , 0.515, 0.44, MANTEL_D * 0.55, 1.03)
    box(0.0, 0.895, FIREBOX_W + 0.10, MANTEL_D * 0.55, 0.27)

    # Two fluted Ionic columns. Fluting is modelled, not faked - it catches the
    # cove wash and reads from anywhere in the room.
    for side in (-1, 1):
        x = side * COLUMN_X
        box(x, 0.055, 0.16, 0.16, 0.110)   # plinth
        box(x, 0.130, 0.145, 0.145, 0.040)  # torus base
        shaft_z0, shaft_z1 = 0.150, 0.940
        for i in range(20):
            a = math.pi * (i + 0.5) / 20.0  # half round; only the front shows
            oo.add_box(
                v, f,
                origin + tangent * (x + 0.0475 * math.cos(a))
                + back * (0.0475 * math.sin(a)) + up * ((shaft_z0 + shaft_z1) / 2.0),
                tangent, back, up, 0.011, 0.011, shaft_z1 - shaft_z0,
            )
        box(x, (shaft_z0 + shaft_z1) / 2.0, 0.088, 0.088, shaft_z1 - shaft_z0)  # core
        box(x, 0.975, 0.165, 0.115, 0.070)  # Ionic capital
        box(x, 1.020, 0.150, 0.105, 0.020)  # abacus
        box(x, 1.050, 0.150, 0.100, 0.040)  # die
        box(x, 1.125, 0.155, 0.105, 0.110)  # rosette end block

    # Dentil course, breaking forward over the end blocks.
    for i in range(int(MANTEL_W / 0.040)):
        x = -MANTEL_W / 2.0 + 0.020 + i * 0.040
        box(x, 1.2075, 0.020, 0.075, 0.055)

    box(0.0, 1.250, MANTEL_W, 0.115, 0.030)  # reeded bed band
    box(0.0, SHELF_Z + 0.0175, MANTEL_W + 0.25, MANTEL_D, 0.035)  # shelf slab

    # Raised central tablet. The carving on its face is a map, not geometry.
    box(0.0, 1.1075, 0.42, 0.075, 0.145)

    obj = oo.new_mesh_object(f"{PREFIX}_Mantel", v, f, coll)
    return obj


def build_hearth(coll):
    origin, tangent, into, up = frame()
    v, f = [], []
    oo.add_box(v, f, origin + (-into) * (HEARTH_D / 2.0) + up * 0.012,
               tangent, -into, up, HEARTH_W, HEARTH_D, 0.024)
    return oo.new_mesh_object(f"{PREFIX}_Hearth", v, f, coll)


def build_firebox(coll):
    """Recess behind the opening, so it reads as depth rather than a black decal."""
    origin, tangent, into, up = frame()
    v, f = [], []
    oo.add_box(v, f, origin + into * 0.22 + up * (FIREBOX_H / 2.0),
               tangent, into, up, FIREBOX_W, 0.30, FIREBOX_H)
    obj = oo.new_mesh_object(f"{PREFIX}_Firebox", v, f, coll)
    return obj


def marble_material():
    mat = bpy.data.materials.get(f"{PREFIX}_Marble")
    if mat is not None:
        bpy.data.materials.remove(mat)
    mat = bpy.data.materials.new(f"{PREFIX}_Marble")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (400, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (150, 0)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    bsdf.inputs["Base Color"].default_value = MARBLE
    bsdf.inputs["Roughness"].default_value = 0.30
    # Marble reads translucent at the arrises, which is most of what separates it
    # from painted plaster at a distance.
    if "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = 0.12
        bsdf.inputs["Subsurface Radius"].default_value = (0.6, 0.5, 0.45)

    # Soft grey-green veining.
    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-450, -200)
    noise.inputs["Scale"].default_value = 3.2
    noise.inputs["Detail"].default_value = 8.0
    noise.inputs["Distortion"].default_value = 2.4

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (-220, -200)
    ramp.color_ramp.elements[0].position = 0.44
    ramp.color_ramp.elements[0].color = MARBLE
    ramp.color_ramp.elements[1].position = 0.56
    ramp.color_ramp.elements[1].color = (0.772, 0.784, 0.749, 1.0)
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def main():
    oo.purge(PREFIX)
    coll = oo.get_collection()

    breast_dado, breast_wall = build_breast(coll)
    mantel = build_mantel(coll)
    hearth = build_hearth(coll)
    firebox = build_firebox(coll)

    marble = marble_material()
    for obj in (mantel, hearth):
        obj.data.materials.clear()
        obj.data.materials.append(marble)

    # Breast takes the wall finishes. 03_materials runs after this phase and
    # owns those materials, so they are looked up there rather than here - a
    # lookup at this point returns None and leaves the object bare.
    breast_dado["oo_material"] = "wainscot"
    breast_wall["oo_material"] = "wallpaper"

    soot = bpy.data.materials.get(f"{PREFIX}_Soot")
    if soot is None:
        soot = bpy.data.materials.new(f"{PREFIX}_Soot")
        soot.use_nodes = True
        b = soot.node_tree.nodes.get("Principled BSDF")
        b.inputs["Base Color"].default_value = (0.035, 0.032, 0.030, 1.0)
        b.inputs["Roughness"].default_value = 0.92
    firebox.data.materials.clear()
    firebox.data.materials.append(soot)

    return {
        "breast": f"{BREAST_W} x {BREAST_H}",
        "mantel": f"{MANTEL_W} x {MANTEL_H} x {MANTEL_D}",
        "firebox": f"{FIREBOX_W} x {FIREBOX_H}",
        "shelf_z": SHELF_Z,
        "faces": sum(len(o.data.polygons)
                     for o in (breast_dado, breast_wall, mantel, hearth, firebox)),
    }


result = main()
