"""Shared constants and helpers for the Oval Office build.

Every build script imports this. It is the single source of truth for the room's
dimensions and the axis convention, so that no two scripts can disagree about
where the walls are.

Axis convention
---------------
Room centre is the origin. -Y is south (the window wall, behind the desk), +Y is
north (the fireplace). The long axis runs north-south along Y; the short axis
runs east-west along X. Z is up, with the floor at Z=0.

Bearings elsewhere in the project are given in degrees clockwise from due south,
so 0 deg is the centre window and 180 deg is the fireplace. Use `bearing_to_t`
to convert one into the ellipse parameter used here.
"""

import math

import bmesh
import bpy
from mathutils import Vector

# --- Room shell, all metres -------------------------------------------------
# 35 ft 10 in x 29 ft, ceiling 18 ft 6 in, cove springs at 16 ft 7 in.
# Verified against Wikipedia and the White House Historical Association.

SEMI_X = 4.420  # east-west, half of 29 ft
SEMI_Y = 5.461  # north-south, half of 35 ft 10 in

CEIL_CENTRE = 5.639  # 18 ft 6 in
COVE_SPRING = 5.055  # 16 ft 7 in, where the cornice ends and the cove begins

# --- Wall section -----------------------------------------------------------
# Heights of the horizontal bands that run round the room.

BASEBOARD_H = 0.180
DADO_H = 0.880  # top of the wainscot panel field
RAIL_H = 0.940  # top of the chair rail; wallpaper starts here
CORNICE_BOTTOM = 4.620

# How far each band projects inward from the plaster wall plane. The ellipse
# itself is the wallpaper plane, so these are all positive (toward the centre).
BASEBOARD_P = 0.030
WAINSCOT_P = 0.012
RAIL_P = 0.045
CORNICE_P = 0.300  # total projection at the top of the cornice

COVE_RUN = 0.750  # how far the cove travels inward, on top of CORNICE_P

# Where the flat central ceiling begins, as an inset from the ellipse.
CEIL_INSET = CORNICE_P + COVE_RUN

SEG = 256  # segments around the ellipse
COVE_STEPS = 14  # subdivisions through the cove curve

COLLECTION = "Oval Office"


# --- Geometry helpers -------------------------------------------------------


def ellipse_point(t, inset=0.0, semi_x=SEMI_X, semi_y=SEMI_Y):
    """Point on the room ellipse at parameter `t`, pulled `inset` toward centre.

    The inset is measured along the true inward normal, not radially, so bands
    keep a constant apparent thickness all the way round. Radial insetting would
    make the cornice look thinner at the ends of the long axis.
    """
    cx, sy = math.cos(t), math.sin(t)
    x, y = semi_x * cx, semi_y * sy

    # Outward normal of an ellipse at t is (cos t / a, sin t / b), normalised.
    nx, ny = cx / semi_x, sy / semi_y
    n = math.hypot(nx, ny)
    if n == 0.0:
        return Vector((x, y, 0.0))
    return Vector((x - inset * nx / n, y - inset * ny / n, 0.0))


def bearing_to_t(deg):
    """Convert a bearing in degrees clockwise from due south to ellipse `t`.

    Due south is -Y, which is t = -pi/2. Bearings increase clockwise when viewed
    from above, which is decreasing t.
    """
    return -math.pi / 2 - math.radians(deg)


def t_positions(count=SEG):
    return [2.0 * math.pi * i / count for i in range(count)]


# --- Scene plumbing ---------------------------------------------------------


def get_collection(name=COLLECTION):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


def purge(prefix):
    """Delete every object whose name starts with `prefix`, and its data.

    This is what makes the build scripts idempotent. Re-running a phase must not
    leave two floors stacked on each other, and iterating on a look means
    re-running phases many times.
    """
    removed = 0
    for obj in [o for o in bpy.data.objects if o.name.startswith(prefix)]:
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        removed += 1
        if isinstance(data, bpy.types.Mesh) and data.users == 0:
            bpy.data.meshes.remove(data)
    for block in [m for m in bpy.data.meshes if m.name.startswith(prefix) and m.users == 0]:
        bpy.data.meshes.remove(block)
    return removed


def new_mesh_object(name, verts, faces, collection=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(v) for v in verts], [], faces)
    mesh.update()
    mesh.validate(verbose=False)

    obj = bpy.data.objects.new(name, mesh)
    (collection or get_collection()).objects.link(obj)
    return obj


def orient_normals(obj, inward=True):
    """Make face normals consistent, then point them the way we want.

    The shell is an open surface, so Blender cannot infer an inside from the
    topology. We decide by sampling: take a face near the wall and check whether
    its normal points toward the Z axis. Getting this wrong makes EEVEE light the
    room from behind the walls.
    """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    sample = max(bm.faces, key=lambda f: f.calc_center_median().xy.length)
    centre = sample.calc_center_median()
    to_axis = Vector((-centre.x, -centre.y, 0.0))
    facing_in = sample.normal.xy.dot(to_axis.xy) > 0.0

    if facing_in != inward:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)

    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def action_fcurves(obj):
    """Every F-curve on `obj`, across Blender's old and new Action APIs.

    Blender 4.4 introduced slotted actions and removed `Action.fcurves`. Curves
    now live at `action.layers[i].strips[j].channelbag(slot).fcurves`. Blender
    5.2 has no legacy fallback at all, so reaching for `action.fcurves` raises
    AttributeError rather than returning an empty list.
    """
    anim = obj.animation_data
    if anim is None or anim.action is None:
        return []

    action = anim.action

    if hasattr(action, "layers"):
        curves = []
        slots = list(action.slots) or [None]
        for layer in action.layers:
            for strip in layer.strips:
                for slot in slots:
                    bag = strip.channelbag(slot) if slot is not None else None
                    if bag is not None:
                        curves.extend(bag.fcurves)
        return curves

    return list(getattr(action, "fcurves", []))


def shade_smooth_by_angle(obj, degrees=31.0):
    """Smooth the sweep around the ellipse while keeping profile edges crisp."""
    for poly in obj.data.polygons:
        poly.use_smooth = True
    prev = bpy.context.view_layer.objects.active
    bpy.context.view_layer.objects.active = obj
    try:
        bpy.ops.object.shade_auto_smooth(angle=math.radians(degrees))
    except (AttributeError, RuntimeError):
        # Older builds expose this as a mesh property rather than an operator.
        if hasattr(obj.data, "use_auto_smooth"):
            obj.data.use_auto_smooth = True
            obj.data.auto_smooth_angle = math.radians(degrees)
    finally:
        bpy.context.view_layer.objects.active = prev
