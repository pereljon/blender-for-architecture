# Issues

State of the blender-architectural-renders skill: open bugs, planned work, next steps, open questions, and decisions. The skill-developer project's `docs/ISSUES.md` holds the migration.

## Bugs

- [ ] `wall_gaps` reports a thin gap that a column closes, because a thin region is not tested for fill (Revision 6 code review m4). Contract behaviour; an optional 1D subtraction would close it.

- [ ] No test checks the font `compose.py` loads. With `font()` returning `None`, Pillow falls back to its default font and the suite still passes 37 of 37 (import check, 2026-10-17). Cosmetic.

## Planned

- [x] Receive the design contract (`dev/features/`) and review inputs (`dev/inputs/`) from the development session (resolved 2026-10-17): moved in unedited; three stale paths fixed.
- [ ] Release and install v1.0.0 (skill-developer migration step 5).
- [ ] Revision 6, before Revision 5's remaining items and before release: catch phantom geometry defects (one check gate run before every render, five new checks, loop rules, default eye height). Source: `dev/inputs/2026-10-20-phantom-defects.md`. Design: contract, "Revision 6", revised after the architecture review (G1 to G13). Branch `rev6-phantom-checks`. Tests at `022f22d`, implementation at `352a14b`. Next: fix the code review findings (contract, "Code review findings"): tests first by one subagent, fixes by another, then a re-review, then docs D5 to D12.
- [ ] Revision 5, before release: test the DXF import and export extensions the doc names (install only with the user's consent; DWG is out of scope); write the IFC from the scene script's wall records; Sun Position mapped to `bhelpers.sun()` with a solar-noon test; description covers IFC, scan, and sun tasks, with a discovery eval and a negative case; drawing geometry check; keep-in-step for extension ids and `ifcopenshell.api` names; re-run the evals. Details: contract, "Revision 5 review findings".

## Next steps

- Import check (2026-10-17): suite 37 of 37 in this repo. With `set_units("ft")` broken to 0.3 in a copy of `scripts/`, 8 of 37 steps fail (`bl_helpers`, `bl_mannequin`, `bl_rev2`, `bl_rev3`).

## Open questions


## Decisions

- 2026-10-20, the user: take on Revision 6 as proposed (a `run_checks()` gate before every render, previews included; checks for wall gaps, camera rays, floor fit, clearance, and flipped faces; rules for `view_layer.update()`, exact-name skips, recessed emissive strips, and re-checks after level changes). It goes before Revision 5's remaining items, into v1.0.0. The default eye height is 5'-2 1/2" (a 5'-7" viewer). Rejected: separate checks for exposed slab sides (the coplanar check over the whole scene covers them) and for emissive faces (a rule and a QA item cover one occurrence); a Bonsai route for long-lived models (already in Revision 5).
- 2026-10-20, the user, on review finding G2: add an opening probe to `wall_gap_check`. For each door-sized gap (0.30 m to about 2.5 m) between in-line wall pieces, a ray up from the opening's middle reports a missing header when it first hits at the wall top or hits nothing, and a ray down checks that the floor runs through. Openings meant to run to the ceiling are exempted by exact name. Rejected: documenting a missing header or jamb built as a separate box as not caught.
- 2026-10-20, the user, on review finding G13: keep the user's name in the design text. Rejected: replacing it with "the user".
- 2026-10-20, the user, on the Revision 6 open questions: accept each recommendation. `exempt` takes exact names only (rejected: also accepting prefixes); fix `lathe` normals; add the dark-sill QA item; fold the coplanar mirrored fix into Revision 6; keep the 0.30 m hung limit; approve the revised test plan T16 to T20; send the wiring to the render project after v1.0.0; keep the floor-fit support test (rejected: exempting each supported object by name).
- 2026-10-20, the user, on the Revision 6 code review: fix C1, I1 to I4, m1, m2, m8, and m9 before merge; probe openings only where the lower wall top is at least 2.0 m (m3). Rejected: merging with the findings logged. m4 to m7 go to docs or Bugs.
