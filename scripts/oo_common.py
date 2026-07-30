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
# Photogrammetric solve puts the cornice at 0.47 m tall with its bottom at
# 4.58 m and the cove spring at 5.05 m. See docs/research-findings.md.
CORNICE_BOTTOM = 4.560

# How far each band projects inward from the plaster wall plane. The ellipse
# itself is the wallpaper plane, so these are all positive (toward the centre).
BASEBOARD_P = 0.030
WAINSCOT_P = 0.012
RAIL_P = 0.045
CORNICE_P = 0.300  # projection of the cornice lip, the room's deepest point

# The concealed light trough. The cornice lip rises ABOVE the trough floor and
# hides the lamps from anyone in the room; the cove springs from the back of the
# trough, near the wall plane. Without this gutter there is nowhere to put the
# cove lights and they end up buried inside wall geometry.
LIP_TOP_Z = 5.100  # top of the cornice lip, above the trough floor
LIP_INNER_P = 0.240  # inner face of the lip, where it drops into the trough
TROUGH_Z = COVE_SPRING  # trough floor height
COVE_SPRING_P = 0.030  # inset where the cove springs, just off the wall plane

# Where the flat central ceiling begins, as an inset from the ellipse.
CEIL_INSET = 1.050
COVE_RUN = CEIL_INSET - COVE_SPRING_P  # how far the cove travels inward

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
    """Convert a research bearing to this module's ellipse parameter `t`.

    docs/research-findings.md parametrises the room as
        x = SEMI_X * sin(b),  y = -SEMI_Y * cos(b)
    with `b` in degrees from due south, positive toward the EAST. This module
    uses the conventional
        x = SEMI_X * cos(t),  y = SEMI_Y * sin(t)

    The two agree when t = b - pi/2. Every bearing quoted in the research is in
    the first convention, so always come through here rather than converting by
    hand - the sign is easy to get backwards and the failure is a mirrored room,
    which is surprisingly hard to notice.
    """
    return math.radians(deg) - math.pi / 2.0


def point_and_frame(deg, inset=0.0):
    """Position and local axes at a research bearing. The workhorse for fittings."""
    t = bearing_to_t(deg)
    tangent, inward, up = local_frame(t)
    return ellipse_point(t, inset), tangent, inward, up


def t_positions(count=SEG):
    return [2.0 * math.pi * i / count for i in range(count)]


def perimeter(samples=4096, semi_x=SEMI_X, semi_y=SEMI_Y):
    total = 0.0
    prev = ellipse_point(0.0, semi_x=semi_x, semi_y=semi_y)
    for i in range(1, samples + 1):
        cur = ellipse_point(2.0 * math.pi * i / samples, semi_x=semi_x, semi_y=semi_y)
        total += (cur - prev).length
        prev = cur
    return total


def t_by_arclength(count, samples=4096):
    """`count` values of t spaced evenly by ARC LENGTH, not by parameter.

    Uniform `t` bunches up at the ends of the long axis, so dentils spaced that
    way would visibly crowd at the north and south ends of the room and spread
    out east and west. Anything repeated round the wall has to be spaced this
    way instead.
    """
    step = 2.0 * math.pi / samples
    cumulative = [0.0]
    prev = ellipse_point(0.0)
    for i in range(1, samples + 1):
        cur = ellipse_point(step * i)
        cumulative.append(cumulative[-1] + (cur - prev).length)
        prev = cur

    total = cumulative[-1]
    out = []
    j = 0
    for k in range(count):
        target = total * k / count
        while j < samples and cumulative[j + 1] < target:
            j += 1
        span = cumulative[j + 1] - cumulative[j]
        frac = 0.0 if span <= 0.0 else (target - cumulative[j]) / span
        out.append(step * (j + frac))
    return out


def local_frame(t):
    """Tangent, inward normal and up vectors on the ellipse at `t`."""
    tangent = Vector((-SEMI_X * math.sin(t), SEMI_Y * math.cos(t), 0.0))
    tangent.normalize()
    inward = Vector((-math.cos(t) / SEMI_X, -math.sin(t) / SEMI_Y, 0.0))
    inward.normalize()
    return tangent, inward, Vector((0.0, 0.0, 1.0))


def add_ellipsoid(verts, faces, centre, tangent, inward, up, width, height, depth,
                  rings=6, segments=10):
    """Append a flattened ellipsoid boss to running vert/face lists.

    Used for the oval paterae on the cornice. Deliberately low-poly: at roughly
    80 mm across and 5 m from a camera that never gets closer, extra subdivision
    buys nothing and there are 160-odd of them.
    """
    base = len(verts)
    for i in range(rings + 1):
        v = math.pi * i / rings
        for j in range(segments):
            u = 2.0 * math.pi * j / segments
            verts.append(
                tuple(
                    centre
                    + tangent * (width / 2.0 * math.sin(v) * math.cos(u))
                    + up * (height / 2.0 * math.sin(v) * math.sin(u))
                    + inward * (depth * (1.0 - math.cos(v)) / 2.0)
                )
            )
    for i in range(rings):
        for j in range(segments):
            a = base + i * segments + j
            b = base + i * segments + (j + 1) % segments
            c = base + (i + 1) * segments + (j + 1) % segments
            d = base + (i + 1) * segments + j
            faces.append((a, b, c, d))


def add_box(verts, faces, centre, tangent, inward, up, width, depth, height):
    """Append an axis-aligned-in-local-frame box to running vert/face lists.

    Used to array hundreds of dentils into a single mesh. Separate objects would
    be far more expensive for no benefit - they are never manipulated singly.
    """
    base = len(verts)
    hw, hh = width / 2.0, height / 2.0
    for sign_u in (-1, 1):
        for sign_d in (0, 1):
            for sign_v in (-1, 1):
                verts.append(
                    tuple(
                        centre
                        + tangent * (hw * sign_u)
                        + inward * (depth * sign_d)
                        + up * (hh * sign_v)
                    )
                )
    # Vertex order above is (u, d, v) with v innermost.
    b = base
    faces.extend(
        [
            (b + 0, b + 1, b + 3, b + 2),
            (b + 4, b + 6, b + 7, b + 5),
            (b + 0, b + 4, b + 5, b + 1),
            (b + 2, b + 3, b + 7, b + 6),
            (b + 1, b + 5, b + 7, b + 3),
            (b + 0, b + 2, b + 6, b + 4),
        ]
    )


# --- Scene plumbing ---------------------------------------------------------


def get_collection(name=COLLECTION):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


# Object data lives in a different collection per type, and orphaned data is not
# freed just because the object holding it was deleted.
_DATA_COLLECTIONS = (
    "meshes",
    "lights",
    "cameras",
    "curves",
    "metaballs",
    "armatures",
    "lattices",
    "volumes",
)


def purge(prefix):
    """Delete every object whose name starts with `prefix`, and free its data.

    This is what makes the build scripts idempotent. Re-running a phase must not
    leave two floors stacked on each other, and iterating on a look means
    re-running phases many times.

    Freeing the DATA matters as much as deleting the object. Blender keeps
    orphaned datablocks alive until the file is saved and reloaded, and a new
    datablock asking for a name that is still taken silently becomes
    `OO_Light_Cove_00.001`. Anything that later looks an object up by its
    expected name then fails. This bit once: 29 orphaned lights accumulated
    across a handful of re-runs before it surfaced.
    """
    removed = 0
    for obj in [o for o in bpy.data.objects if o.name.startswith(prefix)]:
        bpy.data.objects.remove(obj, do_unlink=True)
        removed += 1

    for attr in _DATA_COLLECTIONS:
        collection = getattr(bpy.data, attr, None)
        if collection is None:
            continue
        for block in [b for b in collection if b.users == 0 and b.name.startswith(prefix)]:
            collection.remove(block)

    return removed


def purge_orphans():
    """Free every unused datablock, whatever it is called.

    Belt and braces for data that drifted to a `.001` name before `purge` was
    fixed, and for anything an interrupted run left behind.
    """
    freed = 0
    for attr in _DATA_COLLECTIONS + ("materials", "node_groups"):
        collection = getattr(bpy.data, attr, None)
        if collection is None:
            continue
        for block in [b for b in collection if b.users == 0 and not b.use_fake_user]:
            collection.remove(block)
            freed += 1
    return freed


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
    # The operator acts on the SELECTION, not just the active object. Leaving a
    # stale selection meant it tried to add a Smooth by Angle modifier to
    # whatever was selected before - a light probe, in one case, which warned
    # harmlessly but also meant the intended mesh might not be smoothed at all.
    prev = bpy.context.view_layer.objects.active
    prev_selected = [o for o in bpy.context.selected_objects]
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    try:
        bpy.ops.object.shade_auto_smooth(angle=math.radians(degrees))
    except (AttributeError, RuntimeError):
        # Older builds expose this as a mesh property rather than an operator.
        if hasattr(obj.data, "use_auto_smooth"):
            obj.data.use_auto_smooth = True
            obj.data.auto_smooth_angle = math.radians(degrees)
    finally:
        bpy.ops.object.select_all(action="DESELECT")
        for o in prev_selected:
            try:
                o.select_set(True)
            except ReferenceError:
                pass
        bpy.context.view_layer.objects.active = prev
