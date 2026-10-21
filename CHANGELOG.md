# Changelog

All notable changes to this skill. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [Semantic Versioning](https://semver.org/).

## Unreleased

### Added

- Imported from the untracked tree `-skills/blender-architectural-renders/` in the workspace root on 2026-10-17, without `__pycache__/` and `tests/out/`. The files match that tree (Revision 4).
- `reference/extensions.md`: install and per-run enabling of Bonsai and IfcOpenShell, Sun Position, Point Cloud I/O, and DXF tools, with an IFC recipe and a headless plan drawing; an Extensions section in SKILL.md (Revision 5).
- Tests: `bl_extensions` (operator names, a two-wall IFC within 0.01 ft, a headless plan SVG, Sun Position in a background run; skips when the extensions are not installed) and `test_extensions_doc`.
- `run_checks()`: one gate that a scene script calls after it sets the camera and before it renders. It runs six checks over the whole scene and exits 1 on any hit (Revision 6).
- New checks in `scripts/checks.py`: `flipped_check`, `wall_gap_check` (wall gaps, corners, and door-sized openings with no header or no floor), `floor_fit_check`, `camera_check` (faces seen from behind, sky in an interior view), and `clearance_check` (walking box over stair treads).
- `scripts/wall_gaps.py`: plain-Python `wall_gaps` and `wall_openings` for wall rectangles, usable on `load_plan` output.
- `coplanar_check` takes `skip` and reads mirrored objects with their real facing; it works on render-visible objects only.
- `EYE_HEIGHT` in `bhelpers.py` (5'-2 1/2", the eye of a 5'-7" viewer) and an optional `interior` key in perspective VIEWS entries.
- SKILL.md: Checks section rewritten for `run_checks`, with the output lines, limits, and exemption rules; six rules for every scene; loop steps 2 and 3; two QA items; Scripts table rows. `reference/api.md` lists the new functions; `reference/plan-input.md` runs `wall_gaps` on the corrected wall list.
- SKILL.md rules for stair steps (one box from riser to the next riser) and for `interior` in a script without a VIEWS table; `reference/plan-input.md` adds a header box over each door and stable wall names before an opening exemption (Revision 6).

### Fixed

- SKILL.md: Blender ships numpy.
- reference/plan-input.md: extraction misses short wall pieces at junctions; shift door swings with shifted walls.
- `lathe` recalculates its face normals, so a profile in either direction passes `flipped_check` (Revision 6).

### Changed

- `templates/scene_template.py` calls `run_checks` before the render, in place of the scoped `coplanar_check` call, and sets the eye-level camera at `EYE_HEIGHT / U` (Revision 6).
