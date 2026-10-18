"""Plain Python test: sheets.py (fonts, fmt, Sheet, Draw, pack, save_pdf, check_rounding, self-test)."""
import json
import os
import random
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tcommon
from tcommon import OUT, SCRIPTS, check, close, finish

import sheets
from PIL import ImageFont


def overlaps(a, b):
    return a[1] < b[1] + b[3] and b[1] < a[1] + a[3] and a[2] < b[2] + b[4] and b[2] < a[2] + a[4]


def separation(a, b):
    """Gap between two placements (item, x, y, w, h) along the axis where they are apart (max over axes)."""
    gx = max(a[1] - (b[1] + b[3]), b[1] - (a[1] + a[3]))
    gy = max(a[2] - (b[2] + b[4]), b[2] - (a[2] + a[4]))
    return max(gx, gy)


def check_plan(plan, items, tw, th, kerf, label):
    placed = [p for tile in plan for p in tile]
    check(sorted(p[0]["id"] for p in placed) == sorted(i["id"] for i in items), f"{label}: every piece placed once")
    for tile in plan:
        for it, x, y, w, h in tile:
            check(x >= -1e-9 and y >= -1e-9 and x + w <= tw + 1e-9 and y + h <= th + 1e-9,
                  f"{label}: {it['id']} inside the tile ({x:.3f},{y:.3f},{w:.3f},{h:.3f})")
            check(sorted((round(w, 6), round(h, 6))) == sorted((round(it["w"], 6), round(it["h"], 6))),
                  f"{label}: {it['id']} keeps its size (rotation allowed)")
        for i, a in enumerate(tile):
            for b in tile[i + 1:]:
                check(not overlaps(a, b), f"{label}: {a[0]['id']} overlaps {b[0]['id']}")
                check(separation(a, b) >= kerf - 1e-9,
                      f"{label}: gap {separation(a, b):.5f} between {a[0]['id']} and {b[0]['id']} below kerf {kerf}")


def main():
    # constants and fonts
    check(len(sheets.PAGE) == 2 and sheets.S > 0 and len(sheets.INK) == 3 and len(sheets.DIM) == 3, "constants exist")
    for size, bold in ((20, False), (20, True), (33, False)):
        f = sheets.font(size, bold)
        check(f.getlength("Ag") > 0, f"font({size},{bold}) measures text")
    real = ImageFont.truetype

    def broken(font=None, *a, **k):
        if isinstance(font, str):  # a missing system font; Pillow's own default loads from bytes
            raise OSError("no font")
        return real(font, *a, **k)

    ImageFont.truetype = broken
    try:
        f = sheets.font(41, True)
        check(f.getlength("Ag") > 0, "font falls back to a default when no TrueType font opens")
    except Exception as e:
        check(False, f"font raised with missing fonts: {e!r}")
    finally:
        ImageFont.truetype = real

    # fmt
    check(sheets.fmt(1.5) == "1,5", f"fmt(1.5) {sheets.fmt(1.5)!r}")
    check(sheets.fmt(2.0) == "2", f"fmt(2.0) drops the trailing ,0: {sheets.fmt(2.0)!r}")
    check(sheets.fmt(1.5, decimal=".") == "1.5" and sheets.fmt(2.0, decimal=".") == "2", "fmt with a dot decimal")
    check(sheets.mm is sheets.fmt or sheets.mm(1.5) == "1,5", "mm alias of fmt")

    # Sheet and Draw
    sh = sheets.Sheet("Title", "Subtitle", 1, 3, "Footer", page_label="Page {} of {}")
    check(sh.img.size == tuple(sheets.PAGE), "Sheet image is PAGE size")
    sh.text((100, 300), "hello")
    dr = sheets.Draw(sh, 400, 1200, 20)
    p = dr.P(0, 0)
    q = dr.P(100, 50)
    check(close(p[0], 400) and close(p[1], 1200), "Draw.P origin")
    check(close(q[0], 400 + 100 * sheets.S / 20, 1e-6) and close(q[1], 1200 - 50 * sheets.S / 20, 1e-6), "Draw.P scale, y up")
    dr.rect(0, 0, 100, 50, fill=(200, 200, 255))
    px = sh.img.getpixel(tuple(int(c) for c in dr.P(50, 25)))
    check(px == (200, 200, 255), f"rect fill drawn inside the rectangle, pixel {px}")
    dr.line([(0, 0), (100, 50)], dash=True)
    dr.line([(0, 50), (100, 0)])
    dr.text(50, 25, "label")
    dr.hdim(0, 100, -10)
    dr.hdim(0, 100, -20, txt="x", off=20)
    dr.vdim(-10, 0, 50)
    dr.vdim(110, 0, 50, txt="y", side="r")
    sh_path = os.path.join(OUT, "sheet_test.png")
    sh2 = sheets.Sheet("T2", "S2", 2, 3, "F")
    sh.img.save(sh_path)
    check(os.path.getsize(sh_path) > 0, "sheet saved")

    pdf = os.path.join(OUT, "sheets_test.pdf")
    if os.path.exists(pdf):
        os.remove(pdf)
    sheets.save_pdf([sh.img, sh2.img], pdf, resolution=100)
    with open(pdf, "rb") as fh:
        data = fh.read()
    check(data.startswith(b"%PDF") and b"/Count 2" in data, "save_pdf writes a 2-page PDF")

    # save_pdf accepts file paths, alone and mixed with images
    paths = []
    for k, im in enumerate((sh.img, sh2.img, sh.img)):
        pth = os.path.join(OUT, f"sheet_path_{k}.png")
        im.save(pth)
        paths.append(pth)
    pdf2 = os.path.join(OUT, "sheets_paths.pdf")
    if os.path.exists(pdf2):
        os.remove(pdf2)
    try:
        sheets.save_pdf(paths, pdf2, resolution=100)
        with open(pdf2, "rb") as fh:
            data = fh.read()
        check(data.startswith(b"%PDF") and b"/Count 3" in data, "T4 save_pdf writes a 3-page PDF from file paths")
    except Exception as e:
        check(False, f"T4 save_pdf with file paths raised {e!r}")
    pdf3 = os.path.join(OUT, "sheets_mixed.pdf")
    if os.path.exists(pdf3):
        os.remove(pdf3)
    try:
        sheets.save_pdf([paths[0], sh2.img], pdf3, resolution=100)
        with open(pdf3, "rb") as fh:
            data = fh.read()
        check(data.startswith(b"%PDF") and b"/Count 2" in data, "T4 save_pdf accepts paths mixed with images")
    except Exception as e:
        check(False, f"T4 save_pdf with mixed input raised {e!r}")

    # items_from_pieces: export_pieces JSON (feet) to metres
    pj = os.path.join(OUT, "pieces_feet_test.json")
    with open(pj, "w") as fh:
        json.dump({"pieces": [dict(name="wt_a_0_0_0", poly=[[0, 0], [2, 0], [2, 1], [0, 1]], rot=False),
                              dict(name="wt_a_1_0_0", poly=[[2, 0], [4, 0], [4, 1], [3, 1.5]], rot=True)]}, fh)
    try:
        its = sheets.items_from_pieces(pj, unit=0.3048)
        check(len(its) == 2 and all(set(("id", "w", "h")) <= set(i) for i in its), f"T4 items_from_pieces gives id, w, h: {its}")
        check(close(its[0]["w"], 2 * 0.3048, 1e-9) and close(its[0]["h"], 1 * 0.3048, 1e-9),
              f"T4 items_from_pieces feet export gives metres: {its[0]}")
        check(close(its[1]["w"], 2 * 0.3048, 1e-9) and close(its[1]["h"], 1.5 * 0.3048, 1e-9),
              f"T4 items_from_pieces uses the polygon bounding box: {its[1]}")
        check(its[0]["id"] == "wt_a_0_0_0" and its[0]["id"] != its[1]["id"], "T4 items_from_pieces ids come from the piece names")
        its_m = sheets.items_from_pieces(pj)
        check(close(its_m[0]["w"], 2.0, 1e-9), "T4 items_from_pieces default unit is 1.0")
        plan_ = sheets.pack(its)
        check_plan(plan_, its, 1.20, 0.60, 0.003, "items_from_pieces output")
    except Exception as e:
        check(False, f"T4 items_from_pieces raised {e!r}")

    # check_rounding
    check(sheets.check_rounding([0.05, 0.10, 0.15, 0.30000000000000004], 0.05) == [], "multiples of 0.05 pass")
    bad = sheets.check_rounding([0.05, 0.123, 0.20], 0.05)
    check(bad == [0.123], f"non-multiple flagged: {bad}")
    check(sheets.check_rounding([5, 10, 12], 5) == [12], "integer step")
    check(sheets.check_rounding([], 5) == [], "empty input")

    # pack
    items = [dict(id="a", w=0.80, h=0.60), dict(id="b", w=0.327, h=0.60), dict(id="c", w=1.20, h=0.60)]
    plan = sheets.pack(items)
    check_plan(plan, items, 1.20, 0.60, 0.003, "self-test items")
    check(len(plan) == 2, f"a+b share one tile, c takes its own: {len(plan)} tiles")
    tile_of = {p[0]["id"]: k for k, t in enumerate(plan) for p in t}
    check(tile_of["a"] == tile_of["b"] and tile_of["c"] != tile_of["a"], "full-size piece alone on its tile")
    # 0.60 + kerf + 0.60 exceeds the 1.20 tile width
    tight = [dict(id="p", w=0.60, h=0.60), dict(id="q", w=0.60, h=0.60)]
    plan = sheets.pack(tight, kerf=0.003)
    check(len(plan) == 2, f"two 0.60 pieces need two tiles once the kerf is lost: {len(plan)}")
    check_plan(plan, tight, 1.20, 0.60, 0.003, "tight")
    rng = random.Random(7)
    for trial, kerf in enumerate((0.003, 0.01, 0.0)):
        its = [dict(id=f"i{k}", w=round(rng.uniform(0.05, 0.9), 3), h=round(rng.uniform(0.05, 0.55), 3)) for k in range(30)]
        plan = sheets.pack(its, kerf=kerf)
        check_plan(plan, its, 1.20, 0.60, kerf, f"random{trial} kerf={kerf}")
    its = [dict(id=f"j{k}", w=0.4, h=0.3) for k in range(6)]
    plan = sheets.pack(its, tw=0.9, th=0.7, kerf=0.005)
    check_plan(plan, its, 0.9, 0.7, 0.005, "custom tile")

    # self-test entry point
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "sheets.py")], capture_output=True, text=True,
                       timeout=120, env=env, cwd=OUT)
    check(r.returncode == 0 and "PACK" in r.stdout, f"sheets.py self-test exit {r.returncode}: {r.stdout!r} {r.stderr[-300:]!r}")
    finish("test_sheets")


main()
