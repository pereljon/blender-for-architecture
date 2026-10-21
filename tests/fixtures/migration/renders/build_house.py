"""Synthetic monolithic scene script for the migration eval (E10): a small invented house, in feet.

Everything is in this one file: its own helpers, materials, lights, cameras, and render call. It imports no skill
library. Run it from the project root (the folder that holds renders/ and delivered/):
  /Applications/Blender.app/Contents/MacOS/Blender -b -P renders/build_house.py -- --view living --res 800 --samples 48 --out scratch/living.png
The scene renders on CPU. Views: living, bedroom. Finish: --finish painted (the owner chose it on 2026-09-20).
Prints DONE <path> when the image is written.
"""
import argparse
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

FT = 0.3048                 # metres per project unit: every length below is in feet
CYL_SEGMENTS = 24           # segments for every cylinder in this project
WALL_H = 9.0
WALL_T = 0.5

# Walls as (x0, x1, y0, y1, z0, z1). Objects are named wall_<index> in this list's order.
WALLS = [
    (-0.5, 12.0, -0.5, 0.0, 0.0, WALL_H),     # south wall, west of the front door
    (15.0, 30.5, -0.5, 0.0, 0.0, WALL_H),     # south wall, east of the front door
    (-0.5, 0.0, 0.0, 20.0, 0.0, WALL_H),      # west wall
    (-0.5, 30.5, 20.0, 20.5, 0.0, WALL_H),    # north wall
    (30.0, 30.5, 0.0, 20.0, 0.0, WALL_H),     # east wall
    (18.0, 18.5, 0.0, 5.0, 0.0, WALL_H),      # partition between living room and bedroom, south of its door
    (18.0, 18.5, 8.0, 20.0, 0.0, WALL_H),     # partition, north of the door
    (18.5, 30.0, 12.0, 12.5, 0.0, WALL_H),    # partition between bedroom and bath
    (12.0, 15.0, -0.5, 0.0, 7.0, WALL_H),     # header over the front door
    (18.0, 18.5, 5.0, 8.0, 7.0, WALL_H),      # header over the bedroom door
]
ROOMS = {"living": (0.0, 18.0, 0.0, 20.0), "bedroom": (18.5, 30.0, 0.0, 12.0), "bath": (18.5, 30.0, 12.5, 20.0)}
# Camera: eye height is each view's own, in feet (the viewer for these views is a 5'-0" child).
VIEWS = {
    "living": dict(eye=4.6, loc=(16.0, 18.0), target=(4.0, 4.0, 3.5), lens=20),
    "bedroom": dict(eye=4.6, loc=(29.0, 11.0), target=(20.0, 2.0, 2.5), lens=22),
}
# Sun: fixed for every render of this project (elevation, azimuth), taken from the 21 September noon position.
SUN = (46.0, 190.0)
FINISHES = {"painted": "#ece8df", "oak": "#c9a46b"}


# ---------------------------------------------------------------- helpers
def srgb(hexstr):
    h = hexstr.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


def principled(name, color, rough=0.8):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    return m


def new_obj(name, mesh, mat=None):
    ob = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(ob)
    if mat:
        ob.data.materials.append(mat)
    return ob


def box(name, x0, x1, y0, y1, z0, z1, mat=None, bevel=0.0, seg=2):
    x0, x1, y0, y1, z0, z1 = (v * FT for v in (x0, x1, y0, y1, z0, z1))
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]]
    for f in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]:
        bm.faces.new([vs[i] for i in f])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = new_obj(name, me, mat)
    if bevel > 0:
        m = ob.modifiers.new("bev", "BEVEL")
        m.width = bevel * FT
        m.segments = seg
        m.limit_method = "ANGLE"
        ob.data.shade_smooth()
        ob.data.set_sharp_from_angle(angle=math.radians(40))
    return ob


def cyl(name, x, y, z0, z1, r, mat=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=CYL_SEGMENTS, radius1=r * FT, radius2=r * FT,
                          depth=(z1 - z0) * FT)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = new_obj(name, me, mat)
    ob.location = (x * FT, y * FT, (z0 + z1) / 2 * FT)
    ob.data.shade_smooth()
    return ob


def area_light(name, x0, x1, y0, y1, z, watts):
    ld = bpy.data.lights.new(name, "AREA")
    ld.shape = "RECTANGLE"
    ld.size, ld.size_y = (x1 - x0) * 0.6 * FT, (y1 - y0) * 0.6 * FT
    ld.energy = watts
    ob = bpy.data.objects.new(name, ld)
    ob.location = ((x0 + x1) / 2 * FT, (y0 + y1) / 2 * FT, z * FT)
    ob.visible_camera = False
    bpy.context.scene.collection.objects.link(ob)


def make_sun():
    ld = bpy.data.lights.new("sun", "SUN")
    ld.energy = 3.0
    ld.angle = math.radians(1.5)
    ob = bpy.data.objects.new("sun", ld)
    ob.rotation_euler = (math.radians(90 - SUN[0]), 0, math.pi - math.radians(SUN[1]))
    bpy.context.scene.collection.objects.link(ob)


def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras):
        for d in list(coll):
            coll.remove(d)


# ---------------------------------------------------------------- project-specific builders
def cabinet_run(prefix, x0, y0, count, width, depth, height, mat, handle_mat):
    """A run of base cabinets along +x: a carcass, a door panel, and a handle each. The project's own builder."""
    for k in range(count):
        cx0 = x0 + k * width
        box(f"{prefix}_carcass_{k}", cx0, cx0 + width, y0, y0 + depth, 0.0, height, mat)
        box(f"{prefix}_door_{k}", cx0 + 0.04, cx0 + width - 0.04, y0 - 0.06, y0, 0.1, height - 0.1, mat, bevel=0.01)
        cyl(f"{prefix}_handle_{k}", cx0 + width / 2, y0 - 0.1, height - 0.45, height - 0.15, 0.02, handle_mat)
    box(f"{prefix}_top", x0 - 0.05, x0 + count * width + 0.05, y0 - 0.08, y0 + depth + 0.05, height, height + 0.12,
        handle_mat)


def door_leaf(name, x, y, width, swing_deg, mat):
    """A door leaf, 6'-8" tall and 1 3/8" thick, hinged at (x, y) and opened by swing_deg about the hinge."""
    ob = box(name, 0.0, width, -0.057, 0.057, 0.0, 6.667, mat)
    ob.location = (x * FT, y * FT, 0.0)
    ob.rotation_euler = (0.0, 0.0, math.radians(swing_deg))
    return ob


def skylight(name, x0, x1, y0, y1, z, watts):
    """Daylight through the bath skylight: an area light the size of the opening, out of the camera."""
    ld = bpy.data.lights.new(name, "AREA")
    ld.shape = "RECTANGLE"
    ld.size, ld.size_y = (x1 - x0) * FT, (y1 - y0) * FT
    ld.energy = watts
    ob = bpy.data.objects.new(name, ld)
    ob.location = ((x0 + x1) / 2 * FT, (y0 + y1) / 2 * FT, z * FT)
    ob.visible_camera = False
    bpy.context.scene.collection.objects.link(ob)


def report():
    """Print the mesh count and the house's extents in feet, so a run shows what it built."""
    bpy.context.view_layer.update()
    pts = [ob.matrix_world @ Vector(c) for ob in bpy.data.objects if ob.type == "MESH" for c in ob.bound_box]
    lo = [min(p[i] for p in pts) / FT for i in range(3)]
    hi = [max(p[i] for p in pts) / FT for i in range(3)]
    n = sum(1 for ob in bpy.data.objects if ob.type == "MESH")
    print(f"BUILT {n} meshes, extents ft x {lo[0]:.1f}..{hi[0]:.1f}, y {lo[1]:.1f}..{hi[1]:.1f}, z {lo[2]:.1f}..{hi[2]:.1f}")


# ---------------------------------------------------------------- scene
def build(finish):
    floor_m = principled("floor", srgb("#a98e6c"), 0.45)
    wall_m = principled("wall", srgb("#e6e1d6"))
    trim_m = principled("trim", srgb(FINISHES[finish]), 0.6)
    wood_m = principled("wood", srgb(FINISHES["oak"]), 0.5)
    fabric_m = principled("fabric", srgb("#5f6f7a"), 0.95)
    box("floor", -0.5, 30.5, -0.5, 20.5, -0.4, 0.0, floor_m)
    for i, (x0, x1, y0, y1, z0, z1) in enumerate(WALLS):
        box(f"wall_{i}", x0, x1, y0, y1, z0, z1, wall_m)
    # living room
    box("sofa_seat", 1.0, 3.5, 6.0, 12.0, 0.0, 1.4, fabric_m, bevel=0.1)
    box("sofa_back", 0.5, 1.0, 6.0, 12.0, 0.0, 2.8, fabric_m, bevel=0.1)
    box("coffee_top", 6.0, 8.5, 7.5, 10.5, 1.4, 1.55, wood_m, bevel=0.03)
    for k, (lx, ly) in enumerate(((6.2, 7.7), (8.3, 7.7), (6.2, 10.3), (8.3, 10.3))):
        cyl(f"coffee_leg_{k}", lx, ly, 0.0, 1.4, 0.07, wood_m)
    box("tv_unit", 17.0, 17.9, 6.0, 12.0, 0.0, 1.8, wood_m, bevel=0.03)
    box("shelf_floating", 0.2, 1.0, 14.0, 18.0, 0.8, 1.0, trim_m)
    # bedroom
    box("bed_base", 19.5, 26.0, 1.0, 5.5, 0.0, 1.5, wood_m, bevel=0.04)
    box("bed_mattress", 19.6, 25.9, 1.1, 5.4, 1.5, 2.2, fabric_m, bevel=0.1)
    box("wardrobe", 28.5, 29.9, 1.0, 7.0, 0.0, 7.5, trim_m)
    # bath
    box("vanity", 19.0, 21.0, 18.5, 19.8, 0.0, 2.8, trim_m)
    cyl("stool", 25.0, 16.0, 0.0, 1.6, 0.6, wood_m)
    # kitchen run on the living room's north wall, and the doors
    cabinet_run("kitchen", 4.0, 18.0, 5, 2.0, 2.0, 2.9, trim_m, wood_m)
    door_leaf("door_front", 12.0, 0.0, 3.0, -70.0, wood_m)
    door_leaf("door_bedroom", 18.25, 5.0, 3.0, 80.0, wood_m)
    # lights and sun
    for name, (x0, x1, y0, y1) in ROOMS.items():
        area_light(f"L_{name}", x0, x1, y0, y1, WALL_H - 0.05, 24.0 * (x1 - x0) * (y1 - y0) * FT * FT)
    make_sun()
    skylight("skylight_bath", 21.0, 24.0, 14.0, 17.0, WALL_H, 600.0)


def setup_render(samples):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.55, 0.70, 0.95, 1)
    bg.inputs["Strength"].default_value = 1.0
    sc.world = world
    return sc


def add_camera(view, res):
    sc = bpy.context.scene
    sc.render.resolution_x = res
    sc.render.resolution_y = round(res * 0.625)
    sc.render.resolution_percentage = 100
    cam_d = bpy.data.cameras.new("cam")
    cam_d.lens = view["lens"]
    cam_d.clip_start = 0.05
    cam = bpy.data.objects.new("cam", cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    loc = Vector((view["loc"][0] * FT, view["loc"][1] * FT, view["eye"] * FT))
    target = Vector(view["target"]) * FT
    cam.location = loc
    cam.rotation_euler = (target - loc).to_track_quat("-Z", "Y").to_euler()


def render(out):
    out = os.path.abspath(out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sc = bpy.context.scene
    sc.render.filepath = out
    sc.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    print(f"DONE {out}")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--view", choices=sorted(VIEWS), default="living")
    ap.add_argument("--res", type=int, default=800)
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--finish", choices=sorted(FINISHES), default="painted")
    ap.add_argument("--out", default="scratch/house.png")
    args = ap.parse_args(argv)
    clear_scene()
    build(args.finish)
    report()
    setup_render(args.samples)
    add_camera(VIEWS[args.view], args.res)
    render(args.out)


if __name__ == "__main__":
    main()
