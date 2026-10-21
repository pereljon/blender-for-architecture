"""Draw circled callouts on an ortho plan render (PIL post-pass).

Usage: uvx --with pillow python -I blender/lib/<LIB>/annotate_plan.py IN.png OUT.png CALLOUTS.json

CALLOUTS.json gives the plan camera's framing (the same centre and width as the plan view, in project units) and
the callouts in plan coordinates. width is the plan view's width: the ortho span of the image's larger side.
  {"center": [15.5, 12.4], "width": 84.0,
   "callouts": [{"x": 43.3, "y": 7.0, "label": "Existing post in new glass", "above": false, "r": 1.2}]}
"above" puts the label above the point instead of below it. "r" is the circle radius in project units; by default the
radius is 0.014 of the image's larger side in pixels. Label and leader offsets scale with the radius.
Labels are clamped inside the image.
"""
import json
import sys

from PIL import Image, ImageDraw, ImageFont


def font(size):
    try:
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
    except OSError:
        return ImageFont.load_default()


def main():
    im = Image.open(sys.argv[1]).convert("RGB")
    with open(sys.argv[3]) as fh:
        cfg = json.load(fh)
    W, H = im.size
    k = max(W, H) / cfg["width"]                                 # pixels per project unit, as Blender's ortho_scale
    cx0, cy0 = cfg["center"]

    def px(x, y):
        return (W / 2 + (x - cx0) * k, H / 2 - (y - cy0) * k)    # image y runs down, plan y runs up

    d = ImageDraw.Draw(im)
    f = font(max(12, int(W / 105)))
    for c in cfg["callouts"]:
        cx, cy = px(c["x"], c["y"])
        r = c["r"] * k if "r" in c else 0.014 * max(W, H)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(220, 0, 0), width=max(3, int(W / 600)))
        tx = cx + 1.33 * r
        ty = cy - (1.33 * r if c.get("above") else 0.42 * r)
        d.line([cx + r * 0.7, cy, tx, ty + 0.33 * r], fill=(220, 0, 0), width=max(2, int(W / 900)))
        tw = d.textlength(c["label"], font=f)
        tx = min(tx, W - tw - 12)                                # keep the label inside the image
        ty = max(4, min(ty, H - f.size - 10))
        d.rectangle([tx - 4, ty - 4, tx + tw + 4, ty + f.size + 6], fill=(255, 255, 255))
        d.text((tx, ty), c["label"], fill=(200, 0, 0), font=f)
    im.save(sys.argv[2])


if __name__ == "__main__":
    main()
