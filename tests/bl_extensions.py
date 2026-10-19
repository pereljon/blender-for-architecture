"""Blender test: extensions (T13, T14) from the scripts contract. Skips when an extension is not installed."""
import glob
import os
import sys
import time

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # Blender -P does not add the script folder
import tcommon
from tcommon import check, finish

from extensions_names import EXTENSIONS, LAS_ARGS, OPS, SUN_FIELDS

NAME = "bl_extensions"
FT = 0.3048


def enable_all():
    """Enable each extension for this run; return the ids that could not be enabled."""
    import addon_utils
    forced = [x for x in os.environ.get("EXT_FORCE_MISSING", "").split(",") if x]
    missing = []
    for ext in EXTENSIONS:
        if ext in forced:
            missing.append(ext)
            continue
        try:
            ok = addon_utils.enable(f"bl_ext.blender_org.{ext}", default_set=True)
        except Exception as e:
            print(f"  enable {ext} raised {e!r}")
            ok = None
        if ok is None:
            missing.append(ext)
    return missing


# ---------------------------------------------------------------- T13a: names resolve
def t13a():
    for op in OPS:
        mod, name = op.split(".")
        try:
            getattr(getattr(bpy.ops, mod), name).get_rna_type()
        except Exception as e:
            check(False, f"T13a bpy.ops.{op} does not resolve: {e!r}")
    props = bpy.ops.import_scene.point_cloud_las.get_rna_type().properties.keys()
    for a in LAS_ARGS:
        check(a in props, f"T13a LAS importer has property {a}")
    try:
        import ifcopenshell  # noqa: F401
    except Exception as e:
        check(False, f"T13a import ifcopenshell: {e!r}")


# ---------------------------------------------------------------- T13b: two-wall IFC
# Source boxes in feet: (x0, x1, y0, y1, z0, z1)
EW_BOX = (0.0, 10.0, 0.0, 0.5, 0.0, 8.0)       # east-west wall
NS_BOX = (19.5, 20.0, 0.0, 10.0, 0.0, 8.0)     # north-south wall, east face at x = 20


def write_ifc(path):
    import numpy as np
    import ifcopenshell
    import ifcopenshell.api
    run = ifcopenshell.api.run
    f = run("project.create_file", version="IFC4")
    project = run("root.create_entity", f, ifc_class="IfcProject", name="ext test")
    run("unit.assign_unit", f)
    model = run("context.add_context", f, context_type="Model")
    body = run("context.add_context", f, context_type="Model", context_identifier="Body",
               target_view="MODEL_VIEW", parent=model)
    site = run("root.create_entity", f, ifc_class="IfcSite", name="site")
    building = run("root.create_entity", f, ifc_class="IfcBuilding", name="building")
    storey = run("root.create_entity", f, ifc_class="IfcBuildingStorey", name="level 1")
    run("aggregate.assign_object", f, products=[site], relating_object=project)
    run("aggregate.assign_object", f, products=[building], relating_object=site)
    run("aggregate.assign_object", f, products=[storey], relating_object=building)

    def wall(name, length_ft, thick_ft, height_ft, x_ft, y_ft, rotate):
        w = run("root.create_entity", f, ifc_class="IfcWall", name=name)
        rep = run("geometry.add_wall_representation", f, context=body,
                  length=length_ft * FT, height=height_ft * FT, thickness=thick_ft * FT)
        run("geometry.assign_representation", f, product=w, representation=rep)
        m = np.eye(4)
        if rotate:  # local +x -> world +y, local +y -> world -x
            m[:2, :2] = [[0, -1], [1, 0]]
        m[0, 3], m[1, 3] = x_ft * FT, y_ft * FT
        run("geometry.edit_object_placement", f, product=w, matrix=m, is_si=True)
        run("spatial.assign_container", f, products=[w], relating_structure=storey)
        return w

    walls = {
        "ew": wall("ew", 10.0, 0.5, 8.0, 0.0, 0.0, False),
        "ns": wall("ns", 10.0, 0.5, 8.0, 20.0, 0.0, True),
    }
    f.write(path)
    return walls


def world_box_ft(ifc_file, wall):
    import numpy as np
    import ifcopenshell.geom
    s = ifcopenshell.geom.settings()
    s.set("use-world-coords", True)
    shape = ifcopenshell.geom.create_shape(s, wall)
    v = np.array(shape.geometry.verts).reshape(-1, 3) / FT
    return v.min(axis=0), v.max(axis=0)


def t13b(ifc):
    import ifcopenshell
    write_ifc(ifc)
    check(os.path.isfile(ifc), "T13b IFC file written")
    f = ifcopenshell.open(ifc)
    for w in f.by_type("IfcWall"):
        src = EW_BOX if w.Name == "ew" else NS_BOX
        lo, hi = world_box_ft(f, w)
        got = (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2])
        worst = max(abs(g - s) for g, s in zip(got, src))
        check(worst <= 0.01, f"T13b wall {w.Name} world box {tuple(round(g, 4) for g in got)} vs source {src} (off {worst:.4f} ft)")


# ---------------------------------------------------------------- T13c: Bonsai plan drawing
def t13c(ifc, started):
    bpy.ops.bim.load_project(filepath=ifc)
    import bonsai.tool as tool
    f = tool.Ifc.get()
    dp = bpy.context.scene.DocProperties
    bpy.ops.bim.load_drawings()
    dp.target_view = "PLAN_VIEW"
    dp.location_hint = str(f.by_type("IfcBuildingStorey")[0].id())
    bpy.ops.bim.add_drawing()
    dwgs = [a for a in f.by_type("IfcAnnotation") if a.ObjectType == "DRAWING"]
    if not check(dwgs, "T13c add_drawing created a drawing annotation"):
        return
    bpy.ops.bim.activate_drawing(drawing=dwgs[0].id())
    bpy.ops.bim.create_drawing()
    bpy.ops.bim.save_project(filepath=ifc)
    svgs = [p for p in glob.glob(os.path.join(os.path.dirname(ifc), "**", "*.svg"), recursive=True)
            if os.path.getmtime(p) >= started]
    check(len(svgs) >= 1, "T13c an SVG newer than the run start exists beside the IFC")
    for p in svgs:
        print("  svg", os.path.relpath(p, tcommon.OUT))
        check(os.path.getsize(p) > 0, f"T13c {os.path.basename(p)} is not empty")


# ---------------------------------------------------------------- T14: Sun Position
def t14():
    props = bpy.context.scene.sun_pos_properties
    for n in SUN_FIELDS:
        check(hasattr(props, n), f"T14 sun_pos_properties has {n}")
    sun_data = bpy.data.lights.new("sun_t14", "SUN")
    sun = bpy.data.objects.new("sun_t14", sun_data)
    bpy.context.scene.collection.objects.link(sun)
    props.sun_object = sun
    props.latitude, props.longitude, props.UTC_zone = 37.77, -122.42, -8
    props.year, props.month, props.day = 2026, 6, 21
    rots = []
    for t in (9.0, 15.0):
        props.time = t
        bpy.context.view_layer.update()
        rots.append(tuple(sun.rotation_euler))
    diff = max(abs(a - b) for a, b in zip(*rots))
    print(f"  sun rotation 09:00 {rots[0]}, 15:00 {rots[1]}, max axis difference {diff:.3f} rad")
    check(diff > 0.1, f"T14 sun rotation differs between 09:00 and 15:00 by {diff:.3f} rad (need > 0.1)")


def main():
    missing = enable_all()
    if missing:
        print(f"SKIP extensions not installed: {', '.join(missing)}")
        finish(NAME)
        return
    started = time.time() - 1
    ifc = os.path.join(tcommon.OUT, "ext_two_walls.ifc")
    t13a()
    t13b(ifc)
    t13c(ifc, started)
    t14()
    finish(NAME)


main()
