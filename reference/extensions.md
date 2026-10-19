# Blender extensions

Tested on Blender 5.2 LTS on macOS. Extension versions: Bonsai 0.9.0, IfcOpenShell 0.9.0.

In the commands below, `$BLENDER` is the full Blender path from SKILL.md Environment.

## Install and enable

- To see what is installed, run `"$BLENDER" -c extension list`. An installed extension shows `[installed]`.
- If it is not installed, install it from the command line: `"$BLENDER" -c extension install bonsai,sun_position,point_cloud_io`.
- If the install cannot find a package, run `"$BLENDER" -c extension sync` first.
- Install without `-e`. An enabled extension loads in every Blender session, including the user's own.
- Enable the extension per run, before the scene script:

```
"$BLENDER" --factory-startup -b --python-exit-code 1 \
  --python-expr "import addon_utils; addon_utils.enable('bl_ext.blender_org.bonsai', default_set=True)" \
  -P script.py -- args
```

- The module name is `bl_ext.blender_org.<id>`.
- Pass `default_set=True`. Without it, Bonsai fails with a KeyError when it reads its own preferences.

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

Use `ifcopenshell.api.run`, in this order:

1. `project.create_file` with `version="IFC4"`, then `root.create_entity` for the `IfcProject`.
2. `unit.assign_unit`. The default units are metres.
3. `context.add_context` for the Model context, then a `Body` subcontext with `target_view="MODEL_VIEW"`.
4. Create `IfcSite`, `IfcBuilding`, and `IfcBuildingStorey`, and nest them with `aggregate.assign_object`.
5. For each element: `root.create_entity`, `geometry.add_wall_representation`, `geometry.assign_representation`, `geometry.edit_object_placement`, and `spatial.assign_container`.

- Convert feet to metres (multiply by 0.3048) before you pass a length.
- Pass `is_si=True` to `geometry.edit_object_placement`.
- `add_wall_representation` draws the profile along local +x, with the thickness along local +y.
- For a wall that runs north-south, rotate the placement 90 degrees, and place it at the wall's east face.
- When a wall is given by its centreline, offset the placement by half its thickness.
- At a corner, run the east-west walls the full outer length. Run the north-south walls between their inside faces, so no two walls overlap.
- The thickness then runs west from the placement.
- Use `add_wall_representation` for posts and beams too, as a box.
- After you write the file, compare each element's world bounding box with the source.
- Use `ifcopenshell.geom.create_shape` with the `use-world-coords` setting.
- The shape's vertices are in metres. Divide by 0.3048 before you compare them with feet.
- Expect no difference over 0.01 ft.

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

Not yet verified headless: doors and windows in openings, dimensions and labels, sheets, and rendering an IFC scene with project materials.

## Sun Position

- Use Sun Position to set the sun from the site, date, and time, instead of a hand-placed sun.
- Set the values on `scene.sun_pos_properties`.
- The fields are `latitude`, `longitude`, `UTC_zone`, `use_daylight_savings`, `year`, `month`, `day`, `time`, `north_offset`, and `sun_object`.
- Keep one fixed date and time for every render in a project.
- In a background run, the sun object turns as soon as you set the time.

## Point Cloud I/O

- Use Point Cloud I/O to bring a LiDAR scan into the scene and check walls, slabs, and grades against the model.
- Import a LAS file with `bpy.ops.import_scene.point_cloud_las(filepath=...)`.
- The other importers are `bpy.ops.import_scene.point_cloud_e57`, `bpy.ops.import_scene.point_cloud_ply`, `bpy.ops.import_scene.point_cloud_pcd`, `bpy.ops.import_scene.point_cloud_pts`, and `bpy.ops.import_scene.point_cloud_xyz`.
- The LAS importer takes `import_colors`, `import_intensity`, `import_classification`, `center_on_origin`, `scale_factor`, and `point_radius`.
- Phone scans (Scaniverse) come in metres, in UTM coordinates, each with its own heading and height datum.
- Rotate and offset each scan onto the model before you compare.
- For flat slices and measured profiles, use laspy outside Blender: `uvx --with laspy --with numpy`.

Not yet verified: a full import of a project scan.

## DXF

DXF extensions are not installed by default. Install one only when a project exchanges DXF.

- To import an architect's DXF with layers, units, and blocks, install `cad2cube`.
- To export Blender geometry as DXF R12, install `export_autocad_dxf_format_dxf`.
- To send drawings as DXF, prefer writing them with ezdxf from Python: `uvx --with ezdxf`.
- ezdxf writes layers, text, and dimensions.
- No extension reads DWG. Ask the architect for a DXF. When no CAD file is shared, use the PDF extraction in [plan-input.md](plan-input.md).
