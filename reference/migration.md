# Migration

How to upgrade a script's pinned lib version, and how to move a project's own helpers onto the lib. SKILL.md ("Project lib") holds the pin rules that run every session. This file holds the longer procedures, which are rare. The skill folder is the folder that holds SKILL.md. The owner and the user are defined in SKILL.md.

## Before you start

1. Make the current state restorable before any change.
   - In a project under git, work on a branch. Commit each version folder, and ignore `__pycache__/`.
   - In a project without git, copy the Blender folder to a dated backup beside it. Or ask the owner to put the project in a repo.
2. Without history, the backup is the only record of which version made a delivered render. Keep it.
3. Keep these as they are. A change to any of them is the owner's decision.
   - Flag defaults, which are owner decisions.
   - Cameras, including each view's own eye height.
   - Units and the height datum.
   - A fixed sun. Do not switch it to Sun Position.
   - The page size and pixel size of sheets.
   - Any output whose IDs a third party holds, such as tile piece IDs and packing results. A change to a held ID is a reissue.

## Geometry dump

The geometry dump is a JSON file that describes every object in the built scene. Two dumps compare with a plain diff. Geometry decides whether a swap or an upgrade changed the model, so the dumps must be equal.

Each entry is keyed by object name and holds four fields:
- `type`: the object type.
- `vertices`: the vertex count of the evaluated mesh, or 0 for other types.
- `box`: the world bounding box of the evaluated object, rounded to 1e-6 m.
- `materials`: the material names of the object's slots.

```python
import json
import bpy


def dump_geometry(path):
    """Write one entry per object: type, evaluated vertex count, world box, slot material names."""
    deps = bpy.context.evaluated_depsgraph_get()
    out = {}
    for ob in bpy.data.objects:
        ev = ob.evaluated_get(deps)
        n = 0
        if ob.type == "MESH":
            me = ev.to_mesh()
            n = len(me.vertices)
            ev.to_mesh_clear()
        m = ev.matrix_world
        pts = [[m[r][0] * c[0] + m[r][1] * c[1] + m[r][2] * c[2] + m[r][3] for r in range(3)] for c in ev.bound_box]
        box = [round(f(p[i] for p in pts), 6) for f in (min, max) for i in range(3)]
        out[ob.name] = {"type": ob.type, "vertices": n, "box": box,
                        "materials": [s.material.name if s.material else None for s in ob.material_slots]}
    with open(path, "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
```

Add a `--dump PATH` flag to the scene script, as `--export-pieces` works. With the flag, the script does these steps:
1. Build the scene.
2. Call `dump_geometry(PATH)`.
3. Print `DONE <PATH>`.
4. Skip the camera, the checks, and the render.

The dump does not see material settings, light energy, or the world. A swap that changes a material's values but not its name passes the dump. The pixel review below finds it.

## Upgrade a pin

Use this when the installed skill is newer than a script's `LIB`.

1. Offer the upgrade for every script on an older pin. The user names the scripts to hold back.
2. For each script to upgrade, render one delivered view and write its geometry dump into `scratch/baseline/`. Use the current pin.
3. Copy the installed version's folder into `blender/lib/` if it is missing.
4. Change the pins. Fix the calls that the CHANGELOG lists as changed.
5. Compare each upgraded script's dump and view with its baseline (see "Compare and decide").

A project with the old flat `blender/lib/` moves it to `blender/lib/pre-1.0/` in the same change. Give every script that had no `LIB` a pin in that change, with the two lines from SKILL.md ("Project lib"). Set `LIB` to the new version. Or, when the user holds the script back, set `LIB = "pre-1.0"` with a `# held:` comment. Without a pin, a held script loses its imports.

## Move a project's own helpers onto the lib

Use this for a project that built its scene with its own functions, such as a single long script.

1. Write the baseline first.
   - Write the geometry dump from the current code.
   - Render each delivered view at one small fixed setting, for example `--res 800 --samples 48` on CPU.
   - Regenerate each sheet into `scratch/baseline/`.
   - Use the delivered images only to confirm camera and framing. They can predate later model changes.
2. Set up the version folder and the pins (SKILL.md, "Project lib").
3. Replace a project helper with a lib import only when its signature matches. The dump after the swap must equal the baseline dump.
4. Replace one helper group at a time, and compare after each.
5. Keep these in the project:
   - Every helper that reads project constants instead of taking parameters.
   - Every project-specific builder, material, pass, tile pipeline, and sheet layout.
6. For a command-line tool that the project forked (`compose.py`, `annotate_plan.py`, `extract_plan.py`), diff the fork against the lib's copy first. Switch only when every option the project's commands use exists with the same meaning, and the output matches.
7. Keep the project's own sheet basics unless `set_paper` reproduces its page pixels and its pixels per mm exactly. For example, `set_paper("a3")` gives 3307 x 2339 px at 200 dpi. A kit that draws A3 at 3300 x 2340 px keeps its own page.
8. A script run with `python -I` does not see its own folder. If the script imports a sibling module, it inserts its own folder on `sys.path`.

## Wire the checks

Do this as a separate step, after the helper swap compares clean.

1. Rename walls named by list index (`wall_27`) to stable names.
2. Add `run_checks` as SKILL.md ("Checks") says. Call it right before the render call, with `unit` set to metres per project unit.
3. Expect many hits on a large existing model. Take them check by check.
   - Fix a real defect.
   - Exempt an intended one by its exact name, with the reason in a comment.
   - Never exempt by prefix to clear a long list.
4. List each view that a fix changes, for the owner.

## Compare and decide

Pixels guide the owner's review. This script finds the changed regions of two renders. Save it as `scratch/diff.py`.

```python
import sys
from PIL import Image, ImageChops

a, b = (Image.open(p).convert("RGB") for p in sys.argv[1:3])
diff = ImageChops.difference(a, b).point(lambda v: v if v > 8 else 0)
print(diff.getbbox())
```

It ignores channel differences of 8 levels or less, which are render noise. That value is a starting point, not a measured one.

1. Compare geometry first. The dumps must be equal.
2. Render each view at the baseline setting. Run `uvx --with pillow python -I scratch/diff.py A.png B.png` on each pair. A printed `None` means no visible change.
3. Regenerate each sheet into `scratch/`. Compare it with its baseline sheet by `ImageChops.difference(a, b).getbbox()`, with no tolerance. Sheets are drawn without noise.
4. Never write over a delivered issue.
5. Show the owner every view or sheet that differs, side by side on a study page. The owner decides.
6. Keep the pin of a script that the owner holds back. Add a `# held: <reason>` comment to its `LIB` line.
