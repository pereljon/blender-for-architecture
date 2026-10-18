# Construction sheets

Optional module. Sheets for trades (carpentry, plumbing, electrical, tile) are drawn with Pillow from the same numbers as the model, so the sheets and the renders cannot disagree.

## Sources of numbers

- Import the scene script's constants into the sheet generator, or
- Export pieces from the model. The template's `--export-pieces PATH` flag builds the scene, writes every tile piece, and skips rendering.

Never retype a model position into a sheet generator. A hand copy drifts from the model when the geometry changes.

```
/Applications/Blender.app/Contents/MacOS/Blender --factory-startup -b --python-exit-code 1 \
  -P blender/build_bath.py -- --export-pieces scratch/pieces.json
```

Pieces are written in project units. `items_from_pieces(path, unit=U)` reads them back as metres for `pack`; pass the project's metres per unit (0.3048 for feet).

## Drawing a sheet

`sheets.py` holds the drawing kit. A sheet is A3 landscape at about 200 dpi.

```python
from sheets import Sheet, Draw, save_pdf
sh = Sheet("Vanity wall", "Elevation 1:20", 1, 3, "Project / date / revision", page_label="Sheet {} of {}")
d = Draw(sh, ox=300, oy=1900, scale=20)          # origin in sheet pixels, drawing in mm, y up
d.rect(0, 0, 1200, 900)
d.hdim(0, 1200, -60)
sh.save("scratch/sheet1.png")
```

- Pass every label as a parameter, so sheets can be in any language.
- `fmt(v, decimal=",")` writes numbers with the project's decimal separator.
- Split sheets by room and by trade, one generator file per trade.
- Mark each dimension as measured on site or assumed.

## Check before sending

1. Before plumbing or electrical sheets go to a trade, ask the site for a tape-measure photo of the as-built rough-in. Replace assumed positions with the measured ones.
2. Save each sheet as PNG, and read the image.
3. Look for overlapping labels, drawings too big for their scale, and wet and dry sides swapped in sections.
4. Run `check_rounding(values, step)` on owner-facing dimensions, and assert the result is empty.
5. Join the sheets into one PDF with `save_pdf(images, path)`. It takes PIL images or PNG paths.

The owner's rounding rule (for example 5 mm or 10 mm) applies to every dimension the owner reads. Odd numbers such as 1.29 or 249.5 draw questions.

## Tile cutting plans

`pack(items, tw, th, kerf)` packs cut pieces onto stock tiles with guillotine cuts. Items are `dict(id, w, h)` in metres.

```python
from sheets import items_from_pieces, pack
tiles = pack(items_from_pieces("scratch/pieces.json"), tw=1.20, th=0.60, kerf=0.003)
```

Write the cutting-plan sheet generator per project; it draws each stock tile and its pieces with `Draw`. It tries several orderings and keeps the plan with the fewest tiles.

- Give pieces at finished size. The packer adds the saw cut (`kerf`, for example 3 mm) between pieces.
- Full tiles get their own stock tile.
- List spares separately, for breakage and site trimming.
