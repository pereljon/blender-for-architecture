"""check_png.py PATH WIDTH: exit 0 when PATH is a PNG of the given width, a positive height and a mean brightness in 0.05..0.98."""
import sys

from PIL import Image, ImageStat

im = Image.open(sys.argv[1])
im.load()
mean = sum(ImageStat.Stat(im.convert("L")).mean) / 255.0
ok = im.format == "PNG" and im.width == int(sys.argv[2]) and im.height > 0 and 0.05 <= mean <= 0.98
print(f"{sys.argv[1]}: {im.format} {im.size} mean brightness {mean:.3f}")
sys.exit(0 if ok else 1)
