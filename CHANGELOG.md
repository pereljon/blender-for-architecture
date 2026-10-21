# Changelog

All notable changes to this skill. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [Semantic Versioning](https://semver.org/).

Conventions, kept from v1.1.0 on:
- Each release heading is `## [X.Y.Z] - YYYY-MM-DD`, newest first. The release retitles `## Unreleased`, which sits above them.
- Name each public function whose signature or behaviour changed, or that was added or removed, as `module.function()`. Put it under Changed, Fixed, Added, or Removed.
- The skill reads the installed version from the first numbered heading.

## Unreleased

### Changed

- `bhelpers.setup_cycles()`: with `gpu=True` it tries each backend in `bhelpers.GPU_BACKENDS` in order, and uses every device of the first backend that has one. The order is Metal on macOS, else OptiX, CUDA, then HIP. With no device it prints one line, `WARN no GPU device found (tried ...), rendering on CPU`, and renders on CPU. The old code tried only Metal.
- `templates/scene_template.py`: defines `LIB = "v1.1.0"` and imports the lib from `lib/<LIB>/`; sets the eye-level camera at `EYE`, from the new `VIEWER` line; the run line uses `$BLENDER`.
- `bhelpers.EYE_HEIGHT` stays at 1.5875 m, for scripts pinned before v1.1.0. New scripts use `bhelpers.eye_height()`.
- Usage lines of `compose.py`, `annotate_plan.py`, `extract_plan.py`, and `sheets.py` name `blender/lib/<LIB>/`.
- The install ships `CHANGELOG.md`, which is how a session reads the installed version.
- SKILL.md: a Project lib section pins each script to one skill version in `blender/lib/<LIB>/`, with a pin check each session. `$BLENDER` has one definition and a table of paths and GPU backends for macOS, Linux, and Windows (only macOS is tested). The Blender folder, the notes files, and the delivery folder have plain defaults, and `context/` and `deliverables/` are optional. Git rules are gone. Checks run in the order run, read the output, exemptions, setup, limits.
- Docs restructure: the owner and the user are defined; "figure" and "scene script" are the only terms; each repeated fact has one home; `reference/api.md` has a signature line and a description line per entry; history notes are in the present tense or in `docs/ISSUES.md`; examples are neutral; poché, kerf, guillotine cut, pole, and piece ID are defined where they first appear.
- `reference/extensions.md`: the scan note is a general check of a scan's length unit, coordinate system, and height datum.

### Added

- `bhelpers.eye_height()`: the eye height of a viewer of a given height, in project units. The default viewer is 5'-7".
- `bhelpers.GPU_BACKENDS`: the backends that `setup_cycles` tries.
- `reference/migration.md`: the geometry dump (`dump_geometry`), the pin upgrade, moving a project's own helpers onto the lib, wiring the checks, and the comparison steps.
- `reference/extensions.md`: how a scene script exposes its corrected wall list and runs an IFC-only pass (`--ifc PATH`).

### Fixed

- `reference/api.md`: `load_plan` returns the tuple `(walls, doors, leaves)`; `EXAMPLE_POSE` and `FONTS` no longer show cut-off values; `Sheet` and `Draw` list each method's signature; `floor_fit_check` defines the hang limit (0.3 m); `cut_openings` says its `min_piece` is an argument, separate from the config list.
- `reference/studies.md`: `sun` shows its real parameter names; the study-page example path is neutral.
- `reference/views.md`: the usual plan cut is stated as 1.2 m or 5 ft, not as equal values.
- `reference/plan-input.md`: each `sheets` entry needs `page`, `region`, and `out`; the config `min_piece` list is distinguished from the `cut_openings` argument.
- `SKILL.md`: the Point Cloud I/O format list matches `reference/extensions.md` (no LAZ); "hit", "walking box", and "hang limit" are defined where they first appear; the `paths` instruction is split into two sentences.

## [1.0.0] - 2026-10-21

### Changed

- Renamed from `blender-architectural-renders` to `blender-for-architecture`.

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
