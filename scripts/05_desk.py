"""Phase 5 - the Resolute desk.

Hand-modelled, because it is a specific 1880 object made from HMS Resolute
timbers and nothing off the shelf substitutes for it.

The research is emphatic about one thing and it is right: the CANTED CORNERS are
the single most recognisable silhouette cue, and a plain rectangular box reads
as a replica rather than the real desk. So the plan is an octagon, carried
consistently through plinth, case and top.

Carved relief - the acanthus scrolls, husk drops and the eagle on the FDR panel -
is left to maps. It is shallow, and the camera sits at room centre and never
comes close.

Dimensions from docs/research-findings.md (20 findings).
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


PREFIX = "OO_Desk"

W, D = 1.829, 1.219  # east-west, north-south
CANT = 0.080  # corner cut
PLINTH_H = 0.085
CASE_TOP = 0.838  # underside of the top slab
TOP_H = 0.040
TOP_OVERHANG = 0.030
PLINTH_OVERHANG = 0.050

KNEE_W = 0.600
KNEE_H = 0.540

# Plan position from the layout research. The desk sits well forward of the
# south wall: the ellipse curves away, so at the desk ends the clearance is
# about 1.23 m rather than the 1.35 m on the centre line.
POS = Vector((0.0, -3.75, 0.0))

X = Vector((1.0, 0.0, 0.0))
Y = Vector((0.0, 1.0, 0.0))
Z = Vector((0.0, 0.0, 1.0))


def octagon(half_w, half_d, cant):
    """Rectangle with the four corners cut off, wound counter-clockwise."""
    return [
        (-half_w + cant, -half_d),
        (half_w - cant, -half_d),
        (half_w, -half_d + cant),
        (half_w, half_d - cant),
        (half_w - cant, half_d),
        (-half_w + cant, half_d),
        (-half_w, half_d - cant),
        (-half_w, -half_d + cant),
    ]


def clip_x(outline, lo, hi):
    """Keep the part of an outline between two X values, closing the cut edge.

    Used to split the octagonal case plan into two pedestals either side of the
    kneehole, so the outer corners keep their cants and the inner faces are
    square. Cheaper and more reliable than booleaning the recess.
    """
    pts = []
    n = len(outline)
    for i in range(n):
        x0, y0 = outline[i]
        x1, y1 = outline[(i + 1) % n]
        if lo <= x0 <= hi:
            pts.append((x0, y0))
        # Add the crossing point wherever the edge leaves the band.
        for bound in (lo, hi):
            if (x0 - bound) * (x1 - bound) < 0:
                t = (bound - x0) / (x1 - x0)
                pts.append((bound, y0 + t * (y1 - y0)))
    return pts


def prism(verts, faces, outline, z0, z1, offset=Vector((0, 0, 0))):
    oo.add_prism(verts, faces, outline, POS + offset + Z * z0, X, Z, Y, z1 - z0)


def build_desk(coll):
    v, f = [], []

    case = octagon(W / 2.0, D / 2.0, CANT)
    plinth = octagon(W / 2.0 + PLINTH_OVERHANG, D / 2.0 + PLINTH_OVERHANG,
                     CANT + PLINTH_OVERHANG * 0.5)
    top = octagon(W / 2.0 + TOP_OVERHANG, D / 2.0 + TOP_OVERHANG,
                  CANT + TOP_OVERHANG * 0.5)

    # Plinth runs continuously across the kneehole - it is not cut away.
    prism(v, f, plinth, 0.0, PLINTH_H)

    half_knee = KNEE_W / 2.0
    prism(v, f, clip_x(case, -W / 2.0, -half_knee), PLINTH_H, CASE_TOP)
    prism(v, f, clip_x(case, half_knee, W / 2.0), PLINTH_H, CASE_TOP)
    # Rail bridging the pedestals above the kneehole.
    prism(v, f, clip_x(case, -half_knee, half_knee), PLINTH_H + KNEE_H, CASE_TOP)

    prism(v, f, top, CASE_TOP, CASE_TOP + TOP_H)

    body = oo.new_mesh_object(f"{PREFIX}_Body", v, f, coll)

    # Raised cupboard panels and drawer divisions, as shallow extrusions. Real
    # geometry because they catch the window light across the desk face.
    pv, pf = [], []
    for side in (-1, 1):
        px = side * ((half_knee + W / 2.0) / 2.0)
        for face_y in (-1, 1):
            for row, (z, h) in enumerate(((0.62, 0.16), (0.34, 0.26))):
                oo.add_box(
                    pv, pf,
                    POS + X * px + Y * (face_y * (D / 2.0 + 0.006)) + Z * z,
                    X, Y * face_y, Z, 0.46, 0.012, h,
                )
    # Fluted pilasters on the canted corners - cheap, and they read in silhouette.
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx = sx * (W / 2.0 - CANT / 2.0)
            cy = sy * (D / 2.0 - CANT / 2.0)
            for i in range(3):
                oo.add_box(
                    pv, pf,
                    POS + X * (cx + sx * 0.004) + Y * cy + Z * 0.46
                    + X * ((i - 1) * 0.018) * sy,
                    X, Vector((sx, sy, 0)).normalized(), Z, 0.010, 0.010, 0.62,
                )
    panels = oo.new_mesh_object(f"{PREFIX}_Panels", pv, pf, coll)

    # The FDR kneehole panel: a separate plate on the NORTH face only, carrying
    # the presidential coat of arms as a map.
    kv, kf = [], []
    oo.add_box(kv, kf, POS + Y * (D / 2.0 - 0.04) + Z * (PLINTH_H + KNEE_H / 2.0),
               X, Y, Z, KNEE_W - 0.01, 0.022, 0.500)
    fdr = oo.new_mesh_object(f"{PREFIX}_FDRPanel", kv, kf, coll)

    return body, panels, fdr


def build_top_leather(coll):
    """Inset leather writing surface on the desk top."""
    v, f = [], []
    oo.add_box(v, f, POS + Z * (CASE_TOP + TOP_H - 0.002), X, Y, Z,
               W - 0.20, D - 0.20, 0.006)
    return oo.new_mesh_object(f"{PREFIX}_Leather", v, f, coll)


def leather_material():
    name = f"{PREFIX}_Leather"
    existing = bpy.data.materials.get(name)
    if existing is not None:
        bpy.data.materials.remove(existing)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.128, 0.075, 0.048, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.58
    return mat


def main():
    oo.purge(PREFIX)
    coll = oo.get_collection()

    body, panels, fdr = build_desk(coll)
    leather = build_top_leather(coll)

    # Ask for the Poly Haven dark wood by name. It is built in 03b_pbr.py, which
    # runs after this phase, so looking it up here would return None.
    for obj in (body, panels, fdr):
        obj["oo_material"] = "darkwood"

    leather.data.materials.clear()
    leather.data.materials.append(leather_material())
    leather["oo_material"] = "keep"

    # Clearance check against the curved south wall, since the research warns
    # the ellipse falls away at the desk ends.
    clearances = {}
    for label, x in (("centre", 0.0), ("end", 0.914)):
        t = math.asin(min(1.0, x / oo.SEMI_X))
        wall_y = -oo.SEMI_Y * math.cos(t)
        clearances[label] = round(abs(wall_y - (POS.y - D / 2.0)), 3)

    return {
        "position": tuple(round(c, 3) for c in POS),
        "size": f"{W} x {D} x {round(CASE_TOP + TOP_H, 3)}",
        "canted_corners": CANT,
        "kneehole": f"{KNEE_W} x {KNEE_H}",
        "faces": sum(len(o.data.polygons) for o in (body, panels, fdr, leather)),
        "south_wall_clearance_m": clearances,
    }


result = main()
