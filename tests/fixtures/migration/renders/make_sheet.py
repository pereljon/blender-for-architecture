"""Sheet generator of the invented house: one A3 cutting sheet, drawn with Pillow. Imports its sibling cuts.py.

Run from the project root, as this project always has:
  python3 renders/make_sheet.py scratch/cutting_sheet.png
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

from cuts import KERF, STOCK, place_pieces

PAGE = (3300, 2340)             # px: the sheet size this project has always drawn
S = PAGE[0] / 420               # px per mm of paper
INK = (25, 25, 25)


def main(out):
    img = Image.new("RGB", PAGE, "white")
    d = ImageDraw.Draw(img)
    f = ImageFont.load_default(size=42)
    d.rectangle((60, 60, PAGE[0] - 60, PAGE[1] - 60), outline=INK, width=6)
    d.text((120, 110), f"Kitchen top: cutting plan on one {STOCK[0]} x {STOCK[1]} mm board, kerf {KERF} mm", font=f, fill=INK)
    scale = 0.9 * S / 4                              # drawing at 1:4 of the board's millimetres
    ox, oy = 160, 300
    d.rectangle((ox, oy, ox + STOCK[0] * scale, oy + STOCK[1] * scale), outline=INK, width=4)
    for name, x, y, w, h in place_pieces():
        box = (ox + x * scale, oy + y * scale, ox + (x + w) * scale, oy + (y + h) * scale)
        d.rectangle(box, outline=INK, width=3, fill=(235, 230, 215))
        d.text((box[0] + 20, box[1] + 20), f"{name}  {w} x {h}", font=f, fill=INK)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    img.save(out)
    print(f"DONE {out}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "scratch/cutting_sheet.png")
