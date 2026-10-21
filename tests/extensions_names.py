"""Names that reference/extensions.md must cover; shared by bl_extensions.py and test_extensions_doc.py."""
OPS = [
    "bim.load_project", "bim.load_drawings", "bim.add_drawing", "bim.activate_drawing",
    "bim.create_drawing", "bim.save_project",
    "import_scene.point_cloud_las", "import_scene.point_cloud_e57", "import_scene.point_cloud_ply",
    "import_scene.point_cloud_pcd", "import_scene.point_cloud_pts", "import_scene.point_cloud_xyz",
]
SUN_FIELDS = ["latitude", "longitude", "UTC_zone", "use_daylight_savings", "year", "month", "day",
              "time", "north_offset", "sun_object"]
LAS_ARGS = ["import_colors", "import_intensity", "import_classification", "center_on_origin",
            "scale_factor", "point_radius"]
EXTENSIONS = ["bonsai", "sun_position", "point_cloud_io"]


def _api_names():
    """The ifcopenshell.api names scripts/ifc_walls.py calls as run("module.function", ...); empty when the file is absent."""
    import ast
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(os.environ.get("SCRIPTS_DIR") or os.path.join(here, "..", "scripts"), "ifc_walls.py")
    if not os.path.isfile(path):
        return []
    names = set()
    for n in ast.walk(ast.parse(open(path).read())):
        if not isinstance(n, ast.Call) or not n.args:
            continue
        fn = n.func
        called = fn.id if isinstance(fn, ast.Name) else fn.attr if isinstance(fn, ast.Attribute) else None
        a = n.args[0]
        if called == "run" and isinstance(a, ast.Constant) and isinstance(a.value, str) and a.value.count(".") == 1:
            names.add(a.value)
    return sorted(names)


API_NAMES = _api_names()
