# Changelog

All notable changes to this skill. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [Semantic Versioning](https://semver.org/).

## Unreleased

### Added

- `sheets.set_paper(name)` and `PAPERS`: paper size is a parameter. Construction sheets default to US Tabloid (11 x 17 in) landscape at 200 dpi, 3400 x 2200 px. A3 stays available as `set_paper("a3")`.
- Imported from the untracked tree `-skills/blender-architectural-renders/` in the workspace root on 2026-10-17, without `__pycache__/` and `tests/out/`. The files match that tree (Revision 4).
- `reference/extensions.md`: install and per-run enabling of Bonsai and IfcOpenShell, Sun Position, and Point Cloud I/O, with an IFC recipe and a headless plan drawing; an Extensions section in SKILL.md (Revision 5).
- Tests: `bl_extensions` (operator names, a six-record IFC read back within 1e-6 m (T21; `write_walls_ifc` itself allows 3 mm), a headless plan SVG, Sun Position in a background run; skips when the extensions are not installed) and `test_extensions_doc`.
- `run_checks()`: one gate that a scene script calls after it sets the camera and before it renders. It runs six checks over the whole scene and exits 1 on any hit (Revision 6).
- New checks in `scripts/checks.py`: `flipped_check`, `wall_gap_check` (wall gaps, corners, and door-sized openings with no header or no floor), `floor_fit_check`, `camera_check` (faces seen from behind, sky in an interior view), and `clearance_check` (walking box over stair treads).
- `scripts/wall_gaps.py`: plain-Python `wall_gaps` and `wall_openings` for wall rectangles, usable on `load_plan` output.
- `coplanar_check` takes `skip` and reads mirrored objects with their real facing; it works on render-visible objects only.
- `EYE_HEIGHT` in `bhelpers.py` (5'-2 1/2", the eye of a 5'-7" viewer) and an optional `interior` key in perspective VIEWS entries.
- SKILL.md: Checks section rewritten for `run_checks`, with the output lines, limits, and exemption rules; six rules for every scene; loop steps 2 and 3; two QA items; Scripts table rows. `reference/api.md` lists the new functions; `reference/plan-input.md` runs `wall_gaps` on the corrected wall list.
- SKILL.md rules for stair steps (one box from riser to the next riser) and for `interior` in a script without a VIEWS table; `reference/plan-input.md` adds a header box over each door and stable wall names before an opening exemption (Revision 6).
- `scripts/ifc_walls.py`: `write_walls_ifc` writes the scene's wall records as an IFC4 file, reads it back, and sets NEW or EXISTING status from `kind`. `drawing_walls` and `check_drawing` compare a Bonsai plan drawing with the IFC (Revision 5b).
- `reference/extensions.md`: the Sun Position angles passed to `sun()`, with the `north_offset` sign; the LAS importer's `las_origin_offset` and the precision lost with `center_on_origin` off; the drawing check. SKILL.md: `ifc_walls.py` Scripts row, and IFC, sun, and LiDAR terms in the description. Tests: `test_ifc_walls`, `test_description`, and IFC, drawing, Sun Position, and point cloud steps in `bl_extensions` (Revision 5b).

### Fixed

- SKILL.md: Blender ships numpy.
- reference/plan-input.md: extraction misses short wall pieces at junctions; shift door swings with shifted walls.
- `lathe` recalculates its face normals, so a profile in either direction passes `flipped_check` (Revision 6).

### Changed

- `reference/extensions.md`: every run that enables an extension enables all three, and runs that enable extensions do not overlap, because Blender re-syncs the shared packages when the set changes (Revision 5b).
- `templates/scene_template.py` calls `run_checks` before the render, in place of the scoped `coplanar_check` call, and sets the eye-level camera at `EYE_HEIGHT / U` (Revision 6).
