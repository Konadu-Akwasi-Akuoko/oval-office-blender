"""Phase 2b - cut the openings, then build windows and doors.

All positions come from docs/research-findings.md. Bearings are quoted there in
degrees from due south, positive toward the east; `oo.bearing_to_t` converts.

Two things here are easy to get wrong and both are called out in the research:

1. Fittings must be rotated to the ellipse NORMAL, never to the radial
   direction. They differ by 10.65 degrees at the side windows, measured. Using
   the radius makes the side windows sit visibly skewed against the desk, and it
   is reportedly the most common error in models of this room.

2. Only the east and west doors are pedimented. The north-east and north-west
   openings are flush jib doors with no pediment at all. Four pedimented doors
   is a common mistake.

The shell is a swept surface, so it is solidified before booleaning. Cutting an
open surface with Blender's exact solver is unreliable; giving it real thickness
first makes the cuts clean.

Run AFTER 01_shell.py. Idempotent, but a re-run without rebuilding the shell
first will skip the cut rather than cut twice.
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


PREFIX = "OO_Opening"
WALL_THICKNESS = 0.45

# --- Windows ---------------------------------------------------------------
WIN_BEARINGS = (-31.0, 0.0, 31.0)
WIN_W = 1.15
WIN_SILL = 0.50
WIN_HEAD = 4.05
WIN_MEETING = 2.28  # meeting rail height, chest height in every photograph
WIN_REVEAL = 0.40
WIN_COLS, WIN_ROWS = 3, 3  # per sash, giving 9 over 9
WIN_MUNTIN = 0.022
WIN_STILE = 0.055

# --- Doors -----------------------------------------------------------------
DOOR_W = 1.10
DOOR_H = 2.40
CASE_OUTER_W = 1.81
CASE_RECESS = 0.090  # flat recess so the flat case meets the curved wall
PEDIMENT_APEX = 3.62

PEDIMENTED = (-90.0, 90.0)  # west to the private study, east to the Rose Garden
JIB = ((-2.870, 4.150), (2.870, 4.150))  # north-west and north-east, flush


def bearing_of_point(x, y):
    """Recover a research bearing from a point known to lie on the ellipse."""
    return math.degrees(math.atan2(x / oo.SEMI_X, -y / oo.SEMI_Y))


def make_cutter(name, bearing, width, height, z_bottom, coll,
                depth_out=0.90, depth_in=0.25):
    """A flat box spanning the wall at `bearing`, oriented to the true normal."""
    pos, tangent, inward, up = oo.point_and_frame(bearing, -depth_out)
    centre = Vector((pos.x, pos.y, z_bottom + height / 2.0))
    verts, faces = [], []
    oo.add_box(verts, faces, centre, tangent, inward, up,
               width, depth_out + depth_in, height)
    obj = oo.new_mesh_object(name, verts, faces, coll)
    obj.display_type = "WIRE"
    obj.hide_render = True
    return obj


def cut_shell(cutters):
    shell = bpy.data.objects["OO_Shell_Wall"]
    if shell.get("oo_openings_cut"):
        return "already cut - re-run 01_shell.py first for a clean cut"

    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = shell

    # Real thickness first, grown OUTWARD so the inner face - the only one that
    # matters - stays exactly where phase 1 put it.
    #
    # offset MUST be -1.0. The shell's normals point into the room, so +1.0
    # extrudes inward: the room silently shrinks by WALL_THICKNESS on every
    # side, the fittings end up buried behind the new surface, and the cutters
    # miss it entirely. Nothing errors. Caught by raycasting from the camera and
    # finding the south wall at y -5.011 instead of -5.461.
    solid = shell.modifiers.new("Solidify", "SOLIDIFY")
    solid.thickness = WALL_THICKNESS
    solid.offset = -1.0
    solid.use_even_offset = True
    bpy.ops.object.modifier_apply(modifier=solid.name)

    # Verify against the INNER face by raycasting the shell itself. Checking
    # min(vertex.y) instead would read the new OUTER surface, which is correctly
    # at -5.911, and reject a perfectly good result.
    ok, loc, _, _ = shell.ray_cast(Vector((0.0, 0.0, 2.0)), Vector((0.0, -1.0, 0.0)))
    if not ok or abs(loc.y + oo.SEMI_Y) > 0.02:
        raise RuntimeError(
            f"Solidify went the wrong way: inner face at y={loc.y if ok else 'miss'}, "
            f"expected {-oo.SEMI_Y:.3f}. offset must be -1.0."
        )

    for cutter in cutters:
        mod = shell.modifiers.new(f"Cut_{cutter.name}", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = cutter
        # MANIFOLD, not EXACT. On this wall the EXACT solver silently reduces
        # the mesh to ZERO faces - measured, with a plain primitive cube as the
        # cutter, so it is the solver and not the geometry. FLOAT also works but
        # Manifold is the robust choice for a watertight mesh, which solidify
        # has already guaranteed (0 non-manifold edges).
        mod.solver = "MANIFOLD"
        bpy.ops.object.modifier_apply(modifier=mod.name)
        if len(shell.data.polygons) == 0:
            raise RuntimeError(f"Boolean {cutter.name} emptied the wall mesh.")

    shell["oo_openings_cut"] = True
    return "cut"


def build_window(index, bearing, coll):
    """Frame, sill, two 9-light sashes, and two glass planes."""
    parts_v, parts_f = [], []
    height = WIN_HEAD - WIN_SILL

    def box(centre, w, d, h):
        _, tangent, inward, up = oo.point_and_frame(bearing)
        oo.add_box(parts_v, parts_f, centre, tangent, inward, up, w, d, h)

    def at(inset, z, along=0.0):
        pos, tangent, _, _ = oo.point_and_frame(bearing, inset)
        return Vector((pos.x, pos.y, z)) + tangent * along

    # Panelled reveal lining: two jambs, a head and the sill.
    for side in (-1, 1):
        box(at(-WIN_REVEAL / 2.0, WIN_SILL + height / 2.0,
               side * (WIN_W / 2.0 + 0.03)), 0.06, WIN_REVEAL, height)
    box(at(-WIN_REVEAL / 2.0, WIN_HEAD + 0.03), WIN_W + 0.12, WIN_REVEAL, 0.06)
    box(at(-WIN_REVEAL / 2.0 + 0.02, WIN_SILL - 0.04), WIN_W + 0.22, WIN_REVEAL + 0.10, 0.08)

    # Outer casing on the room face.
    for side in (-1, 1):
        box(at(0.015, WIN_SILL + height / 2.0, side * (WIN_W / 2.0 + 0.07)),
            0.14, 0.03, height + 0.14)
    box(at(0.015, WIN_HEAD + 0.07), WIN_W + 0.28, 0.03, 0.14)

    sashes = (
        (WIN_SILL, WIN_MEETING + 0.045, -0.10),
        (WIN_MEETING - 0.045, WIN_HEAD, -0.18),
    )
    glass = []
    for sash_bottom, sash_top, sash_inset in sashes:
        sash_h = sash_top - sash_bottom
        mid = sash_bottom + sash_h / 2.0

        # Stiles and rails.
        for side in (-1, 1):
            box(at(sash_inset, mid, side * (WIN_W / 2.0 - WIN_STILE / 2.0)),
                WIN_STILE, 0.05, sash_h)
        box(at(sash_inset, sash_bottom + 0.065), WIN_W, 0.05, 0.13)
        box(at(sash_inset, sash_top - 0.03), WIN_W, 0.05, 0.06)

        # Muntin grid: WIN_COLS x WIN_ROWS lights per sash.
        light_w = (WIN_W - 2 * WIN_STILE) / WIN_COLS
        light_h = (sash_h - 0.19) / WIN_ROWS
        for c in range(1, WIN_COLS):
            box(at(sash_inset, mid, -WIN_W / 2.0 + WIN_STILE + c * light_w),
                WIN_MUNTIN, 0.04, sash_h - 0.19)
        for r in range(1, WIN_ROWS):
            box(at(sash_inset, sash_bottom + 0.13 + r * light_h),
                WIN_W - 2 * WIN_STILE, 0.04, WIN_MUNTIN)

        glass.append((sash_inset - 0.012, sash_bottom + 0.13, sash_top - 0.06))

    frame = oo.new_mesh_object(f"{PREFIX}_Window{index}_Frame", parts_v, parts_f, coll)

    # Glass. Two planes, not one: the photographs show doubled ghost
    # reflections, which is a historic sash plus a separate interior ballistic
    # panel behind it. One plane cannot produce that.
    gv, gf = [], []
    for inset, z0, z1 in glass:
        _, tangent, inward, up = oo.point_and_frame(bearing)
        centre = at(inset, (z0 + z1) / 2.0)
        oo.add_box(gv, gf, centre, tangent, inward, up, WIN_W - 2 * WIN_STILE, 0.006, z1 - z0)
    ballistic = at(-0.30, WIN_SILL + height / 2.0)
    _, tangent, inward, up = oo.point_and_frame(bearing)
    oo.add_box(gv, gf, ballistic, tangent, inward, up, WIN_W - 0.02, 0.060, height - 0.10)
    pane = oo.new_mesh_object(f"{PREFIX}_Window{index}_Glass", gv, gf, coll)

    return frame, pane


def build_pedimented_case(index, bearing, coll):
    """Architrave, pulvinated frieze, cornice and pediment. East and west only."""
    v, f = [], []

    def at(inset, z, along=0.0):
        pos, tangent, _, _ = oo.point_and_frame(bearing, inset)
        return Vector((pos.x, pos.y, z)) + tangent * along

    def box(centre, w, d, h):
        _, tangent, inward, up = oo.point_and_frame(bearing)
        oo.add_box(v, f, centre, tangent, inward, up, w, d, h)

    face = CASE_RECESS - 0.005  # sits in the flat recess cut for it

    # Architrave, with crossettes stepping out at the head.
    for side in (-1, 1):
        box(at(face, DOOR_H / 2.0, side * (DOOR_W / 2.0 + 0.13)), 0.26, 0.055, DOOR_H)
    box(at(face, DOOR_H + 0.13), DOOR_W + 0.64, 0.055, 0.26)

    # Pulvinated (cushioned) frieze - a half-round lying horizontally.
    box(at(face, 2.71), 1.86, 0.10, 0.22)
    for side in (-1, 1):
        box(at(face, 2.71, side * 0.98), 0.13, 0.11, 0.22)

    box(at(face, 2.91), 2.15, 0.075, 0.10)  # egg-and-dart bed mould
    box(at(face, 3.02), 2.15, 0.23, 0.11)  # horizontal cornice

    # Pediment. Built as two prisms rather than a stack of boxes: stepping boxes
    # up the rake produced a visible staircase instead of a raking cornice.
    rise = PEDIMENT_APEX - 3.075
    run = 2.15 / 2.0
    band = 0.115  # thickness of the raking cornice, measured vertically

    pos, tangent, inward, up = oo.point_and_frame(bearing, face)
    origin = Vector((pos.x, pos.y, 3.075))

    # Tympanum: the plain triangular field. Research says no ornament in it.
    oo.add_prism(v, f, [(-run + 0.10, 0.0), (run - 0.10, 0.0), (0.0, rise - 0.13)],
                 origin, tangent, -inward, up, 0.085)

    # Raking cornice as a chevron band following both rakes.
    chevron = [
        (-run, 0.0),
        (0.0, rise),
        (run, 0.0),
        (run - 0.16, 0.0),
        (0.0, rise - band * 1.32),
        (-run + 0.16, 0.0),
    ]
    oo.add_prism(v, f, chevron, origin, tangent, -inward, up, 0.20)

    case = oo.new_mesh_object(f"{PREFIX}_Door{index}_Case", v, f, coll)

    # Leaves: a pair of panelled doors.
    lv, lf = [], []
    _, tangent, inward, up = oo.point_and_frame(bearing)
    for side in (-1, 1):
        centre = at(face - 0.055, DOOR_H / 2.0, side * DOOR_W / 4.0)
        oo.add_box(lv, lf, centre, tangent, inward, up, DOOR_W / 2.0 - 0.006, 0.045, DOOR_H)
    leaves = oo.new_mesh_object(f"{PREFIX}_Door{index}_Leaves", lv, lf, coll)
    return case, leaves


def build_jib_door(index, x, y, coll):
    """Flush door, no case, no pediment. Reads as a panel in the wall."""
    bearing = bearing_of_point(x, y)
    v, f = [], []
    pos, tangent, inward, up = oo.point_and_frame(bearing, 0.004)
    centre = Vector((pos.x, pos.y, DOOR_H / 2.0))
    oo.add_box(v, f, centre, tangent, inward, up, DOOR_W, 0.030, DOOR_H)
    obj = oo.new_mesh_object(f"{PREFIX}_Jib{index}", v, f, coll)
    return obj, bearing


def main():
    oo.purge(PREFIX)
    coll = oo.get_collection()

    cutters = []
    for i, bearing in enumerate(WIN_BEARINGS):
        cutters.append(make_cutter(f"{PREFIX}_CutWin{i}", bearing, WIN_W,
                                   WIN_HEAD - WIN_SILL, WIN_SILL, coll))

    for i, bearing in enumerate(PEDIMENTED):
        # Shallow flat recess so the flat case can meet the curved wall. Over a
        # 1.81 m chord the wall bows about 60 mm, which would otherwise gape at
        # the architrave edges.
        # Recess spans from CASE_RECESS outside the wall face to just inside it,
        # so it removes the front skin of the wall and leaves a flat back for
        # the case. Passing a negative depth_out put the whole box inside the
        # room, where it cut nothing at all.
        cutters.append(make_cutter(f"{PREFIX}_CutCase{i}", bearing, CASE_OUTER_W + 0.30,
                                   PEDIMENT_APEX + 0.10, 0.0, coll,
                                   depth_out=CASE_RECESS, depth_in=0.05))
        cutters.append(make_cutter(f"{PREFIX}_CutDoor{i}", bearing, DOOR_W, DOOR_H, 0.0, coll))

    jib_bearings = []
    for i, (x, y) in enumerate(JIB):
        b = bearing_of_point(x, y)
        jib_bearings.append(round(b, 2))
        cutters.append(make_cutter(f"{PREFIX}_CutJib{i}", b, DOOR_W, DOOR_H, 0.0, coll))

    status = cut_shell(cutters)
    for cutter in cutters:
        bpy.data.objects.remove(cutter, do_unlink=True)

    windows = [build_window(i, b, coll) for i, b in enumerate(WIN_BEARINGS)]
    doors = [build_pedimented_case(i, b, coll) for i, b in enumerate(PEDIMENTED)]
    jibs = [build_jib_door(i, x, y, coll) for i, (x, y) in enumerate(JIB)]

    trim = bpy.data.materials.get("OO_Mat_Wainscot")
    for group in windows + doors:
        for obj in group:
            if obj.name.endswith("_Glass"):
                continue
            obj.data.materials.clear()
            if trim is not None:
                obj.data.materials.append(trim)
    for obj, _ in jibs:
        obj.data.materials.clear()
        if trim is not None:
            obj.data.materials.append(trim)

    shell = bpy.data.objects["OO_Shell_Wall"]
    return {
        "cut": status,
        "wall_thickness": WALL_THICKNESS,
        "shell_faces": len(shell.data.polygons),
        "windows": len(windows),
        "pedimented_doors": len(doors),
        "jib_doors": len(jibs),
        "jib_bearings_deg": jib_bearings,
        "lights_per_window": WIN_COLS * WIN_ROWS * 2,
    }


result = main()
