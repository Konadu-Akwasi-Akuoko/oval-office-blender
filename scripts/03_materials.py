"""Phase 3 - materials.

All procedural for now. Poly Haven PBR sets replace the floor and any fabric
once phase 4 has pulled them down, but procedural gets the room readable
immediately and costs no memory, which matters on 16 GB.

The shell is one swept mesh, so materials are assigned per face by height:
wainscot below the chair rail, wallpaper above it, plaster from the cornice up.

Colours come from the 2010 scheme: Elizabeth Dow's studio hand-painted the
wallpaper in cafe-au-lait and buff stripes about three inches wide. Exact hex
values are being pinned down by research; these are read off the reference
photographs and are close.

Run with `exec(open(path).read())` inside Blender. Idempotent.
"""

import importlib
import os
import sys

import bpy

_HERE = os.path.dirname(os.path.abspath(bpy.data.filepath)) if bpy.data.filepath else None
_SCRIPTS = os.path.join(_HERE, "scripts") if _HERE else None
if _SCRIPTS and _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import oo_common as oo  # noqa: E402

importlib.reload(oo)


PREFIX = "OO_Mat"

STRIPE_M = 0.076  # three inches

# Read off the 2012 reference photographs. The paper is far LIGHTER and lower in
# contrast than the words "cafe-au-lait" suggest - it is two close creams that
# separate only where light rakes across them, not a bold two-tone stripe. The
# first attempt used properly coffee-coloured values and the room looked like a
# Victorian parlour.
CAFE_AU_LAIT = (0.640, 0.578, 0.455, 1.0)
BUFF = (0.780, 0.730, 0.615, 1.0)
TRIM_WHITE = (0.855, 0.838, 0.795, 1.0)
PLASTER = (0.860, 0.842, 0.800, 1.0)
OAK = (0.290, 0.169, 0.078, 1.0)
WALNUT = (0.110, 0.061, 0.033, 1.0)


def fresh_material(name):
    existing = bpy.data.materials.get(name)
    if existing is not None:
        bpy.data.materials.remove(existing)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    return mat


def principled(mat, location=(0, 0)):
    nodes = mat.node_tree.nodes
    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (location[0] + 300, location[1])
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = location
    mat.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return bsdf


def make_wallpaper():
    """Vertical stripes, alternating matte and satin.

    The stripes are driven off the U coordinate, which phase 1 lays out as true
    arc length in metres. A plain Wave texture on generated coordinates would
    band unevenly round an ellipse.
    """
    mat = fresh_material(f"{PREFIX}_Wallpaper")
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = principled(mat, (200, 0))

    uv = nodes.new("ShaderNodeUVMap")
    uv.location = (-800, 0)
    uv.uv_map = "UVMap"

    sep = nodes.new("ShaderNodeSeparateXYZ")
    sep.location = (-620, 0)
    links.new(uv.outputs["UV"], sep.inputs["Vector"])

    # Square wave: fract(u / stripe_width) < 0.5 picks the darker stripe.
    div = nodes.new("ShaderNodeMath")
    div.operation = "DIVIDE"
    div.location = (-450, 0)
    div.inputs[1].default_value = STRIPE_M
    links.new(sep.outputs["X"], div.inputs[0])

    frac = nodes.new("ShaderNodeMath")
    frac.operation = "FRACT"
    frac.location = (-300, 0)
    links.new(div.outputs["Value"], frac.inputs[0])

    step = nodes.new("ShaderNodeMath")
    step.operation = "LESS_THAN"
    step.location = (-150, 0)
    step.inputs[1].default_value = 0.5
    links.new(frac.outputs["Value"], step.inputs[0])

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (0, 150)
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].color = BUFF
    ramp.color_ramp.elements[1].position = 0.5
    ramp.color_ramp.elements[1].color = CAFE_AU_LAIT
    links.new(step.outputs["Value"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

    # Alternating sheen is the whole character of this paper: the darker stripe
    # is satin and catches the cove light, the lighter one is flat.
    rough = nodes.new("ShaderNodeMapRange")
    rough.location = (0, -150)
    rough.inputs["To Min"].default_value = 0.86
    rough.inputs["To Max"].default_value = 0.42
    links.new(step.outputs["Value"], rough.inputs["Value"])
    links.new(rough.outputs["Result"], bsdf.inputs["Roughness"])

    # Very faint canvas tooth so the wall is not perfectly flat under raking light.
    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-450, -420)
    noise.inputs["Scale"].default_value = 260.0
    noise.inputs["Detail"].default_value = 2.0

    bump = nodes.new("ShaderNodeBump")
    bump.location = (-150, -420)
    bump.inputs["Strength"].default_value = 0.035
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def make_paint(name, colour, roughness=0.42):
    mat = fresh_material(name)
    bsdf = principled(mat)
    bsdf.inputs["Base Color"].default_value = colour
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def make_parquet():
    """Quarter-sawn oak and walnut in a cross pattern, laid 2005.

    Built on world-space metres from the floor's planar UVs, so the block size
    is literal. Blocks alternate species on a checker, and each block gets its
    own grain direction and a slight tone shift so it does not read as tiling.
    """
    mat = fresh_material(f"{PREFIX}_Parquet")
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = principled(mat, (400, 0))

    uv = nodes.new("ShaderNodeUVMap")
    uv.location = (-1000, 0)
    uv.uv_map = "UVMap"

    block = nodes.new("ShaderNodeMapping")
    block.location = (-820, 0)
    block.inputs["Scale"].default_value = (1.0 / 0.30, 1.0 / 0.30, 1.0)  # 300 mm blocks
    links.new(uv.outputs["UV"], block.inputs["Vector"])

    checker = nodes.new("ShaderNodeTexChecker")
    checker.location = (-620, 200)
    checker.inputs["Color1"].default_value = OAK
    checker.inputs["Color2"].default_value = WALNUT
    checker.inputs["Scale"].default_value = 1.0
    links.new(block.outputs["Vector"], checker.inputs["Vector"])

    # Grain. Stretched hard along one axis so it reads as sawn timber rather
    # than marble, and modulated per block by the checker so alternate blocks
    # appear to run crossways.
    grain_map = nodes.new("ShaderNodeMapping")
    grain_map.location = (-620, -200)
    grain_map.inputs["Scale"].default_value = (2.0, 90.0, 1.0)
    links.new(uv.outputs["UV"], grain_map.inputs["Vector"])

    grain = nodes.new("ShaderNodeTexNoise")
    grain.location = (-430, -200)
    grain.inputs["Scale"].default_value = 9.0
    grain.inputs["Detail"].default_value = 6.0
    grain.inputs["Roughness"].default_value = 0.62
    links.new(grain_map.outputs["Vector"], grain.inputs["Vector"])

    mix = nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "OVERLAY"
    mix.location = (-180, 0)
    mix.inputs["Factor"].default_value = 0.30
    links.new(checker.outputs["Color"], mix.inputs[6])
    links.new(grain.outputs["Color"], mix.inputs[7])
    links.new(mix.outputs[2], bsdf.inputs["Base Color"])

    bsdf.inputs["Roughness"].default_value = 0.22
    bsdf.inputs["Specular IOR Level"].default_value = 0.55

    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = 0.35
        bsdf.inputs["Coat Roughness"].default_value = 0.10

    # Grooves between blocks.
    groove = nodes.new("ShaderNodeBump")
    groove.location = (100, -400)
    groove.inputs["Strength"].default_value = 0.12
    links.new(checker.outputs["Fac"], groove.inputs["Height"])
    links.new(groove.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def assign_shell_slots(shell, wallpaper, wainscot, plaster):
    """Split the swept shell into material zones by height.

    Boundaries are taken from the same constants the geometry was built from, so
    a slot can never land halfway up a moulding.
    """
    shell.data.materials.clear()
    for mat in (wainscot, wallpaper, plaster):
        shell.data.materials.append(mat)

    counts = {"wainscot": 0, "wallpaper": 0, "plaster": 0}
    for poly in shell.data.polygons:
        z = sum(shell.data.vertices[v].co.z for v in poly.vertices) / len(poly.vertices)
        if z < oo.RAIL_H:
            poly.material_index = 0
            counts["wainscot"] += 1
        elif z < oo.CORNICE_BOTTOM:
            poly.material_index = 1
            counts["wallpaper"] += 1
        else:
            poly.material_index = 2
            counts["plaster"] += 1
    return counts


def main():
    wallpaper = make_wallpaper()
    wainscot = make_paint(f"{PREFIX}_Wainscot", TRIM_WHITE, roughness=0.38)
    plaster = make_paint(f"{PREFIX}_Plaster", PLASTER, roughness=0.72)
    parquet = make_parquet()

    shell = bpy.data.objects["OO_Shell"]
    counts = assign_shell_slots(shell, wallpaper, wainscot, plaster)

    ceiling = bpy.data.objects["OO_Ceiling"]
    ceiling.data.materials.clear()
    ceiling.data.materials.append(plaster)

    floor = bpy.data.objects["OO_Floor"]
    floor.data.materials.clear()
    floor.data.materials.append(parquet)

    # The placeholder from the lighting test has no users left.
    tmp = bpy.data.materials.get("OO_TmpNeutral")
    if tmp is not None and tmp.users == 0:
        bpy.data.materials.remove(tmp)

    return {
        "materials": [wallpaper.name, wainscot.name, plaster.name, parquet.name],
        "shell_face_counts": counts,
        "stripe_width_m": STRIPE_M,
        "shell_has_uvs": bool(shell.data.uv_layers),
        "floor_has_uvs": bool(floor.data.uv_layers),
    }


result = main()
