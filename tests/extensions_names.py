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
