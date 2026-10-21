"""IFC walls from wall records, and a check of Bonsai's plan drawing against them.

write_walls_ifc turns the wall records (load_plan, fix_walls, extra_walls, cut_openings) into an IFC4 file in metres.
drawing_walls reads the cut outlines of a Bonsai plan drawing (SVG) and runs in plain Python. check_drawing compares
those outlines with the IFC. ifcopenshell and numpy are imported inside the functions that need them: run in Blender in a
run that enables Bonsai, or in plain Python with:
  uvx --with ifcopenshell --with numpy python -I script.py

A wall record is a dict with x0, x1, y0, y1 and optional kind ("new" or "existing"), z0, z1 and ifc_class
(default "IfcWall"), or a tuple (x0, x1, y0, y1). Lengths are in record units; unit is metres per record unit.
"""
import json
import re
import xml.etree.ElementTree as ET

_IFC_NS = "{http://www.ifcopenshell.org/ns}"
_SVG_NS = "{http://www.w3.org/2000/svg}"
_GLOBAL_ID = re.compile(r"[0-3][0-9A-Za-z_$]{21}")
_PATH_TOKEN = re.compile(r"([A-Za-z])|([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)|[\s,]+|(.)")


def _record(w, z0, z1):
    """(x0, x1, y0, y1, z0, z1, kind, ifc_class) of a record, lows first."""
    if isinstance(w, dict):
        x0, x1, y0, y1 = w["x0"], w["x1"], w["y0"], w["y1"]
        z0, z1 = w.get("z0", z0), w.get("z1", z1)
        kind, cls = w.get("kind"), w.get("ifc_class", "IfcWall")
    else:
        x0, x1, y0, y1 = w[:4]
        kind, cls = None, "IfcWall"
    return min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), min(z0, z1), max(z0, z1), kind, cls


def _world_box(settings, element):
    """(x0, x1, y0, y1, z0, z1) of an element's geometry in world metres."""
    import numpy as np
    import ifcopenshell.geom
    v = np.array(ifcopenshell.geom.create_shape(settings, element).geometry.verts).reshape(-1, 3)
    lo, hi = v.min(axis=0), v.max(axis=0)
    return (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2])


def write_walls_ifc(walls, path, z0, z1, unit=1.0, prefix="wall_", storey="Level 1", tol=0.003):
    """Write the wall records to an IFC4 file in metres and return {name: GlobalId} in record order.

    Record k becomes one element of its ifc_class named f"{prefix}{k}", the name walls_from_plan gives the box.
    A record's own z0 and z1 override the arguments. A record with kind "new" or "existing" gets Status NEW or
    EXISTING in Pset_<class>Common. The file is read back, and ValueError names up to five elements whose world box
    differs from the record by more than tol metres. ValueError, before any file is written, names a record with an
    extent of 0 or less. Pass bh.U as unit from a scene script.
    """
    import numpy as np
    import ifcopenshell
    import ifcopenshell.api
    import ifcopenshell.geom
    run = ifcopenshell.api.run
    for k, w in enumerate(walls):
        x0, x1, y0, y1, a, b = (v * unit for v in _record(w, z0, z1)[:6])
        if x1 - x0 <= 0 or y1 - y0 <= 0 or b - a <= 0:
            raise ValueError(f"record {k} ({prefix}{k}) has an extent of 0 or less")
    f = run("project.create_file", version="IFC4")
    project = run("root.create_entity", f, ifc_class="IfcProject", name="walls")
    run("unit.assign_unit", f, units=[run("unit.add_si_unit", f, unit_type="LENGTHUNIT")])
    model = run("context.add_context", f, context_type="Model")
    body = run("context.add_context", f, context_type="Model", context_identifier="Body",
               target_view="MODEL_VIEW", parent=model)
    site = run("root.create_entity", f, ifc_class="IfcSite", name="Site")
    building = run("root.create_entity", f, ifc_class="IfcBuilding", name="Building")
    level = run("root.create_entity", f, ifc_class="IfcBuildingStorey", name=storey)
    run("aggregate.assign_object", f, products=[site], relating_object=project)
    run("aggregate.assign_object", f, products=[building], relating_object=site)
    run("aggregate.assign_object", f, products=[level], relating_object=building)
    placed = {}
    for k, w in enumerate(walls):
        *box, kind, cls = _record(w, z0, z1)
        x0, x1, y0, y1, a, b = (v * unit for v in box)
        along_x = x1 - x0 >= y1 - y0
        length, thickness = (x1 - x0, y1 - y0) if along_x else (y1 - y0, x1 - x0)
        name = f"{prefix}{k}"
        el = run("root.create_entity", f, ifc_class=cls, name=name)
        rep = run("geometry.add_wall_representation", f, context=body, length=length, height=b - a, thickness=thickness)
        run("geometry.assign_representation", f, product=el, representation=rep)
        m = np.eye(4)
        if along_x:
            m[0, 3], m[1, 3] = x0, y0
        else:
            m[:2, :2] = [[0, -1], [1, 0]]
            m[0, 3], m[1, 3] = x1, y0
        m[2, 3] = a
        run("geometry.edit_object_placement", f, product=el, matrix=m, is_si=True)
        run("spatial.assign_container", f, products=[el], relating_structure=level)
        if isinstance(kind, str) and kind.lower() in ("new", "existing"):
            pset = run("pset.add_pset", f, product=el, name=f"Pset_{cls[3:]}Common")
            run("pset.edit_pset", f, pset=pset, properties={"Status": kind.upper()})
        placed[name] = (el.GlobalId, (x0, x1, y0, y1, a, b))
    f.write(path)
    g = ifcopenshell.open(path)
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    off = []
    for name, (gid, box) in placed.items():
        d = max(abs(p - q) for p, q in zip(_world_box(settings, g.by_guid(gid)), box))
        if d > tol:
            off.append(f"{name} ({d:.4f} m)")
    if off:
        raise ValueError("IFC walls differ from the records: " + ", ".join(off[:5]))
    return {name: gid for name, (gid, _) in placed.items()}


def _path_points(d):
    """The (x, y) points of an SVG path of absolute M, L and Z commands; ValueError on anything else."""
    nums = []
    for letter, number, other in _PATH_TOKEN.findall(d):
        if letter and letter not in "MLZ":
            raise ValueError(f"unsupported path command {letter!r} in {d[:60]!r}")
        if other:
            raise ValueError(f"unsupported character {other!r} in {d[:60]!r}")
        if number:
            nums.append(float(number))
    if len(nums) % 2:
        raise ValueError(f"odd number of coordinates in {d[:60]!r}")
    return list(zip(nums[0::2], nums[1::2]))


def drawing_walls(svg):
    """Read the cut outlines of a Bonsai plan drawing; return (cut_z, groups).

    cut_z is the cut height in metres. groups is a list of (ids, (x0, x1, y0, y1)) sorted by ids: ids is the sorted
    tuple of the GlobalIds of one cut outline, and the box bounds every point of it in metres. Bonsai puts the
    GlobalIds of joined walls in the group's class, and the ifc:guid attribute holds those of elements it does not
    join (a column). A cut group with no GlobalId or no point is left out.
    ValueError: not exactly one drawing group, a rotated drawing camera, or a path command other than absolute M, L, Z.
    """
    root = ET.parse(svg).getroot()
    drawings = [g for g in root.iter(_SVG_NS + "g") if _IFC_NS + "matrix3" in g.attrib]
    if len(drawings) != 1:
        raise ValueError(f"expected one drawing group with ifc:matrix3, found {len(drawings)}")
    drawing = drawings[0]
    m = json.loads(drawing.attrib[_IFC_NS + "matrix3"])
    if m[0][1] != 0 or m[1][0] != 0:
        raise ValueError("the drawing camera is rotated (ifc:matrix3 has off-diagonal terms)")
    sx, tx, sy, ty = m[0][0], m[0][2], m[1][1], m[1][2]
    cut_z = float(json.loads(drawing.attrib[_IFC_NS + "plane"])[2][3])
    groups = []
    for g in drawing.iter(_SVG_NS + "g"):
        words = g.attrib.get("class", "").split()
        if "cut" not in words:
            continue
        ids = {w for w in words if _GLOBAL_ID.fullmatch(w)}
        if _IFC_NS + "guid" in g.attrib:
            ids.add(g.attrib[_IFC_NS + "guid"])
        points = [p for path in g.iter(_SVG_NS + "path") for p in _path_points(path.attrib["d"])]
        if not ids or not points:
            continue
        xs = [(x - tx) / sx for x, _ in points]
        ys = [(ty - y) / sy for _, y in points]
        groups.append((tuple(sorted(ids)), (min(xs), max(xs), min(ys), max(ys))))
    return cut_z, sorted(groups)


def check_drawing(svg, ifc_path, tol=0.003):
    """Compare the cut outlines of a Bonsai plan drawing with the IFC; return a sorted list, [] when they match.

    The elements to find are the IfcElements with a body that the cut height passes through. Items:
      ("missing", name, None)  such an element whose GlobalId is in no cut outline
      ("extra", GlobalId, None)  a GlobalId in a cut outline that is not such an element (a stale drawing)
      ("off", names, d)  an outline whose box differs by d metres (more than tol) from the box of its elements;
                         names joins the element names with "+"
    A piece moved inside the box of its joined outline is not caught.
    """
    import ifcopenshell
    import ifcopenshell.geom
    cut_z, groups = drawing_walls(svg)
    f = ifcopenshell.open(ifc_path)
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    cut = {}
    for el in f.by_type("IfcElement"):
        if el.Representation is None:
            continue
        x0, x1, y0, y1, z0, z1 = _world_box(settings, el)
        if z0 < cut_z < z1:
            cut[el.GlobalId] = (el.Name or el.GlobalId, (x0, x1, y0, y1))
    items = []
    drawn = set()
    for ids, box in groups:
        drawn.update(ids)
        items += [("extra", i, None) for i in ids if i not in cut]
        known = [cut[i] for i in ids if i in cut]
        if not known:
            continue
        hull = (min(b[0] for _, b in known), max(b[1] for _, b in known),
                min(b[2] for _, b in known), max(b[3] for _, b in known))
        d = max(abs(p - q) for p, q in zip(box, hull))
        if d > tol:
            items.append(("off", "+".join(sorted(n for n, _ in known)), d))
    items += [("missing", name, None) for gid, (name, _) in cut.items() if gid not in drawn]
    return sorted(items, key=lambda t: (t[0], t[1]))
