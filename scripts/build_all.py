"""Run the whole build, in the one correct order.

    exec(open("/path/to/scripts/build_all.py").read())

PHASE ORDER IS LOAD-BEARING and has caused two silent bugs already, so it lives
here in one place rather than being retyped each time:

- 03_materials must run AFTER 02b/02c. It assigns wall faces by height, and the
  booleans renumber every face. It is also the only place that materials the
  fittings, because a material lookup inside 02b runs before the material
  exists and silently returns None - which left every window frame with no
  material at all.

- 06_lighting owns the WORLD. When the HDRI was set up in 03b, this phase
  rebuilt the world afterwards and silently threw it away.

- The light probe must be re-baked LAST, after every material and light is
  final. A stale bake is invisible until something looks subtly wrong.
"""

import os
import sys
import time

import bpy

_HERE = os.path.dirname(os.path.abspath(bpy.data.filepath))
_SCRIPTS = os.path.join(_HERE, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import oo_common as oo  # noqa: E402

PHASES = [
    "01_shell.py",       # elliptical wall, cornice profile, cove, floor, ceiling
    "02_joinery.py",     # modillions, rosettes, egg-and-dart
    "02b_openings.py",   # cut windows and doors, build sashes and cases
    "02c_niches.py",     # four arch-and-shell units
    "04_fireplace.py",   # Taft mantel and breast
    "05_desk.py",        # Resolute desk
    "03_materials.py",   # procedural materials, and ALL fitting assignment
    "03b_pbr.py",        # Poly Haven PBR overrides
    "06_lighting.py",    # cove lamps, sun, world/HDRI, probe volume
    "07_camera.py",      # 360 rig and render settings
]


def bake_probe():
    probe = bpy.data.objects.get("OO_Light_Irradiance")
    if probe is None:
        return False
    bpy.ops.object.select_all(action="DESELECT")
    probe.select_set(True)
    bpy.context.view_layer.objects.active = probe
    bpy.ops.object.lightprobe_cache_bake(subset="ACTIVE")
    return True


def main(phases=None):
    # Clear everything the build owns, so a re-run cannot stack duplicates or
    # leave a half-cut wall behind.
    for prefix in ("OO_Shell", "OO_Opening", "OO_Niche", "OO_Cornice",
                   "OO_Fire", "OO_Desk", "OO_Furn", "OO_Rug",
                   "OO_Light", "OO_Cam", "OO_Floor", "OO_Ceiling"):
        oo.purge(prefix)
    oo.purge_orphans()

    results, timings = {}, {}
    for name in (phases or PHASES):
        path = os.path.join(_SCRIPTS, name)
        if not os.path.exists(path):
            results[name] = "SKIPPED - not written yet"
            continue
        start = time.time()
        namespace = {"__file__": path, "__name__": "__main__"}
        exec(compile(open(path).read(), path, "exec"), namespace)
        results[name] = namespace.get("result")
        timings[name] = round(time.time() - start, 2)

    baked = bake_probe()

    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    bare = [o.name for o in meshes if not o.data.materials]
    if bare:
        # Checked here, at the very end, because phases hand materials to each
        # other by request and no single phase can assert this on its own.
        raise RuntimeError(f"Objects left with no material: {bare[:10]}")

    return {
        "phases": results,
        "seconds": timings,
        "probe_baked": baked,
        "mesh_objects": len(meshes),
        "total_faces": sum(len(o.data.polygons) for o in meshes),
        "no_material": [o.name for o in meshes if not o.data.materials],
    }


result = main()
