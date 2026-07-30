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

WALL_ROWS = 10  # vertical subdivisions of the tall wallpaper run


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
    ]

    # Wallpaper field, the tall plain run. Subdivided rather than left as one
    # 3.68 m quad: phase 2 booleans doors and windows through this band, and
    # cutting into a single enormous face produces messy n-gons along the edge.
    for i in range(1, WALL_ROWS + 1):
        p.append((0.0, oo.RAIL_H + (oo.CORNICE_BOTTOM - oo.RAIL_H) * i / WALL_ROWS))

    # Corinthian modillion cornice. Member heights come from the photogrammetric
    # solve in docs/research-findings.md, which fits a fisheye camera model to an
    # upward-looking ceiling photograph. Total 0.49 m, bottom at 4.560, cove
    # spring at 5.050. Read bottom to top.
    #
    # This replaced an invented bed-mould-and-dentil stack. There is no dentil
    # course anywhere in this cornice - what looks like one in low-angle
    # photographs is the coffered modillion soffit seen edge-on.
    p += [
        (0.045, 4.600),  # cyma reversa dies into the wall
        (0.055, 4.625),  # fine guilloche / bead-and-reel band
    ]
    # Deep plain cavetto - this hollow is the "deep" in "deep bracketed cornice".
    # Swept as a curve rather than a straight chamfer; it is 0.150 m tall and the
    # concavity is what catches the cove wash.
    for i in range(1, 5):
        s = i / 4.0
        p.append((0.055 + 0.080 * (s * s), 4.625 + 0.150 * s))
    p += [
        (0.135, 4.775),  # egg-and-dart ovolo starts
        (0.185, 4.835),
        (0.185, 4.845),  # coffered modillion soffit, set back behind the corona
        (0.255, 4.945),
        (0.270, 4.960),  # bead / astragal
        (oo.CORNICE_P, 5.030),  # plain corona, the deepest projection
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
    add_shell_uvs(obj, profile, ts)
    return obj


def add_shell_uvs(obj, profile, ts):
    """UV the shell in metres: U is arc length round the room, V is up the wall.

    Arc length, not the ellipse parameter. Uniform `t` covers noticeably
    different distances at the ends of the long and short axes, so UVs built
    from it would stretch the wallpaper stripes wider on some walls than others.
    The stripes are 76 mm and the eye picks that up immediately.

    V accumulates real distance along the profile rather than using Z, so the
    mouldings and the cove get texture space proportional to their actual
    surface, instead of being crushed where the section runs horizontally.
    """
    u_at = [0.0]
    for i in range(1, len(ts) + 1):
        prev = oo.ellipse_point(ts[i - 1])
        cur = oo.ellipse_point(ts[i % len(ts)])
        u_at.append(u_at[-1] + (cur - prev).length)

    v_at = [0.0]
    for k in range(1, len(profile)):
        di = profile[k][0] - profile[k - 1][0]
        dz = profile[k][1] - profile[k - 1][1]
        v_at.append(v_at[-1] + math.hypot(di, dz))

    rows = len(profile)
    uv_layer = obj.data.uv_layers.new(name="UVMap")
    uvs = uv_layer.uv

    for poly in obj.data.polygons:
        for loop_index in poly.loop_indices:
            vert = obj.data.loops[loop_index].vertex_index
            column, row = divmod(vert, rows)
            uvs[loop_index].vector = (u_at[column], v_at[row])

    # Faces bridging the seam back to column 0 would otherwise run the U
    # coordinate backwards across the whole room. Push them past the end.
    total_u = u_at[-1]
    last_column = len(ts) - 1
    for poly in obj.data.polygons:
        cols = [obj.data.loops[li].vertex_index // rows for li in poly.loop_indices]
        if last_column in cols and 0 in cols:
            for loop_index in poly.loop_indices:
                if obj.data.loops[loop_index].vertex_index // rows == 0:
                    uv = uvs[loop_index].vector
                    uvs[loop_index].vector = (uv[0] + total_u, uv[1])


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

    # Planar UVs straight from world XY, in metres, so the parquet lays out at
    # real-world scale without any further fiddling.
    uv_layer = obj.data.uv_layers.new(name="UVMap")
    for poly in obj.data.polygons:
        for loop_index in poly.loop_indices:
            co = obj.data.vertices[obj.data.loops[loop_index].vertex_index].co
            uv_layer.uv[loop_index].vector = (co.x, co.y)
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
