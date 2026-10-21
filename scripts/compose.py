"""Compose labelled study sheets from rendered views (PIL).

Usage: uvx --with pillow python -I blender/lib/<LIB>/compose.py OUT.jpg [--title=TEXT] [--width=PX] ITEM ...

ITEM is one of:
  "Label=path.png"   an image with its label; "Label=-" leaves a blank cell with the label
  "|"                ends the current row
  "#Heading"         a section heading on its own line

Without "|" every image goes in one row (the original side-by-side sheet). Each row is scaled so its cells
share the sheet width.
"""
import sys

from PIL import Image, ImageDraw, ImageFont

GAP = 20
BAR = 56


def font(size):
    try:
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
    except OSError:
        return ImageFont.load_default()


def main():
    out, args = sys.argv[1], sys.argv[2:]
    title = next((a.split("=", 1)[1] for a in args if a.startswith("--title=")), None)
    width = next((int(a.split("=", 1)[1]) for a in args if a.startswith("--width=")), None)
    items = [a for a in args if not a.startswith(("--title=", "--width="))]
    blocks, row = [], []                          # ("row", [(label, path)]) or ("head", text)
    for a in items:
        if a == "|":
            if row:
                blocks.append(("row", row))
            row = []
        elif a.startswith("#"):
            if row:
                blocks.append(("row", row))
            row = []
            blocks.append(("head", a[1:].strip()))
        else:
            row.append(tuple(a.split("=", 1)))
    if row:
        blocks.append(("row", row))
    if width is None:                             # original behaviour: 1000 px per cell
        width = max(len(r) for k, r in blocks if k == "row") * (1000 + GAP) - GAP
    f_label, f_head, f_title = font(30), font(40), font(52)

    laid, y = [], 0
    if title:
        laid.append(("title", title, y))
        y += 90
    for kind, b in blocks:
        if kind == "head":
            laid.append(("head", b, y))
            y += 70
            continue
        n = len(b)
        cw = (width - GAP * (n - 1)) // n
        cells, h = [], 0
        for label, path in b:
            im = None
            if path != "-":
                im = Image.open(path).convert("RGB")
                im = im.resize((cw, int(im.height * cw / im.width)))
                h = max(h, im.height)
            cells.append((label, im))
        h = h or int(cw * 2 / 3)
        laid.append(("row", (cells, cw, h), y))
        y += BAR + h + GAP
    sheet = Image.new("RGB", (width, y), "white")
    d = ImageDraw.Draw(sheet)
    for kind, b, y0 in laid:
        if kind == "title":
            d.text((8, y0 + 16), b, fill=(20, 20, 20), font=f_title)
        elif kind == "head":
            d.text((8, y0 + 14), b, fill=(20, 20, 20), font=f_head)
            d.line([(8, y0 + 64), (width - 8, y0 + 64)], fill=(180, 180, 180), width=2)
        else:
            cells, cw, h = b
            for i, (label, im) in enumerate(cells):
                x = i * (cw + GAP)
                d.text((x + 8, y0 + 12), label, fill=(30, 30, 30), font=f_label)
                if im is None:
                    d.rectangle([x, y0 + BAR, x + cw, y0 + BAR + h], fill=(242, 240, 236))
                    d.text((x + 20, y0 + BAR + h // 2 - 15), "not applicable", fill=(140, 140, 140), font=f_label)
                else:
                    sheet.paste(im, (x, y0 + BAR))
    sheet.save(out, quality=90)


if __name__ == "__main__":
    main()
