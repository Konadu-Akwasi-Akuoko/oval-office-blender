"""Phase 5c - furniture, to the researched plan.

Positions and footprints come from the layout table in
docs/research-findings.md, which gives x, y, footprint and azimuth for every
piece. Azimuth is degrees clockwise from +Y, so rot_z = -azimuth.

Everything here is hand-modelled rather than sourced. The sourcing agents
inspected the previews and found no acceptable match for the pieces that matter:
the Obama sofas need to be large, rolled-arm, skirted to the floor AND olive
damask, and nothing in either library has all four. Every remaining candidate
needed a skirt built and a recolour, which is most of the work anyway.

These are simplified but correctly proportioned. At room centre with a 24 mm
lens nothing is closer than about 2 m, so silhouette and tone carry the read,
not upholstery detail.

WALL-HUGGING PIECES follow the ellipse tangent rather than sitting square - the
chest, side chairs and clock are all against a curved wall.
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


PREFIX = "OO_Furn"

X = Vector((1.0, 0.0, 0.0))
Y = Vector((0.0, 1.0, 0.0))
Z = Vector((0.0, 0.0, 1.0))

OLIVE = (0.246, 0.222, 0.140, 1.0)
WALNUT = (0.118, 0.066, 0.036, 1.0)
BRASS = (0.65, 0.50, 0.22, 1.0)
SHADE = (0.86, 0.80, 0.68, 1.0)


def mat(name, colour, roughness=0.62, metallic=0.0):
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


def emit(v, f, centre, w, d, h, ax=X, ay=Y):
    oo.add_box(v, f, centre, ax, ay, Z, w, d, h)


def finish(name, v, f, coll, material, location=(0, 0, 0), az=0.0, soften=0.0):
    obj = oo.new_mesh_object(f"{PREFIX}_{name}", v, f, coll)
    obj.location = location
    obj.rotation_euler = (0.0, 0.0, math.radians(-az))
    obj.data.materials.append(material)
    obj["oo_material"] = "keep"

    if soften:
        # Upholstery has no sharp arrises. Without this the sofas read as a
        # stack of plain boxes, which was by some distance the weakest thing in
        # the render. A bevel is far cheaper than modelling real curvature and
        # does most of the work, because what gives fabric away at this distance
        # is the highlight running along a rounded edge.
        bev = obj.modifiers.new("Soften", "BEVEL")
        bev.width = soften
        bev.segments = 3
        bev.limit_method = "ANGLE"
        bev.angle_limit = math.radians(40.0)
        bev.harden_normals = False
        oo.shade_smooth_by_angle(obj, degrees=42.0)
    return obj


def sofa(name, coll, location, az, fabric, wood):
    """Large plainly-tailored sofa: rolled arms, three cushions, skirt to floor."""
    w, d = 2.35, 0.95  # long axis along local X
    v, f = [], []
    emit(v, f, Vector((0, 0, 0.20)), w, d, 0.40)                     # skirt to floor
    emit(v, f, Vector((0, 0, 0.46)), w - 0.30, d - 0.10, 0.14)        # seat platform
    for i in (-1, 0, 1):
        emit(v, f, Vector((i * 0.68, -0.03, 0.578)), 0.63, d - 0.21, 0.17)  # cushions
    emit(v, f, Vector((0, d / 2.0 - 0.14, 0.62)), w, 0.24, 0.46)      # back
    for i in (-1, 0, 1):
        emit(v, f, Vector((i * 0.68, d / 2.0 - 0.24, 0.70)), 0.62, 0.16, 0.34)  # back cushions

    # Rolled arms, as a real half-cylinder rather than stepped boxes. The steps
    # were readable as steps.
    for side in (-1, 1):
        cx = side * (w / 2.0 - 0.13)
        segments, radius = 9, 0.135
        for k in range(segments):
            a0 = math.pi * k / segments
            a1 = math.pi * (k + 1) / segments
            zc = 0.635 + radius * (math.sin(a0) + math.sin(a1)) / 2.0
            xc = cx + radius * (math.cos(a0) + math.cos(a1)) / 2.0 * side * -1.0
            seg_w = abs(radius * (math.cos(a0) - math.cos(a1))) + 0.012
            seg_h = abs(radius * (math.sin(a0) - math.sin(a1))) + 0.030
            emit(v, f, Vector((xc, 0.0, zc)), seg_w, d - 0.04, seg_h)
        emit(v, f, Vector((cx, 0.0, 0.545)), 0.27, d - 0.04, 0.19)
    return finish(name, v, f, coll, fabric, location, az, soften=0.030)


def armchair(name, coll, location, az, fabric):
    w, d = 0.78, 0.88
    v, f = [], []
    emit(v, f, Vector((0, 0, 0.20)), w, d, 0.40)
    emit(v, f, Vector((0, -0.02, 0.47)), w - 0.16, d - 0.16, 0.12)
    emit(v, f, Vector((0, -0.02, 0.565)), w - 0.20, d - 0.22, 0.10)   # seat cushion
    emit(v, f, Vector((0, d / 2.0 - 0.11, 0.72)), w, 0.20, 0.62)
    emit(v, f, Vector((0, d / 2.0 - 0.21, 0.70)), w - 0.16, 0.14, 0.36)  # back cushion
    for side in (-1, 1):
        cx = side * (w / 2.0 - 0.09)
        for k in range(7):
            a0, a1 = math.pi * k / 7.0, math.pi * (k + 1) / 7.0
            zc = 0.635 + 0.105 * (math.sin(a0) + math.sin(a1)) / 2.0
            xc = cx + 0.105 * (math.cos(a0) + math.cos(a1)) / 2.0 * side * -1.0
            emit(v, f, Vector((xc, -0.02, zc)),
                 abs(0.105 * (math.cos(a0) - math.cos(a1))) + 0.012,
                 d - 0.14,
                 abs(0.105 * (math.sin(a0) - math.sin(a1))) + 0.028)
        emit(v, f, Vector((cx, -0.02, 0.545)), 0.21, d - 0.14, 0.17)
    return finish(name, v, f, coll, fabric, location, az, soften=0.026)


def coffee_table(coll, location, az, wood):
    w, d, h = 1.40, 0.90, 0.44
    v, f = [], []
    emit(v, f, Vector((0, 0, h - 0.025)), w, d, 0.05)
    emit(v, f, Vector((0, 0, h - 0.09)), w - 0.12, d - 0.12, 0.08)
    for sx in (-1, 1):
        for sy in (-1, 1):
            emit(v, f, Vector((sx * (w / 2.0 - 0.08), sy * (d / 2.0 - 0.08), (h - 0.13) / 2.0)),
                 0.07, 0.07, h - 0.13)
    return finish("CoffeeTable", v, f, coll, wood, location, az)


def side_table(name, coll, location, az, wood):
    w, d, h = 0.66, 0.88, 0.72
    v, f = [], []
    emit(v, f, Vector((0, 0, h - 0.02)), w, d, 0.04)
    for sx in (-1, 1):
        for sy in (-1, 1):
            emit(v, f, Vector((sx * (w / 2.0 - 0.06), sy * (d / 2.0 - 0.06), (h - 0.04) / 2.0)),
                 0.055, 0.055, h - 0.04)
    return finish(name, v, f, coll, wood, location, az)


def table_lamp(name, coll, location, brass_mat, shade_mat, coll_out):
    base_h = 0.46
    v, f = [], []
    emit(v, f, Vector((0, 0, 0.02)), 0.20, 0.20, 0.04)
    emit(v, f, Vector((0, 0, base_h / 2.0)), 0.10, 0.10, base_h)
    body = finish(name + "_Base", v, f, coll, brass_mat, location)

    # Tapered drum shade, as a ring of quads.
    v, f = [], []
    segments, r0, r1, h0, h1 = 18, 0.155, 0.205, base_h + 0.04, base_h + 0.34
    for i in range(segments):
        a = 2.0 * math.pi * i / segments
        v.append((r0 * math.cos(a), r0 * math.sin(a), h1))
        v.append((r1 * math.cos(a), r1 * math.sin(a), h0))
    for i in range(segments):
        j = (i + 1) % segments
        f.append((2 * i, 2 * i + 1, 2 * j + 1, 2 * j))
    shade = finish(name + "_Shade", v, f, coll, shade_mat, location)
    return body, shade


def flagpole(name, coll, location, wood, cloth):
    v, f = [], []
    emit(v, f, Vector((0, 0, 0.03)), 0.36, 0.36, 0.06)
    emit(v, f, Vector((0, 0, 1.55)), 0.045, 0.045, 3.00)
    pole = finish(name + "_Pole", v, f, coll, wood, location)

    # Cloth hanging from just below the finial, furled against the pole with a
    # slow vertical wave. Built as a grid so it has real width - the first pass
    # made a two-vertex-wide strip that rendered as a thin sliver.
    v, f = [], []
    cols, rows = 9, 7
    length, height = 0.78, 1.05
    top = 2.96
    for r in range(rows + 1):
        for c in range(cols + 1):
            u, w = c / cols, r / rows
            # Furl deepens away from the pole; the fold runs down the drop.
            furl = 0.085 * math.sin(u * math.pi * 1.9) * (0.35 + 0.65 * u)
            sag = 0.10 * u * u
            v.append((furl, u * length, top - w * height - sag))
    for r in range(rows):
        for c in range(cols):
            a = r * (cols + 1) + c
            f.append((a, a + 1, a + cols + 2, a + cols + 1))
    flag = finish(name + "_Cloth", v, f, coll, cloth, location)
    return pole, flag


def chest(name, coll, location, az, wood):
    w, d, h = 1.15, 0.56, 0.92
    v, f = [], []
    emit(v, f, Vector((0, 0, h - 0.02)), w + 0.05, d + 0.04, 0.04)
    emit(v, f, Vector((0, 0, (h - 0.04) / 2.0 + 0.10)), w, d, h - 0.14)
    for i in range(4):
        emit(v, f, Vector((0, -d / 2.0 - 0.008, 0.22 + i * 0.18)), w - 0.10, 0.016, 0.14)
    for sx in (-1, 1):
        emit(v, f, Vector((sx * (w / 2.0 - 0.05), 0, 0.05)), 0.08, d - 0.06, 0.10)
    return finish(name, v, f, coll, wood, location, az)


def side_chair(name, coll, location, az, wood, fabric_mat):
    v, f = [], []
    for sx in (-1, 1):
        for sy in (-1, 1):
            emit(v, f, Vector((sx * 0.20, sy * 0.19, 0.22)), 0.035, 0.035, 0.44)
    emit(v, f, Vector((0, 0, 0.465)), 0.46, 0.44, 0.05)
    emit(v, f, Vector((0, 0.20, 0.75)), 0.44, 0.035, 0.52)
    emit(v, f, Vector((0, 0.20, 0.98)), 0.44, 0.05, 0.07)
    return finish(name, v, f, coll, wood, location, az)


def desk_chair(coll, location, leather):
    v, f = [], []
    emit(v, f, Vector((0, 0, 0.035)), 0.62, 0.62, 0.07)
    emit(v, f, Vector((0, 0, 0.28)), 0.09, 0.09, 0.42)
    emit(v, f, Vector((0, 0, 0.50)), 0.60, 0.58, 0.10)
    emit(v, f, Vector((0, 0.26, 0.82)), 0.58, 0.12, 0.56)
    for sx in (-1, 1):
        emit(v, f, Vector((sx * 0.31, 0.02, 0.66)), 0.06, 0.44, 0.07)
    return finish("DeskChair", v, f, coll, leather, location, 0.0)


def wall_azimuth(x, y):
    """Azimuth that puts a piece's back flat against the curved wall."""
    bearing = oo.bearing_of_point(x, y)
    _, _, inward, _ = oo.point_and_frame(bearing)
    return math.degrees(math.atan2(inward.x, inward.y))


def main():
    oo.purge(PREFIX)
    coll = oo.get_collection()

    fabric = mat("Olive", OLIVE, roughness=0.86)
    wood = mat("Walnut", WALNUT, roughness=0.34)
    brass = mat("Brass", BRASS, roughness=0.30, metallic=0.85)
    shade = mat("Shade", SHADE, roughness=0.90)
    leather = mat("Leather", (0.045, 0.040, 0.038, 1.0), roughness=0.48)
    cloth = mat("Cloth", (0.30, 0.28, 0.32, 1.0), roughness=0.80)

    made = []
    made.append(sofa("SofaWest", coll, (-1.45, 2.25, 0.0), 90.0, fabric, wood))
    made.append(sofa("SofaEast", coll, (1.45, 2.25, 0.0), 270.0, fabric, wood))
    made.append(coffee_table(coll, (0.0, 2.25, 0.0), 0.0, wood))
    made.append(armchair("ArmchairWest", coll, (-0.80, 4.05, 0.0), 150.0, fabric))
    made.append(armchair("ArmchairEast", coll, (0.80, 4.05, 0.0), 210.0, fabric))
    made.append(side_table("SideTableWest", coll, (-1.75, 3.95, 0.0), 0.0, wood))
    made.append(side_table("SideTableEast", coll, (1.75, 3.95, 0.0), 0.0, wood))

    lamps = []
    for tag, x in (("West", -1.75), ("East", 1.75)):
        lamps.extend(table_lamp(f"Lamp{tag}", coll, (x, 3.95, 0.72), brass, shade, coll))
    made.extend(lamps)

    for tag, x in (("US", 1.60), ("Pres", -1.60)):
        made.extend(flagpole(f"Flag{tag}", coll, (x, -4.85, 0.0), wood, cloth))

    made.append(desk_chair(coll, (0.0, -4.85, 0.0), leather))

    # Wall-hugging pieces take the ellipse tangent, not a square azimuth.
    for tag, x, y in (("ChestSW", -2.98, -3.60), ("TableSE", 2.98, -3.60)):
        made.append(chest(tag, coll, (x, y, 0.0), wall_azimuth(x, y), wood))

    for i, (x, y) in enumerate(((-3.81, 1.90), (-3.30, 3.04), (3.81, 1.90), (3.30, 3.04))):
        made.append(side_chair(f"SideChair{i}", coll, (x, y, 0.0), wall_azimuth(x, y),
                               wood, fabric))
    for i, (x, y) in enumerate(((-1.05, -2.55), (1.05, -2.55))):
        made.append(side_chair(f"DeskChair{i}", coll, (x, y, 0.0), 180.0, wood, fabric))

    return {
        "pieces": len(made),
        "faces": sum(len(o.data.polygons) for o in made),
        "wall_hugging_azimuths": {
            "ChestSW": round(wall_azimuth(-2.98, -3.60), 1),
            "SideChair0": round(wall_azimuth(-3.81, 1.90), 1),
        },
    }


result = main()
