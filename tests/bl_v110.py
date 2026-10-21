"""Blender test: v1.1.0 (T37 GPU backend, T38 eye height, T39 geometry dump) from Revision 8 of the design."""
import ast
import contextlib
import io
import json
import math
import os
import re
import shutil
import sys
import tempfile
import traceback

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # Blender -P does not add the script folder
import tcommon
from tcommon import check, close, finish

import bhelpers as bh

SKILL = os.path.dirname(tcommon.HERE)
FT = 0.3048
WARN_CPU = "WARN no GPU device found (tried {}), rendering on CPU"


def cap(fn, *a, **kw):
    """Run fn and return (result, stdout lines)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        res = fn(*a, **kw)
    return res, buf.getvalue().splitlines()


def cycles_prefs():
    return bpy.context.preferences.addons["cycles"].preferences


def has_metal():
    prefs = cycles_prefs()
    prefs.get_devices()
    return any(dv.type == "METAL" for dv in prefs.devices)


# ---------------------------------------------------------------- T37: GPU backend
def t37():
    names = getattr(bh, "GPU_BACKENDS", None)
    want = ("METAL",) if sys.platform == "darwin" else ("OPTIX", "CUDA", "HIP")
    check(names == want, f"T37 GPU_BACKENDS is {want} on {sys.platform}, got {names}")
    if names is None:
        return
    saved = bh.GPU_BACKENDS
    sc = bpy.context.scene
    metal = has_metal()
    try:
        for tried in (("CUDA",), ("NONE",)):
            bh.GPU_BACKENDS = tried
            _, out = cap(bh.setup_cycles, 8, gpu=True)
            warns = [ln for ln in out if ln.startswith("WARN")]
            check(sc.cycles.device == "CPU", f"T37 {tried}: device is CPU, got {sc.cycles.device}")
            check(warns == [WARN_CPU.format(", ".join(tried))], f"T37 {tried}: exactly one WARN line naming the backend, got {warns}")
        for tried in (("CUDA", "METAL"), ("NONE", "METAL")):
            if not metal:
                print(f"SKIP T37 no Metal device ({tried})")
                continue
            bh.GPU_BACKENDS = tried
            _, out = cap(bh.setup_cycles, 8, gpu=True)
            check(sc.cycles.device == "GPU", f"T37 {tried}: device is GPU, got {sc.cycles.device}")
            check(cycles_prefs().compute_device_type == "METAL", f"T37 {tried}: compute_device_type is METAL, got {cycles_prefs().compute_device_type}")
            check(all(dv.use for dv in cycles_prefs().devices), f"T37 {tried}: every device is enabled")
            check(not [ln for ln in out if ln.startswith("WARN")], f"T37 {tried}: no WARN line, got {out}")
        bh.GPU_BACKENDS = saved
        if metal:
            _, out = cap(bh.setup_cycles, 8, gpu=True)
            check(sc.cycles.device == "GPU" and not [ln for ln in out if ln.startswith("WARN")],
                  f"T37 default backends: GPU and no WARN line, got {sc.cycles.device} {out}")
        _, out = cap(bh.setup_cycles, 8, gpu=False)
        check(sc.cycles.device == "CPU" and not out, f"T37 gpu=False: CPU and no output, got {sc.cycles.device} {out}")
    finally:
        bh.GPU_BACKENDS = saved


# ---------------------------------------------------------------- T38: eye height
def template_lib():
    tree = ast.parse(open(os.path.join(SKILL, "templates", "scene_template.py")).read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "LIB" for t in node.targets):
            return node.value.value
    return None


def template_camera_z(replace_viewer=None):
    """Copy the template with its scripts under lib/<LIB>/, import it, build the scene, add the persp camera; return world z."""
    lib = template_lib()
    if not check(lib, "T38 the template defines LIB"):
        return None
    tmp = tempfile.mkdtemp(prefix="bl_v110_")
    try:
        src = open(os.path.join(SKILL, "templates", "scene_template.py")).read()
        if replace_viewer is not None:
            new, n = re.subn(r"^VIEWER = None\b", f"VIEWER = {replace_viewer}", src, flags=re.M)
            if not check(n == 1, "T38 the template has one line starting 'VIEWER = None'"):
                return None
            src = new
        mod = "scene_tpl_default" if replace_viewer is None else "scene_tpl_seeded"
        open(os.path.join(tmp, f"{mod}.py"), "w").write(src)
        shutil.copytree(tcommon.SCRIPTS, os.path.join(tmp, "lib", lib), ignore=shutil.ignore_patterns("__pycache__"))
        sys.path.insert(0, tmp)
        try:
            st = __import__(mod)
        finally:
            sys.path.remove(tmp)
        bh.clear_scene()
        st.build(type("Opts", (), {"option": "a"})())
        cam = bh.add_camera(st.VIEWS["persp"], 160)
        bpy.context.view_layer.update()
        z = cam.matrix_world.translation.z
        bh.set_units("m")
        return z
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def t38():
    check(getattr(bh, "EYE_HEIGHT", None) == 1.5875, f"T38 EYE_HEIGHT is still 1.5875: {getattr(bh, 'EYE_HEIGHT', None)}")
    eye = getattr(bh, "eye_height", None)
    if check(callable(eye), "T38 bhelpers.eye_height exists"):
        bh.set_units("m")
        check(close(eye(), 1.5875, 1e-9) and close(eye(), bh.EYE_HEIGHT, 1e-9), f"T38 eye_height() in metres is 1.5875, got {eye()}")
        check(close(eye(1.52), 1.4057, 1e-9), f"T38 eye_height(1.52) is 1.4057 (a fixed drop), got {eye(1.52)}")
        bh.set_units("ft")
        try:
            check(close(eye(), 1.5875 / FT, 1e-6), f"T38 eye_height() in feet is 1.5875 / 0.3048, got {eye()}")
            check(close(eye(5 + 7 / 12), 5.208333, 1e-6), f"T38 eye_height(5 + 7/12) in feet is 5.208333, got {eye(5 + 7 / 12)}")
        finally:
            bh.set_units("m")
    z = template_camera_z()
    if z is not None:
        check(close(z, 1.5875, 1e-6), f"T38 template default: the persp camera stands at 1.5875, got {z}")
    z = template_camera_z(replace_viewer="1.52")
    if z is not None:
        check(close(z, 1.4057, 1e-6), f"T38 template with VIEWER = 1.52: the persp camera stands at 1.4057, got {z}")


# ---------------------------------------------------------------- T39: geometry dump
def dump_block():
    """The first fenced code block under the heading 'Geometry dump' in reference/migration.md, or None."""
    path = os.path.join(SKILL, "reference", "migration.md")
    if not check(os.path.isfile(path), "T39 reference/migration.md exists"):
        return None
    lines = open(path, encoding="utf-8").read().splitlines()
    start = next((i for i, ln in enumerate(lines) if re.match(r"#+\s+Geometry dump\s*$", ln)), None)
    if not check(start is not None, "T39 migration.md has a heading 'Geometry dump'"):
        return None
    level = len(re.match(r"#+", lines[start]).group(0))
    block, inside = [], False
    for ln in lines[start + 1:]:
        if not inside and re.match(rf"#{{1,{level}}}\s", ln):
            break
        if ln.lstrip().startswith("```"):
            if inside:
                return "\n".join(block)
            inside = True
        elif inside:
            block.append(ln)
    check(False, "T39 no fenced code block under 'Geometry dump'")
    return None


def run_block(code, path):
    """Run the doc's block so that it writes the dump to path.

    The block either writes the file at module level from the names PATH or path, or defines one function that takes the path."""
    tree = ast.parse(code)
    bad = [n for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
           for n in ([a.name.split(".")[0] for a in node.names] if isinstance(node, ast.Import) else [node.module.split(".")[0]])
           if n not in ("bpy", "json")]
    check(not bad, f"T39 the block imports only bpy and json, also imports {bad}")
    g = {"__name__": "geometry_dump", "PATH": path, "path": path}
    exec(compile(code, "migration.md:Geometry dump", "exec"), g)
    funcs = [v for v in g.values() if callable(v) and getattr(v, "__globals__", None) is g]
    if not os.path.exists(path):
        pick = [f for f in funcs if f.__name__ in ("dump", "geometry_dump", "dump_geometry")] or funcs
        if check(len(pick) == 1, f"T39 the block writes the dump from PATH, or defines one function that takes the path; functions: {[f.__name__ for f in funcs]}"):
            pick[0](path)
    if not check(os.path.exists(path), "T39 the block writes the dump file"):
        return None
    return json.load(open(path))


def flat_numbers(v):
    if isinstance(v, bool):
        return []
    if isinstance(v, (int, float)):
        return [float(v)]
    if isinstance(v, (list, tuple)):
        return [x for e in v for x in flat_numbers(e)]
    if isinstance(v, dict):
        return [x for e in v.values() for x in flat_numbers(e)]
    return []


def world_box(ob):
    from mathutils import Vector
    ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    pts = [ev.matrix_world @ Vector(c) for c in ev.bound_box]
    return [min(p[i] for p in pts) for i in range(3)] + [max(p[i] for p in pts) for i in range(3)]


def eval_vertex_count(ob):
    ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    try:
        return len(me.vertices)
    finally:
        ev.to_mesh_clear()


def entry_matches_scene(name, entry, label):
    """Check one dump entry against the scene by value, without knowing the field names."""
    ob = bpy.data.objects[name]
    if not check(isinstance(entry, dict), f"T39 {label}: the entry for {name} is an object"):
        return
    values = list(entry.values())
    check(ob.type in values, f"T39 {label}: {name} entry holds its type {ob.type}")
    ints = [v for v in values if isinstance(v, int) and not isinstance(v, bool)]
    if ob.type == "MESH":
        n = eval_vertex_count(ob)
        check(n in ints, f"T39 {label}: {name} entry holds the evaluated vertex count {n}, ints are {ints}")
        nums = flat_numbers([v for v in values if isinstance(v, (list, tuple, dict))])
        for want in world_box(ob):
            check(any(abs(want - x) <= 2e-6 for x in nums), f"T39 {label}: {name} entry holds world box value {want:.6f}")
        mats = [s.material.name if s.material else None for s in ob.material_slots]
        check(mats in values, f"T39 {label}: {name} entry holds the slot materials {mats}")
    else:
        check(ints == [0], f"T39 {label}: non-mesh {name} has vertex count 0, ints are {ints}")


def diff_keys(a, b):
    return sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))


TOL = 3e-6


def has_num(x, nums, tol=TOL):
    return any(abs(x - n) <= tol for n in nums)


def has_all(xs, nums, tol=TOL):
    return all(has_num(x, nums, tol) for x in xs)


def flat_strings(v):
    if isinstance(v, str):
        return [v.lower()]
    if isinstance(v, (list, tuple)):
        return [x for e in v for x in flat_strings(e)]
    if isinstance(v, dict):
        return [x for e in v.values() for x in flat_strings(e)]
    return []


def leaves(v, path=()):
    """Yield (path, leaf) for every scalar in a JSON value."""
    if isinstance(v, dict):
        for k, e in v.items():
            yield from leaves(e, path + (k,))
    elif isinstance(v, list):
        for i, e in enumerate(v):
            yield from leaves(e, path + (i,))
    else:
        yield path, v


def leaf_diffs(a, b):
    """List (path, old, new) for every scalar that differs between two dumps."""
    la, lb = dict(leaves(a)), dict(leaves(b))
    return [(k, la.get(k), lb.get(k)) for k in sorted(set(la) | set(lb), key=str) if la.get(k) != lb.get(k)]


def at(tree, path):
    for k in path:
        tree = tree[k]
    return tree


def belongs_to(dump, path, name, object_names):
    """True when some dict on the path to a leaf is the entry of the named material, light or camera.

    An entry is a dict stored under the key name, or a dict that holds the name as a string value.
    A top-level key that names an object does not count as a material entry."""
    for i in range(1, len(path)):
        node = at(dump, path[:i])
        if not isinstance(node, dict):
            continue
        if path[i - 1] == name and not (i == 1 and name in object_names):
            return True
        if name.lower() in [v.lower() for v in node.values() if isinstance(v, str)]:
            return True
    return False


def entry_dicts(dump, name, object_names):
    """Every dict in the dump that is the entry for a material of this name (see belongs_to)."""
    found = []

    def walk(node, depth):
        if isinstance(node, dict):
            if name.lower() in [v.lower() for v in node.values() if isinstance(v, str)]:
                found.append(node)
            for k, v in node.items():
                if k == name and isinstance(v, dict) and not (depth == 0 and name in object_names):
                    found.append(v)
                walk(v, depth + 1)
        elif isinstance(node, list):
            for v in node:
                walk(v, depth + 1)

    walk(dump, 0)
    return found


def principled_inputs(mat):
    """(base color rgb or None, roughness or None, metallic or None); None for a linked or missing input."""
    if not mat or not mat.use_nodes:
        return None
    node = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if node is None:
        return None
    def val(name):
        s = node.inputs[name]
        return None if s.is_linked else s.default_value
    col = val("Base Color")
    return (list(col)[:3] if col is not None else None, val("Roughness"), val("Metallic"))


def rotation_forms(ob):
    m = ob.matrix_world.to_3x3().normalized()
    e, q = m.to_euler(), m.to_quaternion()
    return {
        "euler radians": list(e),
        "euler degrees": [math.degrees(a) for a in e],
        "quaternion": list(q),
        "negated quaternion": [-x for x in q],
        "rotation matrix": [m[r][c] for r in range(3) for c in range(3)],
    }


def check_rotation(label, ob, nums):
    forms = rotation_forms(ob)
    ok = any(has_all(v, nums) for v in forms.values())
    check(ok, f"T39 {label}: entry holds the world rotation as euler radians, euler degrees, a quaternion, or a matrix; "
              f"wanted one of {({k: [round(x, 6) for x in v] for k, v in forms.items()})}")


def check_material_entries(dump, label):
    """Every material that a scene object uses has its Principled BSDF base color, roughness and metallic in the dump."""
    names = {o.name for o in bpy.data.objects}
    used = {s.material for o in bpy.data.objects for s in o.material_slots if s.material}
    for mat in sorted(used, key=lambda m: m.name):
        vals = principled_inputs(mat)
        if vals is None:
            continue
        cands = entry_dicts(dump, mat.name, names)
        if not check(cands, f"T39 {label}: the dump has an entry for material {mat.name} (a dict under that key or holding that name)"):
            continue
        col, rough, metal = vals
        want = [("base color", col), ("roughness", None if rough is None else [rough]), ("metallic", None if metal is None else [metal])]
        for what, xs in want:
            if xs is None:
                continue
            check(any(has_all(xs, flat_numbers(list(c.values()))) for c in cands),
                  f"T39 {label}: material {mat.name} entry holds {what} {[round(x, 6) for x in xs]}")


def check_light_entry(label, dump, ob):
    ent = dump.get(ob.name)
    if not check(isinstance(ent, dict), f"T39 {label}: entry for light {ob.name}"):
        return
    nums = flat_numbers(list(ent.values()))
    check(ob.data.type.lower() in flat_strings(ent), f"T39 {label}: light {ob.name} entry holds its light type {ob.data.type}")
    check(has_num(ob.data.energy, nums), f"T39 {label}: light {ob.name} entry holds energy {ob.data.energy}")
    check(has_all(list(ob.data.color), nums), f"T39 {label}: light {ob.name} entry holds color {[round(x, 6) for x in ob.data.color]}")
    check_rotation(f"{label}: light {ob.name}", ob, nums)


def check_camera_entry(label, dump, ob):
    ent = dump.get(ob.name)
    if not check(isinstance(ent, dict), f"T39 {label}: entry for camera {ob.name}"):
        return
    nums = flat_numbers(list(ent.values()))
    loc = list(ob.matrix_world.translation)
    check(has_all(loc, nums), f"T39 {label}: camera {ob.name} entry holds world location {[round(x, 6) for x in loc]}")
    check(has_num(ob.data.lens, nums), f"T39 {label}: camera {ob.name} entry holds lens {ob.data.lens}")
    check_rotation(f"{label}: camera {ob.name}", ob, nums)


def only_counter_differs(label, d0, d1):
    keys = diff_keys(d0, d1)
    ok = check(keys == ["counter"], f"T39 {label}: exactly the counter entry differs, got {keys}")
    if not ok or "counter" not in d0 or "counter" not in d1:
        return None
    fields = [k for k in set(d0["counter"]) | set(d1["counter"]) if d0["counter"].get(k) != d1["counter"].get(k)]
    return {k: (d0["counter"].get(k), d1["counter"].get(k)) for k in fields}


def t39():
    code = dump_block()
    if code is None:
        return
    lib = template_lib()
    if not check(lib, "T39 the template defines LIB"):
        return
    tmp = tempfile.mkdtemp(prefix="bl_v110_dump_")
    try:
        shutil.copy(os.path.join(SKILL, "templates", "scene_template.py"), tmp)
        shutil.copytree(tcommon.SCRIPTS, os.path.join(tmp, "lib", lib), ignore=shutil.ignore_patterns("__pycache__"))
        sys.path.insert(0, tmp)
        try:
            import scene_template as st
        finally:
            sys.path.remove(tmp)
        bh.set_units("m")
        bh.clear_scene()
        st.build(type("Opts", (), {"option": "a"})())
        counter = bpy.data.objects["counter"]

        def dump(tag):
            p = os.path.join(tmp, f"dump_{tag}.json")
            return run_block(code, p)

        d0, d1 = dump("0"), dump("1")
        if d0 is None or d1 is None:
            return
        check(d0 == d1, "T39 two dumps of the same scene are equal")
        names = {o.name for o in bpy.data.objects}
        check(names <= set(d0), f"T39 the dump has an entry keyed by name for every object, missing {sorted(names - set(d0))}")
        for name in ("counter", "floor", "wall_south"):
            if name in d0:
                entry_matches_scene(name, d0[name], "base")
        for ob in bpy.data.objects:
            if ob.type == "LIGHT":
                entry_matches_scene(ob.name, d0[ob.name], "base")
                break

        # 1 mm along x: exactly the counter's box differs, by 1 mm
        counter.location.x += 0.001
        bpy.context.view_layer.update()
        dm = dump("move")
        if dm is not None:
            f = only_counter_differs("1 mm move", d0, dm)
            if f is not None:
                check(len(f) == 1, f"T39 1 mm move: exactly one field of the counter entry differs, got {sorted(f)}")
                for old, new in f.values():
                    a, b = flat_numbers(old), flat_numbers(new)
                    check(len(a) == len(b) and a and abs(max(abs(x - y) for x, y in zip(a, b)) - 0.001) <= 2e-6,
                          f"T39 1 mm move: the box changes by 1 mm, from {old} to {new}")
            if "counter" in dm:
                entry_matches_scene("counter", dm["counter"], "after move")
        # a move below 1 mm but above the 1e-6 rounding step is still seen
        counter.location.x += 0.00001
        bpy.context.view_layer.update()
        dt = dump("tiny")
        if dt is not None and dm is not None:
            check(diff_keys(dm, dt) == ["counter"], f"T39 a 0.01 mm move changes exactly the counter entry (box rounded to 1e-6), got {diff_keys(dm, dt)}")
        counter.location.x -= 0.00101
        bpy.context.view_layer.update()
        dback = dump("back")
        if dback is not None:
            check(all(abs(x - y) <= 2e-6 for k in d0["counter"] for x, y in zip(flat_numbers(d0["counter"][k]), flat_numbers(dback["counter"].get(k)))),
                  "T39 moving the counter back restores its box")

        # material: exactly the counter's materials differ
        base = dump("base2")
        orig_mat = counter.material_slots[0].material
        other = bpy.data.materials.new("other_mat")
        counter.material_slots[0].material = other
        bpy.context.view_layer.update()
        dmat = dump("mat")
        if dmat is not None and base is not None:
            objs = {o.name for o in bpy.data.objects}
            keys = diff_keys(base, dmat)
            sections = [k for k in keys if k not in objs]
            check(sorted(k for k in keys if k in objs) == ["counter"] and len(sections) == 1,
                  f"T39 material change: only the counter entry and the materials section differ, got {keys}")
            if "counter" in base and "counter" in dmat:
                fields = {k: (base["counter"].get(k), dmat["counter"].get(k)) for k in set(base["counter"]) | set(dmat["counter"])
                          if base["counter"].get(k) != dmat["counter"].get(k)}
                check(len(fields) == 1, f"T39 material change: exactly one field of the counter entry differs, got {sorted(fields)}")
                for old, new in fields.values():
                    check(isinstance(new, list) and "other_mat" in new, f"T39 material change: the field lists the new material, got {new}")
            for k in sections:
                b0, b1 = base.get(k), dmat.get(k)
                if not check(isinstance(b0, dict) and isinstance(b1, dict), f"T39 material change: section {k} exists in both dumps as an object"):
                    continue
                check(set(b0) <= set(b1) and all(b0[m] == b1[m] for m in b0) and set(b1) - set(b0) == {"other_mat"},
                      f"T39 material change: section {k} only gains an other_mat entry, added {sorted(set(b1) - set(b0))}, "
                      f"changed {sorted(m for m in b0 if m in b1 and b0[m] != b1[m])}, removed {sorted(set(b0) - set(b1))}")
        # a boolean cut changes the evaluated vertex count, not the mesh data
        counter.material_slots[0].material = orig_mat
        cutter = bh.box("cutter", 2.0, 2.2, 0.2, 0.4, 0.8, 1.0)
        cutter.hide_render = True
        before = dump("pre_bool")
        mod = counter.modifiers.new("cut", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.solver = "EXACT"
        mod.object = cutter
        bpy.context.view_layer.update()
        dbool = dump("bool")
        if dbool is not None and before is not None:
            n_mesh, n_eval = len(counter.data.vertices), eval_vertex_count(counter)
            check(n_eval != n_mesh, f"T39 the boolean cut changes the evaluated vertex count ({n_mesh} -> {n_eval})")
            entry_matches_scene("counter", dbool["counter"], "after boolean")
            changed = [k for k in dbool["counter"] if dbool["counter"][k] != before["counter"].get(k)]
            check(any(isinstance(dbool["counter"][k], int) and not isinstance(dbool["counter"][k], bool) for k in changed),
                  f"T39 the boolean cut changes the counter's vertex count field, changed fields {changed}")

        # materials, lights and cameras: the dump runs after the camera is placed
        counter.modifiers.remove(mod)
        cam = bh.add_camera(st.VIEWS["persp"], 160)
        lights = [o for o in bpy.data.objects if o.type == "LIGHT"]
        if not check(lights and cam is not None, "T39 the scene has a light and a camera"):
            return
        light = lights[0]
        light.rotation_euler = (0.3, 0.2, 0.1)
        bpy.context.view_layer.update()
        all_names = {o.name for o in bpy.data.objects}
        dl = dump("lcm")
        if dl is None:
            return
        check(all_names <= set(dl), f"T39 the dump has an entry for every object including the camera, missing {sorted(all_names - set(dl))}")
        check_material_entries(dl, "base")
        check_light_entry("base", dl, light)
        check_camera_entry("base", dl, cam)

        # roughness 0.8 to 0.5 on the wall material changes only that material's entry
        wall_mat = bpy.data.materials["wall"]
        node = next(n for n in wall_mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        check(abs(node.inputs["Roughness"].default_value - 0.8) < 1e-6, "T39 the wall material starts at roughness 0.8")
        node.inputs["Roughness"].default_value = 0.5
        bpy.context.view_layer.update()
        dr = dump("rough")
        if dr is not None:
            diffs = leaf_diffs(dl, dr)
            check(diffs, "T39 a roughness change 0.8 to 0.5 changes the dump")
            for path, old, new in diffs:
                num = isinstance(old, (int, float)) and isinstance(new, (int, float))
                check(num and abs(old - 0.8) <= TOL and abs(new - 0.5) <= TOL,
                      f"T39 roughness change: only the roughness value differs, but {path} went from {old} to {new}")
                check(path in dict(leaves(dr)) and belongs_to(dr, path, "wall", all_names),
                      f"T39 roughness change: the changed value {path} sits in the entry of material wall")
            others = [p for p, _, _ in diffs if any(belongs_to(dr, p, m.name, all_names) for m in bpy.data.materials if m.name != "wall" and m.users)]
            check(not others, f"T39 roughness change: no other material's entry changes, but {others} do")
        node.inputs["Roughness"].default_value = 0.8

        # a light energy change is detected, in the light's entry only
        bpy.context.view_layer.update()
        dl2 = dump("lcm2")
        old_e = light.data.energy
        light.data.energy = old_e * 1.5
        bpy.context.view_layer.update()
        de = dump("energy")
        if de is not None and dl2 is not None:
            check(diff_keys(dl2, de) == [light.name], f"T39 a light energy change changes exactly the light's entry, got {diff_keys(dl2, de)}")
            diffs = leaf_diffs(dl2, de)
            check(len(diffs) == 1 and all(isinstance(o, (int, float)) and abs(o - old_e) <= TOL * 10 and abs(n - old_e * 1.5) <= TOL * 10
                                           for _, o, n in diffs),
                  f"T39 a light energy change changes only the energy value, from {old_e} to {old_e * 1.5}; diffs {diffs}")
            check_light_entry("after energy change", de, light)
        light.data.energy = old_e

        # a camera rotation change is detected, in the camera's entry only
        bpy.context.view_layer.update()
        dc0 = dump("cam0")
        cam.rotation_euler.z += 0.05
        bpy.context.view_layer.update()
        dc1 = dump("cam1")
        if dc0 is not None and dc1 is not None:
            check(diff_keys(dc0, dc1) == [cam.name], f"T39 a camera rotation change changes exactly the camera's entry, got {diff_keys(dc0, dc1)}")
            check_camera_entry("after rotation", dc1, cam)
    finally:
        sys.modules.pop("scene_template", None)
        shutil.rmtree(tmp, ignore_errors=True)
        bh.set_units("m")


CASES = (t37, t38, t39)


def main():
    for fn in CASES:
        try:
            fn()
        except Exception as e:
            check(False, f"{fn.__name__} raised {type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}")
    finish("bl_v110")


main()
