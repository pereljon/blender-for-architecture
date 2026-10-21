# Plan input

Two routes bring the plan into the scene script. Choose one per drawing set.

- **Route A, PDF extraction:** the architect's plan PDF has vector linework. `extract_plan.py` turns it into walls JSON in project units.
- **Route B, hand-entered coordinates:** the plan is a scan, or the scene is small. Enter coordinates from the plans and `context/dimensions.md` into the script's constants block.

## Route A: extract from a PDF

1. Copy `plan_config.example.json` next to the script. Set `pdf`, `pt_per_unit`, and `origin`, and give each entry in `sheets` its `region` and `out`.
2. List `page.get_drawings()` for a small area that holds known walls, doors, and posts.
3. Read their fill, stroke color, and stroke width. Set `new_fill`, `existing_width`, `swing_width`, and `leaf_width` from them.
4. Run `uvx --with pymupdf python -I lib/extract_plan.py plan_config.json`.
5. Render a plan view and compare it with the sheet. Fix differences in the correction layer, never in the JSON.
6. Run the extraction again whenever a new plan set arrives.

At 1/8" = 1'-0", `pt_per_unit` is 9.0 points per foot. Every office draws walls differently, so tune the thresholds per drawing set.

### What extraction misses

- Angled walls and some outside walls. Add them in `EXTRA_WALLS`, or as `seg()` calls for angled walls.
- Short wall pieces where one wall meets another. Check each junction, and add a missing piece in the correction block.
- Stray pieces in doorways and jamb fragments. The config's `min_piece` drops most of them; `cut_openings` trims the rest.

### The correction layer

Keep every hand correction in three named lists in the scene script. Give each entry a dated comment that names its source: owner markup, a site measurement, or a newer sheet.

```python
# Rectangles are (x0, x1, y0, y1) in project units.
WALL_FIXES = [((12.0, 18.5, 4.1, 4.5), (4.0, 4.4))]   # 2026-05-02 site: false jog in sheet A2
WALL_REPLACE = [((30.2, 31.0, 9.0, 12.4), None)]       # 2026-05-10 owner: wall opened
EXTRA_WALLS = [("new", 40.0, 40.5, 0.0, 6.0)]          # 2026-05-02 missed by extraction
```

Apply them in this order:

```python
walls, doors, leaves = load_plan("plan_walls.json")
walls = fix_walls(walls, WALL_FIXES, WALL_REPLACE) + extra_walls(EXTRA_WALLS)
walls = cut_openings(walls, OPENINGS)
walls_from_plan(walls, 0.0, CEIL, wall_mat)
```

After you apply the correction layer, run `wall_gaps(walls, unit=<metres per unit>)` on the corrected list. Fix each hit before you build the walls.

When you shift walls to match site measurements, shift the door swings and leaves in the same region. Otherwise the leaves are trimmed away as if inside a wall.

`extra_walls` turns the `EXTRA_WALLS` tuples into the same wall records that `load_plan` returns.

### Several sheets

- Give each sheet its own entry in the config's `sheets`, with a shift that registers it onto the first sheet.
- Find the shift from a feature drawn on both sheets, such as a lot-line post.
- Never reuse one source's offset for a drawing from another source. A uniform shift misplaced items in practice.

## Route B: hand-entered coordinates

- Put every coordinate in the constants block, in one frame. Record the origin and axis directions in the dimensions file.
- Enter each dimension from the plan or a site measurement, and mark which in the dimensions file.
- Use `box`, `seg`, and `prism` for walls; `slab` for sloped or shaped floors and counters.

## State the accuracy

- State the plan accuracy in deliverables, and name its source.
- Vector extraction matches the PDF linework exactly. Positions scaled from an older or raster sheet can be inches off. In one project, posts scaled from a 2016 sheet were about 6 in off.
- Mark which positions are measured on site and which are assumed.
