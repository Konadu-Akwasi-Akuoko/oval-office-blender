"""Phase 3b - swap procedural materials for the Poly Haven PBR sets, and the
placeholder sky for a real HDRI.

Run AFTER 03_materials.py, which it overrides for the floor and plaster, and
after 06_lighting.py has built the world.

Requires assets/. Run `python3 scripts/fetch_polyhaven.py` first. If the files
are missing this reports it and leaves the procedural materials in place rather
than failing the whole build - a missing texture should not stop a render.
"""

import importlib
import math
import os
import sys

import bpy

_HERE = os.path.dirname(os.path.abspath(bpy.data.filepath)) if bpy.data.filepath else None
_SCRIPTS = os.path.join(_HERE, "scripts") if _HERE else None
if _SCRIPTS and _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import oo_common as oo  # noqa: E402

importlib.reload(oo)


ASSETS = os.path.join(_HERE or ".", "assets", "polyhaven")
RES = "2k"


def tex_path(slug, kind):
    return os.path.join(ASSETS, "textures", slug, f"{slug}_{kind}_{RES}.jpg")


def load_image(path):
    if not os.path.exists(path):
        return None
    existing = bpy.data.images.get(os.path.basename(path))
    if existing is not None:
        return existing
    img = bpy.data.images.load(path)
    # Relative so the .blend stays portable and, more importantly, so textures
    # are never packed into it. Packing is what turns 300 KB into 400 MB.
    img.filepath = bpy.path.relpath(path)
    return img


def pbr_material(name, slug, scale_m, rough_boost=0.0, coat=0.0):
    """Build a Principled material from a Poly Haven texture set.

    `scale_m` is how many metres one tile of the texture covers, so the UVs laid
    out in real metres by phase 1 map at true-world scale.
    """
    diffuse = load_image(tex_path(slug, "Diffuse"))
    if diffuse is None:
        return None

    mat = bpy.data.materials.get(name)
    if mat is not None:
        bpy.data.materials.remove(mat)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (600, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (300, 0)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    uv = nodes.new("ShaderNodeUVMap")
    uv.location = (-900, 0)
    uv.uv_map = "UVMap"
    mapping = nodes.new("ShaderNodeMapping")
    mapping.location = (-700, 0)
    mapping.inputs["Scale"].default_value = (1.0 / scale_m, 1.0 / scale_m, 1.0)
    links.new(uv.outputs["UV"], mapping.inputs["Vector"])

    col = nodes.new("ShaderNodeTexImage")
    col.location = (-450, 250)
    col.image = diffuse
    links.new(mapping.outputs["Vector"], col.inputs["Vector"])
    links.new(col.outputs["Color"], bsdf.inputs["Base Color"])

    rough_img = load_image(tex_path(slug, "Rough"))
    if rough_img is not None:
        rough_img.colorspace_settings.name = "Non-Color"
        r = nodes.new("ShaderNodeTexImage")
        r.location = (-450, 0)
        r.image = rough_img
        links.new(mapping.outputs["Vector"], r.inputs["Vector"])
        if rough_boost:
            adj = nodes.new("ShaderNodeMath")
            adj.operation = "ADD"
            adj.location = (-180, 0)
            adj.inputs[1].default_value = rough_boost
            links.new(r.outputs["Color"], adj.inputs[0])
            links.new(adj.outputs["Value"], bsdf.inputs["Roughness"])
        else:
            links.new(r.outputs["Color"], bsdf.inputs["Roughness"])

    nor_img = load_image(tex_path(slug, "nor_gl"))
    if nor_img is not None:
        nor_img.colorspace_settings.name = "Non-Color"
        n = nodes.new("ShaderNodeTexImage")
        n.location = (-450, -260)
        n.image = nor_img
        links.new(mapping.outputs["Vector"], n.inputs["Vector"])
        nmap = nodes.new("ShaderNodeNormalMap")
        nmap.location = (-180, -260)
        links.new(n.outputs["Color"], nmap.inputs["Color"])
        links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

    if coat and "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = coat
        bsdf.inputs["Coat Roughness"].default_value = 0.09

    return mat


def main():
    applied, missing = {}, []

    # 0.9 m covers one tile of the herringbone, which puts the individual blocks
    # at a believable size against a 1.10 m door.
    floor_mat = pbr_material("OO_Mat_Parquet_PBR", "herringbone_parquet", 0.90, coat=0.30)
    if floor_mat is not None:
        floor = bpy.data.objects["OO_Floor"]
        floor.data.materials.clear()
        floor.data.materials.append(floor_mat)
        applied["floor"] = floor_mat.name
    else:
        missing.append("herringbone_parquet")

    plaster = pbr_material("OO_Mat_Plaster_PBR", "beige_wall_001", 2.4, rough_boost=0.10)
    if plaster is not None:
        for name in ("OO_Shell_Cornice", "OO_Ceiling"):
            obj = bpy.data.objects.get(name)
            if obj is not None:
                obj.data.materials.clear()
                obj.data.materials.append(plaster)
        applied["plaster"] = plaster.name
    else:
        missing.append("beige_wall_001")

    # Built now, used by phase 4 when the sofas arrive.
    velvet = pbr_material("OO_Mat_Velvet", "velour_velvet", 1.1)
    if velvet is not None:
        applied["velvet"] = velvet.name
    wood = pbr_material("OO_Mat_DarkWood", "dark_wood", 1.6, coat=0.22)
    if wood is not None:
        applied["dark_wood"] = wood.name

    # The world is owned by 06_lighting.py, not here.
    return {"applied": applied, "missing": missing,
            "hint": "run python3 scripts/fetch_polyhaven.py" if missing else None}


result = main()
