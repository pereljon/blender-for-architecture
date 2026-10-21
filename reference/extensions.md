# Blender extensions

Tested on Blender 5.2 LTS on macOS. Extension versions: Bonsai 0.9.0, IfcOpenShell 0.9.0.

In the commands below, `$BLENDER` is the full Blender path from SKILL.md Environment.

## Install and enable

- To see what is installed, run `"$BLENDER" -c extension list`. An installed extension shows `[installed]`.
- Before you install or sync anything, ask the user. Name each extension and its download size; Bonsai is about 140 MB.
- After the user agrees, install from the command line: `"$BLENDER" -c extension install bonsai,sun_position,point_cloud_io`.
- If the install cannot find a package, run `"$BLENDER" -c extension sync` first.
- Install without `-e`. An enabled extension loads in every Blender session, including the user's own.
- Enable the extensions per run, before the scene script:

```
"$BLENDER" --factory-startup -b --python-exit-code 1 \
  --python-expr "import addon_utils; assert all(addon_utils.enable('bl_ext.blender_org.' + x, default_set=True) for x in ('bonsai', 'sun_position', 'point_cloud_io'))" \
  -P script.py -- args
```

- The module name is `bl_ext.blender_org.<id>`.
- Pass `default_set=True`. Without it, Bonsai fails with a KeyError when it reads its own preferences.
- Keep the `assert`. A failed enable only prints an error, and the scene script would run without the extension.
- A per-run enable does not change the saved preferences. Bonsai still adds each IFC it opens to its recent-projects list.
- Enable the same three extensions in every run that enables any. Blender re-syncs their shared packages whenever the set changes.
- Do not run two Blender runs that enable extensions at the same time. A re-sync can remove the other run's packages.

## Bonsai and IfcOpenShell

IfcOpenShell is the library that reads and writes IFC files. Bonsai is the Blender add-on built on it. Bonsai adds IFC inside Blender, drawings, and sheets.

### When to use them

- Use IFC when the drawings must stay consistent with the model.
- In IFC, a door or window sits in an opening of its wall and moves with the wall.
- Use IFC when an architect or engineer needs a model file. Revit and ArchiCAD import IFC.
- Keep furniture, finishes, site, and lighting in the scene script.

### Choose the tool

- To write or check an IFC from measurements, use IfcOpenShell alone.
- IfcOpenShell runs outside Blender: `uvx --with ifcopenshell --with numpy python -I script.py`. The placement API needs numpy.
- To render an IFC or to generate plans and sections, use Bonsai.
- Inside Blender, `import ifcopenshell` works only after Bonsai is enabled.

### Write an IFC

Write the IFC from the scene script's own wall list, after the correction passes. Never retype the coordinates.

```python
from ifc_walls import write_walls_ifc
ids = write_walls_ifc(walls, "out/walls.ifc", 0.0, CEIL, unit=bh.U)
```

- Run it in a Blender run that enables the extensions, or through `uvx --with ifcopenshell --with numpy python -I`.
- Pass the same `walls` list that `walls_from_plan` gets. The IFC names match the scene's box names.
- Pass `z0` and `z1` in the records' units. `unit` converts them to metres with the other lengths.
- Give each record a `kind` of `new` or `existing`. The IFC then carries it as the element's status.
- For a post or a beam, add a record with its own `z0`, `z1`, and `ifc_class`, such as `IfcColumn`.
- `write_walls_ifc` reads the file back and raises an error when an element differs from its record by over 3 mm.
- For other elements, read `scripts/ifc_walls.py` as the recipe.

### Generate a drawing headless

```python
bpy.ops.bim.load_project(filepath=ifc)
import bonsai.tool as tool
f = tool.Ifc.get()
dp = bpy.context.scene.DocProperties
bpy.ops.bim.load_drawings()
dp.target_view = "PLAN_VIEW"
dp.location_hint = str(f.by_type("IfcBuildingStorey")[0].id())
bpy.ops.bim.add_drawing()
dwg = [a for a in f.by_type("IfcAnnotation") if a.ObjectType == "DRAWING"][0]
bpy.ops.bim.activate_drawing(drawing=dwg.id())
bpy.ops.bim.create_drawing()
bpy.ops.bim.save_project(filepath=ifc)
```

- The SVG is written to `drawings/` beside the IFC, named after the storey and view (for example `LEVEL 1 PLAN.svg`).
- In Bonsai 0.9, `bpy.ops.bim.add_drawing` takes no arguments. Set the view and the storey on `DocProperties` first.
- To review an SVG, rasterise it with PyMuPDF (`pymupdf.open(svg)`).
- PyMuPDF ignores the SVG's CSS, so line weights and fills do not show.
- The model origin sits at the sheet centre, so the plan fills only part of the sheet. Crop the raster to the drawn area before you review it.
- After you create the drawing, run `check_drawing(svg, ifc)` from `ifc_walls`. It must return `[]`.
- Run `check_drawing` the same way as `write_walls_ifc`.
- A `missing` item names an element that the drawing does not show. Check the cut height and the storey.
- An `extra` item names an outline with no element in the IFC. Generate the drawing again from the current IFC.
- An `off` item names the walls of one outline whose extent is more than 3 mm off.
- Bonsai joins touching walls of one class, material, and status into one outline. The check compares each joined outline as a whole.
- Review the image only for appearance. The check covers the geometry.

Not yet verified headless: doors and windows in openings, dimensions and labels, sheets, and rendering an IFC scene with project materials.

## Sun Position

- Use Sun Position to get the sun's angles for the site, date, and time. Then build the sun with `sun()`.

```python
p = bpy.context.scene.sun_pos_properties
p.latitude, p.longitude, p.UTC_zone = 37.77, -122.42, -8
p.use_daylight_savings = True
p.year, p.month, p.day, p.time = 2026, 6, 21, 15.5
sun(math.degrees(p.sun_elevation), math.degrees(p.sun_azimuth), plan_north_deg=PLAN_NORTH)
```

- The fields are `latitude`, `longitude`, `UTC_zone`, `use_daylight_savings`, `year`, `month`, `day`, `time`, `north_offset`, and `sun_object`.
- Set `UTC_zone` to the site's standard-time offset.
- If the date falls in daylight saving time, set `use_daylight_savings`.
- `sun_elevation` and `sun_azimuth` are in radians. Convert them to degrees for `sun()`.
- If you let Sun Position turn a sun object instead, set `north_offset` to `-math.radians(PLAN_NORTH)`. It is in radians. In a background run, the sun object turns as soon as you set the time.
- Keep one fixed date and time for every render in a project. Record the angles in the dimensions file.

## Point Cloud I/O

- Use Point Cloud I/O to bring a LiDAR scan into the scene and check walls, slabs, and grades against the model.
- Import a LAS file with `bpy.ops.import_scene.point_cloud_las(filepath=...)`.
- The other importers are `bpy.ops.import_scene.point_cloud_e57`, `bpy.ops.import_scene.point_cloud_ply`, `bpy.ops.import_scene.point_cloud_pcd`, `bpy.ops.import_scene.point_cloud_pts`, and `bpy.ops.import_scene.point_cloud_xyz`.
- The LAS importer takes `import_colors`, `import_intensity`, `import_classification`, `center_on_origin`, `scale_factor`, and `point_radius`.
- Phone scans (Scaniverse) come in metres, in UTM coordinates, each with its own heading and height datum.
- Leave `center_on_origin` on for scans in UTM coordinates. The importer then moves the points to the origin, and the object's `location` stays (0, 0, 0).
- The importer keeps the offset in the object's custom property `las_origin_offset`, three floats. It is the bounding-box minimum of the points, not the LAS header offset.
- To get a point's scan coordinates, add `las_origin_offset` to its position. In the test scan, the worst error after adding it back was 1.2e-7 m.
- With `center_on_origin` off, the points keep their UTM coordinates and Blender stores them as 32-bit floats. They lose millimetre precision. In the test scan, at easting 551234, the worst error was 0.125 m.
- The scan is a `POINTCLOUD` object. Read its positions from `obj.data.attributes["position"]`.
- Record each scan's `las_origin_offset` before you align scans with each other.
- Rotate and offset each scan onto the model before you compare.
- For flat slices and measured profiles, use laspy outside Blender: `uvx --with laspy --with numpy`.
