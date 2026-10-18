"""Plain Python test: extract_plan.py returns walls from a generated vector PDF."""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tcommon
from tcommon import OUT, SCRIPTS, check, finish

import pymupdf

PT = 9.0
ORIGIN = (300.0, 300.0)
FILL = 0.754


def rect_pdf(path, rects, fill):
    doc = pymupdf.open()
    page = doc.new_page(width=800, height=400)
    for r in rects:
        shape = page.new_shape()
        shape.draw_rect(pymupdf.Rect(*r))
        shape.finish(fill=(fill, fill, fill), color=None)
        shape.commit()
    doc.save(path)
    doc.close()


def plan_coords(r):
    x0, y0, x1, y1 = r
    return ((x0 - ORIGIN[0]) / PT, (x1 - ORIGIN[0]) / PT, (ORIGIN[1] - y1) / PT, (ORIGIN[1] - y0) / PT)


def run(name, rects, fill):
    pdf = os.path.join(OUT, f"{name}.pdf")
    rect_pdf(pdf, rects, fill)
    cfg = os.path.join(OUT, f"{name}_config.json")
    with open(cfg, "w") as fh:
        json.dump({"pdf": pdf, "pt_per_unit": PT, "origin": list(ORIGIN), "new_fill": FILL,
                   "sheets": [{"page": 0, "region": [100, 50, 700, 320], "out": f"{name}_walls.json"}]}, fh)
    r = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "extract_plan.py"), cfg], capture_output=True,
                       text=True, timeout=120, cwd=OUT)
    check(r.returncode == 0, f"{name}: extract_plan exit {r.returncode}: {r.stderr[-400:]}")
    out = os.path.join(OUT, f"{name}_walls.json")
    check(os.path.isfile(out), f"{name}: output JSON written next to the config")
    if not os.path.isfile(out):
        return None
    with open(out) as fh:
        return json.load(fh)


def main():
    horiz = (200.0, 200.0, 380.0, 206.0)
    vert = (200.0, 120.0, 206.0, 200.0)
    data = run("extract_new", [horiz, vert], FILL)
    if data:
        check(all(k in data for k in ("walls", "doors", "leaves")), f"JSON has walls, doors, leaves: {list(data)}")
        walls = data["walls"]
        new = [w for w in walls if w["kind"] == "new"]
        check(len(new) >= 2, f"two gray-filled rectangles come back as new walls: {walls}")
        for label, rect in (("horizontal", horiz), ("vertical", vert)):
            x0, x1, y0, y1 = plan_coords(rect)
            ok = any(abs(w["x0"] - x0) < 0.3 and abs(w["x1"] - x1) < 0.3 and abs(w["y0"] - y0) < 0.3
                     and abs(w["y1"] - y1) < 0.3 for w in new)
            check(ok, f"{label} wall found near plan coords {(x0, x1, y0, y1)} (plan units, Y up): {new}")
    other = run("extract_other", [horiz, vert], 0.4)
    if other:
        check(not [w for w in other["walls"] if w["kind"] == "new"], "rectangles of another gray are not new walls")
    finish("test_extract")


main()
