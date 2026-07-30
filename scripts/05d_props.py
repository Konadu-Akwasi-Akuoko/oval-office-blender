"""Phase 5d - books, framed art and mantel objects.

Added after a full-rotation sweep showed two things the earlier per-frame checks
had missed, because they only ever looked at the south and east:

- The bookcase niches were EMPTY. They are bookcases; empty shelves read as
  unfinished joinery.
- There was no art at all, anywhere. Beyond being wrong, this is why the north
  end rendered washed out: with pale wallpaper, pale marble and no dark object
  anywhere in frame, there was nothing to anchor the exposure against.

The paintings are framed panels with muted canvas tones rather than the real
images. At room centre with a 20 mm lens they are small in frame, and what does
the work is the dark frame breaking the wall and giving the eye a black point.
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


PREFIX = "OO_Prop"

# Bookcase niches, from 02c_niches.py.
NICHE_CENTRES = ((-4.275, -1.389), (-4.275, +1.389))
BASE_Z = 0.90
SHELF_PITCH = 0.317
CASE_W = 0.90
RECESS_D = 0.26

SPINE_COLOURS = [
    (0.075, 0.048, 0.032, 1.0),
    (0.105, 0.028, 0.024, 1.0),
    (0.030, 0.048, 0.075, 1.0),
    (0.088, 0.070, 0.032, 1.0),
    (0.055, 0.062, 0.048, 1.0),
]


def mat(name, colour, roughness=0.72, metallic=0.0):
    full = f"{PREFIX}_{name}"
    existing = bpy.data.materials.get(full)
    if existing is not None:
        bpy.data.materials.remove(existing)
    m = bpy.data.materials.new(full)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = colour
    b.inputs["Roughness"].default_value = roughness
    b.inputs["Metallic"].default_value = metallic
    return m


def build_books(coll, materials):
    """Rows of spines on the three upper tiers of each niche."""
    made = []
    for n, (x, y) in enumerate(NICHE_CENTRES):
        bearing = oo.bearing_of_point(x, y)
        _, tangent, inward, up = oo.point_and_frame(bearing)
        origin_pt = oo.ellipse_point(oo.bearing_to_t(bearing))
        origin = Vector((origin_pt.x, origin_pt.y, 0.0))
        back = -inward

        for tier in range(1, 4):
            z = BASE_Z + tier * SHELF_PITCH
            # Deterministic but irregular: vary width and height per book so the
            # row does not read as a striped block.
            cursor = -CASE_W / 2.0 + 0.03
            i = 0
            while cursor < CASE_W / 2.0 - 0.06:
                w = 0.026 + 0.020 * ((i * 7 + tier * 3 + n) % 5) / 5.0
                h = 0.215 + 0.045 * ((i * 5 + tier) % 4) / 4.0
                lean = 0.0
                colour_idx = (i * 3 + tier + n) % len(SPINE_COLOURS)

                v, f = [], []
                oo.add_box(v, f,
                           origin + tangent * (cursor + w / 2.0)
                           + back * (RECESS_D - 0.20) + up * (z + 0.012 + h / 2.0),
                           tangent, back, up, w - 0.004, 0.175, h)
                obj = oo.new_mesh_object(f"{PREFIX}_Book_{n}_{tier}_{i}", v, f, coll)
                obj.data.materials.append(materials[colour_idx])
                obj["oo_material"] = "keep"
                if lean:
                    obj.rotation_euler = (0.0, lean, 0.0)
                made.append(obj)
                cursor += w
                i += 1
    return made


def build_frame(name, coll, bearing, z_centre, width, height, frame_mat, canvas_mat,
                inset=0.02):
    """A framed painting hung flat against the curved wall."""
    _, tangent, inward, up = oo.point_and_frame(bearing, inset)
    pt = oo.ellipse_point(oo.bearing_to_t(bearing), inset)
    centre = Vector((pt.x, pt.y, z_centre))

    # Depth runs INWARD, into the room. add_box extrudes from its centre along
    # the direction given, so passing the into-wall vector buries the whole
    # frame in the plaster and leaves only a sliver at the surface showing.
    # Exactly the mistake the door panels made.
    v, f = [], []
    b = 0.055  # frame border
    oo.add_box(v, f, centre + up * ((height + b) / 2.0), tangent, inward, up,
               width + 2 * b, 0.058, b)
    oo.add_box(v, f, centre - up * ((height + b) / 2.0), tangent, inward, up,
               width + 2 * b, 0.058, b)
    for side in (-1, 1):
        oo.add_box(v, f, centre + tangent * (side * (width + b) / 2.0),
                   tangent, inward, up, b, 0.058, height + 2 * b)
    frame = oo.new_mesh_object(f"{PREFIX}_Frame_{name}", v, f, coll)
    frame.data.materials.append(frame_mat)
    frame["oo_material"] = "keep"

    # Canvas sits just proud of the wall and recessed within the frame's depth.
    v, f = [], []
    oo.add_box(v, f, centre, tangent, inward, up, width, 0.014, height)
    canvas = oo.new_mesh_object(f"{PREFIX}_Canvas_{name}", v, f, coll)
    canvas.data.materials.append(canvas_mat)
    canvas["oo_material"] = "keep"
    return frame, canvas


def build_mantel_objects(coll, materials):
    """Clock and a pair of urns on the shelf, plus a firescreen."""
    made = []
    gilt, dark = materials
    shelf_z = 1.30
    y = 5.24

    v, f = [], []
    oo.add_box(v, f, Vector((0.0, y - 0.09, shelf_z + 0.16)),
               Vector((1, 0, 0)), Vector((0, -1, 0)), Vector((0, 0, 1)),
               0.22, 0.12, 0.32)
    clock = oo.new_mesh_object(f"{PREFIX}_MantelClock", v, f, coll)
    clock.data.materials.append(dark)
    clock["oo_material"] = "keep"
    made.append(clock)

    for side in (-1, 1):
        v, f = [], []
        oo.add_box(v, f, Vector((side * 0.62, y - 0.09, shelf_z + 0.11)),
                   Vector((1, 0, 0)), Vector((0, -1, 0)), Vector((0, 0, 1)),
                   0.14, 0.14, 0.22)
        urn = oo.new_mesh_object(f"{PREFIX}_Urn{'LR'[max(side,0)]}", v, f, coll)
        urn.data.materials.append(gilt)
        urn["oo_material"] = "keep"
        made.append(urn)
    return made


def main():
    oo.purge(PREFIX)
    coll = oo.get_collection()

    spines = [mat(f"Spine{i}", c, roughness=0.62) for i, c in enumerate(SPINE_COLOURS)]
    gilt = mat("Gilt", (0.412, 0.318, 0.128, 1.0), roughness=0.28, metallic=0.80)
    dark_wood = mat("FrameWood", (0.052, 0.030, 0.020, 1.0), roughness=0.40)

    canvases = {
        "landscape": mat("CanvasLandscape", (0.118, 0.105, 0.072, 1.0), roughness=0.82),
        "portrait": mat("CanvasPortrait", (0.085, 0.062, 0.048, 1.0), roughness=0.82),
        "flag": mat("CanvasFlag", (0.075, 0.082, 0.115, 1.0), roughness=0.82),
    }

    books = build_books(coll, spines)

    # Bearings are degrees from due south, positive east. Hung on the blank wall
    # segments between the openings.
    art = []
    art.append(build_frame("OverMantel", coll, 180.0, 2.55, 1.05, 1.30,
                           gilt, canvases["portrait"]))
    art.append(build_frame("NE", coll, 122.0, 2.30, 0.72, 0.90,
                           gilt, canvases["landscape"]))
    art.append(build_frame("NW", coll, -122.0, 2.30, 0.72, 0.90,
                           gilt, canvases["flag"]))
    art.append(build_frame("SE", coll, 52.0, 2.25, 0.62, 0.78,
                           dark_wood, canvases["landscape"]))
    art.append(build_frame("SW", coll, -52.0, 2.25, 0.62, 0.78,
                           dark_wood, canvases["portrait"]))

    mantel_objects = build_mantel_objects(coll, (gilt, dark_wood))

    return {
        "books": len(books),
        "paintings": len(art),
        "mantel_objects": len(mantel_objects),
        "faces": sum(len(o.data.polygons) for o in books + mantel_objects)
        + sum(len(o.data.polygons) for pair in art for o in pair),
    }


result = main()
