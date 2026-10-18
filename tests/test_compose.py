"""Plain Python test: compose.py and annotate_plan.py on the smoke renders."""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tcommon
from tcommon import OUT, SCRIPTS, check, finish

from PIL import Image


def run(script, *args):
    return subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, script), *args], capture_output=True, text=True,
                          timeout=120, cwd=OUT)


def main():
    persp = os.path.join(OUT, "render_persp.png")
    plan = os.path.join(OUT, "render_plan.png")
    for p in (persp, plan):
        check(os.path.isfile(p), f"smoke render present: {p} (run the render step first)")
    if tcommon.FAILURES:
        finish("test_compose")

    # compose: one row, explicit width
    one = os.path.join(OUT, "compose_one.jpg")
    r = run("compose.py", one, "--title=Study", "--width=800", f"Persp={persp}", f"Plan={plan}")
    check(r.returncode == 0, f"compose one row exit {r.returncode}: {r.stderr[-300:]}")
    im1 = Image.open(one)
    check(im1.width == 800 and im1.height > 100, f"compose --width honoured: {im1.size}")

    # compose: rows, heading, blank cell
    many = os.path.join(OUT, "compose_rows.jpg")
    r = run("compose.py", many, "--width=800", "#Section", f"Persp={persp}", f"Plan={plan}", "|", "Blank=-", f"Plan2={plan}")
    check(r.returncode == 0, f"compose rows exit {r.returncode}: {r.stderr[-300:]}")
    im2 = Image.open(many)
    check(im2.width == 800 and im2.height > im1.height, f"compose rows are taller than one row: {im2.size} vs {im1.size}")

    # compose: default width is per cell
    dflt = os.path.join(OUT, "compose_default.jpg")
    r = run("compose.py", dflt, f"A={persp}", f"B={plan}")
    check(r.returncode == 0 and Image.open(dflt).width > 800, "compose without --width makes a wide sheet")

    # annotate
    cfg = os.path.join(OUT, "callouts.json")
    with open(cfg, "w") as fh:
        json.dump({"center": [6, 5], "width": 14.0,
                   "callouts": [{"x": 6, "y": 5, "label": "Centre point", "r": 1.2},
                                {"x": 12.8, "y": 9.0, "label": "A long label near the right edge", "above": True}]}, fh)
    out = os.path.join(OUT, "annotated.png")
    r = run("annotate_plan.py", plan, out, cfg)
    check(r.returncode == 0, f"annotate exit {r.returncode}: {r.stderr[-300:]}")
    src, dst = Image.open(plan).convert("RGB"), Image.open(out).convert("RGB")
    check(src.size == dst.size, f"annotated image keeps its size: {dst.size}")
    k = src.width / 14.0
    x_ring = int(src.width / 2 + 1.2 * k)
    y_mid = src.height // 2
    ring = [dst.getpixel((x, y_mid)) for x in range(x_ring - 3, x_ring + 4)]
    check(any(p[0] > 180 and p[1] < 80 and p[2] < 80 for p in ring), f"red callout circle drawn at the plan point: {ring}")
    check(src.tobytes() != dst.tobytes(), "annotation changes the image")

    # T4: portrait image, pixels per unit follow the larger side (the plan view's width spans it)
    port = os.path.join(OUT, "portrait_plan.png")
    Image.new("RGB", (120, 240), (255, 255, 255)).save(port)
    cfg2 = os.path.join(OUT, "callouts_portrait.json")
    with open(cfg2, "w") as fh:
        json.dump({"center": [0, 0], "width": 12.0, "callouts": [{"x": 1, "y": 2, "label": "P", "r": 1.0}]}, fh)
    out2 = os.path.join(OUT, "annotated_portrait.png")
    r = run("annotate_plan.py", port, out2, cfg2)
    check(r.returncode == 0, f"portrait annotate exit {r.returncode}: {r.stderr[-300:]}")
    if r.returncode == 0:
        im = Image.open(out2).convert("RGB")
        k = 240 / 12.0
        cx, cy = 60 + 1 * k, 120 - 2 * k
        top = [im.getpixel((int(cx), int(cy - k) + d)) for d in range(-3, 4)]
        check(any(p[0] > 180 and p[1] < 80 and p[2] < 80 for p in top), f"T4 portrait ring top at ({cx:.0f},{cy - k:.0f}): {top}")
    finish("test_compose")


main()
