"""Drawing sheets and cut-piece packing (Pillow, plain Python; not for Blender).

Run with: uvx --with pillow python -I blender/lib/<LIB>/sheets.py   (self-test of the packing)
Units: millimetres on sheets, metres for packed pieces.
"""
import json
import math
import os

FONTS = ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
         "/System/Library/Fonts/Helvetica.ttc")
DPI = 200
PAPERS = {"letter": (279.4, 215.9), "tabloid": (431.8, 279.4), "arch-c": (609.6, 457.2),
          "arch-d": (914.4, 609.6), "a4": (297, 210), "a3": (420, 297)}   # landscape mm
PAGE = (3400, 2200)                 # set by set_paper: sheet size in px
S = PAGE[0] / 431.8                 # set by set_paper: px per mm at 1:1; a drawing at 1:n uses S / n
INK, DIM = (25, 25, 25), (60, 60, 60)
_fonts = {}


def set_paper(name):
    """Set the sheet size by name from PAPERS (case-insensitive); returns PAGE. Call before creating a Sheet."""
    global PAGE, S
    key = str(name).lower()
    if key not in PAPERS:
        raise ValueError(f"unknown paper {name!r}; choose one of {', '.join(PAPERS)}")
    w, h = PAPERS[key]
    PAGE = (round(w * DPI / 25.4), round(h * DPI / 25.4))
    S = PAGE[0] / w
    return PAGE


set_paper("tabloid")


def font(size, bold=False):
    """Cached font: Arial (Arial Bold when bold), then Helvetica, then the Pillow default; never raises."""
    from PIL import ImageFont
    key = (size, bold)
    if key not in _fonts:
        order = (FONTS[1], FONTS[0], FONTS[2]) if bold else (FONTS[0], FONTS[2])
        for path in order:
            try:
                _fonts[key] = ImageFont.truetype(path, size)
                break
            except OSError:
                pass
        else:
            _fonts[key] = ImageFont.load_default(size=size)
    return _fonts[key]


def fmt(v, decimal=","):
    """Number to a string with one decimal and no trailing zero decimal; decimal is the separator."""
    s = f"{v:.1f}".replace(".", decimal)
    return s[:-2] if s.endswith(decimal + "0") else s


mm = fmt


def check_rounding(values, step):
    """Values that are not multiples of step (relative tolerance 1e-9). Sheet generators assert this is empty."""
    return [v for v in values if not math.isclose(v, round(v / step) * step, rel_tol=1e-9, abs_tol=1e-12)]


class Sheet:
    """Sheet of the current paper size (PAGE) with title, subtitle, page number and footer. Labels are parameters so any language works.

    Save each sheet as PNG, look at it for overlapping labels, then join the PNGs with save_pdf.
    """

    def __init__(self, title, subtitle, page_no, total, footer, page_label="Sheet {} of {}"):
        from PIL import Image, ImageDraw
        self.img = Image.new("RGB", PAGE, "white")
        self.d = ImageDraw.Draw(self.img)
        self.d.text((80, 50), title, font=font(64, True), fill="black")
        self.d.text((80, 135), subtitle, font=font(36), fill=(70, 70, 70))
        self.d.text((PAGE[0] - 80, 60), page_label.format(page_no, total), font=font(36, True), fill="black", anchor="ra")
        self.d.line((80, 195, PAGE[0] - 80, 195), fill="black", width=3)
        self.d.text((80, PAGE[1] - 60), footer, font=font(26), fill=(90, 90, 90))

    def text(self, xy, s, size=30, bold=False, fill="black", anchor="la"):
        self.d.text(xy, s, font=font(size, bold), fill=fill, anchor=anchor)

    def paragraph(self, x, y, lines, size=34, width=None, gap=12):
        """Word-wrapped notes; a line starting with ** is bold. Returns the next y."""
        for ln in lines:
            bold = ln.startswith("**")
            ln = ln.strip("*")
            cur = ""
            for w in ln.split(" "):
                trial = (cur + " " + w).strip()
                if width and self.d.textlength(trial, font=font(size, bold)) > width:
                    self.text((x, y), cur, size, bold)
                    y += size + gap
                    cur = "   " + w
                else:
                    cur = trial
            self.text((x, y), cur, size, bold)
            y += size + gap
        return y

    def save(self, path):
        self.img.save(path)


class Draw:
    """A scaled drawing on a Sheet: origin at sheet pixel (ox, oy), coordinates in mm, y up. scale 20 = 1:20."""

    def __init__(self, sh, ox, oy, scale):
        self.sh, self.d, self.ox, self.oy, self.k = sh, sh.d, ox, oy, S / scale

    def P(self, x, y):
        return (self.ox + x * self.k, self.oy - y * self.k)

    def rect(self, x0, y0, x1, y1, fill=None, outline=INK, width=3):
        a, b = self.P(x0, y1), self.P(x1, y0)
        self.d.rectangle((a[0], a[1], b[0], b[1]), fill=fill, outline=outline, width=width)

    def line(self, pts, fill=INK, width=2, dash=False):
        """Polyline in mm; dash=True for hidden or removed lines."""
        q = [self.P(x, y) for x, y in pts]
        for a, b in zip(q, q[1:]):
            if not dash:
                self.d.line((a, b), fill=fill, width=width)
                continue
            L, t = math.dist(a, b), 0.0
            while t < L:
                t1 = min(L, t + 14)
                self.d.line((a[0] + (b[0] - a[0]) * t / L, a[1] + (b[1] - a[1]) * t / L,
                             a[0] + (b[0] - a[0]) * t1 / L, a[1] + (b[1] - a[1]) * t1 / L), fill=fill, width=width)
                t = t1 + 9

    def text(self, x, y, s, size=24, bold=False, fill=INK, anchor="mm"):
        self.sh.text(self.P(x, y), s, size, bold, fill, anchor)

    def hdim(self, x0, x1, y, txt=None, off=0, size=24):
        """Horizontal dimension line with architectural ticks at height y (mm), shifted down by off px."""
        a, b = self.P(x0, y), self.P(x1, y)
        yy = a[1] + off
        self.d.line((a[0], yy, b[0], yy), fill=DIM, width=2)
        for x in (a[0], b[0]):
            self.d.line((x, yy - 10, x, yy + 10), fill=DIM, width=2)
            self.d.line((x - 6, yy + 6, x + 6, yy - 6), fill=DIM, width=3)
        self.sh.text(((a[0] + b[0]) / 2, yy - 6), txt or fmt(x1 - x0), size, False, DIM, "mb")

    def vdim(self, x, y0, y1, txt=None, off=0, size=24, side="l"):
        """Vertical dimension line at x (mm), shifted by off px; text left (side='l') or right ('r')."""
        a, b = self.P(x, y0), self.P(x, y1)
        xx = a[0] + off
        self.d.line((xx, a[1], xx, b[1]), fill=DIM, width=2)
        for y in (a[1], b[1]):
            self.d.line((xx - 10, y, xx + 10, y), fill=DIM, width=2)
            self.d.line((xx - 6, y + 6, xx + 6, y - 6), fill=DIM, width=3)
        self.sh.text((xx - 10 if side == "l" else xx + 10, (a[1] + b[1]) / 2), txt or fmt(y1 - y0), size, False, DIM,
                     "rm" if side == "l" else "lm")


def save_pdf(images, path, resolution=200):
    """Join page images, PIL images or PNG file paths, into one multi-page PDF."""
    from PIL import Image
    images = [Image.open(i).convert("RGB") if isinstance(i, (str, os.PathLike)) else i for i in images]
    images[0].save(path, save_all=True, append_images=images[1:], resolution=resolution)


def items_from_pieces(path, unit=1.0):
    """Pieces from an export_pieces JSON as pack() items dict(id, w, h) in metres; unit is metres per project unit."""
    with open(path) as fh:
        pieces = json.load(fh)["pieces"]
    out = []
    for p in pieces:
        us, vs = zip(*p["poly"])
        out.append(dict(id=p["name"], w=(max(us) - min(us)) * unit, h=(max(vs) - min(vs)) * unit))
    return out


# ------------------------------------------------------------ guillotine packing of cut pieces onto stock tiles
def _pack_once(items, tw, th, kerf, order, fit, split):
    """One greedy guillotine pass; full-size pieces get their own tile. Returns [[(item, x, y, w, h), ...], ...]."""
    placas, free = [], []

    def is_full(it):
        return abs(max(it["w"], it["h"]) - tw) < 1e-3 and abs(min(it["w"], it["h"]) - th) < 1e-3

    for it in [i for i in items if is_full(i)]:
        placas.append([(it, 0, 0, tw, th)])
    for it in sorted([i for i in items if not is_full(i)], key=order):
        best = None
        for k, (pi, x, y, w, h) in enumerate(free):
            for pw, ph in ((it["w"], it["h"]), (it["h"], it["w"])):
                if pw <= w + 1e-9 and ph <= h + 1e-9:
                    score = (w * h - pw * ph) if fit == "area" else min(w - pw, h - ph)
                    if best is None or score < best[0]:
                        best = (score, k, pw, ph)
        if best is None:
            placas.append([])
            free.append((len(placas) - 1, 0.0, 0.0, tw, th))
            pw, ph = (it["w"], it["h"]) if it["w"] >= it["h"] else (it["h"], it["w"])
            best = (0, len(free) - 1, pw, ph)
        _, k, pw, ph = best
        pi, x, y, w, h = free.pop(k)
        placas[pi].append((it, x, y, pw, ph))
        rw, rh = w - pw - kerf, h - ph - kerf          # the saw cut is lost between a piece and its offcut
        horiz = (rw * h > w * rh) if split == "area" else ((w - pw) < (h - ph) if split == "short" else (w - pw) >= (h - ph))
        if horiz:
            if rw > 0.01:
                free.append((pi, x + pw + kerf, y, rw, h))
            if rh > 0.01:
                free.append((pi, x, y + ph + kerf, pw, rh))
        else:
            if rh > 0.01:
                free.append((pi, x, y + ph + kerf, w, rh))
            if rw > 0.01:
                free.append((pi, x + pw + kerf, y, rw, ph))
    return placas


def pack(items, tw=1.20, th=0.60, kerf=0.003):
    """Pack pieces dict(id, w, h) (finished size, metres) onto tw x th stock with a kerf saw cut between pieces.

    Tries several orderings and split rules and keeps the plan with the fewest tiles (ties: fuller tiles).
    Count spares separately (breakage, site trimming); pieces carry no trim allowance.
    """
    orders = [lambda i: (-max(i["w"], i["h"]), -i["w"] * i["h"]), lambda i: -i["w"] * i["h"],
              lambda i: (-min(i["w"], i["h"]), -max(i["w"], i["h"])), lambda i: (-i["h"], -i["w"])]
    if not items:
        return []
    best = None
    for order in orders:
        for fit in ("area", "short"):
            for split in ("area", "short", "long"):
                pl = _pack_once(items, tw, th, kerf, order, fit, split)
                key = (len(pl), -max(sum(p[3] * p[4] for p in placa) for placa in pl))
                if best is None or key < best[0]:
                    best = (key, pl)
    return best[1]


if __name__ == "__main__":
    items = [dict(id="a", w=0.80, h=0.60), dict(id="b", w=0.327, h=0.60), dict(id="c", w=1.20, h=0.60)]
    print("PACK", [[(p[0]["id"], round(p[1], 3)) for p in pl] for pl in pack(items)])
