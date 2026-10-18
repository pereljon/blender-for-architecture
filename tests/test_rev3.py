"""Plain Python test: Revision 3 annotate_plan.py ring radius (T10)."""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tcommon
from tcommon import OUT, SCRIPTS, check, finish

from PIL import Image

W, H = 1000, 800


def ring_radius(width, **callout):
    src = os.path.join(OUT, "rev3_plain.png")
    Image.new("RGB", (W, H), (255, 255, 255)).save(src)
    cfg = os.path.join(OUT, f"rev3_callouts_{width}.json")
    with open(cfg, "w") as fh:
        json.dump({"center": [0, 0], "width": width,
                   "callouts": [dict(x=0, y=0, label="", **callout)]}, fh)
    out = os.path.join(OUT, f"rev3_annotated_{width}.png")
    r = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "annotate_plan.py"), src, out, cfg],
                       capture_output=True, text=True, timeout=120, cwd=OUT)
    check(r.returncode == 0, f"annotate width={width} exit {r.returncode}: {r.stderr[-300:]}")
    if r.returncode:
        return None
    im = Image.open(out).convert("RGB")
    cx, cy = W // 2, H // 2
    xs = [x for y in (cy - 1, cy, cy + 1) for x in range(W)
          if (lambda p: p[0] > 150 and p[1] < 80 and p[2] < 80)(im.getpixel((x, y)))]
    check(bool(xs), f"annotate width={width}: red ring pixels found")
    return cx - min(xs) if xs else None     # leftmost ring pixel on the centre row; the leader runs right


def main():
    a = ring_radius(84.0)
    b = ring_radius(25.6)
    if a is not None and b is not None:
        check(abs(a - b) <= 1, f"T10 same ring radius in pixels for width 84 and 25.6: {a} vs {b}")
        want = 0.014 * max(W, H)
        check(abs(a - want) <= 3, f"T10 default ring radius is 0.014 * max(W, H) = {want:.1f} px, measured {a}")
    # an explicit r stays in project units
    c = ring_radius(50.0, r=2.0)
    d = ring_radius(100.0, r=2.0)
    if c is not None and d is not None:
        check(abs(c - 2.0 * max(W, H) / 50.0) <= 3, f"T10 explicit r=2 at width 50 is {2.0 * max(W, H) / 50.0:.1f} px, measured {c}")
        check(abs(c - 2 * d) <= 3, f"T10 explicit r halves when width doubles: {c} vs {d}")
    finish("test_rev3")


main()
