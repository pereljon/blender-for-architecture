"""Blender test: a small scene with every procedural material renders both a perspective and a plan view."""
import contextlib
import io
import os

import bpy

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # Blender -P does not add the script folder
import tcommon
from tcommon import OUT, check, finish

import bhelpers as bh


def render_view(name, view):
    scene = bpy.context.scene
    bh.add_camera(view, 160)
    path = os.path.join(OUT, f"{name}.png")
    if os.path.exists(path):
        os.remove(path)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        bh.render(path)
    print(buf.getvalue(), end="")  # the runner also looks for the DONE line in the log
    check(f"DONE {path}" in buf.getvalue().splitlines(), f"{name}: render prints exactly 'DONE <out>': {buf.getvalue()!r}")
    check(os.path.isfile(path) and os.path.getsize(path) > 0, f"{name}: image written")
    img = bpy.data.images.load(path)
    check(tuple(img.size) == (scene.render.resolution_x, scene.render.resolution_y), f"{name}: size {tuple(img.size)}")
    return tuple(img.size)


def main():
    bh.set_units("ft")
    bh.clear_scene()
    src = os.path.join(OUT, "tile_src.png")
    im = bpy.data.images.new("tile_src", 8, 8)
    im.filepath_raw = src
    im.file_format = "PNG"
    im.save()
    mats = [bh.stone_tile("m_stone", (0.6, 0.6, 0.6)), bh.planks("m_planks", (0.5, 0.35, 0.2)),
            bh.wood_material("m_wood"), bh.fabric("m_fabric", (0.5, 0.2, 0.2)),
            bh.image_tile_material("m_img", src, mult=(1, 1, 1), rough=0.5, bump=0.1),
            bh.projected_tile_material("m_proj", src, 2.0), bh.emission("m_em", (1, 1, 1), 5.0),
            bh.principled("m_pm", (0.7, 0.7, 0.7), 0.5)]
    bh.box("floor", 0, 12, 0, 10, -0.1, 0, mats[1])
    for i, m in enumerate(mats):
        bh.box(f"obj_{i}", 1 + i * 1.2, 1.8 + i * 1.2, 4, 4.8, 0, 1.5, m)
    bh.room_fill_lights({"main": (0, 12, 0, 10)}, 9.0)
    bh.setup_cycles(8, gpu=False)
    s1 = render_view("render_persp", dict(loc=(6, -8, 5), target=(6, 5, 1.5), lens=24, aspect=0.625))
    check(s1 == (160, 100), f"perspective output 160x100, got {s1}")
    s2 = render_view("render_plan", dict(plan=True, center=(6, 5), width=14, cut=4.0, aspect=1.0))
    check(s2 == (160, 160), f"plan output 160x160, got {s2}")
    finish("bl_render")


main()
