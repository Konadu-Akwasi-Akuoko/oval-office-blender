"""Phase 5b - the 2010 Michael S. Smith / Scott Group rug.

A true oval, 23 ft x 30 ft, long axis north-south. Wheat field, cream border
carrying five quotations chosen by Obama, navy bands and stars, presidential
seal centred.

The border text is worth the effort. The camera tilts 7 degrees up from room
centre, so the near floor is out of frame and what is actually visible is the
OUTER ring of the rug - exactly where the quotations run.

Text is real geometry bent round an elliptical bezier with a Curve modifier.
Character counts set each quotation's arc, because letterspacing is uniform all
the way round: TR is 81 characters and takes 102 degrees, FDR is 44 and takes
59. Spacing them evenly would be visibly wrong.

All dimensions, colours and the border order from docs/research-findings.md.
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


PREFIX = "OO_Rug"

SEMI_X = 3.505  # 23 ft east-west
SEMI_Y = 4.572  # 30 ft north-south
THICK = 0.012
Z = 0.0

SEAL_D = 1.60

# Colours, white-balanced off photographs.
WHEAT = (0.712, 0.605, 0.435, 1.0)
CREAM = (0.878, 0.827, 0.729, 1.0)
NAVY = (0.043, 0.051, 0.086, 1.0)
GOLD = (0.549, 0.447, 0.212, 1.0)
LETTER = (0.400, 0.325, 0.247, 1.0)
SEAL_GROUND = (0.902, 0.855, 0.769, 1.0)

# Counter-clockwise from due south, in the order the 2010 press releases listed.
# Character counts drive the arc each one occupies.
QUOTES = [
    ("FDR", "THE ONLY THING WE HAVE TO FEAR IS FEAR ITSELF"),
    ("MLK", "THE ARC OF THE MORAL UNIVERSE IS LONG, BUT IT BENDS TOWARD JUSTICE"),
    ("LINCOLN", "GOVERNMENT OF THE PEOPLE, BY THE PEOPLE, FOR THE PEOPLE"),
    ("JFK", "ASK NOT WHAT YOUR COUNTRY CAN DO FOR YOU"),
    ("TR", "THE WELFARE OF EACH OF US IS DEPENDENT FUNDAMENTALLY UPON THE WELFARE OF ALL OF US"),
]

TEXT_INSET = 0.42  # from the rug edge in to the text path
TEXT_SIZE = 0.145


def ellipse_ring(verts, faces, a0, b0, a1, b1, z, segments=192):
    """Flat annular band between two concentric ellipses."""
    base = len(verts)
    for i in range(segments):
        t = 2.0 * math.pi * i / segments
        c, s = math.cos(t), math.sin(t)
        verts.append((a0 * c, b0 * s, z))
        verts.append((a1 * c, b1 * s, z))
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((base + 2 * i, base + 2 * i + 1,
                      base + 2 * j + 1, base + 2 * j))


def ellipse_disc(verts, faces, a, b, z, segments=192):
    base = len(verts)
    verts.append((0.0, 0.0, z))
    for i in range(segments):
        t = 2.0 * math.pi * i / segments
        verts.append((a * math.cos(t), b * math.sin(t), z))
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((base, base + 1 + i, base + 1 + j))


def flat_material(name, colour, roughness=0.86):
    existing = bpy.data.materials.get(name)
    if existing is not None:
        bpy.data.materials.remove(existing)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = colour
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def build_bands(coll):
    """Field, pinstripes and border, as stacked flat rings at rising heights.

    Rings rather than one textured plane, because at 4K the boundaries stay
    crisp and it costs nothing. Each band sits a fraction higher than the last
    so there is no z-fighting.
    """
    made = []
    layers = [
        ("Field", 0.0, 0.0, SEMI_X - 0.62, SEMI_Y - 0.62, WHEAT, 0.0),
        ("PinstripeInner", SEMI_X - 0.62, SEMI_Y - 0.62, SEMI_X - 0.585, SEMI_Y - 0.585, GOLD, 0.0006),
        ("Border", SEMI_X - 0.585, SEMI_Y - 0.585, SEMI_X - 0.145, SEMI_Y - 0.145, CREAM, 0.0012),
        ("PinstripeOuter", SEMI_X - 0.145, SEMI_Y - 0.145, SEMI_X - 0.110, SEMI_Y - 0.110, GOLD, 0.0018),
        ("Navy", SEMI_X - 0.110, SEMI_Y - 0.110, SEMI_X, SEMI_Y, NAVY, 0.0024),
    ]
    for name, a0, b0, a1, b1, colour, lift in layers:
        v, f = [], []
        if a0 == 0.0:
            ellipse_disc(v, f, a1, b1, Z + THICK + lift)
        else:
            ellipse_ring(v, f, a0, b0, a1, b1, Z + THICK + lift)
        obj = oo.new_mesh_object(f"{PREFIX}_{name}", v, f, coll)
        obj.data.materials.append(flat_material(f"{PREFIX}_Mat_{name}", colour))
        obj["oo_material"] = "keep"
        made.append(obj)

    # Pile edge, so the rug has thickness against the parquet.
    v, f = [], []
    segments = 192
    for i in range(segments):
        t = 2.0 * math.pi * i / segments
        c, s = math.cos(t), math.sin(t)
        v.append((SEMI_X * c, SEMI_Y * s, Z))
        v.append((SEMI_X * c, SEMI_Y * s, Z + THICK + 0.0024))
    for i in range(segments):
        j = (i + 1) % segments
        f.append((2 * i, 2 * i + 1, 2 * j + 1, 2 * j))
    edge = oo.new_mesh_object(f"{PREFIX}_Edge", v, f, coll)
    edge.data.materials.append(bpy.data.materials[f"{PREFIX}_Mat_Navy"])
    edge["oo_material"] = "keep"
    made.append(edge)
    return made


def build_seal(coll):
    """Simplified presidential seal: ivory ground, navy ring, ring of 50 stars.

    Not the full heraldic eagle. At 1.60 m across, seen from a camera 1.6 m up
    and 7 degrees off it, the eagle occupies very few pixels - the ring, the
    star circle and the tone are what actually read.
    """
    made = []
    r = SEAL_D / 2.0

    v, f = [], []
    ellipse_disc(v, f, r, r, Z + THICK + 0.003)
    ground = oo.new_mesh_object(f"{PREFIX}_SealGround", v, f, coll)
    ground.data.materials.append(flat_material(f"{PREFIX}_Mat_SealGround", SEAL_GROUND))
    ground["oo_material"] = "keep"
    made.append(ground)

    v, f = [], []
    ellipse_ring(v, f, r - 0.045, r - 0.045, r, r, Z + THICK + 0.0036)
    ellipse_ring(v, f, r - 0.30, r - 0.30, r - 0.275, r - 0.275, Z + THICK + 0.0036)
    ring = oo.new_mesh_object(f"{PREFIX}_SealRing", v, f, coll)
    ring.data.materials.append(bpy.data.materials[f"{PREFIX}_Mat_Navy"])
    ring["oo_material"] = "keep"
    made.append(ring)

    # 50 stars, as the medallion research established for the ceiling.
    v, f = [], []
    star_r = r - 0.17
    for i in range(50):
        a = 2.0 * math.pi * i / 50.0
        cx, cy = star_r * math.cos(a), star_r * math.sin(a)
        base = len(v)
        v.append((cx, cy, Z + THICK + 0.0042))
        for k in range(10):
            ang = math.pi / 2.0 + 2.0 * math.pi * k / 10.0
            rad = 0.030 if k % 2 == 0 else 0.013
            v.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang), Z + THICK + 0.0042))
        for k in range(10):
            f.append((base, base + 1 + k, base + 1 + (k + 1) % 10))
    stars = oo.new_mesh_object(f"{PREFIX}_SealStars", v, f, coll)
    stars.data.materials.append(bpy.data.materials[f"{PREFIX}_Mat_Navy"])
    stars["oo_material"] = "keep"
    made.append(stars)
    return made


def build_text(coll):
    """Quotations bent round an elliptical bezier with a Curve modifier."""
    a = SEMI_X - TEXT_INSET
    b = SEMI_Y - TEXT_INSET

    bpy.ops.curve.primitive_bezier_circle_add(radius=1.0, location=(0, 0, Z + THICK + 0.0016))
    curve = bpy.context.active_object
    curve.name = f"{PREFIX}_TextPath"
    curve.scale = (a, b, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    curve.data.resolution_u = 24
    for c in list(curve.users_collection):
        c.objects.unlink(curve)
    coll.objects.link(curve)

    # Approximate perimeter, to convert an arc share into a distance along the
    # curve. Ramanujan's formula is well within tolerance at this eccentricity.
    h = ((a - b) ** 2) / ((a + b) ** 2)
    perimeter = math.pi * (a + b) * (1.0 + (3.0 * h) / (10.0 + math.sqrt(4.0 - 3.0 * h)))

    total_chars = sum(len(q) for _, q in QUOTES)
    letter_mat = flat_material(f"{PREFIX}_Mat_Letter", LETTER)

    # Build them all first at a nominal size, measure the real rendered width,
    # then rescale everything by one factor so the five together fill the
    # perimeter exactly.
    #
    # Sizing by eye does not work: the text's width comes from the font's
    # advance widths, not from the character count, and at 0.145 the five ran
    # about 16 percent long. The quotations overlapped - "TOWARD JUSTICE" ran
    # straight into "GOVERNMENT OF THE PEOPLE". One shared factor keeps
    # letterspacing uniform all the way round, which the research says it is.
    built = []
    for name, quote in QUOTES:
        txt_data = bpy.data.curves.new(f"{PREFIX}_Q{name}", type="FONT")
        txt_data.body = quote
        txt_data.size = TEXT_SIZE
        txt_data.align_x = "CENTER"
        txt_data.align_y = "CENTER"
        txt_data.extrude = 0.0005
        txt_data.space_character = 1.06
        obj = bpy.data.objects.new(f"{PREFIX}_Q{name}", txt_data)
        coll.objects.link(obj)
        built.append((obj, name, quote))

    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    widths = {name: obj.evaluated_get(depsgraph).dimensions.x
              for obj, name, _ in built}
    measured = sum(widths.values())

    # Leave a little air at each join for the star.
    fit = (perimeter * 0.955) / measured if measured else 1.0

    made = []
    cursor = 0.0
    for obj, name, quote in built:
        obj.data.size = TEXT_SIZE * fit
        share = len(quote) / total_chars
        centre_frac = (cursor + len(quote) / 2.0) / total_chars
        cursor += len(quote)

        # The Curve modifier maps the object's local X onto distance along the
        # curve, so position is set by X rather than by rotating anything.
        obj.location = (perimeter * (centre_frac - 0.5), 0.0, Z + THICK + 0.0016)
        mod = obj.modifiers.new("Bend", "CURVE")
        mod.object = curve
        mod.deform_axis = "POS_X"

        obj.data.materials.append(letter_mat)
        obj["oo_material"] = "keep"
        made.append((obj, name, round(share * 360.0, 1)))

    # A navy star at each join between quotations.
    v, f = [], []
    cursor = 0.0
    for _, quote in QUOTES:
        cursor += len(quote)
        frac = cursor / total_chars
        t = 2.0 * math.pi * frac - math.pi / 2.0
        cx, cy = a * math.cos(t), b * math.sin(t)
        base = len(v)
        v.append((cx, cy, Z + THICK + 0.0020))
        for k in range(10):
            ang = math.pi / 2.0 + 2.0 * math.pi * k / 10.0
            rad = 0.055 if k % 2 == 0 else 0.024
            v.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang), Z + THICK + 0.0020))
        for k in range(10):
            f.append((base, base + 1 + k, base + 1 + (k + 1) % 10))
    stars = oo.new_mesh_object(f"{PREFIX}_JoinStars", v, f, coll)
    stars.data.materials.append(bpy.data.materials[f"{PREFIX}_Mat_Navy"])
    stars["oo_material"] = "keep"

    bpy.context.view_layer.update()
    return made, curve, round(fit, 4)


def main():
    oo.purge(PREFIX)
    coll = oo.get_collection()

    bands = build_bands(coll)
    seal = build_seal(coll)
    texts, curve, fit = build_text(coll)

    return {
        "size_m": f"{SEMI_X * 2} x {SEMI_Y * 2}",
        "bands": [o.name.split("_")[-1] for o in bands],
        "seal_diameter": SEAL_D,
        "quotations": [(n, f"{deg} deg") for _, n, deg in texts],
        "total_characters": sum(len(q) for _, q in QUOTES),
        "text_fit_factor": fit,
        "faces": sum(len(o.data.polygons) for o in bands + seal),
    }


result = main()
