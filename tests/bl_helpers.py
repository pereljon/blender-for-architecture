"""Blender test: every public bhelpers function runs in metres and in feet; lengths scale by U."""
import json
import math
import os

import bpy
import bmesh
from mathutils import Vector

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # Blender -P does not add the script folder
import tcommon
from tcommon import OUT, check, close, dims, extents, finish

import bhelpers as bh


def new_objs(before):
    return [o for o in bpy.data.objects if o not in before]


def snapshot():
    return set(bpy.data.objects)


def exercise(unit, u):
    print(f"-- unit {unit} (U={u})")
    bh.set_units(unit)
    check(close(bh.U, u, 1e-12), f"{unit}: U == {u}, got {bh.U}")
    bh.clear_scene()
    check(len(bpy.data.objects) == 0, f"{unit}: clear_scene leaves no objects")
    sc = bpy.context.scene
    grey = bh.principled("grey", (0.5, 0.5, 0.5), 0.6)
    tol = 1e-6

    # ---- geometry
    ob = bh.box("b1", 0, 2, 0, 3, 0, 1, grey)
    d = dims(ob)
    check(all(close(d[i], v * u, tol) for i, v in enumerate((2, 3, 1))), f"{unit}: box dims {d}")
    check(ob.name == "b1" and ob.name in sc.collection.objects, f"{unit}: box named and linked")
    lo, _ = extents(ob)
    check(close(lo[0], 0, tol) and close(lo[2], 0, tol), f"{unit}: box origin")
    ob = bh.box("b_off", 1, 2, 4, 5, 0.5, 1.5, grey, bevel=0.05, seg=2)
    lo, hi = extents(ob)
    check(close(lo[0], 1 * u, tol) and close(hi[1], 5 * u, tol) and close(hi[2], 1.5 * u, tol),
          f"{unit}: box offset/bevel extents {lo} {hi}")

    mesh = bpy.data.meshes.new("raw")
    mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
    ob = bh.new_obj("raw_obj", mesh, grey)
    check(ob.name == "raw_obj" and ob.name in sc.collection.objects, f"{unit}: new_obj linked")

    sq = [(0, 0), (4, 0), (4, 3), (0, 3)]
    ob = bh.slab("slab_num", sq, 1.0, 0.2, grey)
    lo, hi = extents(ob)
    check(close(hi[2], 1.0 * u, tol) and close(hi[0] - lo[0], 4 * u, tol) and close(hi[1] - lo[1], 3 * u, tol),
          f"{unit}: slab numeric ztop extents {lo} {hi}")
    check(close(hi[2] - lo[2], 0.2 * u, tol), f"{unit}: slab thickness {hi[2] - lo[2]}")
    ob = bh.slab("slab_fn", sq, lambda x, y: 1.0, 0.2, grey)
    check(close(extents(ob)[1][2], 1.0 * u, tol), f"{unit}: slab callable ztop")
    ob = bh.slab("slab_zbot", sq, 1.0, 0.2, grey, zbot=0.5)
    lo, hi = extents(ob)
    check(close(lo[2], 0.5 * u, tol) and close(hi[2], 1.0 * u, tol), f"{unit}: slab zbot numeric")
    ob = bh.slab("slab_zbot_fn", sq, lambda x, y: 1.0, 0.2, grey, zbot=lambda x, y: 0.5)
    check(close(extents(ob)[0][2], 0.5 * u, tol), f"{unit}: slab zbot callable")

    ob = bh.prism("pr", [(0, 0), (3, 0), (3, 2), (0, 2)], 0.5, 2.5, grey)
    d = dims(ob)
    check(all(close(d[i], v * u, tol) for i, v in enumerate((3, 2, 2))), f"{unit}: prism dims {d}")

    ob = bh.seg("sg", (0, 0), (2, 0), 0.1, 0, 1, grey)
    lo, hi = extents(ob)
    check(close(hi[2] - lo[2], 1 * u, tol) and close(hi[0] - lo[0], 2 * u, tol)
          and close(hi[1] - lo[1], 0.1 * u, tol), f"{unit}: seg dims {lo} {hi}")

    ob = bh.cyl("cy", 1, 2, 0, 2, 0.5, grey)
    d = dims(ob)
    check(close(d[2], 2 * u, tol) and close(d[0], 1 * u, 1e-5), f"{unit}: cyl dims {d}")
    ob = bh.cyl("cy_rot", 1, 2, 0, 2, 0.5, grey, n=16, rot_rad=(0.0, math.radians(90), 0.0))
    d = dims(ob)
    check(close(d[0], 2 * u, 1e-5), f"{unit}: cyl rot turns it, x extent {d}")
    ob = bh.cyl_x("cx", 0, 3, 1, 0.5, 0.05, grey)
    lo, hi = extents(ob)
    check(close(hi[0] - lo[0], 3 * u, 1e-5) and close((hi[1] + lo[1]) / 2, 1 * u, 1e-5)
          and close((hi[2] + lo[2]) / 2, 0.5 * u, 1e-5), f"{unit}: cyl_x extents {lo} {hi}")
    ob = bh.cyl_y("cyy", 0, 3, 1, 0.5, 0.05, grey)
    lo, hi = extents(ob)
    check(close(hi[1] - lo[1], 3 * u, 1e-5) and close((hi[0] + lo[0]) / 2, 1 * u, 1e-5),
          f"{unit}: cyl_y extents {lo} {hi}")
    ob = bh.sphere("sp", 1, 2, 3, 0.5, grey, scale=(1, 1, 2))
    lo, hi = extents(ob)
    check(close((hi[2] + lo[2]) / 2, 3 * u, 1e-5) and close(hi[0] - lo[0], 1 * u, 1e-5)
          and close(hi[2] - lo[2], 2 * u, 1e-5), f"{unit}: sphere extents {lo} {hi}")

    ob = bh.tube("tb", [(0, 0, 0), (0, 0, 1), (0.5, 0, 1.2)], 0.05, grey)
    check(ob.type == "CURVE" and ob.data.use_fill_caps and close(ob.data.bevel_depth, 0.05 * u, 1e-7),
          f"{unit}: tube is a capped curve with radius scaled")
    ob = bh.polyline("pl", [(0, 0), (1, 0), (1, 1)], 0.1, 0.04, grey)
    check(ob.type == "CURVE" and ob.data.use_fill_caps and close(ob.data.bevel_depth, 0.02 * u, 1e-7),
          f"{unit}: polyline curve, width scaled")

    ob = bh.lathe("lt", [(0.0, 0.0), (0.5, 0.0), (0.6, 0.3)], grey)
    d = dims(ob)
    check(close(d[0], 1.2 * u, 1e-5) and close(d[2], 0.3 * u, 1e-5), f"{unit}: lathe dims {d}")
    bh.place(ob, 2, 3, 0.5, rot_deg=30)
    check(all(close(ob.location[i], v * u, tol) for i, v in enumerate((2, 3, 0.5))), f"{unit}: place location")
    check(close(ob.rotation_euler.z, math.radians(30), 1e-6), f"{unit}: place rotation")
    ob = bh.lathe("lt_plan", [(0.0, 0.0), (0.9, 0.0), (1.0, 0.13)], grey, n=32, plan=(0.2, 0.25, 4))
    check(ob.name == "lt_plan" and len(ob.data.vertices) > 0, f"{unit}: lathe plan variant")

    def build_unit():
        bh.box("pl_a", 0, 1, 0, 1, 0, 1, grey)

    before = snapshot()
    bh.placed(build_unit, 2, 3, 0, 0)
    new = new_objs(before)
    check(len(new) == 1 and close(extents(new[0])[0][0], 2 * u, tol) and close(extents(new[0])[0][1], 3 * u, tol),
          f"{unit}: placed moves new objects by scaled offset")

    # cut_holes: boolean volume drops by the scaled hole volume
    bh.box("cutme_a", 0, 4, 0, 4, 0, 0.2, grey)
    bh.box("cutme_b", 10, 14, 0, 4, 0, 0.2, grey)
    bh.cut_holes("cutme_a", [(1, 2, 1, 2, -1, 1)])
    bh.cut_holes(("cutme_b",), [(11, 12, 1, 2, -1, 1)])
    dg = bpy.context.evaluated_depsgraph_get()
    for nm in ("cutme_a", "cutme_b"):
        ev = bpy.data.objects[nm].evaluated_get(dg)
        me = ev.to_mesh()
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.transform(bm, matrix=ev.matrix_world, verts=bm.verts)
        vol = abs(bm.calc_volume())
        bm.free()
        ev.to_mesh_clear()
        want = (16 - 1) * 0.2 * u ** 3
        check(abs(vol - want) < 1e-4 * want, f"{unit}: cut_holes {nm} volume {vol} vs {want}")

    cam_ob = bpy.data.objects.new("lookcam", bpy.data.cameras.new("lookcam"))
    sc.collection.objects.link(cam_ob)
    bh.look(cam_ob, (1, 2, 1.5), (4, 2, 1.5))
    fwd = cam_ob.rotation_euler.to_matrix() @ Vector((0, 0, -1))
    check(all(close(cam_ob.location[i], v * u, tol) for i, v in enumerate((1, 2, 1.5))), f"{unit}: look location")
    check(close(fwd.x, 1.0, 1e-5) and abs(fwd.y) < 1e-5, f"{unit}: look aims at target {tuple(fwd)}")

    before = snapshot()
    h = 1.75 if unit == "m" else 5.75
    bh.person(grey, 1, 1, h=h)
    new = new_objs(before)
    ztop = max(extents(o)[1][2] for o in new if o.type == "MESH")
    check(len(new) >= 2 and abs(ztop - 1.75) < 0.05, f"{unit}: person of {h} {unit} is about 1.75 m tall, got {ztop}")

    # ---- materials
    check(bh.srgb("#ff8000") == bh.srgb("ff8000"), f"{unit}: srgb accepts hex with or without #")
    c = bh.srgb("#ff8000")
    check(close(c[0], 1.0, 1e-6) and close(c[1], 0.2158605, 1e-5) and close(c[2], 0.0, 1e-9), f"{unit}: srgb linear {c}")
    pm = bh.principled("pm", (0.1, 0.2, 0.3), 0.3, 0.5)
    node = pm.node_tree.nodes["Principled BSDF"]
    check(close(node.inputs["Roughness"].default_value, 0.3, 1e-6)
          and close(node.inputs["Metallic"].default_value, 0.5, 1e-6), f"{unit}: principled values")
    check(bh.sock(node, "Roughness") == node.inputs["Roughness"], f"{unit}: sock by name")
    check(bh.osock(node, "BSDF").name == "BSDF", f"{unit}: osock by name")
    mix = pm.node_tree.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    check(bh.sock(mix, "A", "RGBA").type == "RGBA" and bh.sock(mix, "B", "RGBA").type == "RGBA",
          f"{unit}: sock picks the RGBA Mix sockets")
    check(bh.osock(mix, "Result", "RGBA").type == "RGBA", f"{unit}: osock picks the RGBA Mix result")
    em = bh.emission("em", (1, 0.9, 0.8), 5.0)
    emn = [n for n in em.node_tree.nodes if n.type == "EMISSION"]
    check(len(emn) == 1 and close(emn[0].inputs["Strength"].default_value, 5.0, 1e-6), f"{unit}: emission strength")
    for label, mat in (("wood", bh.wood_material("wd", axis="Z")),
                       ("wood_x", bh.wood_material("wd_x", axis="X", rough=0.3)),
                       ("planks", bh.planks("pk", (0.5, 0.35, 0.2), plank_w=0.18, plank_l=1.8)),
                       ("stone", bh.stone_tile("st", (0.6, 0.6, 0.6), tile=0.6, tile_h=0.3, plane="xz", joint=0.01)),
                       ("stone_xy", bh.stone_tile("st2", (0.6, 0.6, 0.6))),
                       ("fabric", bh.fabric("fb", (0.5, 0.2, 0.2), scale=100.0, strength=0.2))):
        check(mat is not None and mat.use_nodes and len(mat.node_tree.nodes) > 2, f"{unit}: {label} material built")

    png = os.path.join(OUT, "tile_src.png")
    img = bpy.data.images.new("tile_src", 8, 8)
    img.filepath_raw = png
    img.file_format = "PNG"
    img.save()
    m1 = bh.image_tile_material("imt", png, mult=(1, 1, 1), rough=0.5, bump=0.1, spec=0.5)
    m2 = bh.projected_tile_material("prj", png, 0.6, rough=0.5, bump=0.1)
    m3 = bh.projected_tile_material("prj3", png, (0.6, 0.6, 0.6))
    check(all(m is not None and m.use_nodes for m in (m1, m2, m3)), f"{unit}: image materials built")

    # ---- tiles (project units throughout)
    face = bh.Face((0, 0, 0), (1, 0, 0), (0, 0, 1), (0, 1, 0))
    ob = bh.tile_poly("tp", [(0, 0, 0), (1.2, 0, 0), (1.2, 0, 0.6), (0, 0, 0.6)],
                      [(0, 0), (1, 0), (1, 1), (0, 1)], (0, 1, 0), grey, thick=0.010)
    d = dims(ob)
    check(close(d[0], 1.2 * u, tol) and close(d[2], 0.6 * u, tol) and close(d[1], 0.010 * u, 1e-7),
          f"{unit}: tile_poly dims {d}")
    n0 = len(bh.PIECES)
    ob = bh.face_piece("fp", face, [(0, 0), (0.5, 0), (0.5, 0.6), (0, 0.6)], (0, 0), grey, (False, True))
    check(len(bh.PIECES) == n0 + 1 and ob.name == "fp", f"{unit}: face_piece records a piece")
    cols = bh.u_pieces(0, 2.4, 0, 1, length=1.2, joint=0.002)
    check(len(cols) == 2 and close(cols[0][0], 0) and close(cols[0][1], 1.2), f"{unit}: u_pieces {cols}")
    check(bh.subtract((0, 4, 0, 3), (1, 2, 1, 2)).__len__() == 4, f"{unit}: subtract with inner hole gives 4 rects")
    check(bh.subtract((0, 4, 0, 3), (5, 6, 5, 6)) == [(0, 4, 0, 3)], f"{unit}: subtract with no overlap")
    import random
    n1 = len(bh.PIECES)
    bh.tile_wall("w", face, 0.0, 2.4, 0.0, 1, [(0, 0.6), (0.602, 1.202)], grey, random.Random(1),
                 tile=(1.2, 0.6), joint=0.002)
    check(len(bh.PIECES) - n1 == 4, f"{unit}: tile_wall 2 columns x 2 rows gives {len(bh.PIECES) - n1} pieces")
    n2 = len(bh.PIECES)
    bh.tile_wall("wh", face, 0.0, 2.4, 0.0, 1, [(0, 0.6), (0.602, 1.202)], grey, random.Random(1),
                 holes=[(0.4, 1.0, 0.1, 0.5)], tile=(1.2, 0.6), joint=0.002)
    check(len(bh.PIECES) - n2 > 4, f"{unit}: tile_wall hole adds cut pieces")
    pj = os.path.join(OUT, f"pieces_{unit}.json")
    bh.export_pieces(pj)
    with open(pj) as fh:
        data = json.load(fh)
    pts = [p for pc in data["pieces"] for p in pc["poly"]]
    check(len(data["pieces"]) == len(bh.PIECES) and max(p[0] for p in pts) <= 2.4 + 1e-6,
          f"{unit}: export_pieces keeps project units")

    # ---- plan input and correction layer
    plan = dict(walls=[dict(kind="new", x0=0, x1=6, y0=0, y1=0.2), dict(kind="new", x0=0, x1=0.2, y0=0, y1=4),
                       dict(kind="existing", x0=3, x1=3.2, y0=1, y1=3)],
                doors=[dict(arc=[[1, 1], [1.5, 1.2], [2, 2]], leaf=None), dict(arc=[[3, 1], [3.5, 1.2]], leaf=None)],
                leaves=[])
    pp = os.path.join(OUT, f"plan_{unit}.json")
    with open(pp, "w") as fh:
        json.dump(plan, fh)
    walls, doors, leaves = bh.load_plan(pp)
    check(len(walls) == 3 and len(doors) == 2 and leaves == [], f"{unit}: load_plan returns walls, doors, leaves")
    fixed = bh.fix_walls(walls, wall_fixes=[((0, 0.2, 0, 4), (0.5, 4.5))],
                         wall_replace=[((3, 3.2, 1, 3), None)])
    check(len(fixed) == 2, f"{unit}: fix_walls removes a replaced-with-None wall")
    f2 = [w for w in fixed if w["x1"] - w["x0"] < 1][0]
    check(close(f2["y0"], 0.5) and close(f2["y1"], 4.5), f"{unit}: fix_walls moves a wall")
    repl = bh.fix_walls(walls, wall_replace=[((0, 6, 0, 0.2), (0, 5, 0, 0.2))])
    check(any(close(w["x1"], 5) for w in repl), f"{unit}: fix_walls replaces a rect")
    cut = bh.cut_openings(walls[:1], [(2, 3, -1, 1)])
    check(len(cut) == 2 and close(max(w["x1"] for w in cut), 6) and close(min(w["x0"] for w in cut), 0),
          f"{unit}: cut_openings splits a wall at an opening")
    before = snapshot()
    made = bh.walls_from_plan(walls, 0, 2.5, grey, prefix="pw_")
    check(len(made) == 3 and sorted(o.name for o in made) == ["pw_0", "pw_1", "pw_2"],
          f"{unit}: walls_from_plan names {[o.name for o in made]}")
    d = dims(made[0])
    check(close(d[0], 6 * u, tol) and close(d[1], 0.2 * u, tol) and close(d[2], 2.5 * u, tol),
          f"{unit}: walls_from_plan wall dims {d}")
    before = snapshot()
    bh.door_swings(doors, grey, z=0.06, width=0.04)
    check(len(new_objs(before)) == 2, f"{unit}: door_swings one object per door")
    before = snapshot()
    bh.door_swings(doors, grey, skip=lambda dd: dd["arc"][0] == [3, 1])
    check(len(new_objs(before)) == 1, f"{unit}: door_swings skip drops one")

    # ---- lights
    before = {l for l in bpy.data.lights}
    bh.room_fill_lights({"r1": (0, 4, 0, 3)}, 2.5, w_per_m2=24.0)
    nl = [l for l in bpy.data.lights if l not in before]
    check(len(nl) == 1 and close(nl[0].energy, 24.0 * 12 * u * u, 1e-3), f"{unit}: room_fill energy by m2 {[l.energy for l in nl]}")
    before = snapshot()
    bh.opening_light("op", 1, 3, 0, 0.5, 2.0, energy=900)
    new = [o for o in new_objs(before) if o.type == "LIGHT"]
    check(len(new) == 1 and close(new[0].location.z, 2.0 * u, tol) and 1 * u - tol <= new[0].location.x <= 3 * u + tol,
          f"{unit}: opening_light placed in scaled units")
    check(close(new[0].data.energy, 900), f"{unit}: opening_light energy not scaled")
    before = snapshot()
    bh.sun(45, 135, plan_north_deg=10, energy=3.0)
    new = [o for o in new_objs(before) if o.type == "LIGHT"]
    check(len(new) == 1 and new[0].data.type == "SUN" and close(new[0].data.energy, 3.0), f"{unit}: sun light")
    before = snapshot()
    em2 = bh.emission("dl", (1, 1, 1), 10)
    bh.downlights(em2, (0, 4, 0, 3), 2.5, nx=3, ny=2, watts=45)
    spots = [o for o in new_objs(before) if o.type == "LIGHT" and o.data.type == "SPOT"]
    check(len(spots) == 6 and all(0 <= o.location.x <= 4 * u + tol and o.location.z < 2.5 * u for o in spots),
          f"{unit}: downlights 6 spots under the ceiling, got {len(spots)}")

    # ---- cameras and render settings
    s = bh.setup_cycles(8, gpu=False)
    check(s is bpy.context.scene and s.render.engine == "CYCLES" and s.cycles.samples == 8
          and s.cycles.device == "CPU", f"{unit}: setup_cycles")
    check(s.world is not None, f"{unit}: setup_cycles creates a world")
    bh.set_resolution(160, aspect=0.625)
    check((s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage) == (160, 100, 100),
          f"{unit}: set_resolution {s.render.resolution_x}x{s.render.resolution_y}")
    cam = bh.new_camera("camx", clip_start=0.05)
    check(cam.name.startswith("camx") and s.camera is cam and close(cam.data.clip_start, 0.05 * u, 1e-7),
          f"{unit}: new_camera clip_start scaled")
    cam = bh.perspective_camera((1, -4, 1.5), (1, 2, 1.0), lens=24, sensor=36, shift_x=0.1)
    check(all(close(cam.location[i], v * u, tol) for i, v in enumerate((1, -4, 1.5))), f"{unit}: perspective loc")
    check(close(cam.data.lens, 24) and close(cam.data.shift_x, 0.1, 1e-6), f"{unit}: perspective lens and shift")
    px = bh.project_points([(1, 2, 1.0)])
    # shift_x=0.1 moves the frame right by a tenth of its width, so the target lands 16 px left of centre
    check(len(px) == 1 and abs(px[0][0] - (80 - 0.1 * 160)) < 1.0 and abs(px[0][1] - 50) < 1.0,
          f"{unit}: project_points maps the target through the shifted frame, got {px}")
    cam = bh.plan_camera((2, 1.5), 8, 1.2, floor_z=0.0, height=12.0)
    check(cam.data.type == "ORTHO" and close(cam.data.ortho_scale, 8 * u, 1e-6), f"{unit}: plan_camera ortho scale")
    check(close(cam.location.z, 12 * u, 1e-5) and close(cam.data.clip_start, (12 - 1.2) * u, 1e-5)
          and close(cam.data.clip_end, 12 * u + 6, 1e-5), f"{unit}: plan_camera clip {cam.data.clip_start} {cam.data.clip_end}")
    bh.box("hide_me", 0, 1, 0, 1, 0, 1, grey)
    bh.box("hide_other", 0, 1, 0, 1, 0, 1, grey)
    cam = bh.add_camera(dict(loc=(1, -4, 1.5), target=(1, 2, 1.0), lens=24, aspect=0.625, hide=("hide_me",)), 160)
    check(cam.data.type == "PERSP" and (s.render.resolution_x, s.render.resolution_y) == (160, 100)
          and s.camera is cam, f"{unit}: add_camera perspective entry")
    check(not bpy.data.objects["hide_me"].visible_camera and bpy.data.objects["hide_other"].visible_camera,
          f"{unit}: add_camera hide prefixes (perspective hide is camera-only, see bl_rev4)")
    bpy.data.objects["hide_me"].hide_render = False
    cam = bh.add_camera(dict(plan=True, center=(2, 1.5), width=8, cut=1.2, aspect=1.0), 160)
    check(cam.data.type == "ORTHO" and (s.render.resolution_x, s.render.resolution_y) == (160, 160)
          and close(cam.data.ortho_scale, 8 * u, 1e-6), f"{unit}: add_camera plan entry")
    cam = bh.add_camera(dict(plan=True, center=(2, 1.5), width=8, cut=1.2, floor_z=0, aspect=1.0,
                             hide=("hide_me",), drop=("b1",), keep=("hide_other",)), 160)
    check(cam.data.type == "ORTHO", f"{unit}: add_camera plan entry with drop/keep")
    bh.plan_cut(1.2, floor_z=0.0, hide=("b_off",), drop=("sp",), keep=())
    check(bpy.data.objects["b_off"].hide_render, f"{unit}: plan_cut hides prefixed objects")
    before = snapshot()
    bh.plan_light((2, 1.5), floor_z=0.0, height=9.0, size=(36.0, 18.0), w_per_m2=60.0)
    new = [o for o in new_objs(before) if o.type == "LIGHT"]
    check(len(new) == 1 and close(new[0].location.z, 9 * u, 1e-5)
          and close(new[0].data.energy, 60.0 * 36 * 18 * u * u, 1e-3),
          f"{unit}: plan_light placed in scaled units, energy by area {[o.data.energy for o in new]}")

    # ---- plan overlays
    for label, fn in (
        ("dotted_square", lambda: bh.dotted_square("dsq", 5, 5, 0.5, 0.0, grey, dash=0.1, pitch=0.2, w=0.05)),
        ("dashed_path", lambda: bh.dashed_path("dpa", [(0, 10), (2, 10)], 0.0, grey, dash=0.3, gap=0.2, w=0.05)),
        ("dotted_rect", lambda: bh.dotted_rect("drc", 0, 2, 20, 21, 0.0, grey, dash=0.1, pitch=0.2, w=0.05)),
    ):
        before = snapshot()
        fn()
        new = [o for o in new_objs(before) if o.type == "MESH"]
        check(len(new) >= 4, f"{unit}: {label} creates dashes ({len(new)})")
        if new:
            lo_x = min(extents(o)[0][0] for o in new)
            hi_x = max(extents(o)[1][0] for o in new)
            lo_y = min(extents(o)[0][1] for o in new)
            hi_y = max(extents(o)[1][1] for o in new)
            box_ = {"dotted_square": (4.4, 5.6, 4.4, 5.6), "dashed_path": (-0.1, 2.1, 9.9, 10.1),
                    "dotted_rect": (-0.3, 2.3, 19.7, 21.3)}[label]
            ok = box_[0] * u - 1e-5 <= lo_x and hi_x <= box_[1] * u + 1e-5 \
                and box_[2] * u - 1e-5 <= lo_y and hi_y <= box_[3] * u + 1e-5
            check(ok, f"{unit}: {label} extents inside scaled bounds {lo_x:.4f}..{hi_x:.4f} {lo_y:.4f}..{hi_y:.4f}")


def main():
    exercise("m", 1.0)
    exercise("ft", 0.3048)
    bh.set_units(0.5)
    check(close(bh.U, 0.5, 1e-12), "set_units(float)")
    bh.clear_scene()
    ob = bh.box("half", 0, 2, 0, 2, 0, 2)
    check(close(dims(ob)[0], 1.0, 1e-6), "set_units(0.5) scales box")
    bh.set_units("m")
    # gpu=True must not raise whether or not Metal exists
    s = bh.setup_cycles(8, gpu=True)
    check(s.cycles.device in ("CPU", "GPU"), "setup_cycles(gpu=True) returns a scene without raising")
    finish("bl_helpers")


main()
