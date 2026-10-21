"""Blender test: extensions (T13, T14, T21 to T24, T29) from the scripts contract. Skips when an extension is not installed."""
import math
import os
import sys
import time

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # Blender -P does not add the script folder
import tcommon
from tcommon import check, finish

from extensions_names import API_NAMES, EXTENSIONS, LAS_ARGS, OPS, SUN_FIELDS

NAME = "bl_extensions"
FT = 0.3048


def enable_all():
    """Enable each installed extension for this run; return the ids that are not installed.
    addon_utils.enable returns None for both a missing module and a failed import, so install is decided separately."""
    import addon_utils
    forced = [x for x in os.environ.get("EXT_FORCE_MISSING", "").split(",") if x]
    installed = {m.__name__ for m in addon_utils.modules()}
    missing = []
    for ext in EXTENSIONS:
        mod = f"bl_ext.blender_org.{ext}"
        if ext in forced or mod not in installed:
            missing.append(ext)
            continue
        try:
            ok = addon_utils.enable(mod, default_set=True)
        except Exception as e:
            print(f"  enable {ext} raised {e!r}")
            ok = None
        check(ok is not None, f"extension {ext} is installed and enables")
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
        import ifcopenshell.api
    except Exception as e:
        check(False, f"T13a import ifcopenshell: {e!r}")
        return
    # T24: every run("module.function") that scripts/ifc_walls.py calls exists in the installed IfcOpenShell
    if not check(API_NAMES, "T24 scripts/ifc_walls.py exists and calls ifcopenshell.api.run"):
        return
    import importlib
    for name in API_NAMES:
        mod, fn = name.split(".")
        try:
            m = importlib.import_module(f"ifcopenshell.api.{mod}")
        except Exception as e:
            check(False, f"T24 ifcopenshell.api.{mod} does not import: {e!r}")
            continue
        check(callable(getattr(m, fn, None)), f"T24 ifcopenshell.api.{name} exists")


# ---------------------------------------------------------------- T21: IFC from wall records
# Records in feet. Normalised boxes (x0, x1, y0, y1, z0, z1) in feet follow, in record order.
RECORDS = [
    dict(kind="existing", x0=0, x1=24, y0=0, y1=0.5),
    dict(kind="new", x0=23.5, x1=24, y0=0.5, y1=14),
    dict(kind="existing", x0=0.5, x1=0, y0=0.5, y1=14),            # reversed x
    dict(kind="new", x0=0, x1=24, y0=14, y1=14.5),
    (10, 10.5, 0.5, 6),                                           # bare tuple
    dict(kind="new", x0=12, x1=12.5, y0=6, y1=6.5, ifc_class="IfcColumn", z0=0, z1=8),
]
BOXES = [(0, 24, 0, 0.5, 0, 9), (23.5, 24, 0.5, 14, 0, 9), (0, 0.5, 0.5, 14, 0, 9), (0, 24, 14, 14.5, 0, 9),
         (10, 10.5, 0.5, 6, 0, 9), (12, 12.5, 6, 6.5, 0, 8)]
STATUS = ["EXISTING", "NEW", "EXISTING", "NEW", None, "NEW"]


def world_box_m(shape_settings, el):
    import numpy as np
    import ifcopenshell.geom
    v = np.array(ifcopenshell.geom.create_shape(shape_settings, el).geometry.verts).reshape(-1, 3)
    lo, hi = v.min(axis=0), v.max(axis=0)
    return (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2])


def t21(ifc):
    """Return the {name: GlobalId} dict, or None when the module or the call fails."""
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.element as ue
    try:
        from ifc_walls import write_walls_ifc
    except ImportError as e:
        check(False, f"T21 cannot import ifc_walls: {e!r}")
        return None
    try:
        ids = write_walls_ifc(RECORDS, ifc, 0.0, 9.0, unit=FT)
    except Exception as e:
        check(False, f"T21 write_walls_ifc raised {e!r}")
        return None
    check(os.path.isfile(ifc), "T21 IFC file written")
    names = [f"wall_{k}" for k in range(6)]
    check(list(ids) == names, f"T21 returned names {list(ids)} (need {names} in order)")
    f = ifcopenshell.open(ifc)
    import ifcopenshell.util.unit
    scale = ifcopenshell.util.unit.calculate_unit_scale(f)
    check(scale == 1.0, f"T21 the IFC length unit is the metre (unit scale {scale}; 0.001 means millimetres)")
    check(len(f.by_type("IfcWall")) == 5, f"T21 IFC has 5 IfcWall (found {len(f.by_type('IfcWall'))})")
    check(len(f.by_type("IfcColumn")) == 1, f"T21 IFC has 1 IfcColumn (found {len(f.by_type('IfcColumn'))})")
    s = ifcopenshell.geom.settings()
    s.set("use-world-coords", True)
    for k, name in enumerate(names):
        gid = ids.get(name)
        try:
            el = f.by_guid(gid)
        except Exception:
            check(False, f"T21 {name}: GlobalId {gid} is not in the file")
            continue
        check(el.Name == name, f"T21 {name}: the element with its GlobalId is named {el.Name}")
        check(el.is_a(("IfcColumn" if k == 5 else "IfcWall")), f"T21 {name} is {el.is_a()}")
        got = world_box_m(s, el)
        want = tuple(v * FT for v in BOXES[k])
        worst = max(abs(g - w) for g, w in zip(got, want))
        check(worst <= 1e-6, f"T21 {name} world box {tuple(round(g, 5) for g in got)} m vs {tuple(round(w, 5) for w in want)} m (off {worst:.2e})")
        cont = ue.get_container(el)
        check(cont is not None and cont.Name == "Level 1", f"T21 {name} is in storey 'Level 1' (got {cont.Name if cont else None})")
        psets = ue.get_psets(el)
        pset = "Pset_ColumnCommon" if k == 5 else "Pset_WallCommon"
        status = psets.get(pset, {}).get("Status")
        check(status == STATUS[k], f"T21 {name} {pset}.Status is {status} (need {STATUS[k]})")
        if STATUS[k] is None:
            check(not any("Status" in p for p in psets.values()), f"T21 {name} has no Status in any pset")
    try:
        write_walls_ifc(RECORDS, ifc + ".bad.ifc", 0.0, 9.0, unit=FT, tol=-1.0)
        check(False, "T21 tol=-1.0 raised no error")
    except ValueError:
        pass
    return ids


# ---------------------------------------------------------------- T13c: Bonsai plan drawing
def t13c(ifc, started):
    """Return the drawing SVG path, or None."""
    import bonsai.tool as tool
    bpy.ops.bim.load_project(filepath=ifc)
    f = tool.Ifc.get()
    dp = bpy.context.scene.DocProperties
    bpy.ops.bim.load_drawings()
    dp.target_view = "PLAN_VIEW"
    dp.location_hint = str(f.by_type("IfcBuildingStorey")[0].id())
    bpy.ops.bim.add_drawing()
    dwgs = [a for a in f.by_type("IfcAnnotation") if a.ObjectType == "DRAWING"]
    if not check(dwgs, "T13c add_drawing created a drawing annotation"):
        return None
    bpy.ops.bim.activate_drawing(drawing=dwgs[0].id())
    bpy.ops.bim.create_drawing()
    bpy.ops.bim.save_project(filepath=ifc)
    svg = os.path.join(os.path.dirname(ifc), "drawings", "LEVEL 1 PLAN.svg")
    if check(os.path.isfile(svg), "T13c drawings/LEVEL 1 PLAN.svg exists beside the IFC"):
        check(os.path.getmtime(svg) >= started, "T13c LEVEL 1 PLAN.svg is newer than the run start")
        check(os.path.getsize(svg) > 0, "T13c LEVEL 1 PLAN.svg is not empty")
        return svg
    return None


# ---------------------------------------------------------------- T22: drawing_walls and check_drawing
ROOM = [  # feet: south, north, west, east, partition
    dict(kind="existing", x0=0, x1=12, y0=0, y1=0.5),
    dict(kind="existing", x0=0, x1=12, y0=9.5, y1=10),
    dict(kind="existing", x0=0, x1=0.5, y0=0.5, y1=9.5),
    dict(kind="existing", x0=11.5, x1=12, y0=0.5, y1=9.5),
    dict(kind="existing", x0=6, x1=6.5, y0=0.5, y1=5),
]


def cut_groups(tree_root, gids):
    """Parents and cut groups whose class or ifc:guid holds one of the GlobalIds."""
    hits = []
    for parent in tree_root.iter():
        for child in list(parent):
            cls = child.attrib.get("class", "").split()
            guid = child.attrib.get("{http://www.ifcopenshell.org/ns}guid")
            if child.tag.endswith("}g") and "cut" in cls and (guid in gids or any(c in gids for c in cls)):
                hits.append((parent, child))
    return hits


def svg_without(svg, gids, out_path):
    """Copy of the drawing without the cut groups that hold the GlobalIds; return the number removed."""
    import xml.etree.ElementTree as ET
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    ET.register_namespace("ifc", "http://www.ifcopenshell.org/ns")
    tree = ET.parse(svg)
    hits = cut_groups(tree.getroot(), set(gids))
    for parent, child in hits:
        parent.remove(child)
    tree.write(out_path)
    return len(hits)


def t22(ifc, svg, ids, started):
    import shutil
    import ifcopenshell
    import ifcopenshell.api
    import ifcopenshell.util.placement
    import ifcopenshell.util.unit
    try:
        from ifc_walls import check_drawing as check_drawing_raw, drawing_walls as drawing_walls_raw, write_walls_ifc
    except ImportError as e:
        check(False, f"T22 cannot import drawing_walls and check_drawing: {e!r}")
        return

    def guarded(fn, name):
        def call(*args):
            try:
                return fn(*args)
            except Exception as e:
                check(False, f"T22 {name} raised {e!r}")
                return None
        return call

    check_drawing = guarded(check_drawing_raw, "check_drawing")
    drawing_walls = guarded(drawing_walls_raw, "drawing_walls")
    names = {gid: name for name, gid in ids.items()}

    got = check_drawing(svg, ifc)
    check(got == [], f"T22 check_drawing on the unchanged IFC returns [] (got {got})")

    # Grouping, pinned from Bonsai 0.9.0, which joins walls of one class, material, and status into one outline.
    res = drawing_walls(svg)
    if res is not None:
        cut_z, groups = res
        check(abs(cut_z - 1.6) <= 1e-6, f"T22 cut height is {cut_z} m (need 1.6)")
        have = sorted(sorted(names.get(i, i) for i in g[0]) for g in groups)
        want = [["wall_0", "wall_2"], ["wall_1", "wall_3"], ["wall_4"], ["wall_5"]]
        check(have == want, f"T22 Bonsai's outline groups are {have} (need {want}); read the new SVG before changing the check")

    # Closed room of one status, in its own folder so T21's drawing stays. Bonsai 0.9.0 joins the south, west, east, and
    # partition walls into one outline and leaves the north wall alone: the union that closes the ring would have a hole.
    room_dir = os.path.join(tcommon.OUT, "room")
    shutil.rmtree(room_dir, ignore_errors=True)
    os.makedirs(room_dir)
    room_ifc = os.path.join(room_dir, "room.ifc")
    try:
        room_ids = write_walls_ifc(ROOM, room_ifc, 0.0, 9.0, unit=FT)
    except Exception as e:
        check(False, f"T22 write_walls_ifc raised {e!r} for the closed room")
        return
    room_names = {gid: name for name, gid in room_ids.items()}
    room_svg = t13c(room_ifc, started)
    if room_svg:
        res = drawing_walls(room_svg)
        if res is not None:
            groups = res[1]
            have = sorted(sorted(room_names.get(i, i) for i in g[0]) for g in groups)
            want = [["wall_0", "wall_2", "wall_3", "wall_4"], ["wall_1"]]
            check(have == want, f"T22 the closed room's outline groups are {have} (need {want}); read the new SVG before changing the check")
            check(set().union(*(g[0] for g in groups)) == set(room_ids.values()), "T22 the room's groups hold all five GlobalIds")
            boxes = [g[1] for g in groups]
            hull = (min(b[0] for b in boxes), max(b[1] for b in boxes), min(b[2] for b in boxes), max(b[3] for b in boxes))
            want = (0.0, 12 * FT, 0.0, 10 * FT)
            worst = max(abs(a - b) for a, b in zip(hull, want))
            check(worst <= 1e-4, f"T22 the room's outlines span {tuple(round(v, 4) for v in hull)} m vs {tuple(round(v, 4) for v in want)} m (off {worst:.2e})")
        got = check_drawing(room_svg, room_ifc)
        check(got == [], f"T22 check_drawing on the closed room returns [] (got {got})")

        # The room's drawing without its cut groups: five missing items.
        gap = os.path.join(tcommon.OUT, "ext_room_gap.svg")
        n = svg_without(room_svg, room_ids.values(), gap)
        check(n == 2, f"T22 test setup removed {n} cut group(s) from the room drawing (need 2)")
        got = check_drawing(gap, room_ifc)
        want = [("missing", f"wall_{k}", None) for k in range(5)]
        check(got == want, f"T22 the room drawing without its outline returns five missing items (got {got})")

        # Stale: the room's drawing against T21's IFC.
        got = check_drawing(room_svg, ifc)
        if got is not None:
            kinds = sorted(k for k, _, _ in got)
            miss = sorted(n for k, n, _ in got if k == "missing")
            extra = sorted(n for k, n, _ in got if k == "extra")
            check(kinds == ["extra"] * 5 + ["missing"] * 6, f"T22 a stale drawing gives 5 extra and 6 missing items (got {kinds})")
            check(miss == [f"wall_{k}" for k in range(6)], f"T22 the stale drawing's missing items are wall_0 to wall_5 (got {miss})")
            check(extra == sorted(room_ids.values()), f"T22 the stale drawing's extra items are the room's GlobalIds (got {extra})")

    # Move wall_1 0.1 m east by its placement. Matrices below are in project units; edit_object_placement takes metres.
    def with_file(path, edit):
        shutil.copy(ifc, path)
        f = ifcopenshell.open(path)
        edit(f, ifcopenshell.util.unit.calculate_unit_scale(f))
        f.write(path)
        return path

    def move_wall_1(f, scale):
        w = next(e for e in f.by_type("IfcWall") if e.Name == "wall_1")
        m = ifcopenshell.util.placement.get_local_placement(w.ObjectPlacement)
        m[:3, 3] *= scale
        m[0][3] += 0.1
        ifcopenshell.api.run("geometry.edit_object_placement", f, product=w, matrix=m, is_si=True)

    moved = with_file(os.path.join(tcommon.OUT, "ext_moved.ifc"), move_wall_1)
    got = check_drawing(svg, moved)
    ok = (got is not None and len(got) == 1 and got[0][0] == "off" and got[0][1] == "wall_1+wall_3"
          and got[0][2] is not None and abs(got[0][2] - 0.1) <= 1e-3)
    check(ok, f"T22 a wall moved 0.1 m east returns [('off', 'wall_1+wall_3', ~0.1)] (got {got})")

    # T21's drawing without wall_4's cut group.
    gap = os.path.join(tcommon.OUT, "ext_gap.svg")
    n = svg_without(svg, [ids["wall_4"]], gap)
    check(n == 1, f"T22 test setup removed {n} cut group(s) for wall_4 (need 1)")
    got = check_drawing(gap, ifc)
    check(got == [("missing", "wall_4", None)], f"T22 a missing outline returns [('missing', 'wall_4', None)] (got {got})")

    # An element above the 1.6 m cut (z 2.0 to 2.6 m) is left out of the result.
    def add_high(f, scale):
        import numpy as np
        body = next(c for c in f.by_type("IfcGeometricRepresentationSubContext") if c.ContextIdentifier == "Body")
        el = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcWall", name="wall_high")
        rep = ifcopenshell.api.run("geometry.add_wall_representation", f, context=body, length=4 / scale, height=0.6 / scale, thickness=0.15 / scale)
        ifcopenshell.api.run("geometry.assign_representation", f, product=el, representation=rep)
        m = np.eye(4)
        m[0, 3], m[1, 3], m[2, 3] = 1.0, 20.0, 2.0
        ifcopenshell.api.run("geometry.edit_object_placement", f, product=el, matrix=m, is_si=True)
        ifcopenshell.api.run("spatial.assign_container", f, products=[el], relating_structure=f.by_type("IfcBuildingStorey")[0])

    high = with_file(os.path.join(tcommon.OUT, "ext_high.ifc"), add_high)
    got = check_drawing(svg, high)
    check(got == [], f"T22 an element above the cut is left out of the result (got {got})")


# ---------------------------------------------------------------- T14 and T23: Sun Position
def t14():
    import bhelpers as bh
    from mathutils import Vector
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

    # T23: bhelpers.sun with the extension's angles lights the scene as the extension's own sun object does.
    def light_dir(ob):
        return (ob.rotation_euler.to_matrix() @ Vector((0, 0, -1))).normalized()

    props.use_daylight_savings = False
    worst = 0.0
    for north in (0.0, 30.0, -75.0):
        props.north_offset = -math.radians(north)
        for t in (9.0, 12.0, 15.5):
            props.time = t
            mine = bh.sun(math.degrees(props.sun_elevation), math.degrees(props.sun_azimuth), plan_north_deg=north)
            ang = math.degrees(light_dir(sun).angle(light_dir(mine)))
            bpy.data.objects.remove(mine)
            worst = max(worst, ang)
            check(ang <= 0.01, f"T23 plan north {north}, time {t}: bh.sun light direction is {ang:.5f} degrees from Sun Position's (need <= 0.01)")
    print(f"  T23 worst light direction difference {worst:.5f} degrees over 9 cases")

    props.north_offset = 0.0
    best = None
    for minute in range(11 * 60, 13 * 60 + 31):
        props.time = minute / 60.0
        if best is None or props.sun_elevation > best[1]:
            best = (minute, props.sun_elevation, props.sun_azimuth)
    minute, elev, az = best
    print(f"  T23 solar noon {minute // 60}:{minute % 60:02d}, elevation {math.degrees(elev):.3f}, azimuth {math.degrees(az):.3f}")
    check(12 * 60 + 9 <= minute <= 12 * 60 + 15, f"T23 solar noon at {minute // 60}:{minute % 60:02d} (need 12:09 to 12:15)")
    check(abs(math.degrees(elev) - 75.67) <= 0.1, f"T23 noon elevation {math.degrees(elev):.3f} (need 75.67 +- 0.1)")
    check(abs(math.degrees(az) - 180) <= 1, f"T23 noon azimuth {math.degrees(az):.3f} (need 180 +- 1)")

    props.use_daylight_savings = True
    props.time = 15.5
    dst = (props.sun_elevation, props.sun_azimuth)
    props.use_daylight_savings = False
    props.time = 14.5
    std = (props.sun_elevation, props.sun_azimuth)
    check(max(abs(a - b) for a, b in zip(dst, std)) <= 1e-9,
          f"T23 daylight time 15:30 gives the angles of 14:30 standard time (elevation {dst[0]:.9f} vs {std[0]:.9f}, azimuth {dst[1]:.9f} vs {std[1]:.9f})")


# ---------------------------------------------------------------- T29: Point Cloud I/O
def fl(a):
    return tuple(round(float(v), 6) for v in a)


def t29():
    import random
    import numpy as np
    import laspy
    path = os.path.join(tcommon.OUT, "ext_room.las")
    rnd = random.Random(1)
    e0, n0, z0 = 551234.0, 4181234.0, 12.0      # UTM-like easting and northing, height in metres
    pts = []
    for i in range(4000):                        # four walls of a 4 by 3 m room, 2.5 m high, and the floor
        t, z, k = rnd.random(), rnd.random() * 2.5, i % 5
        if k == 0:
            x, y = 4 * t, 0.0
        elif k == 1:
            x, y = 4 * t, 3.0
        elif k == 2:
            x, y = 0.0, 3 * t
        elif k == 3:
            x, y = 4.0, 3 * t
        else:
            x, y, z = 4 * t, 3 * rnd.random(), 0.0
        pts.append((e0 + x, n0 + y, z0 + z))
    src = np.array(pts)
    hdr = laspy.LasHeader(point_format=3, version="1.2")
    hdr.offsets = [551000.0, 4181000.0, 0.0]     # a header offset that is not the points' minimum
    hdr.scales = [0.001] * 3
    las = laspy.LasData(hdr)
    las.x, las.y, las.z = src[:, 0], src[:, 1], src[:, 2]
    las.write(path)
    r = laspy.read(path)
    ref = np.column_stack([r.x, r.y, r.z]).astype(np.float64)   # the file's own 1 mm grid
    bbox_min = ref.min(axis=0)

    def run_import(center):
        before = set(bpy.data.objects)
        res = bpy.ops.import_scene.point_cloud_las(filepath=path, center_on_origin=center)
        new = [o for o in bpy.data.objects if o not in before]
        check(res == {"FINISHED"} and len(new) == 1, f"T29 center_on_origin={center}: import finished with one new object (got {res}, {len(new)})")
        if len(new) != 1:
            return None, None
        ob = new[0]
        n = len(ob.data.points)
        buf = np.zeros(n * 3, dtype=np.float32)
        ob.data.attributes["position"].data.foreach_get("vector", buf)
        return ob, buf.reshape(-1, 3).astype(np.float64)

    ob, p = run_import(True)
    if ob is not None:
        check(len(p) == 4000, f"T29 centred: {len(p)} points (need 4000)")
        check("las_origin_offset" in ob.keys(), "T29 centred: the object carries the custom property las_origin_offset")
        off = np.array(ob["las_origin_offset"]) if "las_origin_offset" in ob.keys() else np.zeros(3)
        check(np.abs(off - bbox_min).max() <= 1e-6, f"T29 centred: las_origin_offset {fl(off)} is the points' minimum {fl(bbox_min)}, not the header offset")
        check(tuple(ob.location) == (0.0, 0.0, 0.0), f"T29 centred: object location stays at the origin (got {tuple(ob.location)})")
        err = np.abs(p + off - ref).max()
        print(f"  T29 centred: {len(p)} points, offset {fl(off)} in las_origin_offset, local min {fl(p.min(axis=0))}, max {fl(p.max(axis=0))}, worst position error {err:.2e} m")
        check(np.abs(p.min(axis=0)).max() <= 1e-5, f"T29 centred: the bounding box minimum is at the origin ({fl(p.min(axis=0))})")
        check(err <= 1e-5, f"T29 centred: worst position error {err:.2e} m after adding the offset (need <= 1e-5)")

    ob, p = run_import(False)
    if ob is not None:
        check(len(p) == 4000, f"T29 uncentred: {len(p)} points (need 4000)")
        check("las_origin_offset" not in ob.keys(), "T29 uncentred: no las_origin_offset property")
        err = np.abs(p - ref).max()
        print(f"  T29 uncentred: {len(p)} points, local min {fl(p.min(axis=0))}, worst position error {err:.3f} m")
        check(err > 1e-3, f"T29 uncentred: positions at UTM coordinates lose millimetre precision (worst error {err:.4f} m, expected over 1 mm)")


def main():
    missing = enable_all()
    if missing:
        if os.environ.get("EXT_REQUIRED") == "1":
            check(False, f"extensions not installed (EXT_REQUIRED=1): {', '.join(missing)}")
        else:
            print(f"SKIP extensions not installed: {', '.join(missing)}")
        finish(NAME)
        return
    if tcommon.FAILURES:
        finish(NAME)
        return
    started = time.time() - 1
    ifc = os.path.join(tcommon.OUT, "ext_walls.ifc")
    t13a()
    ids = t21(ifc)
    if ids:
        svg = t13c(ifc, started)
        if svg:
            t22(ifc, svg, ids, started)
    t14()
    t29()
    finish(NAME)


main()
