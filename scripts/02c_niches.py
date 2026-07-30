"""Phase 2c - the four arched shell-head units.

The research corrected the plan here. There are FOUR architecturally identical
arch-and-shell units, not two:

- WEST wall, either side of the study door: the two built-in BOOKCASE niches.
- EAST wall, either side of the Rose Garden door: two identical recesses that
  contain tall WINDOWS instead of shelves.

So one unit is modelled and mirrored four times; only the fill differs.

The shell head is built as real geometry rather than a normal map. The research
argues for this and it is right: it is the most recognisable ornament in the
room after the ceiling medallion, it sits at camera height, and its lobes break
the arch outline - a normal map cannot change a silhouette.

Run AFTER 02b_openings.py, which leaves the wall a solid manifold mesh.
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


PREFIX = "OO_Niche"

# Plan coordinates from the research. Bearings are derived from these rather
# than from its quoted 72/108 degrees, which are marked estimated and are about
# 3 degrees out from the coordinates.
CENTRES = {
    "SW": (-4.275, -1.389, "shelves"),
    "NW": (-4.275, +1.389, "shelves"),
    "SE": (+4.275, -1.389, "window"),
    "NE": (+4.275, +1.389, "window"),
}

OPENING_W = 0.98  # inside the moulded archivolt
UNIT_W = 1.08  # including the arch ring
BASE_Z = 0.90  # sits on the dado cap
SPRING_Z = 2.17
ARCH_R = 0.49
RECESS_D = 0.26

SHELF_TIERS = 4
SHELF_PITCH = 0.317
SHELF_DEPTH = 0.22
SHELF_THICK = 0.023
CASE_W = 0.90  # clear width inside the architrave

SHELL_R = 0.44
SHELL_FLUTES = 21  # odd, so one flute sits on the axis
SHELL_UMBO_PROJ = 0.050
SHELL_RIM_PROJ = 0.012


def unit_frame(x, y, inset=0.0):
    bearing = oo.bearing_of_point(x, y)
    pos, tangent, inward, up = oo.point_and_frame(bearing, inset)
    return bearing, Vector((pos.x, pos.y, 0.0)), tangent, inward, up


def build_cutters(coll):
    cutters = []
    for key, (x, y, fill) in CENTRES.items():
        # The recess goes INTO the wall, which is -inward. `inward` points at the
        # room centre, so extruding along it carves empty room air and leaves the
        # wall untouched - the first attempt did exactly that and the shelves
        # ended up floating in the middle of the room.
        through = fill == "window"
        depth = 1.10 if through else RECESS_D + 0.03
        _, origin, tangent, inward, up = unit_frame(x, y, 0.03)

        v, f = [], []
        oo.add_prism(v, f, oo.arch_outline(OPENING_W, BASE_Z, SPRING_Z, ARCH_R),
                     origin, tangent, -inward, up, depth)
        obj = oo.new_mesh_object(f"{PREFIX}_Cut_{key}", v, f, coll)
        obj.display_type = "WIRE"
        obj.hide_render = True
        cutters.append(obj)
    return cutters


def cut_wall(cutters):
    wall = bpy.data.objects["OO_Shell_Wall"]
    if wall.get("oo_niches_cut"):
        return "already cut"

    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = wall
    for cutter in cutters:
        mod = wall.modifiers.new(f"Niche_{cutter.name}", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = cutter
        mod.solver = "MANIFOLD"  # EXACT empties this mesh; see docs/learnings.md
        bpy.ops.object.modifier_apply(modifier=mod.name)
        if len(wall.data.polygons) == 0:
            raise RuntimeError(f"Boolean {cutter.name} emptied the wall.")
    wall["oo_niches_cut"] = True
    return "cut"


def build_archivolt(key, x, y, coll):
    """The moulded arch ring around the opening, plus the flat tympanum behind."""
    _, origin, tangent, inward, up = unit_frame(x, y)
    v, f = [], []

    outer = oo.arch_outline(UNIT_W, BASE_Z, SPRING_Z, ARCH_R + 0.05)
    inner = oo.arch_outline(OPENING_W, BASE_Z, SPRING_Z, ARCH_R)

    # Ring as a band between the two outlines, projecting slightly into the room.
    n = len(outer)
    base = len(v)
    for depth in (-0.028, 0.0):
        for along, rise in outer:
            v.append(tuple(origin + tangent * along + up * rise + inward * depth))
        for along, rise in inner:
            v.append(tuple(origin + tangent * along + up * rise + inward * depth))
    for layer in (0, 1):
        off = base + layer * 2 * n
        for i in range(n):
            j = (i + 1) % n
            f.append((off + i, off + j, off + n + j, off + n + i))

    return oo.new_mesh_object(f"{PREFIX}_{key}_Archivolt", v, f, coll)


def build_shell_head(key, x, y, coll):
    """Scalloped shell in relief on the lunette, radiating from the umbo.

    The umbo sits at the bottom centre of the arch on the spring line, and the
    flutes fan upward from it. Built as a triangle fan so each flute is a raised
    ridge falling away to a valley either side.
    """
    _, origin, tangent, inward, up = unit_frame(x, y)
    apex = origin + up * SPRING_Z  # umbo, on the spring line

    v, f = [], []
    v.append(tuple(apex + inward * SHELL_UMBO_PROJ))
    rings = 5
    lobes = SHELL_FLUTES * 2 + 1  # ridge and valley alternating

    for ring in range(1, rings + 1):
        radius = SHELL_R * ring / rings
        for k in range(lobes):
            angle = math.pi * k / (lobes - 1)  # 0..pi, a half fan above the umbo
            ridge = (k % 2 == 0)
            # Ridges stand proud, valleys sink toward the tympanum. The relief
            # tapers from the umbo out to the rim.
            taper = 1.0 - (ring / rings)
            proj = SHELL_RIM_PROJ + (SHELL_UMBO_PROJ - SHELL_RIM_PROJ) * taper
            if not ridge:
                proj *= 0.35
            v.append(tuple(
                apex
                + tangent * (radius * math.cos(angle))
                + up * (radius * math.sin(angle))
                + inward * proj
            ))

    for k in range(lobes - 1):
        f.append((0, 1 + k, 1 + k + 1))
    for ring in range(rings - 1):
        a0 = 1 + ring * lobes
        b0 = 1 + (ring + 1) * lobes
        for k in range(lobes - 1):
            f.append((a0 + k, a0 + k + 1, b0 + k + 1, b0 + k))

    obj = oo.new_mesh_object(f"{PREFIX}_{key}_Shell", v, f, coll)
    oo.shade_smooth_by_angle(obj, degrees=44.0)
    return obj


def build_shelves(key, x, y, coll):
    _, origin, tangent, inward, up = unit_frame(x, y)
    back_dir = -inward  # into the wall
    v, f = [], []

    # Back panel closing the recess.
    back = origin + back_dir * RECESS_D
    oo.add_box(v, f, back + up * ((BASE_Z + SPRING_Z) / 2.0), tangent, back_dir, up,
               OPENING_W, 0.02, SPRING_Z - BASE_Z)

    for tier in range(SHELF_TIERS):
        z = BASE_Z + tier * SHELF_PITCH
        centre = origin + back_dir * (RECESS_D - SHELF_DEPTH) + up * z
        oo.add_box(v, f, centre, tangent, back_dir, up, CASE_W, SHELF_DEPTH, SHELF_THICK)

    # Flat soffit closing the top of the case at the spring line.
    oo.add_box(v, f, origin + back_dir * (RECESS_D - SHELF_DEPTH) + up * SPRING_Z,
               tangent, back_dir, up, CASE_W, SHELF_DEPTH, 0.022)

    return oo.new_mesh_object(f"{PREFIX}_{key}_Shelves", v, f, coll)


def build_niche_window(key, x, y, coll):
    """Glass and a light grid for the east recesses, which are glazed."""
    _, origin, tangent, inward, up = unit_frame(x, y)
    back_dir = -inward
    seat = origin + back_dir * 0.12  # sash sits back in the reveal
    v, f = [], []

    cols, rows = 3, 4
    inner_w, inner_h = CASE_W, SPRING_Z - BASE_Z
    for c in range(1, cols):
        oo.add_box(v, f, seat + up * ((BASE_Z + SPRING_Z) / 2.0)
                   + tangent * (-inner_w / 2.0 + c * inner_w / cols),
                   tangent, back_dir, up, 0.022, 0.04, inner_h)
    for r in range(1, rows):
        oo.add_box(v, f, seat + up * (BASE_Z + r * inner_h / rows),
                   tangent, back_dir, up, inner_w, 0.04, 0.022)
    bars = oo.new_mesh_object(f"{PREFIX}_{key}_Bars", v, f, coll)

    gv, gf = [], []
    oo.add_prism(gv, gf, oo.arch_outline(OPENING_W - 0.02, BASE_Z + 0.01, SPRING_Z, ARCH_R - 0.01),
                 seat + back_dir * 0.02, tangent, back_dir, up, 0.006)
    glass = oo.new_mesh_object(f"{PREFIX}_{key}_Glass", gv, gf, coll)
    return bars, glass


def main():
    oo.purge(PREFIX)
    coll = oo.get_collection()

    cutters = build_cutters(coll)
    status = cut_wall(cutters)
    for c in cutters:
        bpy.data.objects.remove(c, do_unlink=True)

    trim = bpy.data.materials.get("OO_Mat_Wainscot")
    plaster = bpy.data.materials.get("OO_Mat_Plaster")
    glass_mat = bpy.data.materials.get("OO_Mat_Glass")

    made = {}
    for key, (x, y, fill) in CENTRES.items():
        arch = build_archivolt(key, x, y, coll)
        shell = build_shell_head(key, x, y, coll)
        for obj, mat in ((arch, trim), (shell, plaster)):
            obj.data.materials.clear()
            if mat is not None:
                obj.data.materials.append(mat)

        if fill == "shelves":
            sh = build_shelves(key, x, y, coll)
            sh.data.materials.clear()
            if trim is not None:
                sh.data.materials.append(trim)
        else:
            bars, glass = build_niche_window(key, x, y, coll)
            bars.data.materials.clear()
            if trim is not None:
                bars.data.materials.append(trim)
            glass.data.materials.clear()
            if glass_mat is not None:
                glass.data.materials.append(glass_mat)
        made[key] = fill

    return {
        "cut": status,
        "units": made,
        "bearings_deg": {k: round(oo.bearing_of_point(x, y), 2)
                         for k, (x, y, _) in CENTRES.items()},
        "shell_flutes": SHELL_FLUTES,
        "wall_faces": len(bpy.data.objects["OO_Shell_Wall"].data.polygons),
    }


result = main()
