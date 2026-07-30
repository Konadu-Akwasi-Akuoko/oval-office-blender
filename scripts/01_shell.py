"""Phase 1 - the room shell.

Builds the elliptical wall, its horizontal bands (baseboard, wainscot, chair
rail), the bracketed cornice, the cove, the flat central ceiling and the floor.

Openings are not cut here. Doors, windows, niches and the fireplace are booleaned
out in phase 2, which is why the wall is swept at a fairly high segment count -
low-poly booleans against a curved wall produce visible faceting along the cut.

Run with `exec(open(path).read())` inside Blender. Idempotent: re-running
replaces the shell rather than stacking a second one on top.
"""

import importlib
import math
import os
import sys

import bpy

# Blender's embedded interpreter does not have the project on its path, and it
# caches modules between runs, so both steps are needed for edits to take.
_HERE = os.path.dirname(os.path.abspath(bpy.data.filepath)) if bpy.data.filepath else None
_SCRIPTS = os.path.join(_HERE, "scripts") if _HERE else None
if _SCRIPTS and _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import oo_common as oo  # noqa: E402

importlib.reload(oo)


PREFIX = "OO_Shell"


def wall_profile():
    """The wall section, from floor to the inner edge of the flat ceiling.

    Returns a list of (inset, z) pairs. Inset is measured inward from the
    wallpaper plane, which is the ellipse itself.

    Vertical runs are given two points at the same height so the profile turns a
    hard corner there rather than being smoothed into a bevel.
    """
    p = [
        # Baseboard.
        (oo.BASEBOARD_P, 0.000),
        (oo.BASEBOARD_P, oo.BASEBOARD_H - 0.025),
        (oo.WAINSCOT_P, oo.BASEBOARD_H),
        # Wainscot panel field. Recessed panels are added as geometry in phase 2;
        # here it is a flat band.
        (oo.WAINSCOT_P, oo.DADO_H),
        # Chair rail.
        (oo.RAIL_P, oo.DADO_H + 0.012),
        (oo.RAIL_P, oo.RAIL_H - 0.018),
        (0.0, oo.RAIL_H),
        # Wallpaper field, the tall plain run.
        (0.0, oo.CORNICE_BOTTOM),
    ]

    # Bracketed cornice. Classical order from the bottom up: bed mould, then the
    # dentil course, then the modillion band, then the projecting corona.
    c = oo.CORNICE_BOTTOM
    p += [
        (0.055, c + 0.040),  # bed mould
        (0.075, c + 0.080),
        (0.150, c + 0.080),  # dentil course front face
        (0.150, c + 0.190),
        (0.230, c + 0.190),  # modillion band
        (0.230, c + 0.340),
        (oo.CORNICE_P, c + 0.340),  # corona, the deepest projection
        # The lip carries on up past the trough floor. This overhang is what
        # hides the concealed lamps from anyone standing in the room.
        (oo.CORNICE_P, oo.LIP_TOP_Z),
        (oo.LIP_INNER_P, oo.LIP_TOP_Z),
        # Inner face of the lip drops back down into the trough.
        (oo.LIP_INNER_P, oo.TROUGH_Z),
        # Trough floor, running back toward the wall.
        (oo.COVE_SPRING_P, oo.TROUGH_Z),
    ]

    # The cove, springing from the back of the trough. Parametrised so the
    # tangent is vertical at the spring and horizontal where it meets the flat
    # ceiling - that is what makes it read as a cove rather than a chamfer.
    rise = oo.CEIL_CENTRE - oo.COVE_SPRING
    for i in range(1, oo.COVE_STEPS + 1):
        s = (i / oo.COVE_STEPS) * (math.pi / 2)
        p.append(
            (
                oo.COVE_SPRING_P + oo.COVE_RUN * (1.0 - math.cos(s)),
                oo.COVE_SPRING + rise * math.sin(s),
            )
        )
    return p


def build_shell(profile, coll):
    ts = oo.t_positions()
    rows = len(profile)

    verts = []
    for t in ts:
        for inset, z in profile:
            pt = oo.ellipse_point(t, inset)
            verts.append((pt.x, pt.y, z))

    faces = []
    for i in range(len(ts)):
        j = (i + 1) % len(ts)
        for k in range(rows - 1):
            a = i * rows + k
            b = j * rows + k
            faces.append((a, a + 1, b + 1, b))

    obj = oo.new_mesh_object(PREFIX, verts, faces, coll)
    oo.orient_normals(obj, inward=True)
    oo.shade_smooth_by_angle(obj)
    return obj


def build_cap(name, z, inset, coll, face_down):
    """Flat elliptical n-gon for the ceiling or the floor."""
    verts = []
    for t in oo.t_positions():
        pt = oo.ellipse_point(t, inset)
        verts.append((pt.x, pt.y, z))

    n = len(verts)
    ring = list(range(n))
    obj = oo.new_mesh_object(name, verts, [tuple(ring)], coll)

    normal = obj.data.polygons[0].normal
    if (normal.z < 0) != face_down:
        obj.data.flip_normals()
    oo.shade_smooth_by_angle(obj, degrees=1.0)
    return obj


def main():
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"

    coll = oo.get_collection()

    removed = oo.purge(PREFIX)
    removed += oo.purge("OO_Floor")
    removed += oo.purge("OO_Ceiling")

    # Clear Blender's startup objects on the first run only. Named explicitly so
    # this can never eat something built later.
    for name in ("Cube", "Light"):
        obj = bpy.data.objects.get(name)
        if obj is not None:
            bpy.data.objects.remove(obj, do_unlink=True)

    profile = wall_profile()
    shell = build_shell(profile, coll)
    floor = build_cap("OO_Floor", 0.0, 0.0, coll, face_down=False)
    ceiling = build_cap("OO_Ceiling", oo.CEIL_CENTRE, oo.CEIL_INSET, coll, face_down=True)

    return {
        "purged": removed,
        "profile_points": len(profile),
        "shell_verts": len(shell.data.vertices),
        "shell_faces": len(shell.data.polygons),
        "floor_verts": len(floor.data.vertices),
        "ceiling_verts": len(ceiling.data.vertices),
        "ceiling_semi_x": round(oo.SEMI_X - oo.CEIL_INSET, 3),
        "ceiling_semi_y": round(oo.SEMI_Y - oo.CEIL_INSET, 3),
    }


result = main()
