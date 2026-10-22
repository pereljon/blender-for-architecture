# Scripts

How to run each script, and its command-line flags. Function signatures are in [api.md](api.md). SKILL.md ("Environment") holds the `$BLENDER` rules.

## Two ways to run

- Inside Blender: `"$BLENDER" --factory-startup -b --python-exit-code 1 -P script.py -- FLAGS` (SKILL.md, "Environment").
- Plain Python, from the project folder: `uvx --with PACKAGES python -I blender/lib/<LIB>/SCRIPT.py ARGS`.

`python -I` leaves the script's own folder off `sys.path`. A project script that imports a lib module inserts the lib folder itself, as a scene script's two `LIB` lines do.

## templates/scene_template.py

Runs in Blender. Command line:

```
"$BLENDER" --factory-startup -b --python-exit-code 1 -P blender/build_<scene>.py -- --view persp --res 800 --samples 48 --gpu --out out/persp.png
```

| Flag | Meaning |
|---|---|
| `--view NAME` | A key of `VIEWS`. Default `persp`. |
| `--res N` | Image width in pixels; the height is the width times the view's aspect. Default 800. |
| `--samples N` | Cycles samples. Default 48. |
| `--gpu` | Render on the system's GPU backend (SKILL.md, "Environment"). Default CPU. |
| `--out PATH` | Output image path. Default `out/<view>.png`. |
| `--option a` or `b` | The study option. Default `a`. A project names its own option flags and sets each owner choice as the default. |
| `--export-pieces PATH` | Build, write the tile pieces JSON, print `DONE <PATH>`, and skip the checks and the render. |

Flags a project adds:

- `--dump PATH` ([migration.md](migration.md), "Geometry dump")
- `--ifc PATH` ([extensions.md](extensions.md), "Write an IFC")

Output: `DONE <path>` when the render is written. Exit 1 on a failed check or a script error.

## bhelpers.py

Imported by a scene script inside Blender. No command line.

## checks.py

Imported by a scene script inside Blender. No command line.

## sheets.py

Imported by a project's sheet generator, run with `uvx --with pillow python -I`. Run directly, it prints a packing self-test line (`PACK ...`).

## extract_plan.py

```
uvx --with pymupdf python -I blender/lib/<LIB>/extract_plan.py CONFIG.json
```

No flags. The config's paths are relative to the config file, and each sheet's JSON goes to its `out`. Config keys: `plan_config.example.json` and [plan-input.md](plan-input.md).

## compose.py

```
uvx --with pillow python -I blender/lib/<LIB>/compose.py OUT.jpg [--title=TEXT] [--width=PX] ITEM ...
```

- `--title=TEXT` sets the page title.
- `--width=PX` sets the page width. Without it, the page is 1000 px per cell of the widest row, plus gaps.
- Each item is `Label=path.png`, `Label=-` (blank cell), `|` (end of row), or `#Heading`. Each row scales so its cells share the page width.

## annotate_plan.py

```
uvx --with pillow python -I blender/lib/<LIB>/annotate_plan.py IN.png OUT.png CALLOUTS.json
```

No flags. CALLOUTS.json is `{"center": [x, y], "width": w, "callouts": [{"x", "y", "label", "above", "r"}]}`. The default ring radius is in pixels. `r` is in project units.

## ifc_walls.py

Imported, in a Blender run that enables the extensions ([extensions.md](extensions.md)), or in plain Python with `uvx --with ifcopenshell --with numpy python -I script.py`. No command line.

## mannequin.py

Imported by a scene script inside Blender. No command line.

## wall_gaps.py

Imported, in Blender or plain Python, with no packages. No command line.
